#!/usr/bin/env python3
"""Baut den fertigen Moodle-Kurs als Kurssicherung (.mbz) – plus Klickanleitung als Rückfallebene.

    python3 moodle_kurs.py [ordner] [--moodle 4|5] [--entwuerfe]

Voraussetzung: bauen.py ist gelaufen. Die Lernpakete baut dieses Skript selbst mit (lernpakete.py).
Ergebnis in ausgabe/moodle/:
    <kurzname>_moodle4.mbz   in Moodle: Kurs › Mehr › Wiederverwendung › Wiederherstellen
    ANLEITUNG_moodle4.md     derselbe Kurs Schritt für Schritt von Hand (falls Wiederherstellen nicht erlaubt ist)
    lernpakete/              die einzelnen Lernpakete (SCORM)

Aufbau des Kurses (alles aus kurs.yaml und den Modulköpfen):
    Abschnitt 0      Startseite „Mein Lernpfad“ und – bei freischaltung: einstufung – die Einstufungstests
    je Stufe         ein Abschnitt; darin je Modul das Lernpaket, ggf. H5P-Kurz-Check (nur Moodle 5, h5p: true)
                     und die Abgabe (abgabe:), beim Meilenstein mit Bewertungsraster (raster:)
                     Moodle 5: jedes Modul als Unterabschnitt; Moodle 4: alles untereinander
Tests (tests: in kurs.yaml): Aktivität „Test“ mit den Fragen aus fragen/*.yaml, hinter dem Modul (nach:)
                     bzw. am Ende der Stufe (stufe:) – Details in moodle_test.py
Freischaltung (moodle: in kurs.yaml):
    reihenfolge: nacheinander   Modul frei, wenn das vorige Lernpaket erledigt ist | frei
    freischaltung: einstufung   Stufe frei nach Abgabe des Meilensteins der vorigen Stufe ODER bestandenem
                                Einstufungstest (Modell A) | offen: alle Stufen sofort (Modell B)
"""
import sys

from bausteine import Uebersetzer
from gemeinsam import Fehler, Kurs, kurs_aus_argumenten, lade_klausur_modul, melde_fehler_und_ende
from lernpakete import baue_lernpakete
import mbz
import moodle_test


def einheit_titel(m):
    return f"★ {m['titel']}" if m.get("meilenstein") else f"{m['id'].upper()} · {m['titel']}"


def raster_zeile(z, punkte_raster):
    """Rasterzeile → Moodle-Kriterium. Mit „punkte“: 0 / Hälfte / volle Punkte (Bewertungsbogen der Schule),
    sonst nicht erreicht / erreicht / besonders gut nach moodle.raster_punkte."""
    name = (f"{z['bereich']}: " if z.get("bereich") else "") + z["kriterium"]
    if "punkte" in z:
        n = z["punkte"]
        stufen = [("nicht erreicht", 0)] + ([("teilweise erreicht", n / 2)] if n >= 2 else []) + \
                 [(f"erreicht{': ' + z['erreicht'] if z.get('erreicht') else ''}", n)]
        return dict(kriterium=name, stufen=stufen)
    return dict(kriterium=name, stufen=[("nicht erreicht", punkte_raster[0]), (f"erreicht: {z['erreicht']}", punkte_raster[1])] +
                ([(f"besonders gut: {z['besonders_gut']}", punkte_raster[2])] if z.get("besonders_gut") else []))


def klausur_ordner(kurs, t):
    return (kurs.ordner / str(t["klausur"])).resolve()


def test_inhalt(kurs, t, version, entwuerfe, u, hinweise):
    """tests:-Eintrag → Inhalt vom Typ „test“ für mbz.Sicherung (None: Klausur nicht freigegeben)."""
    if t.get("klausur"):   # komplette Klausur aus dem Klausur-Baukasten (klausur.yaml in einem eigenen Ordner)
        inh = lade_klausur_modul().inhalt_fuer_lernpfad(klausur_ordner(kurs, t), version, entwuerfe, hinweise,
                                                        kurs.ausgabe / "moodle")
        if inh is None:
            return None
        inh["id"] = t["id"]
        inh["titel"] = f"📝 {t['titel']}" if t.get("titel") else f"📝 {inh['titel']}"
        return inh
    gruppen = moodle_test.test_fragen(kurs, t, version, entwuerfe, hinweise=hinweise)
    return dict(typ="test", id=t["id"], titel=f"📝 {t['titel']}", text=u.block(t.get("text", "")),
                text_md=str(t.get("text", "")).strip(), gruppen=gruppen,
                **{k: t[k] for k in ("punkte", "bestehen", "versuche", "zeit", "pro_seite", "mischen", "feedback") if k in t})


def beschreibung(kurs, pakete, version, h5p_dateien=None, entwuerfe=False, hinweise=None):
    """kurs.yaml + Modulköpfe → Kursbeschreibung für mbz.Sicherung."""
    mo = kurs.moodle
    u = Uebersetzer()
    hinweise = hinweise if hinweise is not None else []
    tests = kurs.k.get("tests") or []
    nach_modul, am_ende = {}, {}
    for t in tests:
        if t.get("nach"):
            nach_modul.setdefault(t["nach"], []).append(t)
        elif t.get("stufe"):
            am_ende.setdefault(t["stufe"], []).append(t)
        else:
            raise Fehler(f"Test {t.get('id')}: „nach: <modul>“ oder „stufe: <stufe>“ fehlt")
    h5p_dateien = h5p_dateien or {}
    punkte_raster = mo.get("raster_punkte", [0, 2, 3])
    b = dict(kurs=dict(titel=kurs.titel, kurzname=kurs.kurzname,
                       text=f"<p>{u.inline(kurs.k.get('untertitel', ''))}</p>" if kurs.k.get("untertitel") else ""),
             allgemein=dict(inhalte=[]), abschnitte=[])
    allg = b["allgemein"]["inhalte"]
    if "start" in pakete:
        allg.append(dict(typ="lernpaket", id="start", titel="🧭 Mein Lernpfad – hier geht's los",
                         datei=pakete["start"], abschluss=False, punkte=0))
    bestehen = (kurs.k.get("einstufung") or {}).get("bestehen", 80)
    einstufung = {}
    if kurs.einstufung_aktiv():
        for s in kurs.stufen[1:]:
            pid = kurs.einstufung_datei(s["id"])[:-5]
            if pid in pakete and any(m in pakete for m in s.get("module") or []):
                einstufung[s["id"]] = pid
                allg.append(dict(typ="lernpaket", id=pid, titel=f"🎯 Einstufungstest: direkt zu {s['name']}",
                                 datei=pakete[pid], abschluss=False))

    vorige_stufe_ende = None  # was die nächste Stufe freischaltet (Meilenstein-Abgabe bzw. letztes Lernpaket)
    for s in kurs.stufen:
        a = dict(titel=f"{s.get('icon', '')} {s['name']}".strip(), text=f"<p>{u.inline(s.get('text', ''))}</p>" if s.get("text") else "",
                 reihenfolge=mo.get("reihenfolge", "nacheinander"), einheiten=[])
        if mo.get("freischaltung", "einstufung") == "einstufung" and b["abschnitte"]:
            bed = [r for r in (vorige_stufe_ende, {"id": einstufung.get(s["id"]), "mindestens": bestehen}
                               if s["id"] in einstufung else None) if r]
            if bed:
                a["freischalten_nach"] = bed
        ende = None
        for m in kurs.module_der_stufe(s["id"]):
            mid = m["id"]
            if mid not in pakete:
                continue  # nicht freigegeben
            inhalte = [dict(typ="lernpaket", id=mid, datei=pakete[mid],
                            titel=(f"{einheit_titel(m)} – Auftrag & Checkliste" if m.get("meilenstein") and m.get("abgabe")
                                   else einheit_titel(m)))]
            ende = mid
            if m.get("h5p") and version == "5" and mid in h5p_dateien:
                inhalte.append(dict(typ="h5p", id=f"{mid}-check", titel=f"{mid.upper()} · Kurz-Check", datei=h5p_dateien[mid]))
            ab = m.get("abgabe")
            if ab:
                auf = dict(typ="aufgabe", id=f"{mid}-abgabe",
                           titel=f"📤 {ab['titel']}" if ab.get("titel") else f"📤 Abgabe: {m['titel']}",
                           text=u.block(ab.get("text", "")), text_md=str(ab.get("text", "")).strip(), punkte=ab.get("punkte", 100),
                           dateitypen=ab.get("dateitypen", ""), dateien=ab.get("dateien", 1))
                if m.get("raster"):
                    auf["raster"] = dict(name=f"Bewertungsraster: {m['titel']}", kriterien=[raster_zeile(z, punkte_raster) for z in m["raster"]])
                inhalte.append(auf)
                if m.get("meilenstein"):
                    ende = auf["id"]
            for t in nach_modul.pop(mid, []):
                ti = test_inhalt(kurs, t, version, entwuerfe, u, hinweise)
                if ti:
                    inhalte.append(ti)
            a["einheiten"].append(dict(titel=einheit_titel(m), inhalte=inhalte))
        for t in am_ende.pop(s["id"], []):
            ti = test_inhalt(kurs, t, version, entwuerfe, u, hinweise)
            if ti:
                a["einheiten"].append(dict(titel=ti["titel"], inhalte=[ti]))
        if a["einheiten"]:
            b["abschnitte"].append(a)
            vorige_stufe_ende = ende
    for rest in list(nach_modul.values()) + list(am_ende.values()):
        for t in rest:
            hinweise.append(f"Test {t['id']} ausgelassen – sein Modul bzw. seine Stufe ist nicht im Kurs (freigegeben?)")
    return b


def anleitung(kurs, b, version, mbz_name):
    """Klickanleitung: derselbe Kurs von Hand."""
    namen = {}
    for inh in b["allgemein"]["inhalte"]:
        namen[inh["id"]] = inh["titel"]
    for a in b["abschnitte"]:
        for e in a["einheiten"]:
            for inh in e["inhalte"]:
                namen[inh["id"]] = inh["titel"]

    def bed(ref):
        teile = []
        for r in ref if isinstance(ref, list) else [ref]:
            if isinstance(r, dict):
                teile.append(f"„{namen[r['id']]}“ mit mindestens {r['mindestens']} % bewertet")
            else:
                teile.append(f"„{namen[r]}“ abgeschlossen")
        return " **oder** ".join(teile)

    z = [f"# {kurs.titel} – Moodle-Kurs von Hand einrichten", "",
         "Normalerweise geht es schneller mit der Kurssicherung:",
         f"**Kurs › Mehr › Wiederverwendung › Wiederherstellen** → `{mbz_name}` hochladen → „In diesen Kurs, "
         "Inhalte hinzufügen“ → durchklicken. Diese Anleitung ist die Rückfallebene, falls Wiederherstellen "
         "nicht erlaubt ist.", "",
         "## Vorbereitung", "",
         "- Kurs › Einstellungen › **Abschlussverfolgung: Ja**",
         "- Kursformat: Themen (Moodle 5: Unterabschnitte müssen von der Moodle-Administration aktiviert sein)", "",
         "## Einstellungen für jedes Lernpaket", "",
         "Aktivität **Lernpaket** (SCORM) anlegen, ZIP aus `lernpakete/` hochladen, dann:", "",
         "- Darstellung: **Anzeige des Pakets: Aktuelles Fenster** · Breite 100 % · Höhe 500",
         "- Darstellung: **Kursstruktur anzeigen: Deaktiviert** · **Navigation anzeigen: Nein** · "
         "**Struktur-Seite überspringen: Immer** · Versuchsstatus anzeigen: Nein",
         "- Bewertung: Höchstbewertung 100, Bewertungsmethode: Höchste Bewertung",
         "- Versuchsverwaltung: Beherrschungswert überschreibt Status: Ja",
         "- Aktivitätsabschluss: **Bedingungen erfüllt** → **Status erforderlich: Abgeschlossen** "
         "(nur „abgeschlossen“ anhaken)",
         "- Ausnahme Startseite und Einstufungstests: **kein Aktivitätsabschluss**; die Startseite außerdem Bewertung 0.", ""]
    z += ["## Abschnitt „Allgemeines“ (ganz oben)", ""]
    for inh in b["allgemein"]["inhalte"]:
        z.append(f"- Lernpaket **{inh['titel']}** – `lernpakete/{inh['datei'].name}`")
    z.append("")
    for a in b["abschnitte"]:
        z += [f"## Abschnitt „{a['titel']}“", ""]
        if a.get("freischalten_nach"):
            z += [f"Voraussetzung am Abschnitt (Einschränkung: Aktivitätsabschluss bzw. Bewertung, verknüpft mit „mindestens eine“): "
                  f"{bed(a['freischalten_nach'])}.", ""]
        vorige = None
        for e in a["einheiten"]:
            sub = version == "5" and len(e["inhalte"]) > 1
            if sub:
                z.append(f"- Unterabschnitt **{e['titel']}**" + (f" – Voraussetzung: {bed(vorige)}" if vorige and a["reihenfolge"] == "nacheinander" else ""))
            for inh in e["inhalte"]:
                einr = "  " if sub else ""
                vor = f" – Voraussetzung: {bed(vorige)}" if not sub and vorige and a["reihenfolge"] == "nacheinander" else ""
                if inh["typ"] == "lernpaket":
                    z.append(f"{einr}- Lernpaket **{inh['titel']}** – `lernpakete/{inh['datei'].name}`{vor}")
                elif inh["typ"] == "h5p":
                    z.append(f"{einr}- H5P **{inh['titel']}** – `{inh['datei'].name}`{vor}")
                elif inh["typ"] == "test":
                    n = sum(1 for g in inh["gruppen"])
                    if inh.get("klausur_ordner"):
                        z.append(f"{einr}- Klausur **{inh['titel']}**{vor} – {n} Aufgaben, Bewertung {inh['punkte']:g} Punkte, "
                                 f"{inh.get('zeit', 0)} Minuten, 1 Versuch. Von Hand ist das viel Arbeit: besser die Klausur "
                                 f"einzeln bauen (`klausur.py bauen {inh['klausur_ordner']}`) und als eigene Sicherung "
                                 "wiederherstellen. Aufgaben, Punkte und Notenschlüssel stehen in den Lehrkraft-Unterlagen.")
                        continue
                    z.append(f"{einr}- Test **{inh['titel']}**{vor} – {n} Fragen aus `fragen/` (Moodle-XML importieren, "
                             "dann in den Test einfügen; Rechenaufgaben mit Varianten als Zufallsfrage aus ihrer Kategorie), "
                             f"Bewertung {inh.get('punkte', 10)} Punkte"
                             + (f", bestanden ab {inh['bestehen']} %, Abschluss: „Bestehensgrenze erreichen“" if inh.get("bestehen")
                                else ", Abschluss: „Bewertung erhalten“")
                             + (f", {inh['versuche']} Versuch(e)" if inh.get("versuche") else ", Versuche unbegrenzt")
                             + (f", Zeitbegrenzung {inh['zeit']} Minuten" if inh.get("zeit") else "")
                             + (", Frageverhalten „Direkte Auswertung“" if inh.get("feedback") == "sofort"
                                else ", Frageverhalten „Spätere Auswertung“"))
                else:
                    z.append(f"{einr}- Aufgabe **{inh['titel']}**{vor} – Dateiabgabe, höchstens {inh['dateien']} Datei(en)"
                             + (f", Dateitypen {inh['dateitypen']}" if inh["dateitypen"] else "") + f", {inh['punkte']} Punkte, "
                             "Abschluss: „Abgabe erforderlich“")
                    if inh.get("text_md"):
                        z.append(f"{einr}  Beschreibung: " + inh["text_md"].replace("\n", " "))
                    if inh.get("raster"):
                        z.append(f"{einr}  Bewertungsmethode **Bewertungsraster** mit diesen Kriterien:")
                        for k in inh["raster"]["kriterien"]:
                            z.append(f"{einr}  - {k['kriterium']}: " + " · ".join(f"{t} ({p} P.)" for t, p in k["stufen"]))
            vorige = e["inhalte"][0]["id"]
        z.append("")
    return "\n".join(z) + "\n"


def baue_kurs(kurs, version=None, entwuerfe=False, still=False):
    version = str(version or kurs.moodle.get("version", 5))
    if version not in ("4", "5"):
        raise Fehler("Moodle-Version muss 4 oder 5 sein")
    pakete = baue_lernpakete(kurs, entwuerfe, still=still)
    h5p_dateien = {}
    ordner_h5p = kurs.ausgabe / "moodle" / "h5p"
    for mid in kurs.module:
        p = ordner_h5p / f"{kurs.kurzname}_{mid}_kurzcheck.h5p"
        if p.exists():
            h5p_dateien[mid] = p
    fehlt = [m for m in kurs.module if kurs.module[m].get("h5p") and m in pakete and m not in h5p_dateien]
    if version == "5" and fehlt:
        print(f"  Hinweis: H5P für {', '.join(fehlt)} fehlt – erst h5p.py laufen lassen.", file=sys.stderr)
    hinweise = []
    b = beschreibung(kurs, pakete, version, h5p_dateien, entwuerfe, hinweise)
    for h in hinweise:
        if not still:
            print(f"  Hinweis: {h}", file=sys.stderr)
    if not b["abschnitte"]:
        raise Fehler("Kein Modul ist freigegeben – in Moodle käme ein leerer Kurs an. "
                     "Module freigeben (review: freigegeben) oder zum Testen --entwuerfe nutzen.")
    s = mbz.Sicherung(b, kurs.ordner, version)
    s.baue()
    ziel = kurs.ausgabe / "moodle" / f"{kurs.kurzname}_moodle{version}.mbz"
    mbz.schreibe_mbz(s, ziel)
    (kurs.ausgabe / "moodle" / f"ANLEITUNG_moodle{version}.md").write_text(anleitung(kurs, b, version, ziel.name), encoding="utf-8")
    typen = {}
    for a in s.activities:
        typen[a["modname"]] = typen.get(a["modname"], 0) + 1
    return ziel, typen


def main(argv=None):
    ap = kurs_aus_argumenten(argv, __doc__)
    ap.add_argument("--moodle", choices=["4", "5"], help="Standard: moodle.version aus kurs.yaml")
    ap.add_argument("--entwuerfe", action="store_true", help="auch nicht freigegebene Module (nur für Testkurse!)")
    args = ap.parse_args(argv)
    try:
        kurs = Kurs(args.ordner)
        ziel, typen = baue_kurs(kurs, args.moodle, args.entwuerfe)
    except Fehler as e:
        melde_fehler_und_ende(e)
    namen = {"scorm": "Lernpakete", "assign": "Aufgaben", "h5pactivity": "H5P", "subsection": "Unterabschnitte",
             "quiz": "Tests", "qbank": "Fragensammlung"}
    print(f"✓ Moodle-Kurs: {ziel}  ({ziel.stat().st_size // 1024} KB)")
    print("  " + ", ".join(f"{v} {namen.get(t, t)}" for t, v in sorted(typen.items())))
    print(f"  Klickanleitung: {ziel.parent / f'ANLEITUNG_moodle{ziel.stem[-1]}.md'}")


if __name__ == "__main__":
    main()
