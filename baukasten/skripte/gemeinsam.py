"""Gemeinsame Grundlage aller Skripte des Lernpfad-Baukastens: Kurs laden, Pfade, kleine Helfer.

Ein Lernpfad ist ein Ordner:
    kurs.yaml            Titel, Stufen (mit Modul-Reihenfolge), Varianten, Selbstcheck, Moodle-Einstellungen
    module/<id>.md       ein Modul: YAML-Kopf (Titel, Lernziele, Kurz-Check, Abgabe …) + Text mit Bausteinen
    seiten/<name>.md     Zusatzseiten (Spickzettel, Hinweise für Lehrkräfte …) – optional
    medien.yaml          Videos und Hilfeseiten (optional)
    quellen.yaml         Quellen mit Prüfstatus (optional, empfohlen)
    fragen/*.yaml        Fragen für Moodle-Tests (optional)
    material/            Bilder, Screenshots, Übungsdateien
    ausgabe/             wird erzeugt (nicht von Hand ändern)
"""
import re
import sys
import unicodedata
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("Es fehlt das Python-Paket „pyyaml“. Installieren mit:  pip install pyyaml markdown-it-py mdit-py-plugins")

SKILL = Path(__file__).resolve().parents[1]
VORLAGE = SKILL / "vorlage"
REVIEW = ("entwurf", "geprueft", "freigegeben")


class Fehler(Exception):
    """Inhaltsfehler, die das Bauen verhindern (mit verständlicher Meldung)."""


def slug(text):
    t = unicodedata.normalize("NFKD", str(text).lower())
    t = t.replace("ß", "ss")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:48] or "seite"


def lies_md(datei):
    """Markdown mit YAML-Kopf (--- … ---) → (kopf: dict, text: str)."""
    s = Path(datei).read_text(encoding="utf-8").replace("\r\n", "\n")
    if s.startswith("---\n"):
        ende = s.find("\n---", 4)
        if ende < 0:
            raise Fehler(f"{datei}: YAML-Kopf ohne abschließendes ---")
        try:
            kopf = yaml.safe_load(s[4:ende]) or {}
        except yaml.YAMLError as e:
            raise Fehler(f"{datei}: YAML-Kopf fehlerhaft – {e}")
        return kopf, s[ende + 4:].lstrip("\n")
    return {}, s


def lies_yaml(datei, standard=None):
    p = Path(datei)
    if not p.exists():
        return standard
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or standard
    except yaml.YAMLError as e:
        raise Fehler(f"{p.name}: YAML fehlerhaft – {e}")


class Kurs:
    """Der ganze Lernpfad, geladen aus seinem Ordner."""

    def __init__(self, ordner):
        self.ordner = Path(ordner).resolve()
        k = lies_yaml(self.ordner / "kurs.yaml")
        if not k:
            raise Fehler(f"Keine kurs.yaml in {self.ordner} gefunden.")
        self.k = k
        self.titel = k.get("titel", "Lernpfad")
        self.kurzname = k.get("kurzname") or slug(self.titel)
        self.stufen = k.get("stufen") or []
        self.module = {}      # id → dict(kopf…, text, datei, stufe)
        self.reihenfolge = []  # Modul-IDs in Pfad-Reihenfolge
        for st in self.stufen:
            for mid in st.get("module") or []:
                datei = self.ordner / "module" / f"{mid}.md"
                if not datei.exists():
                    raise Fehler(f"Modul „{mid}“ aus Stufe „{st.get('id')}“: Datei module/{mid}.md fehlt.")
                kopf, text = lies_md(datei)
                kopf.setdefault("id", mid)
                if kopf["id"] != mid:
                    raise Fehler(f"module/{mid}.md: id im Kopf („{kopf['id']}“) passt nicht zum Dateinamen.")
                kopf["text"] = text
                kopf["quelle"] = datei
                kopf["stufe"] = st["id"]
                kopf.setdefault("titel", mid)
                kopf.setdefault("review", "entwurf")
                kopf["datei"] = kopf.get("datei") or f"{mid}-{slug(kopf['titel'])}.html"
                self.module[mid] = kopf
                self.reihenfolge.append(mid)
        self.seiten = []
        for datei in sorted((self.ordner / "seiten").glob("*.md")):
            kopf, text = lies_md(datei)
            kopf["text"] = text
            kopf["quelle"] = datei
            kopf.setdefault("titel", datei.stem)
            kopf["datei"] = kopf.get("datei") or f"{slug(datei.stem)}.html"
            self.seiten.append(kopf)
        self.seiten.sort(key=lambda s: s.get("reihenfolge", 99))
        self.medien = lies_yaml(self.ordner / "medien.yaml", {}) or {}
        self.quellen = lies_yaml(self.ordner / "quellen.yaml", []) or []
        self.moodle = k.get("moodle") or {}

    # -- Abkürzungen
    def stufe(self, sid):
        return next(s for s in self.stufen if s["id"] == sid)

    def module_der_stufe(self, sid):
        return [self.module[m] for m in self.stufe(sid).get("module") or []]

    def freigegeben(self, mid):
        return self.module[mid].get("review") == "freigegeben"

    def einstufung_aktiv(self):
        return (self.moodle.get("freischaltung", "einstufung") == "einstufung") and len(self.stufen) > 1

    def einstufung_datei(self, sid):
        return f"einstufung-{slug(sid)}.html"

    @property
    def ausgabe(self):
        return self.ordner / "ausgabe"


def lade_klausur_modul():
    """Das Modul klausur.py des Klausur-Baukastens (Schwester-Skill) – für `tests: - klausur: <ordner>` in kurs.yaml."""
    try:
        import klausur
        return klausur
    except ImportError:
        pass
    for k in (SKILL / "klausur-baukasten" / "skripte", Path.home() / ".claude" / "skills" / "klausur-baukasten" / "skripte"):
        if (k / "klausur.py").exists():
            sys.path.insert(0, str(k))
            import klausur
            return klausur
    raise Fehler("Für „klausur:“ in tests: fehlt der Klausur-Baukasten (Ordner klausur-baukasten/ im Repo bzw. "
                 "~/.claude/skills/klausur-baukasten).")


def kurs_aus_argumenten(argv=None, beschreibung=""):
    """Ordner des Lernpfads aus der Kommandozeile (Standard: aktueller Ordner)."""
    import argparse
    ap = argparse.ArgumentParser(description=beschreibung)
    ap.add_argument("ordner", nargs="?", default=".", help="Ordner des Lernpfads (mit kurs.yaml)")
    return ap


def melde_fehler_und_ende(e):
    print(f"\n✗ {e}", file=sys.stderr)
    sys.exit(1)
