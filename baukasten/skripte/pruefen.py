#!/usr/bin/env python3
"""Prüft einen Lernpfad-Ordner, bevor gebaut wird.

    python3 pruefen.py [ordner]

Fehler (✗) verhindern das Bauen, Hinweise (!) sollte man sich ansehen. Die Meldungen nennen Datei und Stelle.
"""
import re
import sys
from pathlib import Path

from bausteine import unbekannte_bausteine, werkzeug_config, werkzeuge_im_text
from gemeinsam import REVIEW, VORLAGE, Fehler, Kurs, kurs_aus_argumenten, lade_klausur_modul, lies_yaml

FRAGETYPEN = {"single_choice", "multiple_choice", "zuordnung", "reihenfolge", "lueckentext", "zahl", "offen"}


class Pruefer:
    def __init__(self, kurs):
        self.k = kurs
        self.fehler, self.hinweise = [], []

    def f(self, wo, text):
        self.fehler.append(f"{wo}: {text}")

    def h(self, wo, text):
        self.hinweise.append(f"{wo}: {text}")

    # ---------- kurs.yaml
    def kursdatei(self):
        k, wo = self.k.k, "kurs.yaml"
        if not k.get("titel"):
            self.f(wo, "„titel“ fehlt")
        if not re.fullmatch(r"[a-z0-9-]+", self.k.kurzname):
            self.f(wo, f"„kurzname“ nur aus Kleinbuchstaben, Ziffern und Bindestrichen (ist: {self.k.kurzname})")
        if not self.k.stufen:
            self.f(wo, "keine „stufen“ angegeben")
        ids = [s.get("id") for s in self.k.stufen]
        for s in self.k.stufen:
            for feld in ("id", "name", "module"):
                if not s.get(feld):
                    self.f(wo, f"Stufe {s.get('id', '?')}: „{feld}“ fehlt")
            if s.get("id") and not re.fullmatch(r"[a-z][a-z0-9-]*", s["id"]):
                self.f(wo, f"Stufen-ID „{s['id']}“: nur Kleinbuchstaben, Ziffern, Bindestrich")
        if len(ids) != len(set(ids)):
            self.f(wo, "Stufen-IDs doppelt")
        alle = [m for s in self.k.stufen for m in (s.get("module") or [])]
        doppelt = {m for m in alle if alle.count(m) > 1}
        if doppelt:
            self.f(wo, f"Module mehrfach in den Stufen: {', '.join(sorted(doppelt))}")
        var = k.get("varianten")
        if var and (not isinstance(var.get("optionen"), dict) or len(var["optionen"]) < 2):
            self.f(wo, "„varianten.optionen“ braucht mindestens zwei Einträge (id: Name)")
        sc = k.get("selbstcheck")
        if sc:
            for i, fr in enumerate(sc.get("fragen") or [], 1):
                if len(fr.get("antworten") or []) < 2:
                    self.f(wo, f"Selbstcheck-Frage {i}: mindestens zwei Antworten")
            for e in sc.get("empfehlung") or []:
                if e.get("stufe") not in ids:
                    self.f(wo, f"Selbstcheck-Empfehlung: unbekannte Stufe „{e.get('stufe')}“")
            if sc.get("empfehlung") and sc["empfehlung"][-1].get("bis") is not None:
                self.h(wo, "letzte Selbstcheck-Empfehlung ohne „bis“ angeben (fängt alle höheren Punktzahlen)")
        if k.get("anrede", "du") not in ("du", "sie"):
            self.f(wo, "„anrede“: du oder sie")
        mo = self.k.moodle
        if mo.get("version", 5) not in (4, 5):
            self.f(wo, "moodle.version muss 4 oder 5 sein")
        if mo.get("freischaltung", "einstufung") not in ("einstufung", "offen"):
            self.f(wo, "moodle.freischaltung: einstufung oder offen")
        if mo.get("reihenfolge", "nacheinander") not in ("nacheinander", "frei"):
            self.f(wo, "moodle.reihenfolge: nacheinander oder frei")

    # ---------- Module
    def modul(self, m):
        wo = f"module/{m['id']}.md"
        var = set(((self.k.k.get("varianten") or {}).get("optionen") or {}))
        if m.get("review") not in REVIEW:
            self.f(wo, f"review muss {', '.join(REVIEW)} sein (ist: {m.get('review')})")
        if not m.get("titel") or m["titel"] == m["id"]:
            self.f(wo, "„titel“ fehlt")
        if not isinstance(m.get("minuten", 0), (int, float)):
            self.f(wo, "„minuten“ muss eine Zahl sein")
        if not m.get("meilenstein") and not m.get("lernziele"):
            self.h(wo, "keine Lernziele angegeben")
        for i, fr in enumerate(m.get("kurzcheck") or [], 1):
            ant = fr.get("antworten") or []
            if not fr.get("frage") or len(ant) < 2:
                self.f(wo, f"Kurz-Check {i}: „frage“ und mindestens zwei „antworten“ nötig")
            if fr.get("variante") and fr["variante"] not in var:
                self.f(wo, f"Kurz-Check {i}: Variante „{fr['variante']}“ gibt es nicht")
            r = fr.get("richtig")
            if not isinstance(r, int) or not 1 <= r <= len(ant):
                self.f(wo, f"Kurz-Check {i}: „richtig“ muss die Nummer der richtigen Antwort sein (1–{len(ant)})")
        a = m.get("abgabe")
        if a:
            if a.get("dateitypen") and not re.fullmatch(r"(\.[a-z0-9]+)(,\s*\.[a-z0-9]+)*", str(a["dateitypen"])):
                self.f(wo, "abgabe.dateitypen z. B. „.pptx,.pdf“")
            if not isinstance(a.get("dateien", 1), int):
                self.f(wo, "abgabe.dateien muss eine Zahl sein")
        if m.get("meilenstein"):
            if not a:
                self.h(wo, "Meilenstein ohne „abgabe“ – in Moodle entsteht dann keine Abgabe-Aufgabe")
            if not m.get("raster"):
                self.h(wo, "Meilenstein ohne „raster“ – die Abgabe wird ohne Bewertungsraster angelegt")
        for i, z in enumerate(m.get("raster") or [], 1):
            if not z.get("kriterium") or not (z.get("erreicht") or "punkte" in z):
                self.f(wo, f"Raster-Zeile {i}: „kriterium“ und „erreicht“ (oder „punkte“) nötig")
            if "punkte" in z and not isinstance(z["punkte"], (int, float)):
                self.f(wo, f"Raster-Zeile {i}: „punkte“ muss eine Zahl sein")
        if m.get("h5p") and self.k.moodle.get("version", 5) == 4:
            self.h(wo, "h5p: true wirkt erst mit Moodle 5 (moodle.version: 5)")
        for mid in m.get("medien") or []:
            if mid not in self.k.medien:
                self.f(wo, f"Medium „{mid}“ steht nicht in medien.yaml")
        qids = {q.get("id") for q in self.k.quellen}
        for q in m.get("quellen") or []:
            if q not in qids:
                self.f(wo, f"Quelle „{q}“ steht nicht in quellen.yaml")
        self.text(wo, m["text"], var)

    def text(self, wo, text, var):
        for nr, name in unbekannte_bausteine(text):
            self.f(wo, f"Zeile {nr}: unbekannter Baustein „:::{name}“")
        for nr, name, inhalt in werkzeuge_im_text(text):
            if not ((VORLAGE / "assets/js/werkzeuge" / f"{name}.js").exists() or (self.k.ordner / "werkzeuge" / f"{name}.js").exists()):
                self.f(wo, f"Zeile {nr}: Werkzeug „{name}“ gibt es nicht (weder in der Vorlage noch unter werkzeuge/)")
            try:
                werkzeug_config(inhalt)
            except Exception as e:  # YAML-Fehler mit Zeilenangabe weiterreichen
                self.f(wo, f"Zeile {nr}: Einstellungen des Werkzeugs „{name}“ sind kein gültiges YAML ({str(e).splitlines()[0]})")
        for nr, z in enumerate(text.split("\n"), 1):
            m = re.match(r"^:{3,}\s*(variante|menueband|seitenleiste)\s+(\S+)", z)
            if m and var and m.group(2) not in var:
                self.f(wo, f"Zeile {nr}: Variante „{m.group(2)}“ gibt es nicht (vorhanden: {', '.join(sorted(var))})")
            if m and not var:
                self.f(wo, f"Zeile {nr}: „:::{m.group(1)}“ braucht „varianten“ in kurs.yaml")
            k = re.match(r"^:{3,}\s*\w+.*\{([\w -]+)\}\s*$", z)
            if k and var:
                for v in k.group(1).split():
                    if v not in var:
                        self.f(wo, f"Zeile {nr}: Variante „{{{v}}}“ gibt es nicht (vorhanden: {', '.join(sorted(var))})")
            for ziel in re.findall(r"\(modul:([\w-]+)\)", z):
                if ziel not in self.k.module:
                    self.f(wo, f"Zeile {nr}: Link auf unbekanntes Modul „{ziel}“")
            for pfad in re.findall(r"(?:\]\(|^:{3,}\s*(?:material|screenshot)\s+)(material/[^\s)]+)", z):
                if not (self.k.ordner / pfad).exists():
                    (self.h if "screenshot" in z else self.f)(wo, f"Zeile {nr}: Datei „{pfad}“ fehlt"
                                                              + (" (Platzhalter wird angezeigt)" if "screenshot" in z else ""))
        offen = [z for z in text.split("\n") if re.match(r"^:{3,}\s*\w", z)]
        zu = [z for z in text.split("\n") if re.match(r"^:{3,}\s*$", z)]
        if len(offen) != len(zu):
            self.f(wo, f"{len(offen)} Bausteine geöffnet, aber {len(zu)} geschlossen – ein ::: fehlt oder ist zu viel")

    # ---------- Einstufung, Quellen, Fragen
    def einstufung(self):
        if not self.k.einstufung_aktiv():
            return
        for s in self.k.stufen[:-1]:
            if not any(m.get("kurzcheck") for m in self.k.module_der_stufe(s["id"])):
                self.h("kurs.yaml", f"Stufe „{s['name']}“ hat keine Kurz-Checks – für die nächste Stufe gibt es dann keinen Einstufungstest")

    def quellen(self):
        for q in self.k.quellen:
            wo = f"quellen.yaml ({q.get('id', '?')})"
            if not q.get("id") or not q.get("titel"):
                self.f(wo, "„id“ und „titel“ nötig")
            if q.get("status", "zu_pruefen") != "verifiziert":
                self.h(wo, "noch nicht verifiziert (status: verifiziert, geprueft_am: JJJJ-MM-TT)")

    def fragen(self):
        import yaml
        ids = set()
        for datei in sorted((self.k.ordner / "fragen").glob("*.yaml")):
            try:
                liste = yaml.safe_load(datei.read_text(encoding="utf-8")) or []
            except yaml.YAMLError as e:
                self.f(f"fragen/{datei.name}", f"YAML fehlerhaft – {e}")
                continue
            for a in liste:
                wo = f"fragen/{datei.name} ({a.get('id', '?')})"
                if a.get("id") in ids:
                    self.f(wo, "ID doppelt")
                ids.add(a.get("id"))
                if a.get("typ") not in FRAGETYPEN:
                    self.f(wo, f"unbekannter typ „{a.get('typ')}“")
                if a.get("modul") and a["modul"] not in self.k.module:
                    self.f(wo, f"unbekanntes Modul „{a['modul']}“")
                if a.get("typ") in ("single_choice", "multiple_choice"):
                    n = sum(1 for o in a.get("optionen") or [] if o.get("korrekt"))
                    if a["typ"] == "single_choice" and n != 1:
                        self.f(wo, f"single_choice braucht genau eine richtige Option (hat {n})")
                    if a["typ"] == "multiple_choice" and n < 1:
                        self.f(wo, "multiple_choice braucht mindestens eine richtige Option")
                for feld, erlaubt in (("optionen", {"text", "korrekt", "feedback"}),
                                      ("elemente", {"text", "kategorie", "feedback"})):
                    for o in a.get(feld) or []:
                        if isinstance(o, dict) and set(o) - erlaubt:
                            fremd = ", ".join(f"„{k}“" for k in sorted(set(o) - erlaubt, key=str))
                            self.f(wo, f"{feld}: unbekannter Schlüssel {fremd} – steht ein Komma im Text? "
                                       "In {…} trennt YAML an Kommas; den Text in Anführungszeichen setzen")
                if a.get("typ") == "lueckentext":
                    platz = set(re.findall(r"\{\{\s*(\w+)\s*\}\}", a.get("text", "")))
                    if platz != set(a.get("luecken") or {}):
                        self.f(wo, "Platzhalter im Text und „luecken“ passen nicht zusammen")

    def tests(self):
        """tests: in kurs.yaml (Moodle-Test in der Kurssicherung)."""
        tests = self.k.k.get("tests") or []
        stufen = {s["id"] for s in self.k.stufen}
        fragen = {}
        for d in (self.k.ordner / "fragen").glob("*.yaml"):
            try:
                fragen[d.stem] = {a.get("id"): a for a in (lies_yaml(d, []) or [])}
            except Exception:
                pass
        ids = set()
        for t in tests:
            wo = f"kurs.yaml tests ({t.get('id', '?')})"
            if not t.get("id") or not (t.get("titel") or t.get("klausur")):
                self.f(wo, "„id“ und „titel“ nötig")
            if t.get("id") in ids or t.get("id") in self.k.module:
                self.f(wo, "ID doppelt (auch Modul-IDs zählen)")
            ids.add(t.get("id"))
            if bool(t.get("nach")) == bool(t.get("stufe")):
                self.f(wo, "genau eins von „nach: <modul>“ oder „stufe: <stufe>“ angeben")
            if t.get("nach") and t["nach"] not in self.k.module:
                self.f(wo, f"unbekanntes Modul „{t['nach']}“")
            if t.get("stufe") and t["stufe"] not in stufen:
                self.f(wo, f"unbekannte Stufe „{t['stufe']}“")
            if t.get("klausur"):
                self.klausur_test(wo, t)
                continue
            dateien = t.get("fragen")
            dateien = [dateien] if isinstance(dateien, str) else (dateien or [])
            if not dateien:
                self.f(wo, "„fragen:“ fehlt (Dateiname in fragen/ ohne .yaml)")
            vorhanden = {}
            for d in dateien:
                if d not in fragen:
                    self.f(wo, f"fragen/{d}.yaml gibt es nicht")
                else:
                    vorhanden.update(fragen[d])
            for qid in list(t.get("auswahl") or []) + list(t.get("ohne") or []):
                if vorhanden and qid not in vorhanden:
                    self.f(wo, f"Frage „{qid}“ gibt es in {', '.join(dateien)} nicht")
            if "bestehen" in t and not (0 < float(t["bestehen"]) <= 100):
                self.f(wo, "„bestehen“ ist ein Prozentwert zwischen 1 und 100")
            if t.get("feedback", "nachher") not in ("nachher", "sofort"):
                self.f(wo, "„feedback“: nachher oder sofort")
            gewaehlt = [vorhanden[q] for q in (t.get("auswahl") or vorhanden) if q in vorhanden and q not in (t.get("ohne") or [])]
            if any(a.get("typ") == "offen" for a in gewaehlt) and t.get("bestehen"):
                self.h(wo, "enthält offene Fragen – „bestanden“ gibt es erst, wenn die Lehrkraft sie bewertet hat")
            if any(a.get("typ") == "reihenfolge" for a in gewaehlt) and str(self.k.moodle.get("version", 5)) == "4":
                self.h(wo, "Fragen vom Typ „reihenfolge“ fallen in Moodle 4.2 weg (Anordnung erst ab 4.4 im Standard)")
            offen = [a.get("id") for a in gewaehlt if a.get("review", "entwurf") != "freigegeben"]
            if offen:
                self.h(wo, f"{len(offen)} Frage(n) nicht freigegeben – kommen nur mit --entwuerfe in den Test")

    def klausur_test(self, wo, t):
        """tests: - klausur: <ordner> – die Klausur selbst prüft klausur.py (Klausur-Baukasten)."""
        ordner = (self.k.ordner / str(t["klausur"])).resolve()
        if not (ordner / "klausur.yaml").exists():
            self.f(wo, f"„klausur: {t['klausur']}“ – dort liegt keine klausur.yaml")
            return
        try:
            kl_modul = lade_klausur_modul()
            kl = kl_modul.Klausur(ordner)
            fehler, hinweise = kl_modul.pruefe(kl)
        except Fehler as e:
            self.f(wo, str(e))
            return
        for m in fehler:
            self.f(wo, f"Klausur: {m}")
        for m in hinweise:
            self.h(wo, f"Klausur: {m}")
        if kl.review != "freigegeben":
            self.h(wo, f"Klausur nicht freigegeben (review: {kl.review}) – kommt nur mit --entwuerfe in den Kurs")
        if t.get("feedback") or t.get("bestehen") or t.get("zeit"):
            self.h(wo, "feedback/bestehen/zeit gelten bei „klausur:“ nicht – die Klausurdatei bestimmt das")

    def zugang(self):
        """zugang: in kurs.yaml (einfacher Passwortschutz der Web-Version) und :::schluessel in den Modulen."""
        z = self.k.k.get("zugang")
        wo = "kurs.yaml zugang"
        stufen = [s["id"] for s in self.k.stufen]
        ziele = set()
        if z is not None:
            if not isinstance(z, dict):
                self.f(wo, "erwartet passwort:, stufen: und/oder module:")
                return
            fremd = set(z) - {"passwort", "stufen", "module", "text", "stufen_text"}
            if fremd:
                self.f(wo, f"unbekannte Einträge: {', '.join(sorted(fremd))}")
            codes = []
            if z.get("passwort") is not None:
                codes.append(("passwort", z["passwort"]))
            for feld, erlaubt in (("stufen", set(stufen)), ("module", set(self.k.module))):
                for k, v in (z.get(feld) or {}).items():
                    if k not in erlaubt:
                        self.f(wo, f"{feld}: „{k}“ gibt es nicht")
                    codes.append((f"{feld}.{k}", v))
                    ziele.add(k)
            for name, v in codes:
                if not isinstance(v, (str, int)) or not str(v).strip():
                    self.f(wo, f"{name}: Code fehlt oder ist leer")
                elif len(str(v).strip()) < 4:
                    self.h(wo, f"{name}: sehr kurzer Code – leicht zu erraten")
            gleich = {}
            for name, v in codes:
                gleich.setdefault(str(v).strip().lower(), []).append(name)
            for v, namen in gleich.items():
                if len(namen) > 1:
                    self.h(wo, f"derselbe Code für {', '.join(namen)} – er öffnet alle davon")
            if stufen and stufen[0] in (z.get("stufen") or {}):
                self.h(wo, f"die erste Stufe „{stufen[0]}“ ist gesperrt – dafür reicht meist das Gesamtpasswort")
            for k in (z.get("stufen") or {}):
                if not self._hat_schluessel(k):
                    self.h(wo, f"Stufe „{k}“: kein :::schluessel {k} in einem Modul – woher bekommen die Schüler:innen den Code?")
            self.h(wo, "Sichtschutz, keine echte Sicherheit: Inhalte stehen im Quelltext der Seiten – "
                       "nichts Vertrauliches (Noten, Personendaten, Prüfungslösungen) in die Web-Version")
        for mid in self.k.reihenfolge:
            for m in re.finditer(r"^:{3,}\s*schluessel\s+(\S+)", self.k.module[mid].get("text", ""), re.M):
                if m.group(1) not in ziele:
                    self.f(f"module/{mid}.md", f":::schluessel {m.group(1)} – dafür steht kein Code unter zugang.stufen/zugang.module")

    def _hat_schluessel(self, ziel):
        return any(re.search(rf"^:{{3,}}\s*schluessel\s+{re.escape(ziel)}\b", self.k.module[mid].get("text", ""), re.M)
                   for mid in self.k.reihenfolge)

    def alles(self):
        self.kursdatei()
        for mid in self.k.reihenfolge:
            self.modul(self.k.module[mid])
        for s in self.k.seiten:
            self.text(f"seiten/{Path(s['quelle']).name}", s["text"], set(((self.k.k.get("varianten") or {}).get("optionen") or {})))
        self.einstufung()
        self.quellen()
        self.fragen()
        self.tests()
        self.zugang()
        return not self.fehler


def pruefe(ordner, still=False):
    kurs = Kurs(ordner)
    p = Pruefer(kurs)
    ok = p.alles()
    if not still or not ok:
        for x in p.fehler:
            print(f"  ✗ {x}")
        for x in p.hinweise:
            print(f"  ! {x}")
    return ok, p


def main(argv=None):
    args = kurs_aus_argumenten(argv, __doc__).parse_args(argv)
    try:
        ok, p = pruefe(args.ordner)
    except Fehler as e:
        print(f"  ✗ {e}")
        sys.exit(1)
    freigegeben = sum(1 for m in p.k.module.values() if m.get("review") == "freigegeben")
    print(("✓ Keine Fehler" if ok else f"✗ {len(p.fehler)} Fehler") + f", {len(p.hinweise)} Hinweise · "
          f"{len(p.k.reihenfolge)} Module, {freigegeben} freigegeben")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
