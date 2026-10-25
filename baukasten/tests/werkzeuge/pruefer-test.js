/* Test für den Dokument-Prüfer (vorlage/assets/js/werkzeuge/docx.js) in einem echten Browser.
 *
 *   node tests/werkzeuge/pruefer-test.js        (braucht Playwright: npm i -g playwright oder NODE_PATH)
 *
 * Erwartet: die drei „guten“ Dokumente ohne Fehler, das Fehler-Dokument mit genau den eingebauten Fehlern.
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const V = path.resolve(__dirname, "../../vorlage/assets");
const ERWARTET = {
  "word-gut.docx": [],
  "libreoffice-gut.docx": [],
  "libreoffice-seitenvorlagen.docx": ["Das Verzeichnis passt nicht zum Text"], // im Testdokument absichtlich veraltet
  "word-fehler.docx": ["Seitenränder weichen ab", "Zeilenabstand ist nicht", "drei oder mehr leere Absätze", "sehen aus wie Überschriften",
    "keine Seitenzahl", "Das Verzeichnis passt nicht", "„vgl.“", "„ebd.“", "ohne hängenden Einzug", "Nicht alphabetisch", "nicht im Literaturverzeichnis"]
};

(async () => {
  const seite = path.join(__dirname, "_seite.html");
  fs.writeFileSync(seite, `<!doctype html><meta charset="utf-8"><script src="file://${V}/js/werkzeuge/gemeinsam.js" defer></script>
<script src="file://${V}/js/werkzeuge/docx.js" defer></script><div class="lp-werkzeug" data-werkzeug="docx" data-config="{}"></div>`);
  const opts = fs.existsSync("/opt/pw-browsers/chromium") ? {} : { channel: "chrome" };
  const b = await chromium.launch(opts), p = await b.newPage();
  let fehler = 0;
  p.on("pageerror", e => { console.log("✗ JavaScript-Fehler:", e.message); fehler++; });
  await p.goto("file://" + seite);
  for (const [datei, soll] of Object.entries(ERWARTET)) {
    await p.setInputFiles("input[type=file]", path.join(__dirname, datei));
    await p.waitForFunction(() => !/^Lese/.test(document.querySelector(".lpw-ergebnis").textContent));
    const rot = await p.$$eval(".lpw-meldungen li.bad", l => l.map(x => x.textContent));
    const fehlt = soll.filter(s => !rot.some(r => r.includes(s)));
    const zuviel = rot.filter(r => !soll.some(s => r.includes(s)));
    if (fehlt.length || zuviel.length) {
      fehler++;
      console.log("✗ " + datei);
      fehlt.forEach(s => console.log("    nicht gefunden: " + s));
      zuviel.forEach(s => console.log("    unerwartet: " + s));
    } else console.log("✓ " + datei + " (" + rot.length + " erwartete Fehler)");
  }
  await b.close();
  fs.unlinkSync(seite);
  process.exit(fehler ? 1 : 0);
})();
