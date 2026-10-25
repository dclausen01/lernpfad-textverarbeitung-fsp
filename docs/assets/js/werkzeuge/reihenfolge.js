/* Werkzeug „reihenfolge“: Bausteine in die richtige Reihenfolge klicken (z. B. eine Literaturangabe zusammensetzen).
 * Einstellungen:
 *   aufgaben:
 *     - text: Aufgabenstellung · teile: [richtige Reihenfolge] · ablenker: [falsche Bausteine]
 *       erklaerung: nach dem Lösen · vorschau: true (Ergebnis als Literaturangabe mit hängendem Einzug zeigen)
 *   *kursiv* in einem Baustein wird kursiv angezeigt.
 */
LPW.registriere("reihenfolge", function (box, cfg, h) {
  (cfg.aufgaben || []).forEach(function (a, ai) {
    var div = document.createElement("div");
    div.className = "lpw-aufgabe";
    div.innerHTML = "<p>" + (cfg.aufgaben.length > 1 ? "<strong>" + (ai + 1) + ".</strong> " : "") + h.md(a.text || "") + "</p>" +
      '<p class="lpw-sr">Klicke die Bausteine in der richtigen Reihenfolge an. Ein Klick auf einen gesetzten Baustein nimmt ihn zurück.</p>' +
      '<div class="lpw-teile ziel" aria-label="Deine Angabe"></div><div class="lpw-teile vorrat" aria-label="Bausteine"></div>' +
      (a.vorschau !== false ? '<div class="lpw-vorschau" aria-label="Vorschau" hidden></div>' : "") +
      '<div class="lpw-zeile"><button type="button" class="btn">Prüfen</button><button type="button" class="btn secondary lpw-neu">Neu mischen</button></div>' +
      '<div class="lpw-ergebnis" aria-live="polite"></div>';
    box.appendChild(div);
    var ziel = div.querySelector(".ziel"), vorrat = div.querySelector(".vorrat"), vorschau = div.querySelector(".lpw-vorschau"), aus = div.querySelector(".lpw-ergebnis");
    var teile = (a.teile || []).map(function (t, i) { return { t: String(t), soll: i }; }).concat((a.ablenker || []).map(function (t) { return { t: String(t), soll: -1 }; }));
    function knopf(teil) {
      var b = document.createElement("button");
      b.type = "button"; b.innerHTML = h.md(teil.t); b._teil = teil;
      b.addEventListener("click", function () {
        (b.parentNode === ziel ? vorrat : ziel).appendChild(b);
        Array.prototype.forEach.call(div.querySelectorAll(".lpw-teile button"), function (x) { x.classList.remove("richtig", "falsch"); });
        aus.innerHTML = ""; zeigeVorschau();
      });
      return b;
    }
    function zeigeVorschau() {
      if (!vorschau) return;
      var gesetzt = Array.prototype.map.call(ziel.children, function (b) { return h.md(b._teil.t); });
      vorschau.hidden = !gesetzt.length; vorschau.innerHTML = gesetzt.join(" ");
    }
    function neu() {
      ziel.innerHTML = ""; vorrat.innerHTML = ""; aus.innerHTML = "";
      h.mischen(teile).forEach(function (t) { vorrat.appendChild(knopf(t)); });
      zeigeVorschau();
    }
    div.querySelector(".lpw-neu").addEventListener("click", neu);
    div.querySelector(".btn").addEventListener("click", function () {
      var gesetzt = Array.prototype.slice.call(ziel.children), richtig = 0, ablenker = 0;
      gesetzt.forEach(function (b, i) {
        var ok = b._teil.soll === i;
        if (b._teil.soll < 0) ablenker++;
        b.classList.toggle("richtig", ok); b.classList.toggle("falsch", !ok);
        if (ok) richtig++;
      });
      var n = a.teile.length, m = [];
      if (richtig === n && gesetzt.length === n) {
        m.push({ stufe: "ok", text: "Perfekt – alle Bausteine stehen richtig." });
        if (a.erklaerung) m.push({ stufe: "info", text: h.md(a.erklaerung), html: true });
      } else {
        m.push({ stufe: "bad", text: richtig + " von " + n + " Bausteinen stehen an der richtigen Stelle (grün)." });
        if (ablenker) m.push({ stufe: "warn", text: ablenker + " Baustein(e) gehören gar nicht in die Angabe." });
        if (gesetzt.length < n) m.push({ stufe: "info", text: "Es fehlen noch " + (n - gesetzt.length + ablenker) + " Baustein(e)." });
      }
      aus.innerHTML = h.meldungen(m);
    });
    neu();
  });
});
