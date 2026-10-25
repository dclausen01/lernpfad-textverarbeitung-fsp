"""Erzeugt die Musterlösung des Basistexts „Medien in der Kita“ als Word-Datei (material/musterloesung-basistext.docx).

    python3 lehrkraft/musterloesung.py

Die Datei erfüllt alle Vorgaben der Richtlinien und besteht den Dokument-Prüfer ohne Fehler – sie dient als Lösung für die
Lehrkraft und als Testfall für den Prüfer. Gekürzter Text; die Quellen sind ausgedacht.
"""
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

d = Document()
st = d.styles


def schrift(stil, groesse, fett=False):
    stil.font.name = "Arial"
    stil.font.size = Pt(groesse)
    stil.font.bold = fett
    stil.font.color.rgb = RGBColor(0, 0, 0)
    rpr = stil.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    for k in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(k), "Arial")
    for k in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rf.get(qn(k)) is not None:
            del rf.attrib[qn(k)]


normal = st["Normal"]
schrift(normal, 12)
normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
normal.paragraph_format.line_spacing = 1.5
normal.paragraph_format.space_after = Pt(6)
for i in (1, 2, 3):
    h = st[f"Heading {i}"]
    schrift(h, 14, True)
    h.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h.paragraph_format.space_before = Pt(18 if i == 1 else 12)
    h.paragraph_format.space_after = Pt(12 if i == 1 else 6)
    h.paragraph_format.line_spacing = 1.0
    h.paragraph_format.keep_with_next = True
TOC = {}
for i in (1, 2, 3):
    try:
        t = st[f"TOC {i}"]
    except KeyError:
        from docx.enum.style import WD_STYLE_TYPE
        t = st.add_style(f"TOC {i}", WD_STYLE_TYPE.PARAGRAPH)
        t.element.find(qn("w:name")).set(qn("w:val"), f"toc {i}")
    t.base_style = normal
    t.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    t.paragraph_format.left_indent = Cm(0.6 * (i - 1))
    TOC[i] = t
cap = st["Caption"]
schrift(cap, 10)
cap.font.italic = True
fn = None
from docx.enum.style import WD_STYLE_TYPE
fn = st.add_style("footnote text", WD_STYLE_TYPE.PARAGRAPH)
fn.base_style = normal
schrift(fn, 9)
fn.paragraph_format.line_spacing = 1.0
lit = st.add_style("Literatur", WD_STYLE_TYPE.PARAGRAPH)
lit.base_style = normal
lit.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
lit.paragraph_format.left_indent = Cm(1.25)
lit.paragraph_format.first_line_indent = Cm(-1.25)
titel = st["Title"]
schrift(titel, 16, True)
titel.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
titel.element.get_or_add_pPr()

# Silbentrennung
s = d.settings.element
ah = OxmlElement("w:autoHyphenation")
s.insert(0, ah)

# Nummerierung der Überschriften: 1. / 1.1 / 1.1.1
numbering = d.part.numbering_part.element
absn = OxmlElement("w:abstractNum")
absn.set(qn("w:abstractNumId"), "90")
for lvl, txt in enumerate(["%1.", "%1.%2", "%1.%2.%3"]):
    l = OxmlElement("w:lvl"); l.set(qn("w:ilvl"), str(lvl))
    for tag, val in (("w:start", "1"), ("w:numFmt", "decimal"), ("w:pStyle", f"Heading{lvl + 1}"), ("w:lvlText", txt)):
        e = OxmlElement(tag); e.set(qn("w:val"), val); l.append(e)
    absn.append(l)
numbering.insert(0, absn)
num = OxmlElement("w:num"); num.set(qn("w:numId"), "90")
a = OxmlElement("w:abstractNumId"); a.set(qn("w:val"), "90"); num.append(a)
numbering.append(num)
for i in (1, 2, 3):
    ppr = st[f"Heading {i}"].element.get_or_add_pPr()
    np_ = OxmlElement("w:numPr")
    il = OxmlElement("w:ilvl"); il.set(qn("w:val"), str(i - 1)); np_.append(il)
    ni = OxmlElement("w:numId"); ni.set(qn("w:val"), "90"); np_.append(ni)
    ppr.insert(0, np_)

sec = d.sections[0]
for k, v in (("top_margin", 2.5), ("bottom_margin", 2.5), ("left_margin", 2.5), ("right_margin", 3)):
    setattr(sec, k, Cm(v))
sec.page_width, sec.page_height = Cm(21), Cm(29.7)


def feld(p, instr, ergebnis=""):
    r = p.add_run()
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin"); r._r.append(b)
    r = p.add_run()
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr; r._r.append(it)
    r = p.add_run()
    s_ = OxmlElement("w:fldChar"); s_.set(qn("w:fldCharType"), "separate"); r._r.append(s_)
    p.add_run(ergebnis)
    r = p.add_run()
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end"); r._r.append(e)


def ohne_nummer(p):
    ppr = p._p.get_or_add_pPr()
    np_ = OxmlElement("w:numPr")
    ni = OxmlElement("w:numId"); ni.set(qn("w:val"), "0"); np_.append(ni)
    ppr.insert(1, np_)


def zentriert(text, groesse=12, fett=False, nach=6):
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(nach)
    r = p.add_run(text); r.bold = fett; r.font.size = Pt(groesse)
    return p


# Deckblatt
for t in ("Berufsbildungszentrum Rendsburg-Eckernförde", "Fachschule für Sozialpädagogik", "Röhlingsweg 60", "24768 Rendsburg"):
    zentriert(t)
p = zentriert("Übungsarbeit Textverarbeitung", 16, True)
p.paragraph_format.space_before = Pt(120)
zentriert("Digitale Medien in der Kita", 14, True, 120)
for t in ("eingereicht von: Erika Mustermann", "Klasse: FSP26b", "Betreuende Lehrkraft: Herr Beispiel", "Rendsburg, 14.11.2026"):
    q = d.add_paragraph(t); q.alignment = WD_ALIGN_PARAGRAPH.LEFT
d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

GLIEDERUNG = [(1, "Einleitung"), (1, "Medien im Alltag von Kindern"), (2, "Was Kinder zu Hause erleben"), (2, "Der Auftrag der Kita"),
              (1, "Medienarbeit in der Praxis"), (2, "Rezeptive und aktive Medienarbeit"), (2, "Ein Praxisbeispiel: das Fotoprojekt"),
              (3, "Vorbereitung"), (3, "Durchführung"), (1, "Grenzen und offene Fragen"), (1, "Fazit")]
p = d.add_paragraph(); r = p.add_run("Inhaltsverzeichnis"); r.bold = True; r.font.size = Pt(14)
# TOC-Feld mit Einträgen
erster = True
for i, (e, t) in enumerate(GLIEDERUNG + [(1, "Literaturverzeichnis"), (1, "Eigenständigkeitserklärung")]):
    q = d.add_paragraph(style=TOC[e])
    if erster:
        r = q.add_run(); b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin"); r._r.append(b)
        r = q.add_run(); it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = ' TOC \\o "1-3" \\h \\z \\u '; r._r.append(it)
        r = q.add_run(); s_ = OxmlElement("w:fldChar"); s_.set(qn("w:fldCharType"), "separate"); r._r.append(s_)
        erster = False
    q.add_run(f"{t}\t{i + 1}")
r = q.add_run(); e_ = OxmlElement("w:fldChar"); e_.set(qn("w:fldCharType"), "end"); r._r.append(e_)

# Abschnittswechsel: neuer Abschnitt mit Seitenzahl ab 1
neu = d.add_section(WD_SECTION.NEW_PAGE)
neu.footer.is_linked_to_previous = False
fp = neu.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
feld(fp, " PAGE ", "1")
pg = OxmlElement("w:pgNumType"); pg.set(qn("w:start"), "1"); neu._sectPr.append(pg)

TEXT = {
    "Einleitung": "Kaum ein Thema wird in Kindertagesstätten so kontrovers diskutiert wie der Umgang mit digitalen Medien. Während die einen vor zu früher Bildschirmzeit warnen, verweisen andere darauf, dass Kinder längst in einer von Medien geprägten Welt aufwachsen und Begleitung brauchen. Diese Arbeit geht der Frage nach, welche Rolle digitale Medien in der frühkindlichen Bildung sinnvoll einnehmen können.",
    "Was Kinder zu Hause erleben": "Digitale Geräte gehören für die meisten Kinder zum familiären Alltag, lange bevor sie in die Kita kommen. Viele Kinder nutzen bereits im Vorschulalter regelmäßig ein Tablet oder Smartphone, meist zum Ansehen von Videos. Tabelle 1 zeigt, wie unterschiedlich das in einer Einrichtung aussehen kann.",
    "Der Auftrag der Kita": "Bildungspläne der Länder benennen Medienbildung inzwischen ausdrücklich als Aufgabe der frühkindlichen Bildung. Im Vordergrund steht die Frage, wie Kinder Medien verstehen, einordnen und selbst gestalten lernen. Reimann formuliert es zugespitzt: „Medienbildung beginnt nicht mit dem Gerät, sondern mit dem Gespräch über das Gesehene“ (Reimann, 2021, S. 47).",
    "Rezeptive und aktive Medienarbeit": "In der Fachliteratur wird zwischen rezeptiver und aktiver Medienarbeit unterschieden. Gerade die aktive Medienarbeit gilt als besonders wirksam, weil Kinder dabei erfahren, dass Medieninhalte gemacht werden und nicht einfach vorhanden sind (Bauer, Ott, 2023, S. 21).",
    "Vorbereitung": "Vor dem Projektstart klärt das Team die organisatorischen Fragen: Welche Geräte stehen zur Verfügung, wo werden die Bilder gespeichert und wie wird der Datenschutz gewahrt? Die Eltern werden schriftlich informiert.",
    "Durchführung": "Die Kinder erhalten den Auftrag, ihren Lieblingsort in der Kita zu fotografieren. Jede Kleingruppe bekommt eine Kamera und eine Fachkraft als Begleitung. Zum Abschluss entsteht eine Ausstellung im Flur der Einrichtung.",
    "Grenzen und offene Fragen": "Medienarbeit in der Kita stößt an praktische Grenzen. Viele Einrichtungen verfügen weder über ausreichende Geräte noch über stabiles Internet. Fortbildungen sind deshalb eine wichtige Voraussetzung.",
    "Fazit": "Digitale Medien gehören zur Lebenswelt von Kindern und lassen sich aus der Kita nicht heraushalten. Entscheidend ist nicht die Frage nach dem Ob, sondern die nach dem Wie.",
}
erste_ueberschrift = True
for e, t in GLIEDERUNG:
    d.add_heading(t, e)
    if t in TEXT:
        d.add_paragraph(TEXT[t])
    if t == "Was Kinder zu Hause erleben":
        c = d.add_paragraph(style="Caption"); c.add_run("Tabelle "); feld(c, " SEQ Tabelle \\* ARABIC ", "1"); c.add_run(": Mediennutzung in einer Kita (eigene Darstellung)")
        tb = d.add_table(rows=3, cols=3)
        for zi, zeile in enumerate([("Medium", "täglich", "selten"), ("Bilderbuch", "14", "2"), ("Video", "9", "4")]):
            for si, w in enumerate(zeile):
                tb.cell(zi, si).text = w
        d.add_paragraph("Die Zahlen sind fiktiv und dienen nur der Übung.")
lp = d.add_heading("Literaturverzeichnis", 1); ohne_nummer(lp)
lp.paragraph_format.page_break_before = True
d.add_paragraph("Bauer, N., Ott, H. (2023). Aktive Medienarbeit in der Kita. Frühe Bildung heute. Heft 2. S. 18-26.", style="Literatur")
d.add_paragraph("Reimann, K. (2021). Medienbildung in der frühen Kindheit. Kiel: Fachverlag Nord.", style="Literatur")
ep = d.add_heading("Eigenständigkeitserklärung", 1); ohne_nummer(ep)
ep.paragraph_format.page_break_before = True
d.add_paragraph("Hiermit versichere ich, Erika Mustermann, dass ich die vorliegende Arbeit selbstständig und ohne die Benutzung anderer als der angegebenen Hilfsmittel angefertigt habe.")
ziel = Path(__file__).resolve().parent.parent / "material" / "musterloesung-basistext.docx"
d.core_properties.author = ""
d.save(ziel)
print("✓", ziel)
