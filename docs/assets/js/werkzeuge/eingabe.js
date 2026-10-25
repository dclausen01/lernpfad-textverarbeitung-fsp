/* Werkzeug „eingabe“: Aufgaben mit Eingabefeldern und gezielter Rückmeldung (z. B. Zitat-Trainer, Angaben suchen).
 * Einstellungen:
 *   aufgaben:
 *     - text: Aufgabenstellung (**fett**, *kursiv*)
 *       felder:
 *         - label: Beschriftung · loesung: [akzeptierte Antworten] · breit: true (mehrzeilig)
 *           regeln: [{muster: Regex, meldung: …}]          trifft das Muster → Rückmeldung
 *           pflicht: [{muster: Regex, meldung: …}]         fehlt das Muster → Rückmeldung
 *           hinweis: erscheint nach zwei Fehlversuchen
 *       erklaerung: erscheint, wenn alles stimmt
 *   regeln / pflicht: gelten für alle Felder (zusätzlich)
 *   gross_klein: false   → Groß-/Kleinschreibung egal
 */
LPW.registriere("eingabe", function (box, cfg, h) {
  var sp = h.speicher(box), stand = sp.lies() || {};
  var html = "";
  (cfg.aufgaben || []).forEach(function (a, ai) {
    html += '<div class="lpw-aufgabe" data-a="' + ai + '"><p>' + (cfg.aufgaben.length > 1 ? "<strong>" + (ai + 1) + ".</strong> " : "") + h.md(a.text || "") + "</p>";
    (a.felder || []).forEach(function (f, fi) {
      var id = "lpw-e-" + box.dataset.nr + "-" + ai + "-" + fi, wert = h.esc((stand[ai + ":" + fi]) || "");
      html += '<label class="lpw-feld" for="' + id + '">' + h.md(f.label || "Deine Antwort") + "</label>" +
        (f.breit ? '<textarea id="' + id + '" rows="3" data-f="' + fi + '" spellcheck="false">' + wert + "</textarea>"
          : '<input type="text" id="' + id + '" data-f="' + fi + '" autocomplete="off" spellcheck="false" value="' + wert + '">') +
        '<div class="lpw-fb" data-f="' + fi + '" aria-live="polite"></div>';
    });
    html += '<div class="lpw-zeile"><button type="button" class="btn">Prüfen</button></div><div class="lpw-erkl" aria-live="polite"></div></div>';
  });
  box.insertAdjacentHTML("beforeend", html);

  function gleich(a, b, gk) {
    a = h.norm(a); b = h.norm(b);
    return gk === false ? a.toLowerCase() === b.toLowerCase() : a === b;
  }
  function ohneLeer(s) { return h.norm(s).replace(/\s+/g, "").toLowerCase(); }

  var versuche = {};
  Array.prototype.forEach.call(box.querySelectorAll(".lpw-aufgabe"), function (div) {
    var ai = +div.dataset.a, a = cfg.aufgaben[ai];
    div.querySelector(".btn").addEventListener("click", function () {
      var alleRichtig = true;
      (a.felder || []).forEach(function (f, fi) {
        var feld = div.querySelector('[data-f="' + fi + '"]'), fb = div.querySelector('.lpw-fb[data-f="' + fi + '"]');
        var v = feld.value, key = ai + ":" + fi;
        stand[key] = v; sp.schreib(stand);
        var loes = [].concat(f.loesung == null ? [] : f.loesung).map(String), m = [];
        if (!h.norm(v)) { fb.innerHTML = h.meldungen([{ stufe: "warn", text: "Noch leer." }]); alleRichtig = false; return; }
        if (loes.some(function (l) { return gleich(v, l, cfg.gross_klein); })) {
          fb.innerHTML = h.meldungen([{ stufe: "ok", text: "Richtig!" }]);
          return;
        }
        alleRichtig = false;
        versuche[key] = (versuche[key] || 0) + 1;
        (f.regeln || []).concat(cfg.regeln || []).forEach(function (r) { if (new RegExp(r.muster, r.flags || "").test(h.norm(v))) m.push({ stufe: "bad", text: r.meldung, html: true }); });
        (f.pflicht || []).concat(cfg.pflicht || []).forEach(function (r) { if (!new RegExp(r.muster, r.flags || "").test(h.norm(v))) m.push({ stufe: "bad", text: r.meldung, html: true }); });
        m = m.map(function (x) { return { stufe: x.stufe, text: h.md(x.text), html: true }; });
        if (!m.length && loes.some(function (l) { return ohneLeer(l) === ohneLeer(v); }))
          m.push({ stufe: "warn", text: "Fast! Nur die Leerzeichen oder die Groß-/Kleinschreibung stimmen noch nicht ganz." });
        if (!m.length) m.push({ stufe: "bad", text: "Noch nicht richtig – vergleiche Zeichen für Zeichen mit der Regel." });
        if (versuche[key] >= 2 && f.hinweis) m.push({ stufe: "info", text: h.md(f.hinweis), html: true });
        if (versuche[key] >= 3 && loes.length) m.push({ stufe: "info", text: "Lösung: " + h.esc(loes[0]), html: true });
        fb.innerHTML = h.meldungen(m);
      });
      div.querySelector(".lpw-erkl").innerHTML = alleRichtig && a.erklaerung ? h.meldungen([{ stufe: "info", text: h.md(a.erklaerung), html: true }]) : "";
    });
  });
});
