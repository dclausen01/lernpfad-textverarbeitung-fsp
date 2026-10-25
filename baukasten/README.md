# Bau-Skripte dieses Lernpfads

Eigene Kopie der Skripte und der Vorlage des Lernpfad-Baukastens (BBZ Rendsburg-Eckernförde), **erweitert um interaktive
Werkzeuge** (Dokument-Prüfer & Co.). Der Ordner gehört zu diesem Lernpfad – damit lässt sich das Repository ohne weitere
Abhängigkeiten bauen.

```bash
python3 -m pip install pyyaml markdown-it-py mdit-py-plugins
python3 baukasten/skripte/pruefen.py .        # Inhalte prüfen
python3 baukasten/skripte/bauen.py .          # Web-Version → ausgabe/web/
python3 baukasten/skripte/durchklicken.py .   # Browser-Test (braucht playwright)
```

Erweiterungen gegenüber dem Baukasten:

- Baustein `:::werkzeug` (unten), Skripte unter `vorlage/assets/js/werkzeuge/`
- `abgabe.link` im Modulkopf: eigenes Abgabeformular je Modul in der Web-Version

## Baustein `:::werkzeug` – Werkzeuge mit Sofort-Rückmeldung

```markdown
:::werkzeug docx Dokument-Prüfer
pruefe: [raender, standard, ueberschriften]
:::
```

`:::werkzeug <name> [Titel]` baut ein interaktives Werkzeug ein; der Text darin sind seine **Einstellungen als YAML**.
Alles läuft im Browser (auch im Moodle-Lernpaket) – nichts wird hochgeladen, Eingaben merkt sich nur der Browser.
Die Werkzeuge liegen in `vorlage/assets/js/werkzeuge/<name>.js` (Beschreibung aller Einstellungen jeweils oben in der
Datei). Eigene Werkzeuge eines Kurses kommen nach `<kurs>/werkzeuge/<name>.js` und melden sich mit
`LPW.registriere("<name>", function (box, cfg, h) { … })` an. Texte der Werkzeuge sind in Du-Form.

| Werkzeug | Wozu | Wichtigste Einstellungen |
| --- | --- | --- |
| `docx` | prüft eine Word-Datei (.docx aus Word, OnlyOffice, LibreOffice) auf Formvorgaben: Ränder, Schrift, Zeilenabstand, Silbentrennung, Leerzeilen, Überschriften-Vorlagen, Gliederung, Abschnitte, Seitenzahlen, Deckblatt, Inhaltsverzeichnis, APA-Belege, Literaturverzeichnis, Beschriftungen, Fußnoten, Schlussteile | `pruefe: [...]`, `raender`, `schrift`, `groesse`, `zeilenabstand`, `ueberschrift`, `deckblatt`, `zitate_min`, `hinweis` |
| `dateiname` | prüft einen Dateinamen nach dem Schema JJJJ-MM-TT_Klasse_Titel_Nachname-Vorname | `endungen`, `klasse` (Regex), `beispiel` |
| `gliederung` | prüft eine eingetippte numerische Gliederung (Punkt-Regel, mind. zwei Unterpunkte, Mischformen) | `vorgabe` (z. B. fehlerhafte Gliederung zum Verbessern) |
| `eingabe` | Aufgaben mit Eingabefeldern, akzeptierten Lösungen und gezielten Rückmeldungen über Regex-Regeln | `aufgaben: [{text, felder: [{label, loesung, regeln, pflicht, hinweis}], erklaerung}]`, `regeln` |
| `reihenfolge` | Bausteine in die richtige Reihenfolge klicken (z. B. Literaturangabe), mit Ablenkern und Vorschau | `aufgaben: [{text, teile, ablenker, erklaerung}]` |
| `ampel` | Einschätzung anhand von Leitfragen (ja/teils/nein) mit Ampel-Ergebnis | `fragen: [{frage, hilfe, kritisch}]`, `auswertung`, `feld` |

`pruefen.py` meldet unbekannte Werkzeuge und kaputtes YAML. Tests für den Dokument-Prüfer: `node baukasten/tests/werkzeuge/pruefer-test.js` (braucht Playwright).

