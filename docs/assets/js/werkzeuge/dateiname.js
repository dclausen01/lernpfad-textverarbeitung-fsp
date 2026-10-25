/* Werkzeug „dateiname“: prüft einen Dateinamen nach dem Muster JJJJ-MM-TT_Klasse_Titel_Nachname-Vorname.endung.
 * Einstellungen: endungen: [docx, pdf] · klasse: Regex fürs Klassenkürzel · klasse_hinweis · beispiel · teile: 4
 */
LPW.registriere("dateiname", function (box, cfg, h) {
  var id = "lpw-dn-" + box.dataset.nr;
  box.insertAdjacentHTML("beforeend",
    '<label class="lpw-feld" for="' + id + '">Dein Dateiname (mit Endung):</label>' +
    '<input type="text" id="' + id + '" autocomplete="off" spellcheck="false" placeholder="' + h.esc(cfg.beispiel || "2026-11-14_FSP26b_Textverarbeitung_Mustermann-Erika.docx") + '">' +
    '<div class="lpw-ergebnis" aria-live="polite"></div>');
  var input = box.querySelector("input"), aus = box.querySelector(".lpw-ergebnis"), sp = h.speicher(box);
  function pruefe() {
    var v = input.value.trim();
    sp.schreib(v);
    if (!v) { aus.innerHTML = ""; return; }
    var m = h.dateiname(v, cfg), fehler = m.filter(function (x) { return x.stufe === "bad"; }).length;
    aus.innerHTML = '<p class="lpw-zusammenfassung">' + (fehler ? "Noch " + fehler + " Problem(e):" : "👍 Der Name passt zum Schema.") + "</p>" + h.meldungen(m);
  }
  input.value = sp.lies() || "";
  input.addEventListener("input", pruefe);
  pruefe();
});
