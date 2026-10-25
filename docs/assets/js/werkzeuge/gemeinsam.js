/* Lernpfad-Baukasten – gemeinsame Grundlage der Werkzeuge (:::werkzeug <name>).
 * Jedes Werkzeug liegt in assets/js/werkzeuge/<name>.js und meldet sich mit
 *   LPW.registriere("<name>", function (box, cfg, h) { … });
 * an. box = der Kasten im Modul, cfg = Einstellungen aus dem Baustein (YAML → JSON), h = Hilfsfunktionen.
 * Alles läuft im Browser – es wird nichts hochgeladen oder gespeichert, außer kleinen Eingaben im localStorage.
 */
(function () {
  "use strict";
  var werkzeuge = {};

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  // Einheitliche Schreibweise für Vergleiche: Anführungszeichen, Striche, Leerraum
  function norm(s) {
    return String(s == null ? "" : s)
      .replace(/[„“”‟″"«»]/g, '"').replace(/[‚‘’‛′']/g, "'")
      .replace(/[‐-―−]/g, "-").replace(/ /g, " ")
      .replace(/\s+/g, " ").trim();
  }

  // Ergebnisliste: [{stufe: "ok"|"warn"|"bad"|"info", text: "…", tipp: "…"}]
  function meldungen(liste) {
    var sym = { ok: "✔", warn: "!", bad: "✘", info: "ℹ" };
    return '<ul class="lpw-meldungen">' + liste.map(function (m) {
      return '<li class="' + esc(m.stufe) + '"><span class="sym" aria-hidden="true">' + sym[m.stufe] + "</span><span>" +
        '<span class="sr">' + ({ ok: "In Ordnung: ", warn: "Hinweis: ", bad: "Fehler: ", info: "Info: " }[m.stufe]) + "</span>" +
        (m.html ? m.text : esc(m.text)) + (m.tipp ? '<small>' + (m.html ? m.tipp : esc(m.tipp)) + "</small>" : "") + "</span></li>";
    }).join("") + "</ul>";
  }

  function speicher(box) {
    var key = "lpw:" + location.pathname.split("/").pop() + ":" + box.dataset.nr;
    return {
      lies: function () { try { return JSON.parse(localStorage.getItem(key) || "null"); } catch (e) { return null; } },
      schreib: function (v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) { /* gesperrt: egal */ } }
    };
  }

  /* Gliederungsregeln (numerische Gliederung, wie in vielen Richtlinien für schriftliche Arbeiten):
   * eintraege = [{ebene: 1.., nummer: "2.1" | "2.1." | "", text: "…"}]
   * cfg.punkt_oben (Standard true): Punkt nur hinter der Nummer der obersten Ebene („1.“, aber „1.1“)
   * cfg.min_unterpunkte (Standard 2): wer unterteilt, braucht mindestens so viele Unterpunkte */
  function gliederung(eintraege, cfg) {
    cfg = cfg || {};
    var punktOben = cfg.punkt_oben !== false, minU = cfg.min_unterpunkte || 2;
    var out = [], zaehler = [], kinder = {}, fehlerPunkt = [], fehlerNr = [], spruenge = [];
    eintraege.forEach(function (e, i) {
      var nr = (e.nummer || "").trim();
      // Ebenen-Zähler mitführen und Soll-Nummer bilden
      zaehler.length = e.ebene;
      for (var k = 0; k < e.ebene - 1; k++) if (zaehler[k] == null) { zaehler[k] = 0; spruenge.push(e.text); }
      zaehler[e.ebene - 1] = (zaehler[e.ebene - 1] || 0) + 1;
      var soll = zaehler.slice(0, e.ebene).join(".");
      var eltern = zaehler.slice(0, e.ebene - 1).join(".");
      if (e.ebene > 1) kinder[eltern] = (kinder[eltern] || 0) + 1;
      if (!nr) return;
      var ohnePunkt = nr.replace(/\.$/, "");
      if (ohnePunkt !== soll) fehlerNr.push(nr + " " + e.text + " (erwartet: " + soll + (e.ebene === 1 && punktOben ? "." : "") + ")");
      if (punktOben) {
        if (e.ebene === 1 && !/\.$/.test(nr)) fehlerPunkt.push(nr + " " + e.text + " → „" + ohnePunkt + ".“");
        if (e.ebene > 1 && /\.$/.test(nr)) fehlerPunkt.push(nr + " " + e.text + " → „" + ohnePunkt + "“");
      }
    });
    var einsam = Object.keys(kinder).filter(function (k) { return kinder[k] < minU; });
    var mitNr = eintraege.filter(function (e) { return (e.nummer || "").trim(); }).length;
    if (mitNr && mitNr < eintraege.length)
      out.push({ stufe: "warn", text: "Nicht alle Überschriften haben eine Nummer.", tipp: "Nummeriere entweder alle Kapitel oder – bei Literaturverzeichnis & Co. – bewusst keine." });
    if (spruenge.length)
      out.push({ stufe: "bad", text: "Ebene übersprungen bei: " + spruenge.join(", "), tipp: "Auf Ebene 1 folgt Ebene 2, erst dann Ebene 3." });
    out.push(fehlerNr.length ? { stufe: "bad", text: "Nummern passen nicht zur Reihenfolge: " + fehlerNr.join("; ") }
      : { stufe: "ok", text: "Die Nummern laufen lückenlos durch." });
    if (punktOben) out.push(fehlerPunkt.length ? { stufe: "bad", text: "Punkt-Regel verletzt: " + fehlerPunkt.join("; "), tipp: "Nur die oberste Ebene hat einen Punkt: „1.“ – darunter „1.1“ und „1.1.1“ ohne Punkt am Ende." }
      : { stufe: "ok", text: "Punkt-Regel eingehalten (Punkt nur auf der obersten Ebene)." });
    out.push(einsam.length ? { stufe: "bad", text: "Nur ein Unterpunkt unter: " + einsam.map(function (k) { return k + (punktOben && k.indexOf(".") < 0 ? "." : ""); }).join(", "),
      tipp: "Ein Kapitel darfst du nur unterteilen, wenn mindestens " + minU + " Unterpunkte folgen." }
      : { stufe: "ok", text: "Jedes unterteilte Kapitel hat mindestens " + minU + " Unterpunkte." });
    return out;
  }

  /* Dateinamen nach dem Muster JJJJ-MM-TT_Klasse_Titel_Nachname-Vorname.endung prüfen.
   * cfg.endungen (z. B. [docx, pdf]), cfg.teile (Standard 4), cfg.klasse (Regex für das Klassenkürzel, optional) */
  function dateiname(name, cfg) {
    cfg = cfg || {};
    var out = [], endungen = cfg.endungen || ["docx", "odt", "pdf"];
    name = String(name || "").trim();
    var m = name.match(/^(.*)\.([A-Za-z0-9]+)$/);
    if (!m) return [{ stufe: "bad", text: "Die Dateiendung fehlt (z. B. „.docx“)." }];
    var stamm = m[1], endung = m[2].toLowerCase();
    out.push(endungen.indexOf(endung) > -1 ? { stufe: "ok", text: "Endung „." + endung + "“ passt." }
      : { stufe: "bad", text: "Endung „." + endung + "“ ist hier nicht vorgesehen (erlaubt: " + endungen.map(function (e) { return "." + e; }).join(", ") + ")." });
    if (/\s/.test(stamm)) out.push({ stufe: "bad", text: "Im Namen stehen Leerzeichen.", tipp: "Nimm stattdessen Unterstrich _ (zwischen den Teilen) oder Bindestrich - (in Namen)." });
    if (/[äöüÄÖÜß]/.test(stamm)) out.push({ stufe: "bad", text: "Im Namen stehen Umlaute oder ß.", tipp: "Schreib ae, oe, ue, ss – manche Systeme verändern Umlaute beim Hochladen." });
    if (/[^A-Za-z0-9äöüÄÖÜß_\-\s]/.test(stamm)) out.push({ stufe: "bad", text: "Im Namen stehen Sonderzeichen (z. B. Komma, Punkt, Klammer).", tipp: "Erlaubt sind Buchstaben, Ziffern, _ und -." });
    var teile = stamm.split("_"), soll = cfg.teile || 4;
    if (teile.length !== soll) {
      out.push({ stufe: "bad", text: "Der Name hat " + teile.length + " Teil(e), erwartet sind " + soll + ", getrennt durch Unterstriche.", tipp: "Muster: JJJJ-MM-TT_Klasse_TitelDerArbeit_Nachname-Vorname" });
      return out;
    }
    var d = teile[0].match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!d) {
      out.push({ stufe: "bad", text: "Das Datum vorne hat nicht die Form JJJJ-MM-TT (z. B. 2026-11-14).", tipp: /^\d{1,2}\.\d{1,2}\.\d{2,4}$/.test(teile[0]) ? "Andersherum! Jahr zuerst – sonst sortieren sich die Dateien nicht nach Datum." : "" });
    } else {
      var dt = new Date(+d[1], +d[2] - 1, +d[3]);
      var gueltig = dt.getFullYear() === +d[1] && dt.getMonth() === +d[2] - 1 && dt.getDate() === +d[3];
      out.push(gueltig ? { stufe: "ok", text: "Datum " + teile[0] + " ist gültig und steht vorne." } : { stufe: "bad", text: "Das Datum " + teile[0] + " gibt es nicht." });
    }
    if (cfg.klasse && !new RegExp("^(" + cfg.klasse + ")$", "i").test(teile[1]))
      out.push({ stufe: "warn", text: "Klassenkürzel „" + teile[1] + "“ sieht ungewöhnlich aus.", tipp: cfg.klasse_hinweis || "" });
    else out.push({ stufe: "ok", text: "Klasse: „" + teile[1] + "“." });
    out.push(/^[A-ZÄÖÜ][A-Za-z0-9]*$/.test(teile[2]) ? { stufe: "ok", text: "Titel „" + teile[2] + "“ ohne Leerzeichen, Wortanfänge groß." }
      : { stufe: "warn", text: "Titel „" + teile[2] + "“: Wörter direkt zusammenschreiben, Wortanfänge groß (z. B. MedienInDerKita)." });
    out.push(/^[A-ZÄÖÜ][^-]*(-[A-ZÄÖÜ][^-]*)+$/.test(teile[3]) ? { stufe: "ok", text: "Name „" + teile[3] + "“ in der Form Nachname-Vorname." }
      : { stufe: "bad", text: "Name „" + teile[3] + "“: erwartet wird Nachname-Vorname mit Bindestrich (z. B. Mustermann-Erika)." });
    return out;
  }

  // Mini-Markdown für Texte aus den Einstellungen: **fett**, *kursiv*, `Code`, Zeilenumbruch
  function md(s) {
    return esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/`(.+?)`/g, "<code>$1</code>").replace(/\n/g, "<br>");
  }

  function mischen(liste) {
    var a = liste.slice();
    for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)), t = a[i]; a[i] = a[j]; a[j] = t; }
    return a;
  }

  var h = { esc: esc, norm: norm, md: md, mischen: mischen, meldungen: meldungen, speicher: speicher, gliederung: gliederung, dateiname: dateiname };

  window.LPW = {
    registriere: function (name, fn) { werkzeuge[name] = fn; },
    h: h
  };

  function start() {
    var boxen = document.querySelectorAll(".lp-werkzeug");
    for (var i = 0; i < boxen.length; i++) {
      var box = boxen[i], name = box.dataset.werkzeug, cfg = {};
      box.dataset.nr = i;
      try { cfg = JSON.parse(box.dataset.config || "{}"); } catch (e) { cfg = {}; }
      var titel = box.dataset.titel || cfg.titel || "";
      if (titel) box.insertAdjacentHTML("afterbegin", '<div class="box-title">🛠️ ' + esc(titel) + "</div>");
      if (!werkzeuge[name]) {
        box.insertAdjacentHTML("beforeend", '<p class="lpw-fehler">Werkzeug „' + esc(name) + '“ konnte nicht geladen werden.</p>');
        continue;
      }
      try { werkzeuge[name](box, cfg, h); } catch (e) {
        box.insertAdjacentHTML("beforeend", '<p class="lpw-fehler">Das Werkzeug ist abgestürzt: ' + esc(e.message) + "</p>");
        if (window.console) console.error(e);
      }
    }
  }
  // Werkzeug-Skripte laden mit „defer“ nach dieser Datei – gestartet wird erst, wenn alle da sind
  if (document.readyState === "complete") setTimeout(start, 0); else document.addEventListener("DOMContentLoaded", start);
})();
