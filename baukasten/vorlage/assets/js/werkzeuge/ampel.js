/* Werkzeug „ampel“: eine Sache anhand von Leitfragen einschätzen (z. B. Ist diese Quelle seriös?).
 * Einstellungen:
 *   feld: Beschriftung eines Textfelds (z. B. „Welche Website prüfst du?“) – optional
 *   fragen: [{frage: …, hilfe: Tipp bei „teils“/„nein“, kritisch: true}]   ja = 2, teils = 1, nein = 0 Punkte
 *   antworten: [ja, teils, nein]          eigene Beschriftung (optional)
 *   auswertung: [{ab: Prozent, stufe: ok|warn|bad, text: …}]   von oben nach unten, erste passende
 *   kritisch_text: Meldung, wenn eine kritische Frage mit „nein“ beantwortet ist
 */
LPW.registriere("ampel", function (box, cfg, h) {
  var sp = h.speicher(box), stand = sp.lies() || {}, nr = box.dataset.nr;
  var ant = cfg.antworten || ["ja", "teils", "nein"];
  var html = cfg.feld ? '<label class="lpw-feld" for="lpw-a-' + nr + '">' + h.md(cfg.feld) + '</label><input type="text" id="lpw-a-' + nr + '" value="' + h.esc(stand.feld || "") + '">' : "";
  (cfg.fragen || []).forEach(function (f, i) {
    html += '<fieldset class="lpw-frage" style="border:0;padding:0"><legend style="padding:0"><strong>' + (i + 1) + ".</strong> " + h.md(f.frage) + "</legend><div class=\"lpw-ampel\">" +
      ant.map(function (a, j) {
        return '<label><input type="radio" name="lpw-a-' + nr + "-" + i + '" value="' + (2 - j) + '"' + (stand[i] === String(2 - j) ? " checked" : "") + "><span>" + h.esc(a) + "</span></label>";
      }).join("") + "</div></fieldset>";
  });
  html += '<div class="lpw-zeile"><button type="button" class="btn">Auswerten</button><button type="button" class="btn secondary lpw-neu">Neue Quelle</button></div><div class="lpw-ergebnis" aria-live="polite"></div>';
  box.insertAdjacentHTML("beforeend", html);
  var aus = box.querySelector(".lpw-ergebnis"), feld = box.querySelector('input[type="text"]');
  function merke() {
    stand = { feld: feld ? feld.value : "" };
    (cfg.fragen || []).forEach(function (f, i) { var x = box.querySelector('input[name="lpw-a-' + nr + "-" + i + '"]:checked'); if (x) stand[i] = x.value; });
    sp.schreib(stand);
  }
  box.addEventListener("change", merke);
  box.querySelector(".lpw-neu").addEventListener("click", function () {
    Array.prototype.forEach.call(box.querySelectorAll('input[type="radio"]'), function (r) { r.checked = false; });
    if (feld) feld.value = "";
    aus.innerHTML = ""; merke();
  });
  box.querySelector(".btn").addEventListener("click", function () {
    merke();
    var fragen = cfg.fragen || [], summe = 0, offen = [], tipps = [], kritisch = [];
    fragen.forEach(function (f, i) {
      if (stand[i] == null) { offen.push(i + 1); return; }
      summe += +stand[i];
      if (+stand[i] < 2 && f.hilfe) tipps.push({ stufe: +stand[i] === 0 ? "bad" : "warn", text: "Frage " + (i + 1) + ": " + h.md(f.hilfe), html: true });
      if (+stand[i] === 0 && f.kritisch) kritisch.push(i + 1);
    });
    if (offen.length) { aus.innerHTML = h.meldungen([{ stufe: "warn", text: "Beantworte noch Frage " + offen.join(", ") + "." }]); return; }
    var prozent = Math.round(summe / (fragen.length * 2) * 100), m = [];
    var stufen = cfg.auswertung || [{ ab: 80, stufe: "ok", text: "Sieht seriös aus." }, { ab: 50, stufe: "warn", text: "Mit Vorsicht nutzen." }, { stufe: "bad", text: "Besser nicht verwenden." }];
    var treffer = stufen.filter(function (s) { return s.ab == null || prozent >= s.ab; })[0];
    if (kritisch.length) treffer = { stufe: "bad", text: cfg.kritisch_text || "Bei einer entscheidenden Frage (" + kritisch.join(", ") + ") steht „nein“ – damit fällt die Quelle durch." };
    m.push({ stufe: treffer.stufe, text: (feld && feld.value ? "„" + h.esc(feld.value) + "“: " : "") + h.md(treffer.text) + " (" + summe + " von " + fragen.length * 2 + " Punkten)", html: true });
    aus.innerHTML = h.meldungen(m.concat(tipps));
  });
});
