/* Lernpfad-Baukasten – einfacher Passwortschutz für die Web-Version (zugang: in kurs.yaml).
 *
 * WICHTIG: Das ist ein Sichtschutz, keine Sicherheit. Die Inhalte stehen weiterhin im Quelltext der
 * Seiten; wer sich auskennt, kommt daran. Gedacht für: „nicht jede:r, der die Adresse hat, liest mit“
 * und für Codes, mit denen Schüler:innen spätere Stufen „freispielen“.
 *
 * kurs.js liefert LP_KURS.zugang = { salz, passwort: <Hash>|null, stufen: {id: Hash}, module: {id: Hash},
 *                                    text, stufenText }
 * Hash = SHA-256(salz + ":" + Eingabe), Eingabe ohne Leerzeichen am Rand und in Kleinbuchstaben.
 * Freigeschaltetes merkt sich der Browser (localStorage); ändert die Lehrkraft ein Passwort, ist es wieder zu.
 * Nur in der Web-Version eingebunden – in Moodle-Lernpaketen regelt Moodle den Zugang.
 */
(function () {
  "use strict";
  var K = window.LP_KURS || {};
  var Z = K.zugang;
  if (!Z) return;

  // ---------- SHA-256 (klein, ohne crypto.subtle – das fehlt bei file:// manchmal) ----------
  function sha256(text) {
    function r(n, x) { return (x >>> n) | (x << (32 - n)); }
    var k = [], h = [], i, j;
    var primes = 0, cand = 2;
    while (primes < 64) {
      var ist = true;
      for (j = 2; j * j <= cand; j++) if (cand % j === 0) { ist = false; break; }
      if (ist) {
        if (primes < 8) h[primes] = (Math.pow(cand, 1 / 2) * 4294967296) | 0;
        k[primes] = (Math.pow(cand, 1 / 3) * 4294967296) | 0;
        primes++;
      }
      cand++;
    }
    var bytes = unescape(encodeURIComponent(text)), w = [], bits = bytes.length * 8;
    for (i = 0; i < bytes.length; i++) w[i >> 2] |= bytes.charCodeAt(i) << ((3 - i % 4) * 8);
    w[bits >> 5] |= 0x80 << (24 - bits % 32);
    w[(((bits + 64) >> 9) << 4) + 15] = bits;
    for (j = 0; j < w.length; j += 16) {
      var a = h.slice(0), m = [];
      for (i = 0; i < 64; i++) {
        if (i < 16) m[i] = w[j + i] | 0;
        else {
          var s0 = r(7, m[i - 15]) ^ r(18, m[i - 15]) ^ (m[i - 15] >>> 3);
          var s1 = r(17, m[i - 2]) ^ r(19, m[i - 2]) ^ (m[i - 2] >>> 10);
          m[i] = (m[i - 16] + s0 + m[i - 7] + s1) | 0;
        }
        var t1 = (a[7] + (r(6, a[4]) ^ r(11, a[4]) ^ r(25, a[4])) + ((a[4] & a[5]) ^ (~a[4] & a[6])) + k[i] + m[i]) | 0;
        var t2 = ((r(2, a[0]) ^ r(13, a[0]) ^ r(22, a[0])) + ((a[0] & a[1]) ^ (a[0] & a[2]) ^ (a[1] & a[2]))) | 0;
        a = [(t1 + t2) | 0].concat(a.slice(0, 7));
        a[4] = (a[4] + t1) | 0;
      }
      for (i = 0; i < 8; i++) h[i] = (h[i] + a[i]) | 0;
    }
    var out = "";
    for (i = 0; i < 8; i++) out += ("00000000" + (h[i] >>> 0).toString(16)).slice(-8);
    return out;
  }
  function hash(eingabe) { return sha256(Z.salz + ":" + String(eingabe).trim().toLowerCase()); }

  // ---------- Merken ----------
  var KEY = "lernpfad-" + K.kurzname + "-zugang";
  var mem = { gesamt: null, stufen: {}, module: {} };
  try { var roh = localStorage.getItem(KEY); if (roh) mem = JSON.parse(roh) || mem; } catch (e) { /* ohne Speicher */ }
  mem.stufen = mem.stufen || {}; mem.module = mem.module || {};
  function merken() { try { localStorage.setItem(KEY, JSON.stringify(mem)); } catch (e) { /* nur für diese Seite */ } }

  function gesamtOffen() { return !Z.passwort || mem.gesamt === Z.passwort; }
  function stufeOffen(id) { return !(Z.stufen && Z.stufen[id]) || mem.stufen[id] === Z.stufen[id]; }
  function modulOffen(id) {
    var m = (K.module || []).filter(function (x) { return x.id === id; })[0];
    if (m && !stufeOffen(m.level)) return false;
    return !(Z.module && Z.module[id]) || mem.module[id] === Z.module[id];
  }
  function probiere(eingabe) {
    // Ein Code kann das Gesamtpasswort, eine Stufe oder ein Modul öffnen – alles, was passt.
    var hx = hash(eingabe), treffer = [];
    if (Z.passwort && hx === Z.passwort) { mem.gesamt = hx; treffer.push("gesamt"); }
    Object.keys(Z.stufen || {}).forEach(function (id) { if (Z.stufen[id] === hx) { mem.stufen[id] = hx; treffer.push("stufe:" + id); } });
    Object.keys(Z.module || {}).forEach(function (id) { if (Z.module[id] === hx) { mem.module[id] = hx; treffer.push("modul:" + id); } });
    if (treffer.length) merken();
    return treffer;
  }

  window.LP_ZUGANG = { gesamtOffen: gesamtOffen, stufeOffen: stufeOffen, modulOffen: modulOffen, probiere: probiere };

  // ---------- Sperre der aktuellen Seite ----------
  // Sofort (noch vor dem Aufbau der Seite) verstecken, damit nichts aufblitzt.
  var html = document.documentElement;
  if (!gesamtOffen()) html.className += " lp-gesperrt";

  function stufeName(id) { var s = (K.stufen || []).filter(function (x) { return x.id === id; })[0]; return s ? s.name : id; }

  var SIE = K.anrede === "sie";
  var TEXT_GESAMT = Z.text || (SIE ? "Dieser Lernpfad ist geschützt. Den Code bekommen Sie von Ihrer Lehrkraft."
                                   : "Dieser Lernpfad ist geschützt. Den Code bekommst du von deiner Lehrkraft.");
  var TEXT_TEIL = Z.stufenText || (SIE ? "Den Code bekommen Sie, wenn Sie die Aufgaben davor gelöst haben."
                                       : "Den Code bekommst du, wenn du die Aufgaben davor gelöst hast.");

  function maske(titel, text, zurueck, offen, danach) {
    var d = document.createElement("div");
    d.className = "lp-zugang";
    d.setAttribute("role", "dialog");
    d.setAttribute("aria-modal", "true");
    d.innerHTML = '<form class="lp-zugang-box"><div class="lp-zugang-icon">🔒</div><h1></h1><p class="lp-zugang-text"></p>' +
      '<label>Code <input type="password" autocomplete="off" autocapitalize="off" spellcheck="false" required></label>' +
      '<p class="lp-zugang-fehler" aria-live="polite"></p><p><button class="btn" type="submit">Öffnen</button>' +
      (zurueck ? ' <a class="btn secondary" href="index.html">Zur Übersicht</a>' : "") + "</p></form>";
    d.querySelector("h1").textContent = titel;
    d.querySelector(".lp-zugang-text").textContent = text;
    var input = d.querySelector("input");
    d.querySelector("form").addEventListener("submit", function (e) {
      e.preventDefault();
      probiere(input.value);
      if (offen()) { d.parentNode.removeChild(d); danach(); }
      else { d.querySelector(".lp-zugang-fehler").textContent = "Der Code passt nicht. Groß- und Kleinschreibung ist egal."; input.select(); }
    });
    document.body.appendChild(d);
    setTimeout(function () { input.focus(); }, 30);
  }

  function seiteOffen() {
    var mid = document.body && document.body.dataset.module;
    return !mid || modulOffen(mid);
  }

  function pruefeSeite(nachEntsperren) {
    if (!gesamtOffen()) {
      maske(K.titel || "Lernpfad", TEXT_GESAMT, false, gesamtOffen, function () {
        html.className = html.className.replace(/\s*lp-gesperrt/g, "");
        pruefeSeite(false);
      });
      return;
    }
    if (!seiteOffen()) {
      html.className += " lp-teil-gesperrt";
      var mid = document.body.dataset.module;
      var m = (K.module || []).filter(function (x) { return x.id === mid; })[0];
      var stufeZu = m && !stufeOffen(m.level);
      maske(stufeZu ? "Stufe „" + stufeName(m.level) + "“ ist noch gesperrt" : "Dieses Modul ist noch gesperrt",
            TEXT_TEIL, true, seiteOffen, function () { location.reload(); });
    }
  }

  document.addEventListener("DOMContentLoaded", function () { pruefeSeite(); });
})();
