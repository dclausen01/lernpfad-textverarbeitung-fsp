/* Werkzeug „gliederung“: prüft eine eingetippte Gliederung (eine Überschrift pro Zeile, mit Nummer).
 * Einstellungen: vorgabe: Text im Feld (z. B. eine fehlerhafte Gliederung zum Verbessern) ·
 *   punkt_oben (true) · min_unterpunkte (2) · ohne_nummer: Regex für Teile ohne Kapitelnummer
 */
LPW.registriere("gliederung", function (box, cfg, h) {
  var id = "lpw-gl-" + box.dataset.nr;
  var OHNE = new RegExp(cfg.ohne_nummer || "^(literatur|quellen|übersicht verwendeter hilfsmittel|verwendete hilfsmittel|eigenständigkeit|anhang|abbildungsverzeichnis|tabellenverzeichnis|abkürzungsverzeichnis)", "i");
  box.insertAdjacentHTML("beforeend",
    '<label class="lpw-feld" for="' + id + '">Eine Überschrift pro Zeile, mit Nummer davor:</label>' +
    '<textarea id="' + id + '" rows="10" spellcheck="false"></textarea>' +
    '<div class="lpw-zeile"><button type="button" class="btn">Gliederung prüfen</button>' +
    (cfg.vorgabe ? '<button type="button" class="btn secondary lpw-reset">Vorgabe wiederherstellen</button>' : "") + "</div>" +
    '<div class="lpw-ergebnis" aria-live="polite"></div>');
  var ta = box.querySelector("textarea"), aus = box.querySelector(".lpw-ergebnis"), sp = h.speicher(box);
  ta.value = sp.lies() || cfg.vorgabe || "1. Einleitung\n2. Hauptteil\n2.1 Erster Abschnitt\n2.2 Zweiter Abschnitt\n3. Fazit\nLiteraturverzeichnis";
  function pruefe() {
    sp.schreib(ta.value);
    var eintraege = [], extra = [], misch = [], ohneNrFalsch = [], ohneNrFehlt = [];
    ta.value.split("\n").forEach(function (z) {
      z = h.norm(z);
      if (!z) return;
      var m = /^(\d+(?:\.\d+)*\.?)\s+(.+)$/.exec(z);
      if (m) {
        if (OHNE.test(m[2])) ohneNrFalsch.push(z);
        eintraege.push({ ebene: m[1].replace(/\.$/, "").split(".").length, nummer: m[1], text: m[2] });
      } else if (/^([IVXLC]+\.|[A-Za-z]\.|[a-z]\)|\d+[a-z]\)?|\d+\.\d*[a-z])\s/.test(z)) misch.push(z);
      else if (OHNE.test(z)) extra.push(z);
      else ohneNrFehlt.push(z);
    });
    var out = [];
    if (!eintraege.length) { aus.innerHTML = h.meldungen([{ stufe: "warn", text: "Keine nummerierte Zeile gefunden. Beispiel: „2.1 Der Auftrag der Kita“" }]); return; }
    if (misch.length) out.push({ stufe: "bad", text: "Mischform / andere Gliederungsart: " + misch.join(", "), tipp: "Durchgängig numerisch gliedern: 1. / 1.1 / 1.1.1 – keine I., A., a)." });
    if (ohneNrFehlt.length) out.push({ stufe: "bad", text: "Ohne Nummer: " + ohneNrFehlt.join(", "), tipp: "Alle Kapitel des Textteils bekommen eine Nummer." });
    if (ohneNrFalsch.length) out.push({ stufe: "bad", text: "Haben eine Nummer, dürfen aber keine: " + ohneNrFalsch.join(", "), tipp: "Literaturverzeichnis, Hilfsmittel, Eigenständigkeitserklärung und Anhang bleiben ohne Nummer." });
    if (extra.length) out.push({ stufe: "ok", text: "Ohne Nummer, wie es sein soll: " + extra.join(", ") });
    out = out.concat(h.gliederung(eintraege, cfg));
    var fehler = out.filter(function (x) { return x.stufe === "bad"; }).length;
    aus.innerHTML = '<p class="lpw-zusammenfassung">' + (fehler ? fehler + " Regel(n) verletzt:" : "👍 Die Gliederung hält alle Regeln ein.") + "</p>" + h.meldungen(out);
  }
  box.querySelector(".btn").addEventListener("click", pruefe);
  var r = box.querySelector(".lpw-reset");
  if (r) r.addEventListener("click", function () { ta.value = cfg.vorgabe; aus.innerHTML = ""; sp.schreib(ta.value); });
});
