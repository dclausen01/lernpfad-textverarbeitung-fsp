#!/usr/bin/env python3
"""Baut aus der Web-Version je Modul ein Lernpaket (SCORM) für Moodle.

    python3 lernpakete.py [ordner] [--entwuerfe] [--scorm 1.2]

Voraussetzung: bauen.py ist gelaufen (ausgabe/web/). Ergebnis: ausgabe/moodle/lernpakete/*.zip

Ein Paket = eine Modulseite + Zusatzseiten (Spickzettel, Videos) + alles, was diese Seiten brauchen
(Stil, Skripte, Schriften, Bilder, Übungsdateien). Dazu kommen scorm-config.js und scorm.js: Damit speichert
der Lernpfad Häkchen, Notizen und den Erledigt-Status in Moodle statt im Browser.
Außerdem je ein Paket für die Startseite („Mein Lernpfad“) und für jeden Einstufungstest.

Nur freigegebene Module werden verpackt (review: freigegeben). Mit --entwuerfe auch die übrigen –
zum Ausprobieren in einem Testkurs.
"""
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from gemeinsam import Fehler, Kurs, kurs_aus_argumenten, melde_fehler_und_ende

REF_RE = re.compile(r'(?:src|href|data-src)\s*=\s*"([^"#?]+)', re.I)
CSS_URL_RE = re.compile(r'url\(\s*["\']?([^"\')]+)')
IMMER = ["assets/css/style.css", "assets/css/kurs.css", "assets/js/kurs.js", "assets/js/medien.js",
         "assets/js/app.js", "assets/js/scorm.js"]


def lokale_verweise(text):
    for ref in REF_RE.findall(text):
        if not re.match(r"^([a-z]+:|//|#|mailto:)", ref, re.I):
            yield ref


def einsammeln(web, seiten):
    """Alle lokalen Dateien, die die Seiten (und das CSS) brauchen."""
    dateien = set(seiten) | set(IMMER)
    for s in seiten:
        for ref in lokale_verweise((web / s).read_text(encoding="utf-8")):
            if not ref.endswith(".html") and (web / ref).is_file():
                dateien.add(ref)
    for css in ("assets/css/style.css", "assets/css/kurs.css"):
        for ref in CSS_URL_RE.findall((web / css).read_text(encoding="utf-8")):
            p = (web / "assets/css" / ref).resolve()
            if p.is_file():
                dateien.add(p.relative_to(web).as_posix())
    for lizenz in (web / "assets/fonts").glob("OFL-*.txt"):
        dateien.add(lizenz.relative_to(web).as_posix())
    return sorted(dateien)


def einbinden(html):
    html = html.replace('<script src="assets/js/zugang.js"></script>\n', "")  # in Moodle regelt Moodle den Zugang
    tag = '<script src="assets/js/scorm-config.js"></script>\n<script src="assets/js/scorm.js"></script>\n'
    i = html.find('<script src="assets/js/medien.js"')
    if i < 0:
        i = html.find("</head>")
    return html[:i] + tag + html[i:]


def manifest(ident, titel, start, dateien, version):
    liste = "\n".join(f'      <file href="{escape(f)}"/>' for f in dateien)
    if version == "1.2":
        kopf = ('xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2" '
                'xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"')
        schema, typ = "1.2", 'adlcp:scormtype="sco"'
    else:
        kopf = ('xmlns="http://www.imsglobal.org/xsd/imscp_v1p1" xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3" '
                'xmlns:adlseq="http://www.adlnet.org/xsd/adlseq_v1p3" xmlns:adlnav="http://www.adlnet.org/xsd/adlnav_v1p3" '
                'xmlns:imsss="http://www.imsglobal.org/xsd/imsss"')
        schema, typ = "2004 4th Edition", 'adlcp:scormType="sco"'
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="{escape(ident)}" version="1" {kopf}
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>{schema}</schemaversion>
  </metadata>
  <organizations default="org">
    <organization identifier="org">
      <title>{escape(titel)}</title>
      <item identifier="item" identifierref="res">
        <title>{escape(titel)}</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="res" type="webcontent" {typ} href="{escape(start)}">
{liste}
    </resource>
  </resources>
</manifest>
"""


def paket(web, ziel_ordner, kurzname, seite, zusatz, version):
    """seite: Eintrag aus site.json. Gibt den Pfad des ZIPs zurück."""
    pid = seite.get("id") or Path(seite["datei"]).stem
    seiten = [seite["datei"]] + [z for z in zusatz if z != seite["datei"]]
    dateien = [f for f in einsammeln(web, seiten) if f != "assets/js/zugang.js"]  # Zugang regelt in Moodle Moodle
    config = {"module": pid, "launch": seite["datei"], "files": seiten}
    if seite["art"] == "einstufung":
        config["bestehen"] = seite.get("bestehen", 80)
    alle = sorted(dateien + ["assets/js/scorm-config.js"])
    tag = "scorm12" if version == "1.2" else "scorm2004"
    ziel = ziel_ordner / f"{kurzname}_{pid}_{tag}.zip"
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("imsmanifest.xml", manifest(f"{kurzname}-{pid}", seite["titel"], seite["datei"], alle, version))
        z.writestr("assets/js/scorm-config.js", "window.LP_SCORM_CONFIG = " + json.dumps(config, ensure_ascii=False) + ";\n")
        for f in dateien:
            if f in seiten:
                z.writestr(f, einbinden((web / f).read_text(encoding="utf-8")))
            else:
                z.write(web / f, f)
    return ziel


def baue_lernpakete(kurs, entwuerfe=False, version="2004", still=False):
    """Gibt {id: Pfad des ZIPs} zurück (Module mit ihrer ID, Start als „start“, Tests als „einstufung-<stufe>“)."""
    web = kurs.ausgabe / "web"
    if not (web / "site.json").exists():
        raise Fehler("Erst die Web-Version bauen (bauen.py) – ausgabe/web/site.json fehlt.")
    site = json.loads((web / "site.json").read_text(encoding="utf-8"))
    ziel_ordner = kurs.ausgabe / "moodle" / "lernpakete"
    ziel_ordner.mkdir(parents=True, exist_ok=True)
    for alt in ziel_ordner.glob("*.zip"):
        alt.unlink()
    zusatz = [s["datei"] for s in site["seiten"] if s["art"] == "seite"]
    if (web / "videos.html").exists():
        zusatz.append("videos.html")
    ergebnis, ausgelassen = {}, []
    for s in site["seiten"]:
        if s["art"] == "modul" and s.get("review") != "freigegeben" and not entwuerfe:
            ausgelassen.append(s["id"])
            continue
        if s["art"] in ("modul", "start", "einstufung"):
            pid = s.get("id") or Path(s["datei"]).stem
            ergebnis[pid] = paket(web, ziel_ordner, kurs.kurzname, s, zusatz if s["art"] == "modul" else [], version)
            if not still:
                print(f"  {ergebnis[pid].name}  ({ergebnis[pid].stat().st_size // 1024} KB)")
    if ausgelassen and not still:
        print(f"  (nicht verpackt, noch nicht freigegeben: {', '.join(ausgelassen)} – mit --entwuerfe trotzdem)")
    return ergebnis


def main(argv=None):
    ap = kurs_aus_argumenten(argv, __doc__)
    ap.add_argument("--entwuerfe", action="store_true", help="auch nicht freigegebene Module verpacken")
    ap.add_argument("--scorm", choices=["2004", "1.2"], default="2004")
    args = ap.parse_args(argv)
    try:
        kurs = Kurs(args.ordner)
        n = len(baue_lernpakete(kurs, args.entwuerfe, args.scorm))
    except Fehler as e:
        melde_fehler_und_ende(e)
    print(f"✓ {n} Lernpakete in {kurs.ausgabe / 'moodle' / 'lernpakete'}")


if __name__ == "__main__":
    main()
