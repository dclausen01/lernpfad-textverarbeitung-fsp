# Lernpfad Textverarbeitung für Haus- und Methodikarbeit (FSP)

Interaktiver Lernpfad für die Fachschule für Sozialpädagogik am BBZ Rendsburg-Eckernförde: Schriftliche Arbeiten mit
**Word, OnlyOffice und LibreOffice** nach den *Richtlinien für schriftliche Ausarbeitungen* (Stand 21.11.2025) gestalten.
Erstellt mit dem Lernpfad-Baukasten des BBZ; die nötigen Bau-Skripte liegen in `baukasten/`.

**Umfang:** 5 Stufen, 12 Module, ca. 12 Unterrichtsstunden – Einrichten · Strukturieren · Recherchieren · Belegen & Abschließen ·
Gruppenprojekt (Gruppenabgabe, 20-Punkte-Raster).

**Sofort-Rückmeldung** im Browser (reines JavaScript, nichts wird hochgeladen): Dokument-Prüfer für .docx-Dateien,
Dateinamen-Prüfer, Gliederungs-Prüfer, Quellen-Check, Angaben-Detektiv, Zitat-Trainer, Literatur-Baukasten.

## Aufbau

| Pfad | Inhalt |
| --- | --- |
| `kurs.yaml` | Kursbeschreibung, Stufen, Selbstcheck, Programm-Umschalter |
| `module/*.md` | die Module (g1–g3, s1–s2, r1–r2, b1–b4, gm) |
| `seiten/` | Spickzettel, Checkliste Richtlinien, Seite „Für Lehrkräfte“ (nur per Direktlink) |
| `material/` | Basistext, Rohtext fürs Gruppenprojekt, Musterlösung |
| `lehrkraft/` | Skripte, die Rohtext und Musterlösung erzeugen |
| `quellen.yaml`, `medien.yaml` | geprüfte Quellen und Links |
| `baukasten/` | Bau-Skripte, Vorlage und Werkzeuge (Dokument-Prüfer & Co.) |
| `ausgabe/` | Arbeitsordner beim Bauen (nicht im Repository) |

## Bauen und veröffentlichen

Alles Nötige liegt in diesem Repository – die Bau-Skripte samt Werkzeugen stecken in `baukasten/` (siehe dort).

```bash
python3 -m pip install pyyaml markdown-it-py mdit-py-plugins
python3 baukasten/skripte/bauen.py .          # Web-Version → ausgabe/web/
```

- **GitHub Pages:** Bei jedem Push auf `main` baut die Action `.github/workflows/pages.yml` die Web-Version und veröffentlicht sie
  (einmalig: *Settings › Pages › Source: GitHub Actions*). Lehrkräfte-Seite und Musterlösung werden dabei weggelassen.
- **Plesk / eigener Webserver:** Das ZIP `webversion-plesk` aus dem letzten Action-Lauf herunterladen und den Inhalt hochladen
  (oder lokal bauen und `ausgabe/web/` hochladen).

## Abgaben

Die Web-Version hat keine eigene Abgabe. Die Links zu den Nextcloud-Formularen kommen in die Modulköpfe:
`module/s2.md` (Zwischenabgabe, einzeln) und `module/gm.md` (Gruppenabgabe), jeweils `abgabe: › link: https://…`.

| Abgabe | Modul | Nextcloud-Formular |
| --- | --- | --- |
| Zwischenabgabe Übungsdokument (.docx, 10 Punkte) | `s2` | https://cloud.bbz-rd-eck.de/apps/forms/s/HwdxsScnKFBt5fBzq7NQCkeN |
| Gruppenabgabe Mini-Hausarbeit (.docx + PDF, 20 Punkte) | `gm` | https://cloud.bbz-rd-eck.de/apps/forms/s/QbewgnrzDqRTMnwPDC9RDHYp |

Beide Formulare fragen **Name** und **Klasse** als Textfeld ab (die Gruppenabgabe alle Namen der Gruppe) und
nehmen die Dateien per Upload an. Der Link steht im Modulkopf, daraus baut `bauen.py` den Knopf
„Zum Abgabeformular ↗“; ohne Link erscheint stattdessen der Hinweis, dass die Lehrkraft den Link aushändigt.
