#!/usr/bin/env python3
"""Fragen für Moodle-Tests: fragen/*.yaml → Moodle-XML (zum Import in die Fragensammlung).

    python3 moodle_xml.py [ordner] [--varianten 8]

Ergebnis: ausgabe/moodle/fragen/<datei>.xml – in Moodle: Kurs › Mehr › Fragensammlung › Import,
Format „Moodle-XML“, „Kategorie aus Datei übernehmen“ anhaken. Danach die Fragen in einen Test einbauen.

Fragetypen (Format siehe referenzen/schema.md):
    single_choice   → Multiple-Choice (eine Antwort)
    multiple_choice → Multiple-Choice (mehrere Antworten, falsche Kreuze geben Abzug)
    zuordnung       → Zuordnung
    reihenfolge     → Anordnung (seit Moodle 4.4 im Standard; in 4.2 als Zusatz-Plugin qtype_ordering)
    lueckentext     → Lückentext (Cloze) mit allen akzeptierten Schreibweisen
    zahl            → Lückentext (Cloze, NUMERICAL); mit Parametern mehrere Varianten in einer
                      Unterkategorie → im Test als „Zufallsfrage aus dieser Kategorie“ einbinden
    offen           → Freitext; Musterlösung und Checkliste als Bewertungshinweis und Feedback

Kategorien: top/<Kurstitel>/<Modul> (Feld „modul“ der Frage) bzw. top/<Kurstitel>/<Dateiname>.
Die Fragen-ID wird zur Moodle-ID-Nummer, damit Aktualisierungen zuordenbar bleiben.
Bilder: ![Text](material/bild.png) – werden in die Frage eingebettet.
"""
import ast
import base64
import itertools
import math
import operator
import random
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from xml.sax.saxutils import escape

from markdown_it import MarkdownIt

from gemeinsam import Fehler, Kurs, kurs_aus_argumenten, lies_yaml, melde_fehler_und_ende

# ---------------------------------------------------------------- Markdown → HTML

# CommonMark + GFM-Tabellen – wie die remark-Pipeline des Lernpfads (Listen ohne Leerzeile davor usw.)
MD = MarkdownIt("commonmark").enable("table")


def md(text, bilder=None):
    """Markdown nach HTML. Formeln $…$ → \\(…\\) für den MathJax-Filter von Moodle.
    Bilder (material/…) werden eingebettet und als @@PLUGINFILE@@ referenziert."""
    if not text:
        return ""
    t = str(text)
    t = re.sub(r"\$\$(.+?)\$\$", r"\\\\[\1\\\\]", t, flags=re.S)
    t = re.sub(r"(?<![\\$])\$([^$\n]+?)\$", r"\\\\(\1\\\\)", t)
    html = MD.render(t)
    if bilder is not None:
        def repl(m):
            src = m.group(1)
            if src.startswith("material/"):
                name = src.split("/")[-1]
                bilder.append(src)
                return f'src="@@PLUGINFILE@@/{name}"'
            return m.group(0)
        html = re.sub(r'src="([^"]+)"', repl, html)
    return html


def md_inline(text):
    """Wie md(), aber ohne umschließendes <p> (für Listen und Kurztexte)."""
    h = md(text).strip()
    if h.startswith("<p>") and h.endswith("</p>") and h.count("<p>") == 1:
        h = h[3:-4]
    return h


def cdata(html):
    return "<![CDATA[" + html.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def text_el(tag, html, fmt="html", extra="", dateien_xml=""):
    """Textfeld; eingebettete Bilder (<file>) gehören in Moodle-XML *in* das Feld, das sie zeigt."""
    return f'<{tag} format="{fmt}"{extra}><text>{cdata(html)}</text>{dateien_xml}</{tag}>'


# ---------------------------------------------------------------- Zahlen und Formeln

def runde(x, stellen):
    """Kaufmännisch runden (halbe Werte vom Nullpunkt weg) – wie im Lernpfad."""
    q = Decimal(1).scaleb(-stellen)
    return float(Decimal(repr(x)).quantize(q, rounding=ROUND_HALF_UP))


FUNKTIONEN = {
    "abs": abs, "sqrt": math.sqrt, "min": min, "max": max, "floor": math.floor, "ceil": math.ceil,
    "round": lambda x, d=0: runde(x, int(d)), "ln": math.log, "log10": math.log10, "exp": math.exp,
}
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}


def berechne(formel, werte):
    """Kleiner, sicherer Auswerter (kein eval): nur Zahlen, Namen, + - * / ^, Klammern, erlaubte Funktionen."""
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.Name):
            return werte[n.id]
        if isinstance(n, ast.BinOp) and type(n.op) in OPS:
            return OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in OPS:
            return OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNKTIONEN:
            return FUNKTIONEN[n.func.id](*[ev(a) for a in n.args])
        raise ValueError(f"Nicht erlaubt in Formel: {formel}")
    return ev(ast.parse(formel.replace("^", "**"), mode="eval"))


def stellen_von(x):
    s = repr(float(x))
    return 0 if s.endswith(".0") else len(s.split(".")[1])


def werte_von(d):
    st = max(stellen_von(d["min"]), stellen_von(d["schritt"]))
    n = int((d["max"] - d["min"]) / d["schritt"] + 1e-9) + 1
    return [round(d["min"] + i * d["schritt"], st) for i in range(n)]


def format_de(x, nachkomma=None):
    if nachkomma is None:
        s = f"{x:.6f}".rstrip("0").rstrip(".")
    else:
        s = f"{x:.{nachkomma}f}"
    ganz, _, frac = s.partition(".")
    neg = ganz.startswith("-")
    ganz = ganz.lstrip("-")
    gruppen = []
    while len(ganz) > 3:
        gruppen.insert(0, ganz[-3:])
        ganz = ganz[:-3]
    gruppen.insert(0, ganz)
    out = ".".join(gruppen) + ("," + frac if frac else "")
    return ("−" if neg and float(x) != 0 else "") + out


PLATZHALTER = re.compile(r"\{\{\s*([a-z][a-z0-9_]*)\s*\}\}")


def fuelle(text, werte, nachkomma):
    return PLATZHALTER.sub(lambda m: format_de(werte[m.group(1)], nachkomma.get(m.group(1)))
                           if m.group(1) in werte else m.group(0), text)


# ---------------------------------------------------------------- Moodle-Bausteine

ERLAUBTE_BRUECHE = [100, 90, 83.33333, 80, 75, 70, 66.66667, 60, 50, 40, 33.33333, 30, 25, 20,
                    16.66667, 14.28571, 12.5, 11.11111, 10, 5, 0]


def bruch(p):
    """Auf die Prozentwerte runden, die Moodle beim Import akzeptiert."""
    s = -1 if p < 0 else 1
    return s * min(ERLAUBTE_BRUECHE, key=lambda f: abs(f - abs(p)))


def fmt_bruch(f):
    return f"{f:.7f}".rstrip("0").rstrip(".") if f % 1 else str(int(f))


def kopf(a, name=None, idnumber=None):
    return (f"<name><text>{escape(name or (a['id'] + ' · ' + a['titel']))}</text></name>\n"
            f"<idnumber>{escape(idnumber or a['id'])}</idnumber>\n")


def tags(a):
    t = [f"niveau-{a.get('niveau', 1)}", a["typ"], a.get("review", "entwurf")]
    return "<tags>" + "".join(f"<tag><text>{escape(x)}</text></tag>" for x in t) + "</tags>\n"


def dateien(bilder, modulordner):
    out = []
    for src in dict.fromkeys(bilder):
        p = modulordner / src
        data = base64.b64encode(p.read_bytes()).decode()
        out.append(f'<file name="{escape(p.name)}" path="/" encoding="base64">{data}</file>')
    return "\n".join(out)


def frage(typ, inhalt):
    return f'<question type="{typ}">\n{inhalt}</question>\n'


def feedback_text(a, bilder):
    return md(a.get("erklaerung", ""), bilder)


def fragetext_el(html, bilder, ordner):
    return text_el("questiontext", html, dateien_xml=dateien(bilder, ordner))


def feedback_el(html, bilder, ordner):
    return text_el("generalfeedback", html, dateien_xml=dateien(bilder, ordner))


# ---------------------------------------------------------------- Aufgabentypen

def q_choice(a, ordner):
    bilder = []
    opts = a["optionen"]
    richtig = [o for o in opts if o["korrekt"]]
    einzeln = a["typ"] == "single_choice"
    falsch_n = len(opts) - len(richtig)
    antworten = []
    for o in opts:
        if o["korrekt"]:
            f = 100 if einzeln else bruch(100 / len(richtig))
        else:
            f = 0 if einzeln else -bruch(100 / max(falsch_n, 1))
        antworten.append(f'<answer fraction="{fmt_bruch(f)}" format="html"><text>{cdata(md(o["text"]))}</text>'
                         f'{text_el("feedback", md(o.get("feedback", "")))}</answer>')
    qt = md(a["aufgabe"], bilder)
    fb_bilder = []
    return frage("multichoice",
                 kopf(a) + fragetext_el(qt, bilder, ordner) + "\n" +
                 feedback_el(feedback_text(a, fb_bilder), fb_bilder, ordner) + "\n" +
                 "<defaultgrade>1</defaultgrade><penalty>0.3333333</penalty><hidden>0</hidden>\n" +
                 f"<single>{'true' if einzeln else 'false'}</single>\n"
                 f"<shuffleanswers>{'true' if a.get('mischen', True) else 'false'}</shuffleanswers>\n"
                 "<answernumbering>abc</answernumbering><showstandardinstruction>1</showstandardinstruction>\n" +
                 "\n".join(antworten) + "\n" + tags(a))


def q_zuordnung(a, ordner):
    bilder = []
    subs = []
    for e in a["elemente"]:
        subs.append(f'<subquestion format="html"><text>{cdata(md(e["text"]))}</text>'
                    f'<answer><text>{escape(e["kategorie"])}</text></answer></subquestion>')
    # Kategorien ohne Element als Ablenker ergänzen
    benutzt = {e["kategorie"] for e in a["elemente"]}
    for k in a["kategorien"]:
        if k not in benutzt:
            subs.append(f'<subquestion format="html"><text></text><answer><text>{escape(k)}</text></answer></subquestion>')
    # Feedback je Element gibt es in Moodle nicht → gesammelt ins allgemeine Feedback
    liste = "".join(f"<li><strong>{md_inline(e['text'])}</strong> → {escape(e['kategorie'])}: {md_inline(e.get('feedback', ''))}</li>"
                    for e in a["elemente"] if e.get("feedback"))
    fb_bilder = []
    fb = feedback_text(a, fb_bilder) + (f"<ul>{liste}</ul>" if liste else "")
    return frage("matching",
                 kopf(a) + fragetext_el(md(a["aufgabe"], bilder), bilder, ordner) + "\n" +
                 feedback_el(fb, fb_bilder, ordner) + "\n" +
                 "<defaultgrade>1</defaultgrade><penalty>0.3333333</penalty><hidden>0</hidden>\n"
                 "<shuffleanswers>true</shuffleanswers>\n" +
                 text_el("correctfeedback", "") + text_el("partiallycorrectfeedback", "") +
                 text_el("incorrectfeedback", "") + "<shownumcorrect/>\n" +
                 "\n".join(subs) + "\n" + tags(a))


def q_reihenfolge(a, ordner):
    bilder = []
    antworten = "\n".join(f'<answer fraction="{i}" format="html"><text>{cdata(md(e))}</text></answer>'
                          for i, e in enumerate(a["elemente"], 1))
    fb_bilder = []
    return frage("ordering",
                 kopf(a) + fragetext_el(md(a["aufgabe"], bilder), bilder, ordner) + "\n" +
                 feedback_el(feedback_text(a, fb_bilder), fb_bilder, ordner) + "\n" +
                 "<defaultgrade>1</defaultgrade><penalty>0.3333333</penalty><hidden>0</hidden>\n"
                 "<layouttype>VERTICAL</layouttype><selecttype>ALL</selecttype><selectcount>0</selectcount>\n"
                 "<gradingtype>ABSOLUTE_POSITION</gradingtype><showgrading>SHOW</showgrading>"
                 "<numberingstyle>none</numberingstyle>\n" +
                 text_el("correctfeedback", md(a.get("feedback_richtig", ""))) +
                 text_el("partiallycorrectfeedback", md(a.get("feedback_falsch", ""))) +
                 text_el("incorrectfeedback", md(a.get("feedback_falsch", ""))) + "<shownumcorrect/>\n" +
                 antworten + "\n" + tags(a))


def cloze_esc(s):
    return re.sub(r'([}#~/"\\])', r"\\\1", str(s))


def schreibweisen(wort):
    """Der Lernpfad setzt Bindestrich = Leerzeichen gleich; Moodle braucht jede Variante einzeln."""
    v = {wort, wort.replace("-", " "), re.sub(r"\s+", "-", wort)}
    return [x for x in v if x.strip()]


def q_lueckentext(a, ordner):
    bilder = []
    text = md(a["text"], bilder)
    nummer = {}

    def luecke(m):
        name = m.group(1)
        d = a["luecken"][name]
        nummer[name] = True
        teile = []
        for w in d["akzeptiert"]:
            for v in schreibweisen(w):
                if all(cloze_esc(v) != t.split("%100%")[-1] for t in teile):
                    teile.append("%100%" + cloze_esc(v))
        if d.get("hinweis"):
            teile.append("%0%*#" + cloze_esc(d["hinweis"]))
        return "{1:SHORTANSWER:" + "~".join(teile) + "}"

    text = PLATZHALTER.sub(luecke, text)
    qt = md(a["aufgabe"], bilder) + text
    fb_bilder = []
    return frage("cloze",
                 kopf(a) + fragetext_el(qt, bilder, ordner) + "\n" +
                 feedback_el(feedback_text(a, fb_bilder), fb_bilder, ordner) + "\n" +
                 "<penalty>0.3333333</penalty><hidden>0</hidden>\n" + tags(a))


def q_offen(a, ordner):
    bilder, fb_bilder = [], []
    ml = md(a.get("musterloesung", ""), fb_bilder)
    cl = "".join(f"<li>{md_inline(c)}</li>" for c in a.get("checkliste", []))
    hinweis = f"<h4>Musterlösung</h4>{ml}" + (f"<h4>Checkliste</h4><ul>{cl}</ul>" if cl else "")
    if a.get("kriterien"):  # Erwartungshorizont mit Punkten je Kriterium (Klausuren)
        zeilen = "".join(f"<tr><td>{md_inline(k['kriterium'])}</td><td>{format_de(k['punkte'])}</td></tr>"
                         for k in a["kriterien"])
        hinweis = ("<h4>Erwartungshorizont</h4><table border=\"1\" cellpadding=\"4\"><tr><th>Kriterium</th>"
                   f"<th>Punkte</th></tr>{zeilen}</table>") + hinweis
    fb = hinweis + feedback_text(a, fb_bilder)
    return frage("essay",
                 kopf(a) + fragetext_el(md(a["aufgabe"], bilder), bilder, ordner) + "\n" +
                 feedback_el(fb, fb_bilder, ordner) + "\n" +
                 f"<defaultgrade>{a.get('punkte', 1)}</defaultgrade><penalty>0</penalty><hidden>0</hidden>\n"
                 "<responseformat>editor</responseformat><responserequired>1</responserequired>"
                 f"<responsefieldlines>{int(a.get('zeilen', 15))}</responsefieldlines>"
                 f"<minwordlimit>{a.get('min_woerter', '')}</minwordlimit>"
                 f"<maxwordlimit>{a.get('max_woerter', '')}</maxwordlimit>"
                 "<attachments>0</attachments><attachmentsrequired>0</attachmentsrequired>"
                 "<maxbytes>0</maxbytes><filetypeslist></filetypeslist>\n" +
                 text_el("graderinfo", hinweis) + text_el("responsetemplate", md(a.get("vorlage", ""))) + "\n" + tags(a))


def zahl_variante(a, werte, ordner, name=None, idnumber=None):
    bilder = []
    ergebnis = dict(werte)
    nachkomma = {}
    felder = []
    for i, ant in enumerate(a["antworten"], 1):
        x = runde(berechne(ant["formel"], ergebnis), ant.get("runden", 0))
        ergebnis[ant["id"]] = x
        nachkomma[ant["id"]] = ant.get("runden", 0)
        tol = ant.get("toleranz", 0)
        feld = "{1:NUMERICAL:=" + repr(x) + ":" + repr(tol) + "}"
        felder.append(f"<p>{escape(ant['label'])}: {feld} {escape(ant.get('einheit', ''))}</p>")
    qt = md(fuelle(a["aufgabe"], werte, {}), bilder)
    qt += "<p><em>Dezimalzahlen mit Komma eingeben, z. B. 12,5.</em></p>" + "".join(felder)
    fb_bilder = []
    weg = md(fuelle(a.get("loesungsweg", ""), ergebnis, nachkomma), fb_bilder)
    fb = (f"<h4>Lösungsweg</h4>{weg}" if weg else "") + feedback_text(a, fb_bilder)
    return frage("cloze",
                 kopf(a, name, idnumber) + fragetext_el(qt, bilder, ordner) + "\n" +
                 feedback_el(fb, fb_bilder, ordner) + "\n" +
                 "<penalty>0.3333333</penalty><hidden>0</hidden>\n" + tags(a))


def zahl_varianten(a, anzahl):
    params = a.get("parameter") or {}
    if not params:
        return [{}]
    namen = list(params)
    raum = [werte_von(params[n]) for n in namen]
    gesamt = math.prod(len(r) for r in raum)
    rng = random.Random(a["id"])  # gleiche Varianten bei jedem Lauf
    if gesamt <= anzahl:
        kombis = list(itertools.product(*raum))
    else:
        kombis = set()
        while len(kombis) < anzahl:
            kombis.add(tuple(rng.choice(r) for r in raum))
        kombis = sorted(kombis)
    return [dict(zip(namen, k)) for k in kombis]


# ---------------------------------------------------------------- Kategorien und Ablauf

def kategorie(pfad, info=""):
    pfad_esc = "/".join(t.replace("/", "//") for t in pfad)
    return (f'<question type="category">\n<category><text>{escape(pfad_esc)}</text></category>\n'
            f'{text_el("info", info)}\n</question>\n')


def fragen_xml(kurs, datei, varianten):
    aufgaben = lies_yaml(datei, []) or []
    ordner = kurs.ordner
    out = ['<?xml version="1.0" encoding="UTF-8"?>\n<quiz>\n']
    statistik = {}
    gruppen = {}
    for a in aufgaben:
        a.setdefault("titel", a.get("id", ""))
        gruppen.setdefault(a.get("modul") or "", []).append(a)
    reihe = sorted(gruppen, key=lambda m: kurs.reihenfolge.index(m) if m in kurs.reihenfolge else 999)
    for mid in reihe:
        if mid in kurs.module:
            name = f"{mid.upper()} {kurs.module[mid]['titel']}"
        else:
            name = datei.stem
        pfad = ["top", kurs.titel, name]
        out.append(kategorie(pfad))
        spaeter = []
        for a in gruppen[mid]:
            statistik[a["typ"]] = statistik.get(a["typ"], 0) + 1
            if a["typ"] in ("single_choice", "multiple_choice"):
                out.append(q_choice(a, ordner))
            elif a["typ"] == "zuordnung":
                out.append(q_zuordnung(a, ordner))
            elif a["typ"] == "reihenfolge":
                out.append(q_reihenfolge(a, ordner))
            elif a["typ"] == "lueckentext":
                out.append(q_lueckentext(a, ordner))
            elif a["typ"] == "offen":
                out.append(q_offen(a, ordner))
            elif a["typ"] == "zahl":
                vs = zahl_varianten(a, varianten)
                if len(vs) == 1:
                    out.append(zahl_variante(a, vs[0], ordner))
                else:
                    spaeter.append((a, vs))
            else:
                raise Fehler(f"fragen/{datei.name}: unbekannter Typ {a['typ']} in {a.get('id')}")
        for a, vs in spaeter:
            out.append(kategorie(pfad + [f"{a['id']} {a['titel']} (Varianten)"],
                                 "<p>Varianten derselben Rechenaufgabe mit anderen Zahlen. "
                                 "Im Test als <strong>Zufallsfrage aus dieser Kategorie</strong> einbinden.</p>"))
            for i, w in enumerate(vs, 1):
                out.append(zahl_variante(a, w, ordner, name=f"{a['id']} · {a['titel']} (Variante {i})",
                                         idnumber=f"{a['id']}-v{i:02d}"))
    out.append("</quiz>\n")
    return "".join(out), statistik


def baue_fragen(kurs, varianten=8, still=False):
    dateien = sorted((kurs.ordner / "fragen").glob("*.yaml"))
    ziel_ordner = kurs.ausgabe / "moodle" / "fragen"
    ergebnis = []
    for d in dateien:
        xml, stat = fragen_xml(kurs, d, varianten)
        ziel_ordner.mkdir(parents=True, exist_ok=True)
        ziel = ziel_ordner / f"{d.stem}.xml"
        ziel.write_text(xml, encoding="utf-8")
        ergebnis.append(ziel)
        if not still:
            print(f"  {ziel.name}: " + ", ".join(f"{v}× {k}" for k, v in sorted(stat.items())))
    return ergebnis


def main(argv=None):
    ap = kurs_aus_argumenten(argv, __doc__)
    ap.add_argument("--varianten", type=int, default=8, help="Varianten je Rechenaufgabe mit Parametern")
    args = ap.parse_args(argv)
    try:
        kurs = Kurs(args.ordner)
        n = baue_fragen(kurs, args.varianten)
    except Fehler as e:
        melde_fehler_und_ende(e)
    if not n:
        print("Keine Fragen gefunden (fragen/*.yaml).")
    else:
        print(f"✓ {len(n)} Datei(en) in {kurs.ausgabe / 'moodle' / 'fragen'}")


if __name__ == "__main__":
    main()
