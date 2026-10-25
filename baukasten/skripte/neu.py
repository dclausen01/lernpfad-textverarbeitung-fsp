#!/usr/bin/env python3
"""Legt das Gerüst für einen neuen Lernpfad an.

    python3 neu.py <ordner> --titel "Tabellenkalkulation" [--stufen Einsteiger,Fortgeschrittene,Profis]
                   [--varianten "excel:Excel,calc:LibreOffice Calc"] [--moodle 4|5]

Danach: kurs.yaml und module/*.md mit Inhalt füllen (das macht Claude mit der Lehrkraft), dann alles.py.
"""
import argparse
import sys
from pathlib import Path

from gemeinsam import slug

ICONS = ["🌱", "🚀", "🏆", "⭐", "🎓"]


def praefixe(stufen):
    """Kürzel je Stufe für die Modul-IDs (e, f, p …; bei gleichem Anfangsbuchstaben länger)."""
    out = []
    for s in stufen:
        k = slug(s).replace("-", "")
        n = 1
        while k[:n] in out and n < len(k):
            n += 1
        out.append(k[:n])
    return out


def kurs_yaml(titel, stufen, varianten, moodle):
    kurz = slug(titel)
    zeilen = [f"# Kursbeschreibung – {titel}", "# Aufbau und alle Felder: referenzen/schema.md im Lernpfad-Baukasten", "",
              f"titel: {titel}", f"kurzname: {kurz}", f"ueberschrift: {titel} – Schritt für Schritt",
              "untertitel: Worum geht es? Ein Satz für die Schüler:innen.",
              f"badges: [{len(stufen)} Stufen]", "fusszeile: BBZ Rendsburg-Eckernförde", "",
              "einleitung: |", "  :::notiz 👉 Bevor du startest", "  Arbeite die Module der Reihe nach durch.", "  :::", ""]
    if varianten:
        zeilen += ["varianten:", '  frage: "Ich arbeite mit:"',
                   "  optionen: {" + ", ".join(f"{k}: {v}" for k, v in varianten) + "}", "  beide: true", ""]
    zeilen.append("stufen:")
    for i, (s, praefix) in enumerate(zip(stufen, praefixe(stufen))):
        zeilen += [f"  - id: {slug(s)}", f"    name: {s}", f'    icon: "{ICONS[i % len(ICONS)]}"',
                   "    text: Was lernt man in dieser Stufe? (ein Satz)",
                   f"    module: [{praefix}1{', ' + praefix + 'm' if len(stufen) > 1 else ''}]"]
    zeilen += ["", "# selbstcheck:            # optional: kurzer Selbsteinschätzungs-Check auf der Startseite", ""]
    if len(stufen) > 1:
        zeilen += ["einstufung: {bestehen: 80}   # Einstufungstests aus den Kurz-Checks der vorigen Stufe", ""]
    zeilen += ["moodle:", f"  version: {moodle}                 # 5 = mit Unterabschnitten und H5P (Standard), 4 = ohne Unterabschnitte",
               "  freischaltung: einstufung  # einstufung = Stufe frei nach Meilenstein ODER Einstufungstest; offen = alle Stufen sofort",
               "  reihenfolge: nacheinander  # nacheinander | frei", ""]
    return "\n".join(zeilen)


MODUL = """---
titel: {titel}
minuten: 45
review: entwurf          # entwurf → geprueft → freigegeben (nur freigegebene Module kommen nach Moodle)
lernziele:
  - …
kurzcheck:
  - frage: …
    antworten: [„…“, „…“, „…“]
    richtig: 1
---
## Erster Abschnitt

Text mit Bausteinen – Übersicht: referenzen/bausteine.md

:::aufgabe basis 10 Erste Aufgabe
…
:::
"""

MEILENSTEIN = """---
titel: "Meilenstein: …"
minuten: 90
meilenstein: true
review: entwurf
abgabe:
  titel: Meilenstein abgeben
  text: Lade dein Ergebnis hoch.
  dateitypen: .pdf
  dateien: 1
raster:
  - {kriterium: …, erreicht: …, besonders_gut: …}
---
## Auftrag

…

:::checkliste Checkliste vor der Abgabe
- …
:::
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ordner", type=Path)
    ap.add_argument("--titel", required=True)
    ap.add_argument("--stufen", default="Einsteiger,Fortgeschrittene,Profis")
    ap.add_argument("--varianten", default="", help='z. B. "ppt:PowerPoint,oo:OnlyOffice"')
    ap.add_argument("--moodle", choices=["4", "5"], default="5")
    args = ap.parse_args(argv)
    o = args.ordner
    if (o / "kurs.yaml").exists():
        sys.exit(f"✗ In {o} gibt es schon eine kurs.yaml – nichts überschrieben.")
    stufen = [s.strip() for s in args.stufen.split(",") if s.strip()]
    varianten = [tuple(x.split(":", 1)) for x in args.varianten.split(",") if ":" in x]
    for d in ("module", "seiten", "material", "fragen"):
        (o / d).mkdir(parents=True, exist_ok=True)
    (o / "kurs.yaml").write_text(kurs_yaml(args.titel, stufen, varianten, args.moodle), encoding="utf-8")
    for s, p in zip(stufen, praefixe(stufen)):
        (o / "module" / f"{p}1.md").write_text(MODUL.format(titel=f"Erstes Modul ({s})"), encoding="utf-8")
        if len(stufen) > 1:
            (o / "module" / f"{p}m.md").write_text(MEILENSTEIN, encoding="utf-8")
    (o / "quellen.yaml").write_text("# Quellen mit Prüfstatus – siehe referenzen/qualitaet.md\n"
                                    "# - {id: q1, titel: …, url: …, status: zu_pruefen}\n", encoding="utf-8")
    (o / ".gitignore").write_text("ausgabe/\n", encoding="utf-8")
    print(f"✓ Gerüst angelegt: {o.resolve()}")
    print("  Nächste Schritte: kurs.yaml ausfüllen, Module schreiben, dann  python3 alles.py " + str(o))


if __name__ == "__main__":
    main()
