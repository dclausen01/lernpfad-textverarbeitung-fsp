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
| `docs/` | veröffentlichte Web-Version (erzeugt – nicht von Hand ändern) |
| `ausgabe/` | Arbeitsordner beim Bauen (nicht im Repository) |

## Veröffentlichen

Die fertige Web-Version liegt in **`docs/`** – das Repository braucht zum Ansehen und Veröffentlichen nichts weiter.

- **GitHub Pages:** Bei jedem Push, der `docs/` ändert, veröffentlicht die Action `.github/workflows/pages.yml` den Ordner
  (einmalig: *Settings › Pages › Source: GitHub Actions*).
- **Plesk / eigener Webserver:** Inhalt von `docs/` hochladen – oder das ZIP `webversion-plesk` aus dem letzten Action-Lauf nehmen.

## Ändern und neu bauen

Die Quellen (`kurs.yaml`, `module/`, `seiten/` …) werden mit dem [Lernpfad-Baukasten](https://github.com/dclausen01/Lernpfad-baukasten)
(nicht öffentlich) gebaut:

```bash
python3 lehrkraft/veroeffentlichen.py <pfad-zum-baukasten>   # baut und aktualisiert docs/
```

Danach `docs/` mit committen. Lehrkräfte-Seite und Musterlösung kommen nicht nach `docs/`.

## Abgaben

Die Web-Version hat keine eigene Abgabe. Die Links zu den Nextcloud-Formularen kommen in die Modulköpfe:
`module/s2.md` (Zwischenabgabe, einzeln) und `module/gm.md` (Gruppenabgabe), jeweils `abgabe: › link: https://…`.
