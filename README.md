# Lernpfad Textverarbeitung für Haus- und Methodikarbeit (FSP)

Interaktiver Lernpfad für die Fachschule für Sozialpädagogik am BBZ Rendsburg-Eckernförde: Schriftliche Arbeiten mit
**Word, OnlyOffice und LibreOffice** nach den *Richtlinien für schriftliche Ausarbeitungen* (Stand 21.11.2025) gestalten.
Gebaut mit dem [Lernpfad-Baukasten](https://github.com/dclausen01/Lernpfad-baukasten).

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
| `ausgabe/` | wird erzeugt – nicht von Hand ändern |

## Bauen

```bash
python3 <baukasten>/skripte/bauen.py .          # Web-Version → ausgabe/web/
python3 <baukasten>/skripte/durchklicken.py .   # Browser-Test → ausgabe/pruefung/uebersicht.html
```

## Veröffentlichen

- **GitHub Pages:** Bei jedem Push auf `main` baut die Action `.github/workflows/pages.yml` die Web-Version und veröffentlicht
  sie (einmalig: *Settings › Pages › Source: GitHub Actions*). Lehrkräfte-Seite und Musterlösung werden dabei entfernt.
  Welcher Stand des Baukastens genommen wird, steuert die Repository-Variable `BAUKASTEN_REF` (Standard: `main`).
- **Plesk / eigener Webserver:** Den Inhalt von `ausgabe/web/` per FTP oder Dateimanager in einen Ordner hochladen – fertig.
  Alternativ das ZIP `webversion-plesk` aus dem letzten Lauf der Action herunterladen.

## Abgaben

Die Web-Version hat keine eigene Abgabe. Die Links zu den Nextcloud-Formularen kommen in die Modulköpfe:
`module/s2.md` (Zwischenabgabe, einzeln) und `module/gm.md` (Gruppenabgabe), jeweils `abgabe: › link: https://…`.
