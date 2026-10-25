#!/usr/bin/env python3
"""Die ganze Kette in einem Rutsch: prüfen → Web-Version → durchklicken → (H5P) → Moodle-Kurs → Fragen.

    python3 alles.py [ordner] [--moodle 4|5] [--entwuerfe] [--ohne-browser]

Bricht bei Fehlern ab und sagt, wo es hakt. Ergebnis:
    ausgabe/web/                   Web-Version (index.html im Browser öffnen)
    ausgabe/pruefung/uebersicht.html   alle Seiten als Bilder (Desktop + Handy) mit gefundenen Problemen
    ausgabe/moodle/                Kurssicherung (.mbz), Klickanleitung, Lernpakete, ggf. H5P und Fragen (XML)
"""
from bauen import Bauer
from durchklicken import durchklicken
from gemeinsam import Fehler, Kurs, kurs_aus_argumenten, melde_fehler_und_ende
from h5p import baue_h5p
from moodle_kurs import baue_kurs
from moodle_xml import baue_fragen
from pruefen import pruefe


def main(argv=None):
    ap = kurs_aus_argumenten(argv, __doc__)
    ap.add_argument("--moodle", choices=["4", "5"], help="Standard: moodle.version aus kurs.yaml")
    ap.add_argument("--entwuerfe", action="store_true", help="auch nicht freigegebene Module nach Moodle (nur Testkurse!)")
    ap.add_argument("--ohne-browser", action="store_true", help="durchklicken nur als Dateiprüfung")
    args = ap.parse_args(argv)
    try:
        print("1/5 Prüfen …")
        ok, p = pruefe(args.ordner)
        if not ok:
            raise Fehler("Erst die Fehler oben beheben.")
        kurs = Kurs(args.ordner)
        print("2/5 Web-Version bauen …")
        web = Bauer(kurs).baue()
        print("3/5 Durchklicken (Desktop + Handy) …")
        probleme, hinweise, bericht = durchklicken(kurs, args.ohne_browser)
        for d, g, t in probleme:
            print(f"  ✗ {d} ({g}): {t}")
        for h in hinweise:
            print(f"  ! {h}")
        version = str(args.moodle or kurs.moodle.get("version", 5))
        print("4/5 Moodle-Kurs bauen …")
        if version == "5":
            baue_h5p(kurs, args.entwuerfe, still=True)
        ziel, typen = baue_kurs(kurs, version, args.entwuerfe, still=True)
        print("5/5 Fragen für Moodle-Tests …")
        fragen = baue_fragen(kurs, still=True)
    except Fehler as e:
        melde_fehler_und_ende(e)
    namen = {"scorm": "Lernpakete", "assign": "Aufgaben", "h5pactivity": "H5P", "subsection": "Unterabschnitte",
             "quiz": "Tests", "qbank": "Fragensammlung"}
    frei = sum(1 for m in kurs.module.values() if m.get("review") == "freigegeben")
    print()
    print(f"✓ Fertig: {kurs.titel}  ({len(kurs.reihenfolge)} Module, {frei} freigegeben)")
    print(f"  Web-Version:   {web / 'index.html'}")
    print(f"  Durchgeklickt: {bericht}" + (f"  – {len(probleme)} Problem(e)!" if probleme else "  – keine Probleme"))
    print(f"  Moodle {version}:      {ziel}  (" + ", ".join(f"{v} {namen.get(t, t)}" for t, v in sorted(typen.items())) + ")")
    print(f"  Klickanleitung: {ziel.parent / f'ANLEITUNG_moodle{version}.md'}")
    if fragen:
        print(f"  Fragen (XML):  {', '.join(f.name for f in fragen)} in {fragen[0].parent}")
    if p.hinweise:
        print(f"  {len(p.hinweise)} Hinweis(e) von pruefen.py – bitte ansehen.")


if __name__ == "__main__":
    main()
