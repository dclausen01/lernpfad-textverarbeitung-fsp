#!/usr/bin/env python3
"""Klickt die Web-Version einmal komplett durch – am Desktop und am Handy – und macht Screenshots.

    python3 durchklicken.py [ordner] [--nur-links]

Voraussetzung: bauen.py ist gelaufen. Ergebnis: ausgabe/pruefung/uebersicht.html (alle Seiten als Bilder,
darunter die gefundenen Probleme). Geprüft wird:
    • fehlende Dateien (Links, Bilder, Downloads)          – immer
    • JavaScript-Fehler, kaputte Bilder, Seite breiter als das Handy (seitlich scrollen),
      Kurz-Check reagiert, Häkchen und Umschalter funktionieren  – mit Browser

Browser: nutzt Playwright (pip install playwright). Es reicht der vorhandene Chrome oder Edge – ein eigener
Browser-Download ist nicht nötig. Ohne Playwright gibt es nur die Dateiprüfung (--nur-links erzwingt das).
"""
import html
import json
import os
import re
import sys
from pathlib import Path

from gemeinsam import Fehler, Kurs, kurs_aus_argumenten, melde_fehler_und_ende

GROESSEN = {"desktop": dict(width=1280, height=800), "handy": dict(width=390, height=844)}
REF_RE = re.compile(r'(?:src|href|data-src)\s*=\s*"([^"#?]+)', re.I)


def dateipruefung(web, seiten):
    """→ (probleme, fehlende Screenshots)"""
    probleme, platzhalter = [], []
    for s in seiten:
        text = (web / s["datei"]).read_text(encoding="utf-8")
        for ref in REF_RE.findall(text):
            if re.match(r"^([a-z]+:|//|mailto:)", ref, re.I):
                continue
            if not (web / ref).exists():
                if 'data-src="' + ref in text:
                    platzhalter.append(f"{s['datei']}: {ref}")
                else:
                    probleme.append((s["datei"], "alle", f"Datei fehlt: {ref}"))
    return probleme, platzhalter


def starte_browser(pw):
    """Erst Playwrights eigener Chromium, sonst der installierte Chrome/Edge."""
    versuche = [dict()]
    if os.environ.get("LP_BROWSER"):
        versuche.insert(0, dict(executable_path=os.environ["LP_BROWSER"]))
    if Path("/opt/pw-browsers/chromium").exists():
        versuche.append(dict(executable_path="/opt/pw-browsers/chromium"))
    versuche += [dict(channel="chrome"), dict(channel="msedge")]
    letzter = None
    for v in versuche:
        try:
            return pw.chromium.launch(**v)
        except Exception as e:  # nächster Versuch
            letzter = e
    raise Fehler(f"Kein Browser gefunden (Chrome oder Edge installieren) – {str(letzter).splitlines()[0]}")


PRUEF_JS = """() => {
  const r = {};
  r.breite = document.documentElement.scrollWidth - window.innerWidth;
  r.bilder = [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.getAttribute('src'));
  r.checks = document.querySelectorAll('ul.check li').length;
  r.qa = document.querySelectorAll('.qa').length;
  r.umschalter = document.querySelectorAll('#topbar [data-app], #topbar .seg button, #topbar button[data-v]').length;
  return r;
}"""


def alles_offen_js(web):
    """Bei zugang: in kurs.yaml – vor jeder Seite alles freischalten, damit der Test die Inhalte sieht."""
    text = (web / "assets/js/kurs.js").read_text(encoding="utf-8")
    cfg = json.loads(text.split("window.LP_KURS = ", 1)[1].rstrip().rstrip(";"))
    z = cfg.get("zugang")
    if not z:
        return None
    mem = {"gesamt": z.get("passwort"), "stufen": z.get("stufen") or {}, "module": z.get("module") or {}}
    key = f"lernpfad-{cfg['kurzname']}-zugang"
    return f"try {{ localStorage.setItem({json.dumps(key)}, {json.dumps(json.dumps(mem))}); }} catch (e) {{}}"


def browserpruefung(web, seiten, ziel):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, ["Playwright fehlt – nur Dateiprüfung. Für den Browser-Test: pip install playwright"]
    probleme, bilder = [], {}
    offen = alles_offen_js(web)
    with sync_playwright() as pw:
        browser = starte_browser(pw)
        for name, groesse in GROESSEN.items():
            (ziel / name).mkdir(parents=True, exist_ok=True)
            ctx = browser.new_context(viewport=groesse, device_scale_factor=1,
                                      is_mobile=name == "handy", has_touch=name == "handy")
            if offen:
                ctx.add_init_script(offen)
            for s in seiten:
                if s["art"] == "start":
                    continue  # leitet in der Web-Version nur auf index.html weiter
                page = ctx.new_page()
                fehler = []
                page.on("pageerror", lambda e, f=fehler: f.append(str(e)))
                page.on("console", lambda m, f=fehler: f.append(m.text) if m.type == "error" else None)
                page.goto((web / s["datei"]).as_uri())
                page.wait_for_timeout(400)
                r = page.evaluate(PRUEF_JS)
                wo = (s["datei"], name)
                for f in fehler:
                    if "ERR_FILE_NOT_FOUND" not in f:
                        probleme.append((*wo, f"JavaScript-Fehler: {f}"))
                if r["breite"] > 2:
                    probleme.append((*wo, f"Seite ist {r['breite']} px breiter als der Bildschirm (seitliches Scrollen) – "
                                          "meist eine zu breite Tabelle, ein langes Wort oder ein Bild"))
                for b in r["bilder"]:
                    probleme.append((*wo, f"Bild lädt nicht: {b}"))
                if name == "desktop":
                    probleme += interaktion(page, s)
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(150)
                datei = ziel / name / (Path(s["datei"]).stem + ".png")
                page.screenshot(path=str(datei), full_page=True)
                bilder.setdefault(s["datei"], {})[name] = datei.relative_to(ziel).as_posix()
                page.close()
            ctx.close()
        browser.close()
    return bilder, probleme


def interaktion(page, s):
    """Die wichtigsten Knöpfe einmal drücken."""
    p = []
    wo = (s["datei"], "desktop")
    qa = page.locator(".qa").first
    if qa.count():
        rechts = int(qa.get_attribute("data-right"))
        qa.locator("ol > li button").nth(rechts - 1).click()
        if not qa.locator(".fb").inner_text().strip():
            p.append((*wo, "Kurz-Check zeigt nach einer Antwort keine Rückmeldung"))
    box = page.locator("ul.check li label").first
    if box.count():
        box.click()
        page.wait_for_timeout(100)
        if not page.locator("ul.check li.done").count():
            p.append((*wo, "Checkliste lässt sich nicht abhaken"))
    return p


def uebersicht(kurs, seiten, bilder, probleme, hinweise, ziel):
    zeilen = []
    for s in seiten:
        b = (bilder or {}).get(s["datei"], {})
        pr = [t for d, g, t in probleme if d == s["datei"]]
        zeilen.append(
            f'<section><h2>{html.escape(s["titel"])} <small>{html.escape(s["datei"])}'
            + (f' · <span class="entwurf">{html.escape(s.get("review", ""))}</span>' if s.get("review") not in (None, "freigegeben") else "")
            + "</small></h2>"
            + ("<ul class='pr'>" + "".join(f"<li>{html.escape(t)}</li>" for t in pr) + "</ul>" if pr else "<p class='ok'>✓ keine Probleme</p>")
            + '<div class="bilder">' + "".join(f'<a href="{v}"><img src="{v}" alt="{k}" class="{k}" loading="lazy"></a>' for k, v in b.items())
            + "</div></section>")
    seite = f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Durchgeklickt – {html.escape(kurs.titel)}</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;margin:0 auto;max-width:1200px;padding:1rem;background:#faf8f4;color:#1d2b33}}
h1{{margin:.2rem 0}} h2{{font-size:1.15rem;margin:0 0 .4rem}} small{{color:#667;font-weight:400}}
section{{background:#fff;border:1px solid #e4dfd6;border-radius:12px;padding:1rem;margin:1rem 0}}
.bilder{{display:flex;gap:1rem;align-items:flex-start;overflow-x:auto}} img{{border:1px solid #ddd;border-radius:6px;max-height:420px}}
img.desktop{{width:560px;object-fit:cover;object-position:top}} img.handy{{width:180px;object-fit:cover;object-position:top}}
.pr li{{color:#9b2c1f}} .ok{{color:#2f7a4a;margin:.2rem 0}} .entwurf{{color:#b0660f}}
</style></head><body>
<h1>Durchgeklickt: {html.escape(kurs.titel)}</h1>
<p>{len(seiten)} Seiten · {len(probleme)} Problem(e){" · " + " · ".join(html.escape(h) for h in hinweise) if hinweise else ""}. Bilder anklicken = groß.</p>
{"".join(zeilen)}
</body></html>"""
    (ziel / "uebersicht.html").write_text(seite, encoding="utf-8")


def durchklicken(kurs, nur_links=False):
    web = kurs.ausgabe / "web"
    if not (web / "site.json").exists():
        raise Fehler("Erst die Web-Version bauen (bauen.py) – ausgabe/web/site.json fehlt.")
    seiten = json.loads((web / "site.json").read_text(encoding="utf-8"))["seiten"]
    ziel = kurs.ausgabe / "pruefung"
    ziel.mkdir(parents=True, exist_ok=True)
    probleme, platzhalter = dateipruefung(web, seiten)
    bilder, hinweise = None, []
    if platzhalter:
        hinweise.append(f"{len(platzhalter)} Screenshot(s) fehlen noch (Platzhalter): " + ", ".join(platzhalter))
    if nur_links:
        hinweise.append("nur Dateiprüfung")
    else:
        bilder, mehr = browserpruefung(web, seiten, ziel)
        if bilder is None:
            hinweise += mehr
        else:
            probleme += mehr
    uebersicht(kurs, seiten, bilder, probleme, hinweise, ziel)
    return probleme, hinweise, ziel / "uebersicht.html"


def main(argv=None):
    ap = kurs_aus_argumenten(argv, __doc__)
    ap.add_argument("--nur-links", action="store_true", help="ohne Browser, nur fehlende Dateien suchen")
    args = ap.parse_args(argv)
    try:
        kurs = Kurs(args.ordner)
        probleme, hinweise, bericht = durchklicken(kurs, args.nur_links)
    except Fehler as e:
        melde_fehler_und_ende(e)
    for d, g, t in probleme:
        print(f"  ✗ {d} ({g}): {t}")
    for h in hinweise:
        print(f"  ! {h}")
    print(("✓ Keine Probleme gefunden" if not probleme else f"✗ {len(probleme)} Problem(e)") + f" · Übersicht: {bericht}")
    sys.exit(1 if probleme else 0)


if __name__ == "__main__":
    main()
