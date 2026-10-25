"""Markdown mit Lernpfad-Bausteinen → HTML im Design der Vorlage.

Bausteine (Container, geöffnet mit ::: name …, geschlossen mit :::; verschachtelt: außen mehr Doppelpunkte):
    :::ziele [Titel]            Lernziele-Kasten (sonst automatisch aus „lernziele“ im Modulkopf)
    :::tipp [Titel]             Tipp          :::achtung [Titel]   typischer Fehler, Warnung
    :::notiz [Titel]            Hinweis       :::gestaltung [Titel] Gestaltungsregeln
    :::kasten [Titel]           neutraler Kasten (z. B. um mehrere Checklisten)
    :::aufgabe basis 10 Titel   Aufgabe (Niveau basis|plus|kreativ|pflicht, Minuten optional, Titel)
    :::checkliste [Titel]       Liste zum Abhaken (Markdown-Liste darin)
    :::loesung [Titel]          aufklappbare Lösung
    :::schritte                 nummerierte Schrittfolge (Markdown-Liste 1. 2. 3. darin)
    ::::varianten               Anleitungen nebeneinander (bei „beide“), darin:
    :::variante <id> [Label]    Anleitung nur für eine Variante des Umschalters (z. B. ppt, oo)
    :::material <datei> Titel   Download-Kasten mit Knopf, Text darin = Beschreibung
    :::menueband <variante> <Registerkarte>   Schema eines Menübands (Zeilen: gruppen:, menue:, text:)
    :::seitenleiste <variante> <Titel>        Schema einer Seitenleiste (Zeilen: zeilen:, text:)
    :::screenshot <datei>       Bild (bzw. Platzhalter, solange die Datei fehlt); Text darin = Beschreibung
    :::schluessel <stufe|modul> Code zum Freischalten (zugang: in kurs.yaml); erscheint, sobald das Modul als
                                erledigt markiert ist. Text darin = eigener Hinweis (optional)
    :::werkzeug <name> [Titel]  interaktives Werkzeug mit Sofort-Rückmeldung (assets/js/werkzeuge/<name>.js,
                                eigene im Kursordner unter werkzeuge/); Text darin = Einstellungen als YAML
    :::kurzcheck / :::abgabe / :::raster / :::medien   Platzhalter: hier erscheinen Kurz-Check, Abgabe,
                                Bewertungsraster, Videos aus dem Modulkopf (sonst am Ende des Moduls)
Jeder Baustein kann am Ende der Kopfzeile {id} bekommen, z. B. ":::notiz Nur für PowerPoint {ppt}" – dann erscheint
er nur bei dieser Variante des Umschalters.
Kurzschreibweisen im Text:
    {{Start › Schriftart}}      Menüpfad          ++Strg+C++ oder ++Enter++   Tasten
    [Text](modul:e2)            Link auf ein anderes Modul
    <span class="ppt">…</span>  Text nur für eine Variante (HTML ist erlaubt)
"""
import html
import json
import re

import yaml

from markdown_it import MarkdownIt
from mdit_py_plugins.container import container_plugin

NIVEAU = {"basis": ("basis", "Basis"), "plus": ("plus", "Plus"), "kreativ": ("kreativ", "Kreativ"),
          "pflicht": ("basis", "Pflicht")}
KAESTEN = {  # name: (CSS-Klasse, Standardtitel)
    "ziele": ("goals", "🎯 Das kannst du nach diesem Modul"),
    "tipp": ("tip", "💡 Tipp"),
    "achtung": ("warn", "⚠️ Achtung"),
    "notiz": ("note", ""),
    "gestaltung": ("design", "✏️ Gestaltungsregeln"),
    "kasten": ("plain", ""),
}
ROH = ("menueband", "seitenleiste", "screenshot", "kurzcheck", "abgabe", "raster", "medien", "schluessel", "werkzeug")
ALLE = set(KAESTEN) | {"aufgabe", "checkliste", "loesung", "schritte", "varianten", "variante", "material"} | set(ROH)

esc = lambda s: html.escape(str(s), quote=True)


def klassen(rest):
    """„Titel {ppt}“ → („Titel“, " ppt") – Varianten-Klasse am Ende der Kopfzeile."""
    m = re.search(r"\s*\{([\w -]+)\}\s*$", rest)
    if not m:
        return rest, ""
    return rest[:m.start()].strip(), " " + " ".join(m.group(1).split())


class Uebersetzer:
    def __init__(self, varianten=None, modul_datei=None):
        self.varianten = varianten or {}           # id → Anzeigename
        self.modul_datei = modul_datei or {}       # Modul-ID → HTML-Datei
        self.md = MarkdownIt("commonmark", {"html": True, "typographer": False}).enable("table")
        ich = self

        def render(_renderer, tokens, idx, options, env):  # markdown-it bindet die Funktion an seinen Renderer
            return ich._container(tokens, idx, options, env)
        for name in ALLE - set(ROH):
            self.md.use(container_plugin, name=name, render=render)

        def link_open(renderer, tokens, idx, options, env):  # externe Links im neuen Tab (YouTube & Co. lassen sich nicht im Lernpaket anzeigen)
            if re.match(r"https?://", tokens[idx].attrGet("href") or ""):
                tokens[idx].attrSet("target", "_blank")
                tokens[idx].attrSet("rel", "noopener")
            return renderer.renderToken(tokens, idx, options, env)
        self.md.add_render_rule("link_open", link_open)
        self._stapel = []

    # -- Container
    def _container(self, tokens, idx, _opts, _env):
        t = tokens[idx]
        name = t.info.strip().split(" ", 1)[0]
        rest = t.info.strip()[len(name):].strip()
        if t.nesting == 1:
            self._stapel.append((name, rest))
            return self._auf(name, rest)
        name, rest = self._stapel.pop()
        return self._zu(name, rest)

    def _auf(self, name, rest):
        rest, extra = klassen(rest)
        if name in KAESTEN:
            cls, titel = KAESTEN[name]
            titel = rest or titel
            return f'<div class="box {cls}{extra}">' + (f'<div class="box-title">{self.inline(titel)}</div>' if titel else "")
        if name == "aufgabe":
            teile = rest.split()
            niveau = teile.pop(0).lower() if teile and teile[0].lower() in NIVEAU else "basis"
            minuten = teile.pop(0) if teile and re.fullmatch(r"\d+\+?", teile[0]) else ""
            cls, label = NIVEAU[niveau]
            return (f'<div class="box task {cls}{extra}"><div class="task-head"><span class="lvl {cls}">{label}</span>'
                    f'<h3>{self.inline(" ".join(teile))}</h3>' +
                    (f'<span class="lvl time">{minuten.rstrip("+")} min{" +" if minuten.endswith("+") else ""}</span>' if minuten else "") + "</div>")
        if name == "checkliste":
            return f'<div class="checkliste{extra}">' + (f'<div class="check-title">{self.inline(rest)}</div>' if rest else "")
        if name == "loesung":
            return f"<details{' class=' + chr(34) + extra.strip() + chr(34) if extra else ''}><summary>{self.inline(rest or 'Lösung')}</summary>"
        if name == "schritte":
            return f'<div class="schritte{extra}">'
        if name == "varianten":
            return '<div class="both-grid">'
        if name == "variante":
            v, _, label = rest.partition(" ")
            return f'<div class="box how {esc(v)}"><span class="app-label">{self.inline(label.strip() or self.varianten.get(v, v))}</span>'
        if name == "material":
            datei, _, titel = rest.partition(" ")
            return f'<div class="box download{extra}"><div class="box-title">📥 {self.inline(titel or datei)}</div>'
        return "<div>"

    def _zu(self, name, rest):
        if name == "aufgabe" or name in KAESTEN or name in ("checkliste", "schritte", "varianten", "variante"):
            return "</div>"
        if name == "loesung":
            return "</details>"
        if name == "material":
            datei = klassen(rest)[0].partition(" ")[0]
            return (f'<p><a class="btn" href="{esc(datei)}" download>{esc(datei.rsplit("/", 1)[-1])} herunterladen</a></p></div>')
        return "</div>"

    # -- Verschachtelung: Doppelpunkte automatisch setzen, damit man immer ::: schreiben kann
    @staticmethod
    def _verschachtelung(text):
        zeilen = text.split("\n")
        paare, stapel, in_code = [], [], False
        for i, z in enumerate(zeilen):
            if z.lstrip().startswith("```"):
                in_code = not in_code
            if in_code:
                continue
            auf = re.match(r"^:{3,}\s*(\w+)", z)
            if auf and auf.group(1) in ALLE:
                stapel.append([i, None, []])
                if len(stapel) > 1:
                    stapel[-2][2].append(stapel[-1])
            elif re.match(r"^:{3,}\s*$", z) and stapel:
                knoten = stapel.pop()
                knoten[1] = i
                if not stapel:
                    paare.append(knoten)
        def hoehe(k):
            return 0 if not k[2] else 1 + max(hoehe(c) for c in k[2])
        def setze(k):
            n = 3 + hoehe(k)
            zeilen[k[0]] = re.sub(r"^:{3,}", ":" * n, zeilen[k[0]])
            if k[1] is not None:
                zeilen[k[1]] = ":" * n
            for c in k[2]:
                setze(c)
        for k in paare:
            setze(k)
        return "\n".join(zeilen)

    # -- Vorverarbeitung: Kurzschreibweisen und „rohe“ Bausteine (ohne Markdown darin)
    def _vor(self, text):
        text = self._verschachtelung(text)
        zeilen, out, i = text.split("\n"), [], 0
        in_code = False
        while i < len(zeilen):
            z = zeilen[i]
            if z.lstrip().startswith("```"):
                in_code = not in_code
            m = None if in_code else re.match(r"^(:{3,})\s*(\w+)\s*(.*)$", z)
            if m and m.group(2) in ROH:
                zu, name, rest = m.group(1), m.group(2), m.group(3).strip()
                inhalt = []
                i += 1
                while i < len(zeilen) and zeilen[i].strip() != zu:
                    inhalt.append(zeilen[i])
                    i += 1
                out.append("")
                out.append(self._roh(name, rest, "\n".join(inhalt).strip()))
                out.append("")
                i += 1
                continue
            out.append(z if in_code else self._kurz(z))
            i += 1
        return "\n".join(out)

    def _kurz(self, z):
        z = re.sub(r"\{\{\s*(.+?)\s*\}\}", lambda m: f'<span class="path">{esc(m.group(1))}</span>', z)
        z = re.sub(r"\+\+(.+?)\+\+", lambda m: self._tasten(m.group(1)), z)
        return z

    @staticmethod
    def _tasten(t):
        """++Strg+C++ → <kbd>Strg</kbd>+<kbd>C</kbd>; einzelne Taste wie gehabt."""
        teile = t.split("+")
        if len(teile) > 1 and all(x.strip() for x in teile):
            return "+".join(f"<kbd>{esc(x.strip())}</kbd>" for x in teile)
        return f"<kbd>{esc(t)}</kbd>"

    def _roh(self, name, rest, inhalt):
        rest, extra = klassen(rest)
        felder = {}
        for zeile in inhalt.split("\n"):
            k, sep, v = zeile.partition(":")
            if sep and re.fullmatch(r"[a-zäöü]+", k.strip()):
                felder[k.strip()] = v.strip()
        if name == "menueband":
            app, _, tab = rest.partition(" ")
            attrs = {"data-app": app, "data-tab": tab, "data-groups": felder.get("gruppen", ""),
                     "data-menu": felder.get("menue", ""), "data-caption": felder.get("text", "")}
            return '<figure class="rb" ' + " ".join(f'{k}="{esc(v)}"' for k, v in attrs.items() if v) + "></figure>"
        if name == "seitenleiste":
            app, _, titel = rest.partition(" ")
            attrs = {"data-app": app, "data-title": titel, "data-rows": felder.get("zeilen", ""),
                     "data-caption": felder.get("text", "")}
            return '<figure class="sp" ' + " ".join(f'{k}="{esc(v)}"' for k, v in attrs.items() if v) + "></figure>"
        if name == "schluessel":
            # Der Code selbst kommt von bauen.py (zugang: in kurs.yaml) – hier nur der Platzhalter
            return f'<div class="box lp-schluessel" data-ziel="{esc(rest)}" data-text="{esc(inhalt)}"></div>'
        if name == "werkzeug":
            werkzeug, _, titel = rest.partition(" ")
            return (f'<div class="box lp-werkzeug{extra}" data-werkzeug="{esc(werkzeug)}" data-titel="{esc(titel.strip())}" '
                    f'data-config="{esc(json.dumps(werkzeug_config(inhalt), ensure_ascii=False, default=str))}">'
                    '<noscript>Dieses Werkzeug braucht JavaScript.</noscript></div>')
        if name == "screenshot":
            return f'<figure class="shot{extra}" data-src="{esc(rest)}" data-desc="{esc(inhalt)}"></figure>'
        return f'<div data-lp="{name}"></div>'

    # -- Nachbearbeitung
    def _nach(self, h):
        h = re.sub(r"<table>", '<div class="table-wrap"><table>', h)
        h = re.sub(r"</table>", "</table></div>", h)
        h = re.sub(r'href="modul:([\w-]+)"', lambda m: f'href="{self.modul_datei.get(m.group(1), m.group(1) + ".html")}"', h)
        h = re.sub(r'(<div class="checkliste[^"]*">(?:<div class="check-title">.*?</div>)?\s*)<ul>', r'\1<ul class="check">', h)
        h = re.sub(r'(<div class="schritte[^"]*">\s*)<ol>', r'\1<ol class="steps">', h)
        return h

    def block(self, text):
        self._stapel = []
        return self._nach(self.md.render(self._vor(text or "")))

    def inline(self, text):
        return self.md.renderInline(self._kurz(str(text or "")))


def werkzeug_config(inhalt):
    """Einstellungen eines :::werkzeug (YAML im Baustein) – leer ergibt {}."""
    daten = yaml.safe_load(inhalt) if inhalt.strip() else {}
    if daten is None:
        return {}
    if not isinstance(daten, dict):
        raise ValueError("Die Einstellungen im Werkzeug müssen Felder sein (name: wert).")
    return daten


def werkzeuge_im_text(text):
    """Für pruefen.py: (Zeile, Name, Einstellungen-Text) jedes :::werkzeug."""
    zeilen, out = text.split("\n"), []
    for i, z in enumerate(zeilen):
        m = re.match(r"^(:{3,})\s*werkzeug\s+(\S+)", z)
        if m:
            inhalt = []
            for w in zeilen[i + 1:]:
                if w.strip() == m.group(1) or re.fullmatch(r":{3,}\s*", w):
                    break
                inhalt.append(w)
            out.append((i + 1, m.group(2), "\n".join(inhalt)))
    return out


def unbekannte_bausteine(text):
    """Für pruefen.py: Zeilen mit ::: name, die es nicht gibt (würden sonst als Text erscheinen)."""
    fehler = []
    for nr, z in enumerate(text.split("\n"), 1):
        m = re.match(r"^:{3,}\s*(\w+)", z)
        if m and m.group(1) not in ALLE:
            fehler.append((nr, m.group(1)))
    return fehler
