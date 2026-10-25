"""Moodle-Tests in der Kurssicherung: tests: in kurs.yaml → Aktivität „Test“ samt Fragen in der .mbz.

Wird von moodle_kurs.py / mbz.py benutzt, kein eigener Aufruf nötig.

    tests:
      - id: test-zitieren                 # eindeutig (auch für freischalten_nach)
        titel: "Test: Belege und Literaturverzeichnis"
        nach: w1                          # Test direkt hinter diesem Modul – oder stufe: <id> (ans Ende der Stufe)
        fragen: zitieren                  # fragen/zitieren.yaml (auch Liste: [datei1, datei2])
        auswahl: [zit-01, zit-02]         # optional: nur diese Fragen; ohne: [zit-21] lässt Fragen weg
        punkte: 10                        # Bewertung des Tests (Standard 10)
        bestehen: 60                      # optional, Prozent: Abschluss erst ab dieser Bewertung
        versuche: 0                       # 0 = unbegrenzt
        zeit: 0                           # Minuten, 0 = ohne Zeitbegrenzung
        pro_seite: 1                      # Fragen je Seite (0 = alle auf einer Seite)
        mischen: false                    # Reihenfolge der Fragen mischen
        feedback: nachher                 # nachher (Standard) | sofort (Rückmeldung nach jeder Frage)
                                          # | punkte (nur Punkte nachher) | keine (nichts sichtbar, für Klausuren)
        # nur über klausur.py: oeffnen/schliessen (Unix-Zeit), kennwort, navigation: nacheinander,
        # abschnitte: [(Überschrift, erster Slot)] – Teile mit Überschrift
        text: Markdown-Beschreibung

Die Fragen kommen aus fragen/*.yaml – genau wie beim Moodle-XML (moodle_xml.py), nur fest eingebaut:
Kategorie top/<Kurs>/<Testtitel>. Rechenaufgaben mit Varianten werden eine Zufallsfrage aus ihrer
Unterkategorie. Ohne --entwuerfe kommen nur Fragen mit review: freigegeben in den Test.
Moodle 4: Fragen im Kurs-Fragenpool. Moodle 5: in einer eigenen Fragensammlung (Aktivität „qbank“).
Grenzen: „reihenfolge“ (Anordnung) gibt es in Moodle 4.2 nicht im Standard → wird dort ausgelassen.
Offene Fragen (offen) muss die Lehrkraft von Hand bewerten; bis dahin gilt „bestehen“ als nicht erreicht.
"""
import base64
import hashlib
import json
import re
import xml.etree.ElementTree as ET

from gemeinsam import Fehler, lies_yaml
import moodle_xml as mx

NULL = "$@NULL@$"


def x(v):
    from xml.sax.saxutils import escape
    return NULL if v is None else escape(str(v))


# ---------------------------------------------------------------- Fragen auswählen und umwandeln

def _text(el, tag):
    t = el.find(tag)
    if t is None:
        return "", []
    txt = t.findtext("text") or ""
    files = [(f.get("name"), base64.b64decode(f.text or "")) for f in t.findall("file")]
    return txt, files


def _num(el, tag, standard):
    v = el.findtext(tag)
    return float(v) if v not in (None, "") else standard


CLOZE = re.compile(r"\{(\d*):(SHORTANSWER|SA|MW|NUMERICAL|NM|MULTICHOICE|MC):((?:\\.|[^}])*)\}")


def _cloze_teile(roh):
    """„%100%a~%0%*#Hinweis“ → [(bruch, antwort, feedback)] (Moodles Cloze-Syntax, \\ maskiert)."""
    teile, akt, i = [], "", 0
    while i < len(roh):
        if roh[i] == "\\" and i + 1 < len(roh):
            akt += roh[i:i + 2]
            i += 2
            continue
        if roh[i] == "~":
            teile.append(akt)
            akt = ""
        else:
            akt += roh[i]
        i += 1
    teile.append(akt)
    out = []
    for t in teile:
        bruch = 0.0
        if t.startswith("="):
            bruch, t = 1.0, t[1:]
        else:
            m = re.match(r"%(-?[\d.]+)%", t)
            if m:
                bruch, t = float(m.group(1)) / 100, t[m.end():]
        ant, fb = t, ""
        m = re.search(r"(?<!\\)#", t)
        if m:
            ant, fb = t[:m.start()], t[m.end():]
        un = lambda s: re.sub(r"\\(.)", r"\1", s)
        out.append((bruch, un(ant), un(fb)))
    return out


def aus_moodle_xml(q):
    """<question> aus moodle_xml.py → Frage im Sicherungs-Modell."""
    typ = q.get("type")
    text, files_qt = _text(q, "questiontext")
    fb, files_fb = _text(q, "generalfeedback")
    f = dict(name=q.findtext("name/text") or "", idnumber=q.findtext("idnumber") or None,
             text=text, fb=fb, penalty=_num(q, "penalty", 0.3333333), defaultmark=_num(q, "defaultgrade", 1.0),
             files=[("questiontext", n, d) for n, d in files_qt] + [("generalfeedback", n, d) for n, d in files_fb],
             subs=[])
    if typ == "multichoice":
        f["qtype"] = "multichoice"
        f["answers"] = [(float(a.get("fraction")) / 100, a.findtext("text") or "", _text(a, "feedback")[0])
                        for a in q.findall("answer")]
        f["single"] = q.findtext("single") == "true"
        f["shuffle"] = q.findtext("shuffleanswers") != "false"
    elif typ == "matching":
        f["qtype"] = "match"
        f["matches"] = [(s.findtext("text") or "", s.findtext("answer/text") or "") for s in q.findall("subquestion")]
    elif typ == "ordering":
        f["qtype"] = "ordering"
        f["answers"] = [a.findtext("text") or "" for a in q.findall("answer")]
        f["fb_richtig"] = _text(q, "correctfeedback")[0]
        f["fb_teil"] = _text(q, "partiallycorrectfeedback")[0]
        f["fb_falsch"] = _text(q, "incorrectfeedback")[0]
    elif typ == "essay":
        f["qtype"] = "essay"
        f["graderinfo"] = _text(q, "graderinfo")[0]
        f["zeilen"] = int(_num(q, "responsefieldlines", 15))
        f["min_woerter"] = int(_num(q, "minwordlimit", 0))
        f["max_woerter"] = int(_num(q, "maxwordlimit", 0))
        f["vorlage"] = _text(q, "responsetemplate")[0]
    elif typ == "cloze":
        f["qtype"] = "multianswer"
        n = 0

        def ersetze(m):
            nonlocal n
            n += 1
            gewicht = int(m.group(1) or 1)
            art = m.group(2)
            teile = _cloze_teile(m.group(3))
            sub = dict(name=f["name"], idnumber=None, text=m.group(0), fb="", penalty=0.0, defaultmark=float(gewicht),
                       files=[], subs=[])
            if art in ("NUMERICAL", "NM"):
                sub["qtype"] = "numerical"
                sub["answers"] = []
                for bruch, ant, afb in teile:
                    wert, _, tol = ant.partition(":")
                    sub["answers"].append((bruch, wert, afb, float(tol or 0)))
            elif art in ("SHORTANSWER", "SA", "MW"):
                sub["qtype"] = "shortanswer"
                sub["answers"] = [(b, a, afb) for b, a, afb in teile]
            else:
                sub["qtype"] = "multichoice"
                sub["answers"] = [(b, a, afb) for b, a, afb in teile]
                sub["single"], sub["shuffle"] = True, False
            f["subs"].append(sub)
            return "{#%d}" % n

        f["text"] = CLOZE.sub(ersetze, text)
        f["defaultmark"] = sum(s["defaultmark"] for s in f["subs"]) or 1.0
    else:
        raise Fehler(f"Fragetyp {typ} kann nicht in einen Test übernommen werden")
    return f


def _xml_einer_frage(a, ordner, varianten):
    """Frage aus fragen/*.yaml → Liste von <question>-Elementen (mehrere nur bei Rechenaufgaben mit Varianten)."""
    t = a["typ"]
    if t in ("single_choice", "multiple_choice"):
        teile = [mx.q_choice(a, ordner)]
    elif t == "zuordnung":
        teile = [mx.q_zuordnung(a, ordner)]
    elif t == "reihenfolge":
        teile = [mx.q_reihenfolge(a, ordner)]
    elif t == "lueckentext":
        teile = [mx.q_lueckentext(a, ordner)]
    elif t == "offen":
        teile = [mx.q_offen(a, ordner)]
    elif t == "zahl":
        vs = mx.zahl_varianten(a, varianten)
        if len(vs) == 1:
            teile = [mx.zahl_variante(a, vs[0], ordner)]
        else:
            teile = [mx.zahl_variante(a, w, ordner, name=f"{a['id']} · {a['titel']} (Variante {i})",
                                      idnumber=f"{a['id']}-v{i:02d}") for i, w in enumerate(vs, 1)]
    else:
        raise Fehler(f"Unbekannter Fragetyp {t} in {a.get('id')}")
    return [ET.fromstring(s) for s in teile]


def test_fragen(kurs, test, version, entwuerfe=False, varianten=8, hinweise=None):
    """tests:-Eintrag → Liste von Gruppen: {"frage": f} oder {"zufall": [f, …], "name": …}."""
    hinweise = hinweise if hinweise is not None else []
    dateien = test.get("fragen")
    if not dateien:
        raise Fehler(f"Test {test.get('id')}: „fragen:“ fehlt (Dateiname in fragen/ ohne .yaml)")
    dateien = [dateien] if isinstance(dateien, str) else dateien
    auswahl, ohne = test.get("auswahl"), set(test.get("ohne") or [])
    alle = {}
    for d in dateien:
        p = kurs.ordner / "fragen" / f"{d}.yaml"
        if not p.exists():
            raise Fehler(f"Test {test['id']}: fragen/{d}.yaml gibt es nicht")
        for a in lies_yaml(p, []) or []:
            a.setdefault("titel", a.get("id", ""))
            alle[a["id"]] = a
    ids = list(auswahl) if auswahl else list(alle)
    gruppen = []
    for qid in ids:
        if qid not in alle:
            raise Fehler(f"Test {test['id']}: Frage {qid} gibt es in {', '.join(dateien)} nicht")
        a = alle[qid]
        if qid in ohne:
            continue
        if not entwuerfe and a.get("review", "entwurf") != "freigegeben":
            hinweise.append(f"{qid} ausgelassen (nicht freigegeben)")
            continue
        if a["typ"] == "reihenfolge" and version == "4":
            hinweise.append(f"{qid} ausgelassen (Anordnung gibt es in Moodle 4.2 nicht im Standard)")
            continue
        fs = [aus_moodle_xml(q) for q in _xml_einer_frage(a, kurs.ordner, varianten)]
        if len(fs) == 1:
            gruppen.append({"frage": fs[0]})
        else:
            gruppen.append({"zufall": fs, "name": f"{a['id']} {a['titel']} (Varianten)"})
    if not gruppen:
        raise Fehler(f"Test {test['id']}: keine Frage übrig (freigegeben?)")
    return gruppen


# ---------------------------------------------------------------- Fragenpool in der Sicherung

class Fragenpool:
    """Kategorien und Fragen einer Sicherung. kontext = (contextid, contextlevel, instanceid)."""

    def __init__(self, sicherung, kursname):
        self.s = sicherung
        self.kursname = kursname
        self.kontext = None
        self.kategorien = []   # {id, name, parent, info, entries: [frage…]}
        self._n = {"kat": 10, "q": 100, "ans": 1000, "opt": 10, "file": 0}
        self.top = self.kurs = None

    def nid(self, art):
        self._n[art] += 1
        return self._n[art]

    def kategorie(self, name, parent, info=""):
        k = dict(id=self.nid("kat"), name=name, parent=parent, info=info, entries=[])
        self.kategorien.append(k)
        return k

    def bereit(self, kontext):
        if self.kontext is None:
            self.kontext = kontext
            self.top = self.kategorie("top", 0)
            self.kurs = self.kategorie(self.kursname, self.top["id"])

    def frage(self, kat, f, parent=0):
        f = dict(f)
        f["id"] = self.nid("q")
        f["parent"] = parent
        kat["entries"].append(f)
        for area, name, data in f["files"]:
            self.s.frage_datei(self.kontext[0], area, f["id"], name, data)
        if f["qtype"] == "multianswer":
            f["sequence"] = [self.frage(kat, sub, parent=f["id"])["id"] for sub in f["subs"]]
        return f

    def test(self, titel, gruppen):
        """Legt die Kategorie des Tests an; Rückgabe: Slots [(art, ref, maxmark)]."""
        kat = self.kategorie(titel, self.kurs["id"])
        slots = []
        for g in gruppen:
            if "frage" in g:
                f = self.frage(kat, g["frage"])
                slots.append(("frage", f["id"], f["defaultmark"]))
            else:
                sub = self.kategorie(g["name"], kat["id"],
                                     "<p>Gleichwertige Varianten für denselben Aufgabenplatz (andere Zahlen oder alternative Aufgaben) – im Test als Zufallsfrage.</p>")
                for v in g["zufall"]:
                    self.frage(sub, v)
                slots.append(("zufall", sub["id"], g["zufall"][0]["defaultmark"]))
        return slots


def _antworten(ans, mit_format=0):
    return "\n".join(f"""                    <answer id="{aid}">
                      <answertext>{x(text)}</answertext>
                      <answerformat>{mit_format}</answerformat>
                      <fraction>{bruch:.7f}</fraction>
                      <feedback>{x(fb)}</feedback>
                      <feedbackformat>1</feedbackformat>
                    </answer>""" for aid, bruch, text, fb in ans)


def _plugin(p, f):
    t = f["qtype"]
    if t == "multichoice":
        ans = [(p.nid("ans"), b, txt, fb) for b, txt, fb in f["answers"]]
        return f"""                <plugin_qtype_multichoice_question>
                  <answers>
{_antworten(ans, 1)}
                  </answers>
                  <multichoice id="{p.nid('opt')}">
                    <layout>0</layout>
                    <single>{1 if f['single'] else 0}</single>
                    <shuffleanswers>{1 if f['shuffle'] else 0}</shuffleanswers>
                    <correctfeedback></correctfeedback>
                    <correctfeedbackformat>1</correctfeedbackformat>
                    <partiallycorrectfeedback></partiallycorrectfeedback>
                    <partiallycorrectfeedbackformat>1</partiallycorrectfeedbackformat>
                    <incorrectfeedback></incorrectfeedback>
                    <incorrectfeedbackformat>1</incorrectfeedbackformat>
                    <answernumbering>{'abc' if f['parent'] == 0 else 'none'}</answernumbering>
                    <shownumcorrect>0</shownumcorrect>
                    <showstandardinstruction>{1 if f['parent'] == 0 else 0}</showstandardinstruction>
                  </multichoice>
                </plugin_qtype_multichoice_question>"""
    if t == "match":
        m = "\n".join(f"""                    <match id="{p.nid('ans')}">
                      <questiontext>{x(q)}</questiontext>
                      <questiontextformat>1</questiontextformat>
                      <answertext>{x(a)}</answertext>
                    </match>""" for q, a in f["matches"])
        return f"""                <plugin_qtype_match_question>
                  <matchoptions id="{p.nid('opt')}">
                    <shuffleanswers>1</shuffleanswers>
                    <correctfeedback></correctfeedback>
                    <correctfeedbackformat>1</correctfeedbackformat>
                    <partiallycorrectfeedback></partiallycorrectfeedback>
                    <partiallycorrectfeedbackformat>1</partiallycorrectfeedbackformat>
                    <incorrectfeedback></incorrectfeedback>
                    <incorrectfeedbackformat>1</incorrectfeedbackformat>
                    <shownumcorrect>1</shownumcorrect>
                  </matchoptions>
                  <matches>
{m}
                  </matches>
                </plugin_qtype_match_question>"""
    if t == "ordering":
        ans = [(p.nid("ans"), float(i), txt, "") for i, txt in enumerate(f["answers"], 1)]
        return f"""                <plugin_qtype_ordering_question>
                  <answers>
{_antworten(ans, 1)}
                  </answers>
                  <ordering id="{p.nid('opt')}">
                    <layouttype>0</layouttype>
                    <selecttype>0</selecttype>
                    <selectcount>0</selectcount>
                    <gradingtype>0</gradingtype>
                    <showgrading>1</showgrading>
                    <numberingstyle>none</numberingstyle>
                    <correctfeedback>{x(f['fb_richtig'])}</correctfeedback>
                    <correctfeedbackformat>1</correctfeedbackformat>
                    <incorrectfeedback>{x(f['fb_falsch'])}</incorrectfeedback>
                    <incorrectfeedbackformat>1</incorrectfeedbackformat>
                    <partiallycorrectfeedback>{x(f['fb_teil'])}</partiallycorrectfeedback>
                    <partiallycorrectfeedbackformat>1</partiallycorrectfeedbackformat>
                    <shownumcorrect>1</shownumcorrect>
                  </ordering>
                </plugin_qtype_ordering_question>"""
    if t == "essay":
        return f"""                <plugin_qtype_essay_question>
                  <essay id="{p.nid('opt')}">
                    <responseformat>editor</responseformat>
                    <responserequired>1</responserequired>
                    <responsefieldlines>{f.get('zeilen', 15)}</responsefieldlines>
                    <minwordlimit>{f.get('min_woerter', 0)}</minwordlimit>
                    <maxwordlimit>{f.get('max_woerter', 0)}</maxwordlimit>
                    <attachments>0</attachments>
                    <attachmentsrequired>0</attachmentsrequired>
                    <graderinfo>{x(f['graderinfo'])}</graderinfo>
                    <graderinfoformat>1</graderinfoformat>
                    <responsetemplate>{x(f.get('vorlage', ''))}</responsetemplate>
                    <responsetemplateformat>1</responsetemplateformat>
                    <filetypeslist></filetypeslist>
                    <maxbytes>0</maxbytes>
                  </essay>
                </plugin_qtype_essay_question>"""
    if t == "multianswer":
        return f"""                <plugin_qtype_multianswer_question>
                  <answers>
                  </answers>
                  <multianswer id="{p.nid('opt')}">
                    <question>{f['id']}</question>
                    <sequence>{','.join(map(str, f['sequence']))}</sequence>
                  </multianswer>
                </plugin_qtype_multianswer_question>"""
    if t == "shortanswer":
        ans = [(p.nid("ans"), b, txt, fb) for b, txt, fb in f["answers"]]
        return f"""                <plugin_qtype_shortanswer_question>
                  <answers>
{_antworten(ans)}
                  </answers>
                  <shortanswer id="{p.nid('opt')}">
                    <usecase>0</usecase>
                  </shortanswer>
                </plugin_qtype_shortanswer_question>"""
    if t == "numerical":
        ans = [(p.nid("ans"), b, wert, fb, tol) for b, wert, fb, tol in f["answers"]]
        recs = "\n".join(f"""                    <numerical_record id="{i}">
                      <answer>{aid}</answer>
                      <tolerance>{tol}</tolerance>
                    </numerical_record>""" for i, (aid, _, _, _, tol) in enumerate(ans, 1))
        return f"""                <plugin_qtype_numerical_question>
                  <answers>
{_antworten([(a, b, w, fb) for a, b, w, fb, _ in ans])}
                  </answers>
                  <numerical_units>
                  </numerical_units>
                  <numerical_options>
                    <numerical_option id="{p.nid('opt')}">
                      <showunits>3</showunits>
                      <unitsleft>0</unitsleft>
                      <unitgradingtype>0</unitgradingtype>
                      <unitpenalty>1.0000000</unitpenalty>
                    </numerical_option>
                  </numerical_options>
                  <numerical_records>
{recs}
                  </numerical_records>
                </plugin_qtype_numerical_question>"""
    raise Fehler(f"Fragetyp {t} wird nicht unterstützt")


def questions_xml(p, ziel5, jetzt):
    """questions.xml der Sicherung."""
    if not p or p.kontext is None:
        return "<question_categories>\n</question_categories>"
    ctxid, level, inst = p.kontext
    out = ["<question_categories>"]
    for k in p.kategorien:
        entries = []
        for f in k["entries"]:
            stamp = "lernpfad+" + hashlib.md5(f"{p.kursname}|{k['name']}|{f['id']}".encode()).hexdigest()[:16]
            entries.append(f"""      <question_bank_entry id="{f['id']}">
        <questioncategoryid>{k['id']}</questioncategoryid>
        <idnumber>{x(f['idnumber'])}</idnumber>
        <ownerid>{NULL}</ownerid>{chr(10) + '        <nextversion>' + NULL + '</nextversion>' if ziel5 else ''}
        <question_version>
          <question_versions id="{f['id']}">
            <version>1</version>
            <status>ready</status>
            <questions>
              <question id="{f['id']}">
                <parent>{f['parent']}</parent>
                <name>{x(f['name'])}</name>
                <questiontext>{x(f['text'])}</questiontext>
                <questiontextformat>1</questiontextformat>
                <generalfeedback>{x(f['fb'])}</generalfeedback>
                <generalfeedbackformat>1</generalfeedbackformat>
                <defaultmark>{f['defaultmark']:.7f}</defaultmark>
                <penalty>{f['penalty']:.7f}</penalty>
                <qtype>{f['qtype']}</qtype>
                <length>1</length>
                <stamp>{stamp}</stamp>
                <timecreated>{jetzt}</timecreated>
                <timemodified>{jetzt}</timemodified>
                <createdby>{NULL}</createdby>
                <modifiedby>{NULL}</modifiedby>
{_plugin(p, f)}
                <plugin_qbank_comment_question>
                  <comments>
                  </comments>
                </plugin_qbank_comment_question>
                <plugin_qbank_customfields_question>
                  <customfields>
                  </customfields>
                </plugin_qbank_customfields_question>
                <question_hints>
                </question_hints>
                <tags>
                </tags>
              </question>
            </questions>
          </question_versions>
        </question_version>
      </question_bank_entry>""")
        stamp = "lernpfad+" + hashlib.md5(f"{p.kursname}|kat|{k['id']}|{k['name']}".encode()).hexdigest()[:16]
        out.append(f"""  <question_category id="{k['id']}">
    <name>{x(k['name'])}</name>
    <contextid>{ctxid}</contextid>
    <contextlevel>{level}</contextlevel>
    <contextinstanceid>{inst}</contextinstanceid>
    <info>{x(k['info'])}</info>
    <infoformat>1</infoformat>
    <stamp>{stamp}</stamp>
    <parent>{k['parent']}</parent>
    <sortorder>{0 if k['parent'] == 0 else 999}</sortorder>
    <idnumber>{NULL}</idnumber>
    <question_bank_entries>
{chr(10).join(entries)}
    </question_bank_entries>
  </question_category>""")
    out.append("</question_categories>")
    return "\n".join(out)


def kategorien_ref(p):
    if not p or p.kontext is None:
        return ""
    ids = "\n".join(f"    <question_category>\n      <id>{k['id']}</id>\n    </question_category>" for k in p.kategorien)
    return f"  <question_categoryref>\n{ids}\n  </question_categoryref>"


# ---------------------------------------------------------------- Aktivität Test

REVIEW_ALLES = 0x10000 | 0x01000 | 0x00100 | 0x00010   # während, direkt danach, später, nach Schließen
REVIEW_NACH = 0x01000 | 0x00100 | 0x00010


def quiz_xml(a, p, ziel5, jetzt):
    t = a["test"]
    slots = a["slots"]
    pro_seite = int(t.get("pro_seite", 1))
    # Teile mit Überschrift (Klausuren): [(Überschrift, erster Slot)]; jeder Teil beginnt auf einer neuen Seite
    teile = t.get("abschnitte") or [("", 1)]
    teil_start = {fs for _, fs in teile}
    seite, auf_seite = 0, 0
    inst = []
    for i, (art, ref, maxmark) in enumerate(slots, 1):
        if seite == 0 or i in teil_start or (pro_seite and auf_seite >= pro_seite):
            seite, auf_seite = seite + 1, 0
        auf_seite += 1
        if art == "frage":
            ref_xml = f"""        <question_reference id="{i}">
          <usingcontextid>{a['contextid']}</usingcontextid>
          <component>mod_quiz</component>
          <questionarea>slot</questionarea>
          <questionbankentryid>{ref}</questionbankentryid>
          <version>{NULL}</version>
        </question_reference>"""
        else:
            if ziel5:
                fc = {"filter": {"category": {"jointype": 1, "values": [ref], "filteroptions": {"includesubcategories": 0}}},
                      "cat": f"{ref},{p.kontext[0]}", "tabname": "questions", "qpage": 0, "qperpage": 100, "jointype": 2}
            else:
                fc = {"questioncategoryid": str(ref), "includingsubcategories": 0}
            ref_xml = f"""        <question_set_reference id="{i}">
          <usingcontextid>{a['contextid']}</usingcontextid>
          <component>mod_quiz</component>
          <questionarea>slot</questionarea>
          <questionscontextid>{p.kontext[0]}</questionscontextid>
          <filtercondition>{x(json.dumps(fc, separators=(',', ':')))}</filtercondition>
        </question_set_reference>"""
        inst.append(f"""      <question_instance id="{i}">
        <quizid>{a['instanceid']}</quizid>
        <slot>{i}</slot>
        <page>{seite}</page>
        <displaynumber>{NULL}</displaynumber>
        <requireprevious>0</requireprevious>
        <maxmark>{maxmark:.7f}</maxmark>{chr(10) + '        <quizgradeitemid>' + NULL + '</quizgradeitemid>' if ziel5 else ''}
{ref_xml}
      </question_instance>""")
    fb_art = t.get("feedback", "nachher")   # nachher | sofort | punkte (nur Punkte nachher) | keine (Klausur)
    sofort = fb_art == "sofort"
    rev = {"sofort": REVIEW_ALLES, "keine": 0, "punkte": 0}.get(fb_art, REVIEW_NACH)
    rev_punkte = REVIEW_NACH if fb_art == "punkte" else rev
    rev_antwort = 0 if fb_art in ("keine", "punkte") else REVIEW_NACH
    summe = sum(m for _, _, m in slots)
    sektionen = "\n".join(f"""      <section id="{n}">
        <firstslot>{fs}</firstslot>
        <heading>{x(h)}</heading>
        <shufflequestions>{1 if t.get('mischen') and len(teile) == 1 else 0}</shufflequestions>
      </section>""" for n, (h, fs) in enumerate(teile, 1))
    extra5 = f"""
    <reviewmaxmarks>{REVIEW_ALLES}</reviewmaxmarks>
    <precreateattempts>{NULL}</precreateattempts>""" if ziel5 else ""
    return f"""<activity id="{a['instanceid']}" moduleid="{a['moduleid']}" modulename="quiz" contextid="{a['contextid']}">
  <quiz id="{a['instanceid']}">
    <name>{x(a['name'])}</name>
    <intro>{x(a.get('intro', ''))}</intro>
    <introformat>1</introformat>
    <timeopen>{int(t.get('oeffnen', 0))}</timeopen>
    <timeclose>{int(t.get('schliessen', 0))}</timeclose>
    <timelimit>{int(t.get('zeit', 0)) * 60}</timelimit>
    <overduehandling>autosubmit</overduehandling>
    <graceperiod>0</graceperiod>
    <preferredbehaviour>{'immediatefeedback' if sofort else 'deferredfeedback'}</preferredbehaviour>
    <canredoquestions>0</canredoquestions>
    <attempts_number>{int(t.get('versuche', 0))}</attempts_number>
    <attemptonlast>0</attemptonlast>
    <grademethod>1</grademethod>
    <decimalpoints>2</decimalpoints>
    <questiondecimalpoints>-1</questiondecimalpoints>
    <reviewattempt>{rev}</reviewattempt>
    <reviewcorrectness>{rev}</reviewcorrectness>
    <reviewmarks>{rev_punkte}</reviewmarks>
    <reviewspecificfeedback>{rev}</reviewspecificfeedback>
    <reviewgeneralfeedback>{rev}</reviewgeneralfeedback>
    <reviewrightanswer>{rev_antwort}</reviewrightanswer>
    <reviewoverallfeedback>{rev_antwort}</reviewoverallfeedback>{extra5}
    <questionsperpage>{pro_seite}</questionsperpage>
    <navmethod>{'seq' if t.get('navigation') == 'nacheinander' else 'free'}</navmethod>
    <shuffleanswers>1</shuffleanswers>
    <sumgrades>{summe:.5f}</sumgrades>
    <grade>{float(a['grade_item']['grademax']):.5f}</grade>
    <timecreated>{jetzt}</timecreated>
    <timemodified>{jetzt}</timemodified>
    <password>{x(t.get('kennwort') or '')}</password>
    <subnet></subnet>
    <browsersecurity>-</browsersecurity>
    <delay1>0</delay1>
    <delay2>0</delay2>
    <showuserpicture>0</showuserpicture>
    <showblocks>0</showblocks>
    <completionattemptsexhausted>0</completionattemptsexhausted>
    <completionminattempts>0</completionminattempts>
    <allowofflineattempts>0</allowofflineattempts>
    <subplugin_quizaccess_seb_quiz>
    </subplugin_quizaccess_seb_quiz>{chr(10) + '    <quiz_grade_items>' + chr(10) + '    </quiz_grade_items>' if ziel5 else ''}
    <question_instances>
{chr(10).join(inst)}
    </question_instances>
    <sections>
{sektionen}
    </sections>
    <feedbacks>
    </feedbacks>
    <overrides>
    </overrides>
    <grades>
    </grades>
    <attempts>
    </attempts>
  </quiz>
</activity>"""


def qbank_xml(a, jetzt):
    return f"""<activity id="{a['instanceid']}" moduleid="{a['moduleid']}" modulename="qbank" contextid="{a['contextid']}">
  <qbank id="{a['instanceid']}">
    <name>{x(a['name'])}</name>
    <timecreated>{jetzt}</timecreated>
    <timemodified>0</timemodified>
    <intro>{x(a.get('intro', ''))}</intro>
    <introformat>1</introformat>
    <type>standard</type>
  </qbank>
</activity>"""
