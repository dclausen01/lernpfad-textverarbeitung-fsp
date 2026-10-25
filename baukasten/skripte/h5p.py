#!/usr/bin/env python3
"""H5P-Kurz-Checks für Moodle 5: aus dem „kurzcheck“ im Modulkopf wird ein H5P „Question Set“.

    python3 h5p.py [ordner] [--entwuerfe]

Nur für Module mit „h5p: true“ im Kopf. Ergebnis: ausgabe/moodle/h5p/<kurzname>_<modul>_kurzcheck.h5p –
moodle_kurs.py (--moodle 5) baut sie dann automatisch als H5P-Aktivität unter das Lernpaket.

Warum nur Moodle 5? Die aktuellen H5P-Bibliotheken brauchen den H5P-Kern 1.26/1.27; Moodle 4.2 hat 1.25.
Die Bibliotheken kommen einmalig vom H5P-Hub (Internet nötig) und liegen dann im Skill unter .cache/h5p/.
Das erste Paket muss jemand mit dem Recht „H5P-Bibliotheken aktualisieren“ hochladen (Admin/Manager),
falls die Inhaltstypen in eurem Moodle noch nicht installiert sind.
Die Rückmeldungen („richtig_text“, „falsch_text“) werden übernommen, Knopftexte kommen deutsch aus H5P.
"""
import json
import re
import sys
import urllib.request
import uuid
import zipfile

from bausteine import Uebersetzer
from gemeinsam import SKILL, Fehler, Kurs, kurs_aus_argumenten, melde_fehler_und_ende

CACHE = SKILL / ".cache" / "h5p"
HUB = "https://api.h5p.org/v1/content-types/"
LANG = "de"
HUB_PAKETE = ["H5P.QuestionSet"]


# ---------------------------------------------------------------- Bibliotheken

def hub_paket(name):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{name}.h5p"
    if not p.exists():
        print(f"lade {name} vom H5P-Hub …", file=sys.stderr)
        urllib.request.urlretrieve(HUB + name, p)
    return p


class Bibliotheken:
    """Alle Bibliotheksordner aus den Hub-Paketen (Name-Major.Minor → Zip + Dateiliste)."""

    def __init__(self, pakete):
        self.orte = {}
        for name in pakete:
            z = zipfile.ZipFile(hub_paket(name))
            for n in z.namelist():
                top = n.split("/")[0]
                if "/" in n and top not in ("content",) and top not in self.orte:
                    self.orte[top] = z

    def json(self, lib, datei):
        z = self.orte[lib]
        try:
            return json.loads(z.read(f"{lib}/{datei}"))
        except KeyError:
            return None

    def abhaengigkeiten(self, lib, mit_editor=True):
        """lib und alle (rekursiven) Abhängigkeiten, als Ordnernamen."""
        gesehen, offen = [], [lib]
        while offen:
            cur = offen.pop()
            if cur in gesehen:
                continue
            if cur not in self.orte:
                raise SystemExit(f"Bibliothek fehlt: {cur}")
            gesehen.append(cur)
            info = self.json(cur, "library.json")
            arten = ["preloadedDependencies", "dynamicDependencies"] + (["editorDependencies"] if mit_editor else [])
            for art in arten:
                for d in info.get(art) or []:
                    offen.append(f"{d['machineName']}-{d['majorVersion']}.{d['minorVersion']}")
        return gesehen

    def ordner(self, machine):
        """Neueste vorhandene Version einer Bibliothek, z. B. H5P.MultiChoice → H5P.MultiChoice-1.16"""
        kandidaten = [k for k in self.orte if k.rsplit("-", 1)[0] == machine]
        if not kandidaten:
            raise SystemExit(f"Bibliothek {machine} nicht im Cache")
        return max(kandidaten, key=lambda k: tuple(int(x) for x in k.rsplit("-", 1)[1].split(".")))

    def voreinstellungen(self, lib):
        """Standardwerte aus semantics.json, Texte aus der deutschen Sprachdatei."""
        sem = self.json(lib, "semantics.json") or []
        tr = (self.json(lib, f"language/{LANG}.json") or {}).get("semantics", [])
        return _defaults(sem, tr)

    def schreibe(self, z, libs):
        for lib in libs:
            quelle = self.orte[lib]
            for n in quelle.namelist():
                if n.startswith(lib + "/") and not n.endswith("/"):
                    z.writestr(n, quelle.read(n))


def _defaults(felder, uebersetzung):
    out = {}
    for i, f in enumerate(felder):
        tr = uebersetzung[i] if i < len(uebersetzung) and isinstance(uebersetzung[i], dict) else {}
        v = _default(f, tr)
        if v is not None:
            out[f["name"]] = v
    return out


def _default(f, tr):
    t = f.get("type")
    if t == "group":
        fs, trs = f.get("fields", []), tr.get("fields", [])
        if len(fs) == 1 and not f.get("isSubContent"):
            return _default(fs[0], trs[0] if trs else {})  # H5P speichert Ein-Feld-Gruppen „flach“
        return _defaults(fs, trs)
    if t in ("list", "library"):
        return None
    return tr.get("default", f.get("default"))


def mische(basis, extra):
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(basis.get(k), dict):
            mische(basis[k], v)
        else:
            basis[k] = v
    return basis


def paket(libs, main_machine, content, titel, ziel, unterinhalte=()):
    main = libs.ordner(main_machine)
    runtime = []
    for lib in [main] + [libs.ordner(m) for m in unterinhalte]:
        for dep in libs.abhaengigkeiten(lib, mit_editor=False):
            if dep not in runtime:
                runtime.append(dep)
    alle = []
    for lib in runtime:
        for dep in libs.abhaengigkeiten(lib, mit_editor=True):
            if dep not in alle:
                alle.append(dep)

    def dep(k):
        name, ver = k.rsplit("-", 1)
        ma, mi = ver.split(".")
        return {"machineName": name, "majorVersion": ma, "minorVersion": mi}

    h5p = {"title": titel, "language": LANG, "mainLibrary": main_machine, "embedTypes": ["iframe"],
           "license": "U", "defaultLanguage": LANG, "preloadedDependencies": [dep(k) for k in runtime]}
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("h5p.json", json.dumps(h5p, ensure_ascii=False))
        z.writestr("content/content.json", json.dumps(content, ensure_ascii=False))
        libs.schreibe(z, alle)
    return ziel


# ---------------------------------------------------------------- Kurz-Check aus dem Modulkopf

def h5p_text(html):
    """HTML → das, was H5P in Texten erlaubt (<kbd> und Menüpfade werden fett)."""
    s = re.sub(r"<kbd>(.*?)</kbd>", r"<strong>\1</strong>", html)
    s = re.sub(r'<span class="path">(.*?)</span>', r"<strong>\1</strong>", s)
    s = re.sub(r"<(?!/?(strong|em|b|i|sub|sup|u|code)\b)[^>]+>", "", s)
    return s.strip()


def baue_kurzcheck(libs, kurs, m, ziel):
    u = Uebersetzer()
    mc_lib = libs.ordner("H5P.MultiChoice")
    mc_basis = libs.voreinstellungen(mc_lib)
    questions = []
    for i, f in enumerate(m.get("kurzcheck") or [], 1):
        richtig = int(f["richtig"]) - 1
        ok = f.get("richtig_text", "Richtig!")
        no = f.get("falsch_text", "Noch nicht – versuch es nochmal.")
        params = mische(json.loads(json.dumps(mc_basis)), {
            "question": f"<p>{h5p_text(u.inline(f['frage']))}</p>",
            "answers": [{"text": f"<div>{h5p_text(u.inline(o))}</div>", "correct": j == richtig,
                         "tipsAndFeedback": {"tip": "", "notChosenFeedback": "",
                                             "chosenFeedback": f"<div>{h5p_text(u.inline(ok if j == richtig else no))}</div>"}}
                        for j, o in enumerate(f["antworten"])],
            "behaviour": {"type": "single", "singlePoint": True, "randomAnswers": True,
                          "enableRetry": True, "enableSolutionsButton": True},
            "overallFeedback": [{"from": 0, "to": 100}],
        })
        questions.append({"library": mc_lib.replace("-", " "), "params": params, "subContentId": str(uuid.uuid4()),
                          "metadata": {"contentType": "Multiple Choice", "license": "U", "title": f"Frage {i}"}})
    qs_lib = libs.ordner("H5P.QuestionSet")
    content = mische(libs.voreinstellungen(qs_lib), {
        "introPage": {"showIntroPage": False}, "progressType": "dots", "passPercentage": 50,
        "disableBackwardsNavigation": False, "randomQuestions": False, "questions": questions,
    })
    content["endGame"]["overallFeedback"] = [
        {"from": 0, "to": 49, "feedback": "Schau dir das Modul noch einmal an und probier es dann erneut."},
        {"from": 50, "to": 99, "feedback": "Gut! Die falschen Antworten kannst du dir mit „Lösung anzeigen“ erklären lassen."},
        {"from": 100, "to": 100, "feedback": "Alles richtig – stark!"}]
    return paket(libs, "H5P.QuestionSet", content, f"Kurz-Check {m['id'].upper()}: {m['titel']}", ziel,
                 unterinhalte=["H5P.MultiChoice"])


def baue_h5p(kurs, entwuerfe=False, still=False):
    module = [m for mid, m in kurs.module.items() if m.get("h5p") and m.get("kurzcheck")
              and (entwuerfe or kurs.freigegeben(mid))]
    if not module:
        return []
    try:
        libs = Bibliotheken(HUB_PAKETE)
    except OSError as e:
        raise Fehler(f"H5P-Bibliotheken konnten nicht geladen werden (Internet?): {e}")
    ordner = kurs.ausgabe / "moodle" / "h5p"
    ordner.mkdir(parents=True, exist_ok=True)
    fertig = []
    for m in module:
        z = baue_kurzcheck(libs, kurs, m, ordner / f"{kurs.kurzname}_{m['id']}_kurzcheck.h5p")
        fertig.append(z)
        if not still:
            print(f"  {z.name}  ({z.stat().st_size // 1024} KB)")
    return fertig


def main(argv=None):
    ap = kurs_aus_argumenten(argv, __doc__)
    ap.add_argument("--entwuerfe", action="store_true", help="auch nicht freigegebene Module")
    args = ap.parse_args(argv)
    try:
        kurs = Kurs(args.ordner)
        n = baue_h5p(kurs, args.entwuerfe)
    except Fehler as e:
        melde_fehler_und_ende(e)
    if not n:
        print("Kein Modul mit „h5p: true“ und Kurz-Check gefunden.")
    else:
        print(f"✓ {len(n)} H5P-Paket(e) in {kurs.ausgabe / 'moodle' / 'h5p'}")
    if kurs.moodle.get("version", 5) == 4:
        print("  Hinweis: moodle.version ist 4 – H5P kommt erst mit --moodle 5 in den Kurs.")


if __name__ == "__main__":
    main()
