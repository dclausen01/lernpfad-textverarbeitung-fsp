"""Kurssicherung (.mbz) für Moodle schreiben – der technische Kern hinter moodle_kurs.py.

Bekommt eine Kursbeschreibung als Python-Dict (baut moodle_kurs.py aus kurs.yaml) und erzeugt daraus eine
Sicherung mit Abschnitten, Unterabschnitten (nur Moodle 5), Lernpaketen (SCORM), H5P, Aufgaben mit
Bewertungsraster, Tests (Aktivität „Test“ samt Fragen, siehe moodle_test.py), Aktivitätsabschluss und
Freischaltungen. Keine Personendaten.

Zwei Ziele (geprüft mit Moodle 4.2.3 und 5.2.3):
    "4"   ohne Unterabschnitte: alle Aktivitäten einer Stufe untereinander im Abschnitt (Moodle 4.x)
    "5"   Einheiten als Unterabschnitte (gibt es erst ab Moodle 5.0), H5P möglich
Lernpakete kommen vollständig mit (ZIP, entpackte Dateien und SCO-Struktur aus imsmanifest.xml), so wie Moodle
selbst sichert – Moodle 4.x entpackt Pakete beim Wiederherstellen nicht von allein.

Beschreibung (Dict):
    kurs: {titel, kurzname, text}
    allgemein: {text, inhalte: [...]}                 Abschnitt 0
    abschnitte: [{titel, text, reihenfolge: nacheinander|frei, freischalten_nach, einheiten: [{titel, inhalte}]}]
    Inhalte: {typ: lernpaket|h5p|aufgabe|test, id, titel, datei | text, punkte, dateitypen, dateien, raster, abschluss}
    Test:    {typ: test, id, titel, text, punkte, bestehen, versuche, zeit, pro_seite, mischen, feedback, gruppen}
             gruppen aus moodle_test.test_fragen()
    raster: {name, kriterien: [{kriterium, stufen: [[text, punkte], …]}]}
    freischalten_nach: "id" | {id, mindestens: 80} | [a, b]  (Liste = ODER)
"""
import hashlib
import html
import io
import json
import re
import sys
import tarfile
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from gemeinsam import Fehler

# Ziel-Versionen: Die Sicherung trägt die niedrigste passende Version, dann gibt es beim Wiederherstellen keine Warnung.
ZIELE = {
    # h5p: Die aktuellen H5P-Bibliotheken brauchen H5P-Kern 1.26/1.27; Moodle 4.2 hat 1.25 und kann sie nicht nutzen.
    # qbank: Ab Moodle 5.0 liegen Fragen in einer Fragensammlung (Aktivität qbank), nicht mehr im Kurs.
    "4": dict(version="2023042400", release="4.2 (Build: 20230424)", backup_release="4.2", unterabschnitte=False, h5p=False,
              qbank=False),
    "5": dict(version="2025041400", release="5.0 (Build: 20250414)", backup_release="5.0", unterabschnitte=True, h5p=True,
              qbank=True),
}
NULL = "$@NULL@$"
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".svg": "image/svg+xml",
        ".webp": "image/webp"}
NOW = int(time.time())

ICON_LINK = {"scorm": "SCORMVIEWBYID", "assign": "ASSIGNVIEWBYID", "h5pactivity": "H5PACTIVITYVIEWBYID",
             "quiz": "QUIZVIEWBYID"}


def x(v):
    """Wert für XML: None → $@NULL@$, sonst escapen."""
    return NULL if v is None else escape(str(v))


def xml_doc(body):
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n"


# ---------------------------------------------------------------- Modell aufbauen

class Sicherung:
    def __init__(self, beschreibung, basis, ziel="5"):
        self.b = beschreibung
        self.basis = basis
        self.ziel = ZIELE[ziel]
        self.sections = []      # {id, number, name, summary, sequence[], availability, component, itemid, parentcmid}
        self.activities = []    # {moduleid, modname, instanceid, contextid, sectionid, sectionnumber, insub, ...}
        self.files = []         # {id, hash, contextid, component, filearea, name, size, mime, data}
        self.grade_items = []
        self.ids = {}           # eigene ID → moduleid
        self.akt_by_ref = {}    # eigene ID → Aktivität
        self._n = {"section": 100, "module": 1000, "instance": 1, "context": 5000, "file": 1, "grade": 10, "sco": 1}
        self.pool = None        # Fragenpool (moodle_test.Fragenpool), sobald es einen Test gibt

    def nid(self, art):
        self._n[art] += 1
        return self._n[art]

    # -- Freischaltung (Aktivitätsabschluss einer anderen Aktivität)
    def bedingung(self, ref):
        """freischalten_nach → Moodle-Voraussetzung.
        "id"                       Aktivität abgeschlossen (bei Aufgaben: abgegeben)
        {id: …, mindestens: 80}    Bewertung der Aktivität mindestens 80 %
        [a, b, …]                  eine davon reicht (ODER), z. B. Meilenstein ODER Einstufungstest bestanden"""
        if not ref:
            return None
        def einzel(r):
            rid = r["id"] if isinstance(r, dict) else r
            if rid not in self.ids:
                raise Fehler(f"Unbekannte Referenz in freischalten_nach: {rid}")
            if isinstance(r, dict) and "mindestens" in r:
                gi = self.akt_by_ref[rid]["grade_item"]
                if not gi:
                    raise Fehler(f"{rid} hat keine Bewertung – „mindestens“ geht nur bei bewerteten Aktivitäten")
                return {"type": "grade", "id": gi["id"], "min": float(r["mindestens"])}
            return {"type": "completion", "cm": self.ids[rid], "e": 1}
        if isinstance(ref, list):
            if len(ref) > 1:
                return json.dumps({"op": "|", "c": [einzel(r) for r in ref], "show": True})
            ref = ref[0]
        return json.dumps({"op": "&", "c": [einzel(ref)], "showc": [True]})

    def baue(self):
        kopf = self.b["kurs"]
        # Abschnitt 0 („Allgemeines“): z. B. Start-Lernpaket und Einstufungstests
        s0 = dict(id=self.nid("section"), number=0, name="", summary=self.b.get("allgemein", {}).get("text", ""),
                  sequence=[], availability=None, component=None, itemid=None, parentcmid=None)
        self.sections.append(s0)
        for inh in self.b.get("allgemein", {}).get("inhalte", []):
            self.inhalt(inh, s0, insub=False)
        # erst alle Abschnitte anlegen (Nummern 1..n), Unterabschnitte danach nummerieren (so macht es Moodle)
        oben = []
        for i, a in enumerate(self.b["abschnitte"], 1):
            s = dict(id=self.nid("section"), number=i, name=a["titel"], summary=a.get("text", ""), sequence=[],
                     availability=None, component=None, itemid=None, parentcmid=None, quelle=a)
            self.sections.append(s)
            oben.append(s)
        nummer = len(oben)
        verzoegert = []  # (section, ref) – Freischaltungen, deren Ziel erst später angelegt wird
        for s in oben:
            a = s["quelle"]
            vorige_haupt = None
            for e in a.get("einheiten", []):
                ref = e.get("freischalten_nach") or (vorige_haupt if a.get("reihenfolge", "nacheinander") == "nacheinander" else None)
                if not self.ziel["unterabschnitte"] or len(e.get("inhalte", [])) == 1:
                    # Moodle 4: keine Unterabschnitte (Moodle 5: Einheit mit nur einer Aktivität braucht keinen) – Inhalte direkt in den Abschnitt, jede mit der Freischaltung der Einheit
                    for j, inh in enumerate(e.get("inhalte", [])):
                        akt = self.inhalt(inh, s, insub=False)
                        if akt is None:
                            continue
                        if ref:
                            verzoegert.append((akt, ref))
                        if j == 0:
                            vorige_haupt = inh["id"]
                    continue
                # Unterabschnitt = Aktivität "subsection" + eigener (delegierter) Abschnitt
                sub = self.aktivitaet("subsection", s, dict(name=e["titel"]), insub=False)
                nummer += 1
                ds = dict(id=self.nid("section"), number=nummer, name=e["titel"], summary=e.get("text", ""),
                          sequence=[], availability=None, component="mod_subsection", itemid=sub["instanceid"],
                          parentcmid=sub["moduleid"])
                sub["delegated"] = ds
                self.sections.append(ds)
                if ref:
                    verzoegert.append((sub, ref))
                for j, inh in enumerate(e.get("inhalte", [])):
                    akt = self.inhalt(inh, ds)
                    if j == 0:
                        vorige_haupt = inh["id"]
            if a.get("freischalten_nach"):
                verzoegert.append((s, a["freischalten_nach"]))
        for obj, ref in verzoegert:
            obj["availability"] = self.bedingung(ref)
            # Wie Moodle selbst: die Bedingung eines Unterabschnitts steht auch an seinem Abschnitt,
            # sonst zeigt der Kursindex gesperrte Unterabschnitte mit falschem Namen
            if obj.get("delegated"):
                obj["delegated"]["availability"] = obj["availability"]
        self.weiter_links()

    def aktivitaet(self, modname, section, felder, insub=True, completion=0, completionview=0,
                   completiongradeitemnumber=None):
        akt = dict(moduleid=self.nid("module"), modname=modname, instanceid=self.nid("instance"),
                   contextid=self.nid("context"), sectionid=section["id"], sectionnumber=section["number"],
                   insub=insub, completion=completion, completionview=completionview,
                   completiongradeitemnumber=completiongradeitemnumber, completionpassgrade=0, visible=1,
                   availability=None, files=[], grade_item=None, **felder)
        section["sequence"].append(akt["moduleid"])
        self.activities.append(akt)
        return akt

    def datei(self, akt, component, pfad, mime):
        data = (self.basis / pfad).read_bytes()
        f = dict(id=self.nid("file"), hash=hashlib.sha1(data).hexdigest(), contextid=akt["contextid"],
                 component=component, filearea="package", name=Path(pfad).name, size=len(data), mime=mime, data=data)
        self.files.append(f)
        akt["files"].append(f["id"])
        return f

    def scorm_inhalt(self, akt, paket):
        """Wie Moodle beim Hochladen: Paket entpacken (Dateibereich „content“) und die SCO-Struktur aus
        imsmanifest.xml ablesen. Nötig für Moodle 4.x; Moodle 5 erkennt am Prüfwert, dass nichts zu tun ist."""
        z = zipfile.ZipFile(io.BytesIO(paket["data"]))
        for name in z.namelist():
            if name.endswith("/"):
                continue
            data = z.read(name)
            pfad, _, datei = name.rpartition("/")
            f = dict(id=self.nid("file"), hash=hashlib.sha1(data).hexdigest(), contextid=akt["contextid"],
                     component="mod_scorm", filearea="content", filepath="/" + (pfad + "/" if pfad else ""),
                     name=datei, size=len(data), mime=None, data=data)
            self.files.append(f)
            akt["files"].append(f["id"])
        ns = lambda tag: "{*}" + tag
        man = ET.fromstring(z.read("imsmanifest.xml"))
        ident = man.get("identifier")
        res = {r.get("identifier"): r.get("href") for r in man.iter() if r.tag.endswith("}resource") or r.tag == "resource"}
        scoes, order = [], 0
        for org in man.find(ns("organizations")).findall(ns("organization")):
            order += 1
            org_title = org.findtext(ns("title")) or akt["name"]
            scoes.append(dict(id=self.nid("sco"), manifest=ident, organization="", parent="/",
                              identifier=org.get("identifier"), launch="", scormtype="", title=org_title,
                              sortorder=order, datas=[]))
            for item in org.iter():
                if not (item.tag.endswith("}item") or item.tag == "item"):
                    continue
                order += 1
                href = res.get(item.get("identifierref"), "")
                scoes.append(dict(id=self.nid("sco"), manifest=ident, organization=org.get("identifier"),
                                  parent=org.get("identifier"), identifier=item.get("identifier"), launch=href,
                                  scormtype="sco" if href else "", title=item.findtext(ns("title")) or akt["name"],
                                  sortorder=order, datas=[("isvisible", "true"), ("parameters", "")]))
        akt["scoes"] = scoes
        akt["launch"] = next((s["id"] for s in scoes if s["launch"]), 0)

    def note(self, akt, grademax, gradepass=0):
        gi = dict(id=self.nid("grade"), name=akt["name"], module=akt["modname"], instance=akt["instanceid"],
                  grademax=grademax, gradepass=gradepass)
        self.grade_items.append(gi)
        akt["grade_item"] = gi

    def inhalt(self, inh, ds, insub=True):
        typ = inh["typ"]
        if typ == "h5p" and not self.ziel["h5p"]:
            print(f"  Hinweis: H5P „{inh['titel']}“ ausgelassen – die H5P-Bibliotheken brauchen Moodle 5.", file=sys.stderr)
            return None
        if typ == "lernpaket":
            # abschluss: false → kein Aktivitätsabschluss (Startseite, Einstufungstest); punkte: 0 → keine Bewertung
            akt = self.aktivitaet("scorm", ds, dict(name=inh["titel"], intro=inh.get("text", "")),
                                  completion=2 if inh.get("abschluss", True) else 0, insub=insub)
            f = self.datei(akt, "mod_scorm", inh["datei"], "application/zip")
            akt["reference"] = f["name"]
            akt["sha1hash"] = f["hash"]
            self.scorm_inhalt(akt, f)
            akt["maxgrade"] = inh.get("punkte", 100)
            if akt["maxgrade"]:
                self.note(akt, akt["maxgrade"])
        elif typ == "h5p":
            akt = self.aktivitaet("h5pactivity", ds, dict(name=inh["titel"], intro=inh.get("text", "")),
                                  completion=2, completiongradeitemnumber=0, insub=insub)
            self.datei(akt, "mod_h5pactivity", inh["datei"], "application/zip.h5p")
            self.note(akt, inh.get("punkte", 100))
        elif typ == "aufgabe":
            akt = self.aktivitaet("assign", ds, dict(name=inh["titel"], intro=inh.get("text", "")), completion=2, insub=insub)
            akt["grade"] = inh.get("punkte", 100)
            akt["filetypes"] = inh.get("dateitypen", "")
            akt["maxfiles"] = inh.get("dateien", 1)
            akt["raster"] = self.raster(inh)
            self.note(akt, akt["grade"])
        elif typ == "test":
            akt = self.aktivitaet("quiz", ds, dict(name=inh["titel"], intro=inh.get("text", "")),
                                  completion=2, completiongradeitemnumber=0, insub=insub)
            punkte = float(inh.get("punkte", 10))
            if inh.get("bestehen"):
                akt["completionpassgrade"] = 1
            self.note(akt, punkte, gradepass=round(punkte * float(inh.get("bestehen", 0)) / 100, 5))
            akt["test"] = inh
            akt["slots"] = self.fragenpool().test(inh["titel"], inh["gruppen"])
        else:
            raise Fehler(f"Unbekannter Inhaltstyp: {typ}")
        akt["ref"] = inh["id"]
        self.akt_by_ref[inh["id"]] = akt
        if inh["id"] in self.ids:
            raise Fehler(f"Doppelte ID: {inh['id']}")
        self.ids[inh["id"]] = akt["moduleid"]
        return akt

    def fragenpool(self):
        """Moodle 4: Fragen im Kurskontext. Moodle 5: in einer Fragensammlung (Aktivität qbank) in Abschnitt 0."""
        if self.pool is None:
            import moodle_test
            self.pool = moodle_test.Fragenpool(self, self.b["kurs"]["titel"])
            if self.ziel["qbank"]:
                qb = self.aktivitaet("qbank", self.sections[0], dict(name=f"Fragensammlung: {self.b['kurs']['titel']}",
                                                                      intro=""), insub=False)
                qb["visible"] = 0
                self.pool.bereit((qb["contextid"], 70, qb["moduleid"]))
            else:
                self.pool.bereit((2, 50, 1))   # Kurskontext wie in course.xml
        return self.pool

    def frage_datei(self, contextid, filearea, itemid, name, data):
        """Bild in einer Frage (Fragetext bzw. allgemeines Feedback)."""
        self.files.append(dict(id=self.nid("file"), hash=hashlib.sha1(data).hexdigest(), contextid=contextid,
                               component="question", filearea=filearea, itemid=itemid, name=name, size=len(data),
                               mime=MIME.get(Path(name).suffix.lower(), "application/octet-stream"), data=data))

    def raster(self, inh):
        """Bewertungsraster: {name, kriterien: [{kriterium, stufen: [(text, punkte), …]}]}"""
        r = inh.get("raster")
        if not r:
            return None
        return dict(name=r.get("name", inh["titel"]),
                    kriterien=[dict(kriterium=k["kriterium"], stufen=[tuple(st) for st in k["stufen"]])
                               for k in r["kriterien"]])

    def weiter_links(self):
        """In Aufgaben und H5P einen Link zurück in den Pfad setzen (Moodle zeigt dort kein „Weiter“).
        Die Links sind als Moodle-Platzhalter geschrieben; Moodle rechnet sie beim Wiederherstellen um."""
        reihe = [a for a in self.activities if a["modname"] not in ("subsection", "qbank") and a["sectionnumber"] != 0]
        for i, a in enumerate(reihe):
            if a["modname"] == "scorm":
                continue
            teile = []
            if i > 0:
                p = reihe[i - 1]
                teile.append(f'⬅️ <a href="$@{ICON_LINK[p["modname"]]}*{p["moduleid"]}@$">Zurück: {escape(p["name"])}</a>')
            if i + 1 < len(reihe):
                n = reihe[i + 1]
                teile.append(f'➡️ <a href="$@{ICON_LINK[n["modname"]]}*{n["moduleid"]}@$">Weiter im Lernpfad: {escape(n["name"])}</a>')
            if teile:
                a["intro"] = (a.get("intro") or "") + '<p class="lernpfad-nav">' + " &nbsp;·&nbsp; ".join(teile) + "</p>"


# ---------------------------------------------------------------- XML schreiben

EMPTY = {
    "calendar.xml": "<events>\n</events>",
    "comments.xml": "<comments>\n</comments>",
    "xapistate.xml": "<states>\n</states>",
    "competencies.xml": "<course_module_competencies>\n  <competencies>\n  </competencies>\n</course_module_competencies>",
    "completion.xml": "<completions>\n  <completionviews>\n  </completionviews>\n</completions>",
    "grade_history.xml": "<grade_history>\n  <grade_grades>\n  </grade_grades>\n</grade_history>",
    "filters.xml": "<filters>\n  <filter_actives>\n  </filter_actives>\n  <filter_configs>\n  </filter_configs>\n</filters>",
    "roles.xml": "<roles>\n  <role_overrides>\n  </role_overrides>\n  <role_assignments>\n  </role_assignments>\n</roles>",
}


def module_xml(a):
    return f"""<module id="{a['moduleid']}" version="{a['version']}">
  <modulename>{a['modname']}</modulename>
  <sectionid>{a['sectionid']}</sectionid>
  <sectionnumber>{a['sectionnumber']}</sectionnumber>
  <idnumber></idnumber>
  <added>{NOW}</added>
  <score>0</score>
  <indent>0</indent>
  <visible>{a['visible']}</visible>
  <visibleoncoursepage>{a['visible']}</visibleoncoursepage>
  <visibleold>{a['visible']}</visibleold>
  <groupmode>0</groupmode>
  <groupingid>0</groupingid>
  <completion>{a['completion']}</completion>
  <completiongradeitemnumber>{x(a['completiongradeitemnumber'])}</completiongradeitemnumber>
  <completionpassgrade>{a['completionpassgrade']}</completionpassgrade>
  <completionview>{a['completionview']}</completionview>
  <completionexpected>0</completionexpected>
  <availability>{x(a['availability'])}</availability>
  <showdescription>0</showdescription>
  <downloadcontent>1</downloadcontent>
  <lang>{NULL}</lang>
  <enableaitools>{NULL}</enableaitools>
  <enabledaiactions>{NULL}</enabledaiactions>
  <tags>
  </tags>
</module>"""


def activity_wrap(a, inner):
    return (f'<activity id="{a["instanceid"]}" moduleid="{a["moduleid"]}" modulename="{a["modname"]}" '
            f'contextid="{a["contextid"]}">\n{inner}\n</activity>')


def scorm_xml(a):
    return activity_wrap(a, f"""  <scorm id="{a['instanceid']}">
    <name>{x(a['name'])}</name>
    <scormtype>local</scormtype>
    <reference>{x(a['reference'])}</reference>
    <intro>{x(a.get('intro', ''))}</intro>
    <introformat>1</introformat>
    <version>SCORM_1.3</version>
    <maxgrade>{a['maxgrade']}</maxgrade>
    <grademethod>1</grademethod>
    <whatgrade>0</whatgrade>
    <maxattempt>0</maxattempt>
    <forcecompleted>0</forcecompleted>
    <forcenewattempt>0</forcenewattempt>
    <lastattemptlock>0</lastattemptlock>
    <masteryoverride>1</masteryoverride>
    <displayattemptstatus>0</displayattemptstatus>
    <displaycoursestructure>0</displaycoursestructure>
    <updatefreq>0</updatefreq>
    <sha1hash>{a['sha1hash']}</sha1hash>
    <md5hash></md5hash>
    <revision>1</revision>
    <launch>{a['launch']}</launch>
    <skipview>2</skipview>
    <hidebrowse>0</hidebrowse>
    <hidetoc>3</hidetoc>
    <nav>0</nav>
    <navpositionleft>-100</navpositionleft>
    <navpositiontop>-100</navpositiontop>
    <auto>0</auto>
    <popup>0</popup>
    <options></options>
    <width>100</width>
    <height>500</height>
    <timeopen>0</timeopen>
    <timeclose>0</timeclose>
    <timemodified>{NOW}</timemodified>
    <completionstatusrequired>4</completionstatusrequired>
    <completionscorerequired>{NULL}</completionscorerequired>
    <completionstatusallscos>0</completionstatusallscos>
    <autocommit>0</autocommit>
    <scoes>
{scoes_xml(a)}
    </scoes>
  </scorm>""")


def scoes_xml(a):
    out = []
    for s in a.get("scoes", []):
        datas = "\n".join(f"""          <sco_data id="{s['id'] * 10 + i}">
            <name>{x(n)}</name>
            <value>{x(v)}</value>
          </sco_data>""" for i, (n, v) in enumerate(s["datas"], 1))
        out.append(f"""      <sco id="{s['id']}">
        <manifest>{x(s['manifest'])}</manifest>
        <organization>{x(s['organization'])}</organization>
        <parent>{x(s['parent'])}</parent>
        <identifier>{x(s['identifier'])}</identifier>
        <launch>{x(s['launch'])}</launch>
        <scormtype>{x(s['scormtype'])}</scormtype>
        <title>{x(s['title'])}</title>
        <sortorder>{s['sortorder']}</sortorder>
        <sco_datas>
{datas}
        </sco_datas>
        <seq_ruleconds>
        </seq_ruleconds>
        <seq_rolluprules>
        </seq_rolluprules>
        <seq_objectives>
        </seq_objectives>
        <sco_tracks>
        </sco_tracks>
      </sco>""")
    return "\n".join(out)


def h5p_xml(a):
    return activity_wrap(a, f"""  <h5pactivity id="{a['instanceid']}">
    <name>{x(a['name'])}</name>
    <timecreated>{NOW}</timecreated>
    <timemodified>{NOW}</timemodified>
    <intro>{x(a.get('intro', ''))}</intro>
    <introformat>1</introformat>
    <grade>{a['grade_item']['grademax']}</grade>
    <displayoptions>15</displayoptions>
    <enabletracking>1</enabletracking>
    <grademethod>1</grademethod>
    <reviewmode>1</reviewmode>
    <attempts>
    </attempts>
  </h5pactivity>""")


def assign_xml(a):
    cfg = [("onlinetext", "assignsubmission", "enabled", "0"), ("file", "assignsubmission", "enabled", "1"),
           ("file", "assignsubmission", "maxfilesubmissions", str(a["maxfiles"])),
           ("file", "assignsubmission", "maxsubmissionsizebytes", "0"),
           ("file", "assignsubmission", "filetypeslist", a["filetypes"]),
           ("comments", "assignsubmission", "enabled", "0"),
           ("comments", "assignfeedback", "enabled", "1"), ("comments", "assignfeedback", "commentinline", "0"),
           ("editpdf", "assignfeedback", "enabled", "0"), ("offline", "assignfeedback", "enabled", "0"),
           ("file", "assignfeedback", "enabled", "1")]
    pc = "\n".join(f"""      <plugin_config id="{i}">
        <plugin>{p}</plugin>
        <subtype>{st}</subtype>
        <name>{n}</name>
        <value>{x(v)}</value>
      </plugin_config>""" for i, (p, st, n, v) in enumerate(cfg, 1))
    return activity_wrap(a, f"""  <assign id="{a['instanceid']}">
    <name>{x(a['name'])}</name>
    <intro>{x(a.get('intro', ''))}</intro>
    <introformat>1</introformat>
    <alwaysshowdescription>1</alwaysshowdescription>
    <submissiondrafts>0</submissiondrafts>
    <sendnotifications>0</sendnotifications>
    <sendlatenotifications>0</sendlatenotifications>
    <sendstudentnotifications>1</sendstudentnotifications>
    <duedate>0</duedate>
    <cutoffdate>0</cutoffdate>
    <gradingduedate>0</gradingduedate>
    <allowsubmissionsfromdate>0</allowsubmissionsfromdate>
    <grade>{a['grade']}</grade>
    <timemodified>{NOW}</timemodified>
    <completionsubmit>1</completionsubmit>
    <requiresubmissionstatement>0</requiresubmissionstatement>
    <teamsubmission>0</teamsubmission>
    <requireallteammemberssubmit>0</requireallteammemberssubmit>
    <teamsubmissiongroupingid>0</teamsubmissiongroupingid>
    <blindmarking>0</blindmarking>
    <hidegrader>0</hidegrader>
    <revealidentities>0</revealidentities>
    <attemptreopenmethod>untilpass</attemptreopenmethod>
    <maxattempts>-1</maxattempts>
    <markingworkflow>0</markingworkflow>
    <markingallocation>0</markingallocation>
    <markercount>0</markercount>
    <multimarkmethod>{NULL}</multimarkmethod>
    <markinganonymous>0</markinganonymous>
    <preventsubmissionnotingroup>0</preventsubmissionnotingroup>
    <activity>{NULL}</activity>
    <activityformat>0</activityformat>
    <timelimit>0</timelimit>
    <submissionattachments>0</submissionattachments>
    <gradepenalty>0</gradepenalty>
    <userflags>
    </userflags>
    <allocatedmarkers>
    </allocatedmarkers>
    <submissions>
    </submissions>
    <grades>
    </grades>
    <marks>
    </marks>
    <plugin_configs>
{pc}
    </plugin_configs>
    <overrides>
    </overrides>
  </assign>""")


def subsection_xml(a):
    return activity_wrap(a, f"""  <subsection id="{a['instanceid']}">
    <name>{x(a['name'])}</name>
    <timemodified>{NOW}</timemodified>
  </subsection>""")


def grading_xml(a):
    r = a.get("raster")
    if not r:
        return "<areas>\n</areas>"
    crit, lid = [], 0
    for ci, k in enumerate(r["kriterien"], 1):
        levels = []
        for text, punkte in k["stufen"]:
            lid += 1
            levels.append(f"""                <level id="{lid}">
                  <score>{float(punkte):.5f}</score>
                  <definition>{x(text)}</definition>
                  <definitionformat>0</definitionformat>
                </level>""")
        crit.append(f"""            <criterion id="{ci}">
              <sortorder>{ci}</sortorder>
              <description>{x(k['kriterium'])}</description>
              <descriptionformat>0</descriptionformat>
              <levels>
{chr(10).join(levels)}
              </levels>
            </criterion>""")
    opts = x(json.dumps({"sortlevelsasc": 1, "lockzeropoints": 1, "showdescriptionteacher": 1,
                         "showdescriptionstudent": 1, "showscoreteacher": 1, "showscorestudent": 1,
                         "enableremarks": 1, "showremarksstudent": 1}))
    return f"""<areas>
  <area id="1">
    <areaname>submissions</areaname>
    <activemethod>rubric</activemethod>
    <definitions>
      <definition id="1">
        <method>rubric</method>
        <name>{x(r['name'])}</name>
        <description>Bewertungsraster aus dem Lernpfad</description>
        <descriptionformat>1</descriptionformat>
        <status>20</status>
        <timecreated>{NOW}</timecreated>
        <timemodified>{NOW}</timemodified>
        <options>{opts}</options>
        <plugin_gradingform_rubric_definition>
          <criteria>
{chr(10).join(crit)}
          </criteria>
        </plugin_gradingform_rubric_definition>
        <instances>
        </instances>
      </definition>
    </definitions>
  </area>
</areas>"""


def grade_item_xml(gi, typ="mod", category="1"):
    return f"""    <grade_item id="{gi['id']}">
      <categoryid>{category}</categoryid>
      <itemname>{x(gi.get('name'))}</itemname>
      <itemtype>{typ}</itemtype>
      <itemmodule>{x(gi.get('module'))}</itemmodule>
      <iteminstance>{gi['instance']}</iteminstance>
      <itemnumber>{x(gi.get('itemnumber', 0))}</itemnumber>
      <iteminfo>{NULL}</iteminfo>
      <idnumber>{x(gi.get('idnumber', ''))}</idnumber>
      <calculation>{NULL}</calculation>
      <gradetype>1</gradetype>
      <grademax>{float(gi['grademax']):.5f}</grademax>
      <grademin>0.00000</grademin>
      <scaleid>{NULL}</scaleid>
      <outcomeid>{NULL}</outcomeid>
      <gradepass>{float(gi.get('gradepass', 0)):.5f}</gradepass>
      <multfactor>1.00000</multfactor>
      <plusfactor>0.00000</plusfactor>
      <aggregationcoef>0.00000</aggregationcoef>
      <aggregationcoef2>0.00000</aggregationcoef2>
      <weightoverride>0</weightoverride>
      <sortorder>{gi.get('sortorder', 1)}</sortorder>
      <display>0</display>
      <decimals>{NULL}</decimals>
      <hidden>0</hidden>
      <locked>0</locked>
      <locktime>0</locktime>
      <needsupdate>0</needsupdate>
      <timecreated>{NOW}</timecreated>
      <timemodified>{NOW}</timemodified>
      <grade_grades>
      </grade_grades>
    </grade_item>"""


def activity_grades_xml(a):
    items = grade_item_xml(a["grade_item"]) if a["grade_item"] else ""
    return f"<activity_gradebook>\n  <grade_items>\n{items}\n  </grade_items>\n  <grade_letters>\n  </grade_letters>\n</activity_gradebook>"


def inforef_xml(a, pool=None):
    parts = []
    if a["files"]:
        parts.append("  <fileref>\n" + "\n".join(f"    <file>\n      <id>{i}</id>\n    </file>" for i in a["files"]) + "\n  </fileref>")
    if a["grade_item"]:
        parts.append(f"  <grade_itemref>\n    <grade_item>\n      <id>{a['grade_item']['id']}</id>\n    </grade_item>\n  </grade_itemref>")
    if a["modname"] in ("quiz", "qbank") and pool:
        import moodle_test
        parts.append(moodle_test.kategorien_ref(pool))
    return "<inforef>\n" + "\n".join(parts) + "\n</inforef>"


def section_xml(s):
    return f"""<section id="{s['id']}">
  <number>{s['number']}</number>
  <name>{x(s['name'])}</name>
  <summary>{x(s['summary'])}</summary>
  <summaryformat>1</summaryformat>
  <sequence>{','.join(map(str, s['sequence']))}</sequence>
  <visible>1</visible>
  <availabilityjson>{x(s['availability'])}</availabilityjson>
  <component>{x(s['component'])}</component>
  <itemid>{x(s['itemid'])}</itemid>
  <timemodified>{NOW}</timemodified>
</section>"""


def course_xml(k):
    kurs = k.b["kurs"]
    return f"""<course id="1" contextid="2">
  <shortname>{x(kurs['kurzname'])}</shortname>
  <fullname>{x(kurs['titel'])}</fullname>
  <idnumber></idnumber>
  <summary>{x(kurs.get('text', ''))}</summary>
  <summaryformat>1</summaryformat>
  <format>topics</format>
  <showgrades>1</showgrades>
  <newsitems>0</newsitems>
  <startdate>0</startdate>
  <enddate>0</enddate>
  <marker>0</marker>
  <maxbytes>0</maxbytes>
  <legacyfiles>0</legacyfiles>
  <showreports>0</showreports>
  <visible>1</visible>
  <groupmode>0</groupmode>
  <groupmodeforce>0</groupmodeforce>
  <defaultgroupingid>0</defaultgroupingid>
  <lang>{x(kurs.get('sprache', 'de'))}</lang>
  <theme></theme>
  <timecreated>{NOW}</timecreated>
  <timemodified>{NOW}</timemodified>
  <requested>0</requested>
  <showactivitydates>1</showactivitydates>
  <showcompletionconditions>1</showcompletionconditions>
  <pdfexportfont>{NULL}</pdfexportfont>
  <enablecompletion>1</enablecompletion>
  <completionnotify>0</completionnotify>
  <enableaitools>{NULL}</enableaitools>
  <category id="1">
    <name>Lernpfade</name>
    <description>{NULL}</description>
  </category>
  <tags>
  </tags>
  <customfields>
  </customfields>
  <courseformatoptions>
    <courseformatoption>
      <format>topics</format>
      <sectionid>0</sectionid>
      <name>hiddensections</name>
      <value>1</value>
    </courseformatoption>
    <courseformatoption>
      <format>topics</format>
      <sectionid>0</sectionid>
      <name>coursedisplay</name>
      <value>0</value>
    </courseformatoption>
  </courseformatoptions>
</course>"""


def gradebook_xml(k):
    kursitem = dict(id=1, name=None, module=None, instance=1, grademax=100, itemnumber=None, idnumber=None)
    return f"""<gradebook>
  <attributes>
  </attributes>
  <grade_categories>
    <grade_category id="1">
      <parent>{NULL}</parent>
      <depth>1</depth>
      <path>/1/</path>
      <fullname>?</fullname>
      <aggregation>13</aggregation>
      <keephigh>0</keephigh>
      <droplow>0</droplow>
      <aggregateonlygraded>1</aggregateonlygraded>
      <aggregateoutcomes>0</aggregateoutcomes>
      <timecreated>{NOW}</timecreated>
      <timemodified>{NOW}</timemodified>
      <hidden>0</hidden>
    </grade_category>
  </grade_categories>
  <grade_items>
{grade_item_xml(kursitem, typ="course", category=NULL)}
  </grade_items>
  <grade_letters>
  </grade_letters>
  <grade_settings>
    <grade_setting id="">
      <name>minmaxtouse</name>
      <value>1</value>
    </grade_setting>
  </grade_settings>
</gradebook>"""


def files_xml(k):
    out = []
    for f in k.files:
        out.append(f"""  <file id="{f['id']}">
    <contenthash>{f['hash']}</contenthash>
    <contextid>{f['contextid']}</contextid>
    <component>{f['component']}</component>
    <filearea>{f['filearea']}</filearea>
    <itemid>{f.get('itemid', 0)}</itemid>
    <filepath>{x(f.get('filepath', '/'))}</filepath>
    <filename>{x(f['name'])}</filename>
    <userid>{NULL}</userid>
    <filesize>{f['size']}</filesize>
    <mimetype>{x(f['mime'])}</mimetype>
    <status>0</status>
    <timecreated>{NOW}</timecreated>
    <timemodified>{NOW}</timemodified>
    <source>{x(f['name'] if f['filearea'] == 'package' else None)}</source>
    <author>{NULL}</author>
    <license>{NULL}</license>
    <sortorder>0</sortorder>
    <repositorytype>{NULL}</repositorytype>
    <repositoryid>{NULL}</repositoryid>
    <reference>{NULL}</reference>
  </file>""")
    return "<files>\n" + "\n".join(out) + "\n</files>"


def moodle_backup_xml(k, name):
    kurs = k.b["kurs"]
    acts = "\n".join(f"""        <activity>
          <moduleid>{a['moduleid']}</moduleid>
          <sectionid>{a['sectionid']}</sectionid>
          <modulename>{a['modname']}</modulename>
          <title>{x(a['name'])}</title>
          <directory>activities/{a['modname']}_{a['moduleid']}</directory>
          <insubsection>{'1' if a['insub'] else ''}</insubsection>
        </activity>""" for a in k.activities)
    # Reihenfolge wie Moodle: Abschnitt 0, dann je Abschnitt dessen Unterabschnitte
    order = [k.sections[0]]
    for s in k.sections[1:]:
        if s["component"]:
            continue
        order.append(s)
        for mid in s["sequence"]:
            a = next(a for a in k.activities if a["moduleid"] == mid)
            if a["modname"] == "subsection":
                order.append(a["delegated"])
    secs = "\n".join(f"""        <section>
          <sectionid>{s['id']}</sectionid>
          <title>{x(s['name'] or str(s['number']))}</title>
          <directory>sections/section_{s['id']}</directory>
          <parentcmid>{s['parentcmid'] or ''}</parentcmid>
          <modname>{'subsection' if s['component'] else ''}</modname>
        </section>""" for s in order)
    root = [("filename", name), ("imscc11", 0), ("users", 0), ("anonymize", 0), ("role_assignments", 0),
            ("activities", 1), ("blocks", 0), ("files", 1), ("filters", 0), ("comments", 0), ("badges", 0),
            ("calendarevents", 0), ("userscompletion", 0), ("logs", 0), ("grade_histories", 0)] + \
           ([("questionbank", 1)] if not k.ziel["qbank"] else []) + [("groups", 0),
            ("competencies", 0), ("customfield", 0), ("contentbankcontent", 0), ("xapistate", 0), ("legacyfiles", 0)]
    sets = [f"""      <setting>
        <level>root</level>
        <name>{n}</name>
        <value>{x(v)}</value>
      </setting>""" for n, v in root]
    for s in order:
        for suffix, v in (("included", 1), ("userinfo", 0)):
            sets.append(f"""      <setting>
        <level>section</level>
        <section>section_{s['id']}</section>
        <name>section_{s['id']}_{suffix}</name>
        <value>{v}</value>
      </setting>""")
    for a in k.activities:
        key = f"{a['modname']}_{a['moduleid']}"
        for suffix, v in (("included", 1), ("userinfo", 0)):
            sets.append(f"""      <setting>
        <level>activity</level>
        <activity>{key}</activity>
        <name>{key}_{suffix}</name>
        <value>{v}</value>
      </setting>""")
    return f"""<moodle_backup>
  <information>
    <name>{x(name)}</name>
    <moodle_version>{k.ziel['version']}</moodle_version>
    <moodle_release>{k.ziel['release']}</moodle_release>
    <backup_version>{k.ziel['version']}</backup_version>
    <backup_release>{k.ziel['backup_release']}</backup_release>
    <backup_date>{NOW}</backup_date>
    <mnet_remoteusers>0</mnet_remoteusers>
    <include_files>1</include_files>
    <include_file_references_to_external_content>0</include_file_references_to_external_content>
    <original_wwwroot>https://lernpfad.invalid</original_wwwroot>
    <original_site_identifier_hash>{hashlib.md5(b'lernpfad-generator').hexdigest()}</original_site_identifier_hash>
    <original_course_id>1</original_course_id>
    <original_course_format>topics</original_course_format>
    <original_course_fullname>{x(kurs['titel'])}</original_course_fullname>
    <original_course_shortname>{x(kurs['kurzname'])}</original_course_shortname>
    <original_course_startdate>0</original_course_startdate>
    <original_course_enddate>0</original_course_enddate>
    <original_course_contextid>2</original_course_contextid>
    <original_system_contextid>1</original_system_contextid>
    <details>
      <detail backup_id="{hashlib.md5(name.encode()).hexdigest()}">
        <type>course</type>
        <format>moodle2</format>
        <interactive>1</interactive>
        <mode>10</mode>
        <execution>1</execution>
        <executiontime>0</executiontime>
      </detail>
    </details>
    <contents>
      <activities>
{acts}
      </activities>
      <sections>
{secs}
      </sections>
      <course>
        <courseid>1</courseid>
        <title>{x(kurs['kurzname'])}</title>
        <directory>course</directory>
      </course>
    </contents>
    <settings>
{chr(10).join(sets)}
    </settings>
  </information>
</moodle_backup>"""


ROOT_FILES = {
    "badges.xml": "<badges>\n</badges>",
    "completion.xml": "<course_completion>\n</course_completion>",
    "outcomes.xml": "<outcomes_definition>\n</outcomes_definition>",
    "questions.xml": "<question_categories>\n</question_categories>",
    "scales.xml": "<scales_definition>\n</scales_definition>",
    "grade_history.xml": "<grade_history>\n  <grade_grades>\n  </grade_grades>\n</grade_history>",
    "groups.xml": "<groups>\n  <groupcustomfields>\n  </groupcustomfields>\n  <groupings>\n    <groupingcustomfields>\n    </groupingcustomfields>\n  </groupings>\n</groups>",
    "roles.xml": "<roles_definition>\n</roles_definition>",
}
COURSE_FILES = {
    "calendar.xml": "<events>\n</events>",
    "comments.xml": "<comments>\n</comments>",
    "completiondefaults.xml": "<course_completion_defaults>\n</course_completion_defaults>",
    "contentbank.xml": "<contents>\n</contents>",
    "competencies.xml": "<course_competencies>\n  <competencies>\n  </competencies>\n  <user_competencies>\n  </user_competencies>\n</course_competencies>",
    "filters.xml": "<filters>\n  <filter_actives>\n  </filter_actives>\n  <filter_configs>\n  </filter_configs>\n</filters>",
    "roles.xml": "<roles>\n  <role_overrides>\n  </role_overrides>\n  <role_assignments>\n  </role_assignments>\n</roles>",
    "inforef.xml": "<inforef>\n</inforef>",
    "enrolments.xml": "<enrolments>\n  <enrols>\n  </enrols>\n</enrolments>",
}


def schreibe_mbz(k, ziel):
    name = ziel.name
    eintraege = {}  # pfad → bytes (None = Ordner)

    def add(pfad, text):
        eintraege[pfad] = (xml_doc(text) if isinstance(text, str) else text)

    add("moodle_backup.xml", moodle_backup_xml(k, name))
    add("files.xml", files_xml(k))
    add("gradebook.xml", gradebook_xml(k))
    import moodle_test
    for f, t in ROOT_FILES.items():
        add(f, moodle_test.questions_xml(k.pool, k.ziel["qbank"], NOW) if f == "questions.xml" else t)
    add("course/course.xml", course_xml(k))
    for f, t in COURSE_FILES.items():
        add("course/" + f, t)
    for s in k.sections:
        add(f"sections/section_{s['id']}/section.xml", section_xml(s))
        add(f"sections/section_{s['id']}/inforef.xml", "<inforef>\n</inforef>")
    for a in k.activities:
        d = f"activities/{a['modname']}_{a['moduleid']}/"
        add(d + "module.xml", module_xml(dict(a, version=k.ziel["version"])))
        schreiber = {"scorm": scorm_xml, "h5pactivity": h5p_xml, "assign": assign_xml, "subsection": subsection_xml,
                     "quiz": lambda a: moodle_test.quiz_xml(a, k.pool, k.ziel["qbank"], NOW),
                     "qbank": lambda a: moodle_test.qbank_xml(a, NOW)}
        add(d + a["modname"] + ".xml", schreiber[a["modname"]](a))
        add(d + "grades.xml", activity_grades_xml(a))
        add(d + "grading.xml", grading_xml(a))
        add(d + "inforef.xml", inforef_xml(a, k.pool))
        for f, t in EMPTY.items():
            add(d + f, t)
    for f in k.files:
        eintraege[f"files/{f['hash'][:2]}/{f['hash']}"] = f["data"]

    # Ordnerliste + .ARCHIVE_INDEX wie bei Moodle
    ordner = set()
    for p in eintraege:
        teile = p.split("/")[:-1]
        for i in range(1, len(teile) + 1):
            ordner.add("/".join(teile[:i]) + "/")
    zeilen = []
    for p in sorted(ordner | set(eintraege)):
        if p.endswith("/"):
            zeilen.append(f"{p}\td\t0\t?")
        else:
            data = eintraege[p] if isinstance(eintraege[p], bytes) else eintraege[p].encode()
            zeilen.append(f"{p}\tf\t{len(data)}\t{NOW}")
    index = f"Moodle archive file index. Count: {len(zeilen)}\n" + "\n".join(zeilen) + "\n"

    with tarfile.open(ziel, "w:gz") as tar:
        def tar_add(p, data):
            ti = tarfile.TarInfo(p)
            ti.size, ti.mtime, ti.mode = len(data), NOW, 0o644
            tar.addfile(ti, io.BytesIO(data))
        tar_add(".ARCHIVE_INDEX", index.encode())
        for p in sorted(ordner):
            ti = tarfile.TarInfo(p)
            ti.type, ti.mtime, ti.mode = tarfile.DIRTYPE, NOW, 0o755
            tar.addfile(ti)
        for p in sorted(eintraege):
            v = eintraege[p]
            tar_add(p, v if isinstance(v, bytes) else v.encode("utf-8"))
