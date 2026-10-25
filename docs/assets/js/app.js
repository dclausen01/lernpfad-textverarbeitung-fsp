/* Lernpfad-Baukasten – gemeinsame Logik für alle Seiten eines Lernpfads.
 * Alles Kursspezifische kommt aus window.LP_KURS (assets/js/kurs.js, von bauen.py erzeugt).
 * - Navigation (Seitenleiste, Vor/Zurück) aus den Modulen der Stufen
 * - Varianten-Umschalter (z. B. zwei Programme) – optional
 * - schematische Menüband-Grafiken (figure.rb) und Seitenleisten (figure.sp)
 * - Screenshot-Platzhalter (figure.shot)
 * - Video-/Hilfe-Links aus der zentralen Liste in medien.js (div.media)
 * - Checklisten, Kurz-Checks, "Modul erledigt" – im Browser oder (im Lernpaket) in Moodle
 * - Moodle: Kursnavigation, Startseite „Mein Lernpfad“, Einstufungstests, Kompaktmodus
 * - Zugang (nur Web): Schlösser in Navigation/Übersicht, Code-Feld je Stufe, :::schluessel (zugang.js)
 */
(function () {
  "use strict";

  var K = window.LP_KURS || { titel: "Lernpfad", kurzname: "lernpfad", stufen: [], module: [] };

  // Stufen: { id: { name, color, start } } – Farben aus kurs.css (--lv-<id>)
    // Anrede: kurs.yaml → anrede: sie  (Standard: du)
  var SIE = K.anrede === "sie";
  var DUSIE = [["Die anderen Module findest du im Moodle-Kurs.", "Die anderen Module finden Sie im Moodle-Kurs."], ["💬 Deine Notiz", "💬 Ihre Notiz"], ["Was nimmst du aus diesem Modul mit? Was war schwierig? Wo wirst du das brauchen", "Was nehmen Sie aus diesem Modul mit? Was war schwierig? Wo werden Sie das brauchen"], ["Markiere das Modul erst, wenn du die Basis-Aufgaben und deine Checkliste geschafft hast.", "Markieren Sie das Modul erst, wenn Sie die Basis-Aufgaben und Ihre Checkliste geschafft haben."], [" Dein Stand wird in Moodle gespeichert.", " Ihr Stand wird in Moodle gespeichert."], ["Du bist hier nicht als Teilnehmer:in eingeschrieben. Moodle zeigt dir deshalb", "Sie sind hier nicht als Teilnehmer:in eingeschrieben. Moodle zeigt Ihnen deshalb"], ["Dein Stand im Lernpaket", "Ihr Stand im Lernpaket"], ["Wird frei, wenn du dieses Modul als erledigt markierst.", "Wird frei, wenn Sie dieses Modul als erledigt markieren."], ["Noch gesperrt – schau im Kurs, was noch fehlt.", "Noch gesperrt – schauen Sie im Kurs, was noch fehlt."], ["Geh zurück zum Moodle-Kurs. Dort findest du das nächste Modul.", "Gehen Sie zurück zum Moodle-Kurs. Dort finden Sie das nächste Modul."], [" – wird frei, wenn du diese Seite als erledigt markierst.", " – wird frei, wenn Sie diese Seite als erledigt markieren."], ["Findest du als eigenes Modul im Moodle-Kurs", "Finden Sie als eigenes Modul im Moodle-Kurs"], ["Kopiert – du kannst die Notizen jetzt", "Kopiert – Sie können die Notizen jetzt"], ["Gib deine Dateien in der", "Geben Sie Ihre Dateien in der"], ["Dort siehst du auch, worauf es ankommt, und später das Feedback deiner Lehrkraft.", "Dort sehen Sie auch, worauf es ankommt, und später das Feedback Ihrer Lehrkraft."], ["Melde dich mit deinem Schul-Konto an, lade deine Datei(en) hoch und wähle", "Melden Sie sich mit Ihrem Schul-Konto an, laden Sie Ihre Datei(en) hoch und wählen Sie"], ["Den Link zum Abgabeformular bekommst du von deiner Lehrkraft.", "Den Link zum Abgabeformular bekommen Sie von Ihrer Lehrkraft."], ["Prüf dich zuerst mit dem", "Prüfen Sie sich zuerst mit dem"], ["Absprache mit deiner Lehrkraft geht vor.", "Absprache mit Ihrer Lehrkraft geht vor."], ["Leg los: ", "Los geht’s: "], ["Starte mit dem ersten Modul.", "Starten Sie mit dem ersten Modul."], ["Mach den ", "Machen Sie den "], [" – wenn du bestehst, wird ", " – wenn Sie bestehen, wird "], [" sofort für dich frei. Nicht bestanden? Dann arbeitest du die Module davor durch.", " sofort für Sie frei. Nicht bestanden? Dann arbeiten Sie die Module davor durch."], ["</strong> – wird frei, sobald du das Vorige abgeschlossen hast. Schau in der Kursübersicht, was noch fehlt.</p>", "</strong> – wird frei, sobald Sie das Vorige abgeschlossen haben. Schauen Sie in der Kursübersicht, was noch fehlt.</p>"], ["<p>Du hast alle Module abgeschlossen. Stark!</p>", "<p>Sie haben alle Module abgeschlossen. Stark!</p>"], ["<p>Wird frei, sobald du den Meilenstein der vorigen Stufe abgegeben hast", "<p>Wird frei, sobald Sie den Meilenstein der vorigen Stufe abgegeben haben"], ["🎯 Du kannst schon viel?</div><p>Mit einem Einstufungstest springst du direkt in eine höhere Stufe:", "🎯 Sie können schon viel?</div><p>Mit einem Einstufungstest springen Sie direkt in eine höhere Stufe:"], ["Dein bestes Ergebnis bisher: ", "Ihr bestes Ergebnis bisher: "], ["</strong> ist jetzt für dich frei.", "</strong> ist jetzt für Sie frei."], ["Schau dir die Fragen oben an – bei jeder steht, aus welchem Modul sie kommt. Du kannst es später noch einmal versuchen.", "Schauen Sie sich die Fragen oben an – bei jeder steht, aus welchem Modul sie kommt. Sie können es später noch einmal versuchen."], ["Noch nicht – versuch es nochmal.", "Noch nicht – versuchen Sie es noch einmal."], ["Dein Code für ", "Ihr Code für "], ["Der Code erscheint, sobald du dieses Modul unten als erledigt markierst.", "Der Code erscheint, sobald Sie dieses Modul unten als erledigt markieren."]];
  function A(s) { if (!SIE) return s; for (var i = 0; i < DUSIE.length; i++) s = s.split(DUSIE[i][0]).join(DUSIE[i][1]); return s; }
  // Selbstcheck-Hinweis „Absprache mit deiner Lehrkraft …“ – abschaltbar mit selbstcheck.lehrkraft_hinweis: false (z. B. für Kurse für Lehrkräfte)
  function lehrkraftHinweis() { return (K.selbstcheck && K.selbstcheck.lehrkraftHinweis === false) ? "" : A(" <br><small>Absprache mit deiner Lehrkraft geht vor.</small>"); }

  var LEVELS = {};
  K.stufen.forEach(function (st) {
    LEVELS[st.id] = { name: st.name, icon: st.icon || "", color: "var(--lv-" + st.id + ")", start: st.start };
  });
  // Module in Pfad-Reihenfolge: { id, level, file, title, min, milestone }
  var MODULES = K.module;

  // Abgabe-Link der Web-Version (z. B. Nextcloud-Formular). Leer = kein Knopf; in Moodle gibt es die Aufgabe.
  var ABGABE_LINK = K.abgabeLink || "";

  var EXTRA = K.extras || [];

  // Varianten-Umschalter: { frage, optionen: { id: Name }, beide: true|false } – optional
  var VAR = K.varianten || null;
  var VAR_IDS = VAR ? Object.keys(VAR.optionen) : [];
  // Registerkarten der Menüband-Grafiken je Variante
  var TABS = K.menueband || {};
  var APPNAME = VAR ? VAR.optionen : {};

  window.LP = { MODULES: MODULES, LEVELS: LEVELS };

  // Zugang (zugang.js, nur Web-Version): gesperrte Stufen und Module
  var ZG = window.LP_ZUGANG || null;
  function modZu(m) { return ZG && !PKG && !ZG.modulOffen(m.id); }
  function stufeZu(lv) { return ZG && !PKG && !ZG.stufeOffen(lv); }

  // ---------- Moodle-Paket (SCORM) ----------
  // Im Moodle-Paket setzt das Build-Skript LP_SCORM_CONFIG (enthaltene Dateien, Startseite);
  // scorm.js stellt LP_SCORM bereit. In der Web-Version gibt es beides nicht.
  var PKG = window.LP_SCORM_CONFIG || null;
  var SC = window.LP_SCORM && window.LP_SCORM.active ? window.LP_SCORM : null;
  function inPackage(file) { return !PKG || PKG.files.indexOf(file) > -1; }

  // ---------- Speicher (robust, falls localStorage gesperrt ist) ----------
  // Web: alles im localStorage. Moodle: Fortschritt in der Lernplattform,
  // nur die Programmwahl im localStorage (gilt so für alle Module des Kurses).
  var KEY = "lernpfad-" + K.kurzname + "-v1";
  var APPKEY = KEY + ":app";
  var state = { done: {}, checks: {}, notes: {}, selfcheck: {}, quiz: {}, test: {}, app: VAR_IDS[0] || "" };
  function applyStored(parsed) {
    if (!parsed) return;
    state.done = parsed.done || {};
    state.checks = parsed.checks || {};
    state.notes = parsed.notes || {};
    state.selfcheck = parsed.selfcheck || {};
    state.quiz = parsed.quiz || {};
    state.test = parsed.test || {};
    if (parsed.app) state.app = parsed.app;
  }
  try {
    if (SC) {
      applyStored(SC.load());
      state.app = localStorage.getItem(APPKEY) || state.app;
    } else {
      var raw = localStorage.getItem(KEY);
      if (raw) applyStored(JSON.parse(raw));
    }
  } catch (e) { /* ohne Speicher weiterarbeiten */ }
  function save() {
    if (SC) {
      SC.save({ done: state.done, checks: state.checks, notes: state.notes, quiz: state.quiz, test: state.test });
      try { localStorage.setItem(APPKEY, state.app); } catch (e) { /* ignorieren */ }
      return;
    }
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* ignorieren */ }
  }
  LP.state = state;
  LP.save = save;

  function el(tag, attrs, html) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (html != null) n.innerHTML = html;
    return n;
  }
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  // ---------- App-Umschalter ----------
  function setApp(app) {
    state.app = app;
    document.documentElement.setAttribute("data-app", app);
    var btns = document.querySelectorAll(".app-switch button");
    for (var i = 0; i < btns.length; i++) btns[i].setAttribute("aria-pressed", btns[i].dataset.app === app ? "true" : "false");
    save();
  }
  document.documentElement.setAttribute("data-app", state.app);

  function buildTopbar() {
    var bar = document.getElementById("topbar");
    if (!bar) return;
    bar.className = "topbar";
    bar.innerHTML =
      '<button class="menu-btn" type="button" aria-label="Navigation öffnen">☰</button>' +
      '<a class="brand" href="' + (PKG ? PKG.launch : "index.html") + '"><span class="logo">' + esc(K.logoZeichen || "▶") + "</span><span>" + esc(K.titel) + "</span></a>" +
      '<span class="spacer"></span>' +
      (VAR ? '<span class="app-switch-label">' + esc(VAR.frage || "Ich arbeite mit:") + "</span>" +
        '<div class="app-switch" role="group" aria-label="' + esc(VAR.frage || "Variante wählen") + '">' +
        VAR_IDS.map(function (v) { return '<button type="button" data-app="' + esc(v) + '">' + esc(APPNAME[v]) + "</button>"; }).join("") +
        (VAR.beide ? '<button type="button" data-app="both" title="Alle Anleitungen nebeneinander">beide</button>' : "") +
        "</div>" : "");
    // Im Moodle-Paket: Umschalter für den Kompaktmodus (Moodle-Kopf aus-/einblenden)
    if (NAV && NAV.inMoodle && NAV.inMoodle()) {
      var kb = el("button", { "class": "kompakt-btn", type: "button" });
      var paintK = function (on) {
        kb.textContent = on ? "⤡" : "⤢";
        kb.title = on ? "Moodle-Kopfzeile wieder einblenden" : "Mehr Platz: Moodle-Kopfzeile ausblenden";
        kb.setAttribute("aria-label", kb.title);
        kb.setAttribute("aria-pressed", on ? "true" : "false");
      };
      var kOn = NAV.compactWanted();
      if (kOn) NAV.compact(true);
      paintK(kOn);
      kb.addEventListener("click", function () {
        kOn = !kOn;
        NAV.compact(kOn);
        paintK(kOn);
        try { localStorage.setItem("lp-kompakt", kOn ? "1" : "0"); } catch (e) { /* ignorieren */ }
      });
      bar.insertBefore(kb, bar.querySelector(".spacer"));
    }
    bar.querySelector(".menu-btn").addEventListener("click", function () {
      document.body.classList.toggle("nav-open");
    });
    // Höhe der Kopfzeile messen (bricht am Handy um), damit die Navigation direkt darunter beginnt
    function measure() { document.documentElement.style.setProperty("--topbar-h", bar.offsetHeight + "px"); }
    measure();
    window.addEventListener("resize", measure);
    var btns = bar.querySelectorAll(".app-switch button");
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener("click", function () { setApp(this.dataset.app); });
    }
    if (VAR) setApp(state.app);
  }

  // ---------- Navigation ----------
  function currentFile() {
    var f = location.pathname.split("/").pop();
    return f || "index.html";
  }

  function buildSidebar() {
    var nav = document.getElementById("sidebar");
    if (!nav) return;
    if (PKG) { renderPackageSidebar(nav); return; }
    var cur = currentFile();
    var html = PKG
      ? A('<p class="pkg-hint">Die anderen Module findest du im Moodle-Kurs.</p>')
      : '<a href="index.html" class="btn secondary" style="display:block;text-align:center">Übersicht</a>';
    Object.keys(LEVELS).forEach(function (lv) {
      var mods = MODULES.filter(function (m) { return m.level === lv && inPackage(m.file); });
      if (!mods.length) return;
      var total = mods.reduce(function (s, m) { return s + m.min; }, 0);
      html += '<h4><span class="dot" style="background:' + LEVELS[lv].color + '"></span>' +
        LEVELS[lv].name + (PKG || !total ? "" : ' <span style="font-weight:400;text-transform:none;letter-spacing:0">· ca. ' + (total >= 45 ? Math.round(total / 45) + " Std." : total + " min") + "</span>") + "</h4><ul>";
      mods.forEach(function (m) {
        html += '<li><a href="' + m.file + '"' + (m.file === cur ? ' class="current" aria-current="page"' : "") + ">" +
          '<span class="tick">' + (state.done[m.id] ? "✓" : modZu(m) ? "🔒" : "") + "</span>" +
          "<span>" + (m.milestone ? "★ " : m.id.toUpperCase() + " · ") + esc(m.title) + "</span></a></li>";
      });
      html += "</ul>";
    });
    html += '<div class="extra"><ul>';
    EXTRA.forEach(function (x) {
      if (!inPackage(x.file)) return;
      html += '<li><a href="' + x.file + '"' + (x.file === cur ? ' class="current"' : "") + '><span class="tick"></span><span>' + esc(x.title) + "</span></a></li>";
    });
    html += "</ul></div>";
    nav.innerHTML = html;
  }

  function moduleById(id) {
    for (var i = 0; i < MODULES.length; i++) if (MODULES[i].id === id) return i;
    return -1;
  }

  function buildModuleHead(mod) {
    var main = document.querySelector("main");
    var head = el("div", { "class": "mod-head" });
    head.innerHTML =
      '<div class="badges"><span class="badge lv-' + mod.level + '">' + LEVELS[mod.level].name + "</span>" +
      '<span class="badge">' + (mod.milestone ? "Meilenstein" : "Modul " + mod.id.toUpperCase()) + "</span>" +
      '<span class="badge">⏱ ca. ' + mod.min + " Minuten</span></div>" +
      "<h1>" + esc(mod.title) + "</h1>";
    main.insertBefore(head, main.firstChild);
    document.title = mod.title + " – " + K.titel;
  }

  function buildFooter(mod) {
    var main = document.querySelector("main");
    var idx = moduleById(mod.id);

    // Notizfeld: Was nehme ich mit?
    var noteBox = el("div", { "class": "box note-box" });
    noteBox.innerHTML = '<label class="box-title" for="note-' + mod.id + A('">💬 Deine Notiz</label>') +
      '<p style="margin:.2rem 0 .5rem;color:var(--muted);font-size:.92rem">' + (K.notizfrage ? esc(K.notizfrage) :
        A("Was nimmst du aus diesem Modul mit? Was war schwierig? Wo wirst du das brauchen – in der Schule, in der Ausbildung, in der Praxis?")) + "</p>";
    var ta = el("textarea", { id: "note-" + mod.id, rows: "3", placeholder: "Zum Beispiel: Ich wusste nicht, dass …" });
    ta.value = state.notes[mod.id] || "";
    ta.addEventListener("input", function () { state.notes[mod.id] = ta.value; save(); });
    noteBox.appendChild(ta);
    main.appendChild(noteBox);

    var wrap = el("div", { "class": "done-wrap" });
    var btn = el("button", { "class": "btn", type: "button" });
    function paint() {
      if (state.done[mod.id]) { btn.textContent = "✓ Erledigt – nochmal öffnen?"; btn.classList.add("is-done"); }
      else { btn.textContent = "Modul als erledigt markieren"; btn.classList.remove("is-done"); }
    }
    btn.addEventListener("click", function () {
      state.done[mod.id] = !state.done[mod.id];
      save(); paint(); buildSidebar(); buildSchluessel(mod.id);
      if (SC) {
        SC.setDone(!!state.done[mod.id], state.done[mod.id] ? 1 : checkProgress());
        // Moodle wertet den Abschluss beim Speichern aus – danach die Navigation neu holen (Sperren fallen weg)
        SC.flushNow();
        setTimeout(function () { loadCourseNav(); if (NAV.refreshMoodle) NAV.refreshMoodle(); }, 1500);
      }
    });
    paint();
    wrap.appendChild(btn);
    wrap.appendChild(el("span", { style: "color:var(--muted);font-size:.9rem" },
      A("Markiere das Modul erst, wenn du die Basis-Aufgaben und deine Checkliste geschafft hast.") +
      (SC ? A(" Dein Stand wird in Moodle gespeichert.") : "")));
    main.appendChild(wrap);

    if (PKG) {
      main.appendChild(el("div", { "class": "pager", id: "pkg-pager" }));
      renderPackagePager();
      return;
    }
    var pager = el("div", { "class": "pager" });
    var prev = MODULES[idx - 1], next = MODULES[idx + 1];
    pager.innerHTML =
      (prev ? '<a class="prev" href="' + prev.file + '"><small>← zurück</small>' + esc(prev.title) + "</a>" : '<a class="prev" href="index.html"><small>← zurück</small>Übersicht</a>') +
      (next ? '<a class="next" href="' + next.file + '"><small>weiter →</small>' + esc(next.title) + "</a>" : '<a class="next" href="index.html"><small>weiter →</small>Übersicht</a>');
    main.appendChild(pager);
  }

  // ---------- Menüpfade: "Einfügen › Bilder" ----------
  function buildPaths() {
    var paths = document.querySelectorAll(".path");
    for (var i = 0; i < paths.length; i++) {
      var p = paths[i];
      if (p.dataset.done) continue;
      var parts = p.textContent.split("›").map(function (s) { return s.trim(); });
      p.innerHTML = parts.map(function (s) { return '<span class="seg">' + esc(s) + "</span>"; }).join('<span class="sep">›</span>');
      p.dataset.done = "1";
    }
  }

  // ---------- Menüband-Schema ----------
  // <figure class="rb" data-app="<variante>" data-tab="Einfügen"
  //   data-groups="Bilder: *1 Bilder | Illustrationen: Formen, SmartArt"
  //   data-menu="Bilder einfügen aus|*2 Dieses Gerät …|Stockbilder …"
  //   data-caption="..."></figure>
  function parseItem(s) {
    var m = /^\*(\d)?\s*(.*)$/.exec(s.trim());
    if (m) return { on: true, num: m[1] || "", text: m[2] };
    return { on: false, num: "", text: s.trim() };
  }
  function buildRibbons() {
    var figs = document.querySelectorAll("figure.rb");
    for (var i = 0; i < figs.length; i++) {
      var f = figs[i], app = f.dataset.app || VAR_IDS[0], tab = f.dataset.tab || "";
      f.classList.add(app);
      var tabs = (TABS[app] || []).slice();
      var ctx = tabs.indexOf(tab) === -1 && tab;
      if (ctx) tabs.push(tab);
      var html = '<div class="ribbon ' + app + '" role="img" aria-label="Schema: ' + esc(APPNAME[app]) + ", Registerkarte " + esc(tab) + '">' +
        '<div class="rb-title">' + esc(APPNAME[app]) + (ctx ? " · Kontext-Registerkarte erscheint erst, wenn ein passendes Objekt markiert ist" : "") + "</div>" +
        '<div class="rb-tabs">' + tabs.map(function (t) {
          return '<span class="rb-tab' + (t === tab ? " on" : "") + '">' + esc(t) + "</span>";
        }).join("") + "</div>";
      if (f.dataset.groups) {
        html += '<div class="rb-body">';
        f.dataset.groups.split("|").forEach(function (g) {
          var idx = g.indexOf(":");
          var label = idx > -1 ? g.slice(0, idx).trim() : "";
          var items = (idx > -1 ? g.slice(idx + 1) : g).split(",");
          html += '<div class="rb-group"><div class="rb-btns">' + items.map(function (s) {
            var it = parseItem(s);
            return '<span class="rb-btn' + (it.on ? " on" : "") + '">' + esc(it.text) + (it.num ? '<span class="num">' + it.num + "</span>" : "") + "</span>";
          }).join("") + "</div>" + (label ? '<div class="rb-glabel">' + esc(label) + "</div>" : "") + "</div>";
        });
        html += "</div>";
      }
      if (f.dataset.menu) {
        var mi = f.dataset.menu.split("|");
        html += '<div class="rb-menu"><div class="rb-mhead">' + esc(mi.shift()) + "</div>" + mi.map(function (s) {
          var it = parseItem(s);
          return '<div class="it' + (it.on ? " on" : "") + '">' + (it.num ? "<b>" + it.num + ".</b> " : "") + esc(it.text) + "</div>";
        }).join("") + "</div>";
      }
      html += "</div>";
      if (f.dataset.caption) html += "<figcaption>Schema: " + esc(f.dataset.caption) + "</figcaption>";
      f.innerHTML = html;
    }

    // Seitenleiste / Aufgabenbereich:
    // <figure class="sp" data-app="<variante>" data-title="Folien-Einstellungen" data-rows="#Hintergrund|*Farbfüllung|Muster">
    var sps = document.querySelectorAll("figure.sp");
    for (var j = 0; j < sps.length; j++) {
      var s = sps[j], a = s.dataset.app || VAR_IDS[0];
      s.classList.add(a);
      var h = '<div class="sidepanel ' + a + '" role="img" aria-label="Schema: ' + esc(s.dataset.title || "") + '"><div class="sp-head">' + esc(s.dataset.title || "") + "</div>";
      (s.dataset.rows || "").split("|").forEach(function (r) {
        r = r.trim();
        if (r.charAt(0) === "#") h += '<div class="sp-row h">' + esc(r.slice(1)) + "</div>";
        else { var it = parseItem(r); h += '<div class="sp-row' + (it.on ? " on" : "") + '">' + (it.num ? "<b>" + it.num + ".</b> " : "") + esc(it.text) + "</div>"; }
      });
      h += "</div>";
      if (s.dataset.caption) h += "<figcaption>Schema: " + esc(s.dataset.caption) + "</figcaption>";
      s.innerHTML = h;
    }
  }

  // ---------- Screenshots ----------
  // <figure class="shot" data-src="material/screens/bild.png" data-desc="..."></figure>
  // Solange die Datei fehlt, erscheint ein Platzhalter mit Dateiname und Beschreibung.
  function buildShots() {
    var shots = document.querySelectorAll("figure.shot");
    for (var i = 0; i < shots.length; i++) {
      (function (f) {
        var src = f.dataset.src, desc = f.dataset.desc || "";
        var img = new Image();
        img.alt = desc;
        img.onload = function () {
          f.innerHTML = "";
          var a = el("a", { href: src, target: "_blank", rel: "noopener", title: "Klicken zum Vergrößern" });
          a.appendChild(img);
          f.appendChild(a);
          f.appendChild(el("figcaption", null, esc(desc)));
        };
        img.onerror = function () {
          f.innerHTML = '<div class="placeholder">📷 <strong>Screenshot folgt:</strong> ' + esc(desc) +
            '<br><code>' + esc(src) + "</code></div>";
        };
        img.src = src;
      })(shots[i]);
    }
  }

  // ---------- Videos & Hilfeseiten ----------
  // <div class="media" data-ids="ms-bilder, oo-hilfe-bilder"></div>
  function mediaItem(id, m) {
    var ico = m.type === "video" ? "▶" : "?";
    var meta = [m.source, m.lang === "en" ? "englisch" : "deutsch"];
    if (m.duration) meta.push(m.duration);
    if (m.type === "hilfe") meta.push("Hilfeseite");
    if (m.type === "kurs") meta.push("Kurzkurs mit Videos");
    return '<a class="media-item ' + (m.app || "") + '" href="' + esc(m.url) + '" target="_blank" rel="noopener">' +
      '<span class="ico">' + ico + "</span><span><span class=\"t\">" + esc(m.title) + "</span><br>" +
      '<span class="meta">' + (m.app && APPNAME[m.app] ? esc(APPNAME[m.app]) + " · " : "") + esc(meta.join(" · ")) + "</span>" +
      (m.hint ? '<br><span class="meta">👉 ' + esc(m.hint) + "</span>" : "") + "</span></a>";
  }
  LP.mediaItem = mediaItem;
  function buildMedia() {
    var boxes = document.querySelectorAll("div.media[data-ids]");
    var reg = window.MEDIA || {};
    var cfg = window.MEDIA_CONFIG || {};
    for (var i = 0; i < boxes.length; i++) {
      var b = boxes[i], html = "";
      b.dataset.ids.split(",").forEach(function (id) {
        id = id.trim();
        var m = reg[id];
        if (!m) return;
        if (cfg.nurFreigegebene && !m.freigegeben) return;
        html += '<div class="' + (m.app || "") + '">' + mediaItem(id, m) + "</div>";
      });
      b.innerHTML = html || '<p class="meta" style="color:var(--muted)">Hier folgen geprüfte Videos.</p>';
    }
  }

  // ---------- Checklisten ----------
  function buildChecks(pageKey) {
    var lists = document.querySelectorAll("ul.check, .checkliste > ul");
    var n = 0;
    for (var i = 0; i < lists.length; i++) {
      var lis = lists[i].children;
      for (var j = 0; j < lis.length; j++) {
        (function (li, id) {
          if (li.querySelector("input")) return;
          var key = pageKey + ":" + id;
          var cb = el("input", { type: "checkbox", id: "c-" + id });
          var lab = el("label", { "for": "c-" + id }, li.innerHTML);
          li.innerHTML = "";
          li.appendChild(cb); li.appendChild(lab);
          cb.checked = !!state.checks[key];
          li.classList.toggle("done", cb.checked);
          cb.addEventListener("change", function () {
            state.checks[key] = cb.checked;
            li.classList.toggle("done", cb.checked);
            save();
          });
        })(lis[j], n++);
      }
    }
  }

  // ---------- Kurz-Check (Quiz) ----------
  // <div class="qa" data-right="2"><p class="q">…</p><ol><li>…</li></ol><p class="fb" data-ok="…" data-no="…"></p></div>
  // Erster Versuch je Frage zählt (für Moodle: Antworten und Punkte)
  function quizScore(pageKey, total) {
    var raw = 0;
    for (var i = 0; i < total; i++) if (state.quiz[pageKey + ":q" + i] === true) raw++;
    return raw;
  }
  function buildQuiz(pageKey) {
    var qas = document.querySelectorAll(".qa");
    var letters = "abcdefghij";
    for (var i = 0; i < qas.length; i++) {
      (function (qa, qi) {
        var right = parseInt(qa.dataset.right, 10) - 1;
        var qkey = pageKey + ":q" + qi;
        var qtext = (qa.querySelector(".q") || qa).textContent.trim();
        var fb = qa.querySelector(".fb");
        var lis = qa.querySelectorAll("ol > li");
        for (var j = 0; j < lis.length; j++) {
          (function (li, idx) {
            var b = el("button", { type: "button" }, li.innerHTML);
            li.innerHTML = ""; li.appendChild(b);
            b.addEventListener("click", function () {
              var all = qa.querySelectorAll("button");
              for (var k = 0; k < all.length; k++) all[k].classList.remove("right", "wrong");
              if (state.quiz[qkey] == null) {
                state.quiz[qkey] = idx === right;
                save();
                if (SC) {
                  SC.answer(pageKey + "-frage-" + (qi + 1), qtext, letters.charAt(idx), letters.charAt(right), idx === right);
                  // nur Fragen zählen, die für die gewählte Variante sichtbar sind
                  var sichtbar = [], roh = 0;
                  for (var v = 0; v < qas.length; v++) if (qas[v].offsetParent !== null) sichtbar.push(v);
                  sichtbar.forEach(function (v) { if (state.quiz[pageKey + ":q" + v] === true) roh++; });
                  SC.score(roh, sichtbar.length || qas.length);
                }
              }
              if (idx === right) {
                b.classList.add("right");
                fb.innerHTML = "✅ " + (fb.dataset.ok || "Richtig!");
              } else {
                b.classList.add("wrong");
                fb.innerHTML = "❌ " + (fb.dataset.no || A("Noch nicht – versuch es nochmal."));
              }
            });
          })(lis[j], j);
        }
      })(qas[i], i);
    }
  }

  function checkProgress() {
    var all = document.querySelectorAll("ul.check input[type=checkbox]");
    if (!all.length) return 0;
    var n = 0;
    for (var i = 0; i < all.length; i++) if (all[i].checked) n++;
    return n / all.length;
  }

  // ---------- Moodle-Paket: Navigation durch den ganzen Moodle-Kurs ----------
  // scorm.js holt den Kursaufbau aus Moodle (Abschnitte, Unterabschnitte, Aktivitäten, Häkchen, Sperren).
  // Die Seitenleiste zeigt den Kurs, unten gibt es Zurück/Weiter zur vorigen/nächsten Moodle-Aktivität –
  // auch zu Aufgaben (Upload), H5P und Tests. Ohne Moodle-Daten: nur „Zurück zum Kurs“.
  var NAV = PKG && window.LP_SCORM ? window.LP_SCORM : null;
  var navData = null;
  var ICON = { scorm: "📦", assign: "📤", h5pactivity: "🧩", quiz: "❓", page: "📄", book: "📘", url: "🔗",
    resource: "📎", forum: "💬", lesson: "🧭", glossary: "📚", feedback: "📝", choice: "✅" };

  function loadCourseNav() {
    if (!NAV) return;
    NAV.courseNav(function (data) {
      navData = data;
      trackingHint();
      buildSidebar();
      renderPackagePager();
      renderStart();
    });
  }
  // Reihenfolge aller Aktivitäten; gesperrte Unterabschnitte/Abschnitte als Platzhalter (Inhalt kennt Moodle erst nach Freigabe)
  // Hinweis, wenn Moodle den Abschluss dieses Moduls nicht anzeigt (sonst sucht man den Fehler an der falschen Stelle)
  function trackingHint() {
    var wrap = document.querySelector(".done-wrap");
    var t = navData && navData.tracking;
    if (!wrap || !t || wrap.querySelector(".pkg-tracking")) return;
    var msg = !t.tracked
      ? A("Hinweis für Lehrkräfte: Du bist hier nicht als Teilnehmer:in eingeschrieben. Moodle zeigt dir deshalb keinen Aktivitätsabschluss an ") +
        "(keine Häkchen, keine Freischaltungen). Zum Testen am besten ein Schüler-Testkonto verwenden."
      : !t.enabled
        ? "Hinweis: Moodle speichert hier keinen Aktivitätsabschluss. Bitte im Kurs die <strong>Abschlussverfolgung</strong> einschalten " +
          A("und beim Lernpaket <strong>„Status erforderlich: Abgeschlossen“</strong> einstellen. Dein Stand im Lernpaket wird trotzdem gespeichert.")
        : "";
    if (msg) wrap.appendChild(el("p", { "class": "pkg-tracking box warn", style: "flex-basis:100%;margin:.6rem 0 0" }, msg));
  }
  function flatNav() {
    var out = [];
    function walk(list) {
      list.forEach(function (it) {
        if (it.kind !== "sub") out.push(it);
        else if (it.locked) out.push({ kind: "cm", name: it.title, locked: true });
        else walk(it.items);
      });
    }
    (navData && navData.sections || []).forEach(function (sec) {
      if (sec.locked) out.push({ kind: "cm", name: sec.title, locked: true });
      else walk(sec.items);
    });
    return out;
  }
  function navDone(it) {
    var mid = document.body.dataset.module;
    return it.done || (it.current && mid && state.done[mid]);
  }
  function navItem(it) {
    if (it.kind === "sub") {
      if (it.locked) return '<li class="nav-sub locked"><span>🔒 ' + esc(it.title) + "</span></li>";
      return '<li class="nav-sub"><span class="nav-sub-title">' + esc(it.title) + "</span><ul>" + it.items.map(navItem).join("") + "</ul></li>";
    }
    var ico = ICON[it.module] || "•";
    var label = '<span class="tick">' + (navDone(it) ? "✓" : "") + '</span><span><span class="nav-ico" aria-hidden="true">' + ico + "</span> " + esc(it.name) + "</span>";
    if (it.current) return '<li><a class="current" aria-current="page" href="#">' + label + "</a></li>";
    if (it.locked || !it.url) return '<li><span class="nav-locked" title="Noch gesperrt">' + label.replace('<span class="tick"></span>', '<span class="tick">🔒</span>') + "</span></li>";
    return '<li><a href="' + esc(it.url) + '" data-go="1" title="' + esc(it.modname || "") + '">' + label + "</a></li>";
  }
  function renderPackageSidebar(nav) {
    var html = "";
    if (navData && navData.courseUrl) {
      html += '<a href="' + esc(navData.courseUrl) + '" data-go="1" class="btn secondary" style="display:block;text-align:center">← Zum Kurs</a>';
    } else {
      html += A('<p class="pkg-hint">Die anderen Module findest du im Moodle-Kurs.</p>');
    }
    if (navData && navData.sections) {
      navData.sections.forEach(function (sec) {
        html += "<h4>" + (sec.locked ? "🔒 " : "") + esc(sec.title) + '</h4><ul class="course-nav">' + sec.items.map(navItem).join("") + "</ul>";
      });
    } else {
      var mod = MODULES[moduleById(document.body.dataset.module)];
      if (mod) html += '<ul><li><a class="current" aria-current="page" href="#"><span class="tick">' + (state.done[mod.id] ? "✓" : "") + "</span><span>" + esc(mod.title) + "</span></a></li></ul>";
    }
    html += '<div class="extra"><ul>';
    EXTRA.forEach(function (x) {
      if (!inPackage(x.file)) return;
      html += '<li><a href="' + x.file + '" target="_blank" rel="noopener"><span class="tick"></span><span>' + esc(x.title) + " ↗</span></a></li>";
    });
    nav.innerHTML = html + "</ul></div>";
  }
  function pagerLink(it, cls, label) {
    if (it.locked || !it.url) {
      var mid = document.body.dataset.module;
      return '<span class="' + cls + ' pkg-locked"><small>' + label + "</small>🔒 " + esc(it.name) +
        "<small>" + (mid && !state.done[mid] ? A("Wird frei, wenn du dieses Modul als erledigt markierst.") : A("Noch gesperrt – schau im Kurs, was noch fehlt.")) + "</small></span>";
    }
    return '<a class="' + cls + '" href="' + esc(it.url) + '" data-go="1"><small>' + label + "</small>" + (ICON[it.module] || "") + " " + esc(it.name) + "</a>";
  }
  function renderPackagePager() {
    var pager = document.getElementById("pkg-pager");
    if (!pager) return;
    var list = flatNav(), i = -1;
    for (var k = 0; k < list.length; k++) if (list[k].current) i = k;
    if (i < 0) {
      pager.innerHTML = navData && navData.courseUrl
        ? '<a class="next" href="' + esc(navData.courseUrl) + '" data-go="1"><small>weiter →</small>Zurück zum Moodle-Kurs</a>'
        : A('<div class="box tip" style="flex:1"><div class="box-title">➡️ Wie geht’s weiter?</div><p>Geh zurück zum Moodle-Kurs. Dort findest du das nächste Modul.</p></div>');
    } else {
      var prev = null, next = list[i + 1] || null;
      for (var j = i - 1; j >= 0 && !prev; j--) if (list[j].url) prev = list[j];
      pager.innerHTML = (prev ? pagerLink(prev, "prev", "← zurück") : '<a class="prev" href="' + esc(navData.courseUrl) + '" data-go="1"><small>← zurück</small>Kursübersicht</a>') +
        (next ? pagerLink(next, "next", "weiter →") : '<a class="next" href="' + esc(navData.courseUrl) + '" data-go="1"><small>weiter →</small>Kursübersicht</a>');
      // Meilenstein: Knopf direkt zur nächsten Moodle-Aufgabe
      var ab = document.querySelector(".pkg-abgabe");
      for (var n = i + 1; ab && n < list.length; n++) {
        if (list[n].module === "assign") {
          ab.innerHTML = list[n].url
            ? '<a class="btn" href="' + esc(list[n].url) + '" data-go="1">📤 Zur Abgabe: ' + esc(list[n].name) + "</a>"
            : "🔒 " + esc(list[n].name) + A(" – wird frei, wenn du diese Seite als erledigt markierst.");
          break;
        }
      }
    }
  }
  // Links in die Moodle-Seite: ganzes Fenster wechseln und vorher speichern
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a[data-go]");
    if (!a || !NAV) return;
    e.preventDefault();
    NAV.go(a.getAttribute("href"));
  });

  // Im Moodle-Paket: Links auf Seiten, die nicht im Paket sind, als Text zeigen;
  // Zusatzseiten (Spickzettel, Videos) im neuen Tab öffnen, damit das Modul offen bleibt.
  function fixPackageLinks() {
    if (!PKG) return;
    var links = document.querySelectorAll("a[href]");
    for (var i = 0; i < links.length; i++) {
      var a = links[i], href = a.getAttribute("href");
      if (/^([a-z]+:|#|\/\/)/i.test(href)) continue;
      var file = href.split("#")[0].split("?")[0];
      if (!/\.html$/.test(file)) continue;
      if (!inPackage(file)) {
        var s = el("span", { "class": "pkg-link", title: A("Findest du als eigenes Modul im Moodle-Kurs") }, a.innerHTML);
        a.parentNode.replaceChild(s, a);
      } else if (file !== PKG.launch) {
        a.setAttribute("target", "_blank");
        a.setAttribute("rel", "noopener");
      }
    }
  }

  // ---------- Fortschritt auf der Startseite ----------
  function buildProgress() {
    var bars = document.querySelectorAll("[data-progress]");
    for (var i = 0; i < bars.length; i++) {
      var lv = bars[i].dataset.progress;
      var mods = MODULES.filter(function (m) { return m.level === lv; });
      var done = mods.filter(function (m) { return state.done[m.id]; }).length;
      bars[i].innerHTML = '<div class="progress"><span style="width:' + Math.round(done / mods.length * 100) + '%"></span></div>' +
        '<div class="progress-label">' + done + " von " + mods.length + " erledigt</div>";
    }
    var lists = document.querySelectorAll("[data-modlist]");
    for (var k = 0; k < lists.length; k++) {
      var l = lists[k].dataset.modlist;
      lists[k].innerHTML = MODULES.filter(function (m) { return m.level === l; }).map(function (m) {
        return '<li><a href="' + m.file + '">' + (state.done[m.id] ? "✓ " : modZu(m) ? "🔒 " : "") + esc(m.title) + "</a> <span style=\"color:var(--muted)\">(" + m.min + " min)</span></li>";
      }).join("");
      if (stufeZu(l)) codeFeld(lists[k], l);
    }
    var reset = document.getElementById("reset-progress");
    if (reset) reset.addEventListener("click", function () {
      if (confirm("Wirklich den gesamten Fortschritt (Häkchen, Notizen, erledigte Module) in diesem Browser löschen?")) {
        state.done = {}; state.checks = {}; state.notes = {}; state.selfcheck = {}; save(); location.reload();
      }
    });

    // Alle Notizen als Text kopieren (z. B. zum Abgeben)
    var copyBtn = document.getElementById("copy-notes");
    if (copyBtn) copyBtn.addEventListener("click", function () {
      var txt = MODULES.filter(function (m) { return (state.notes[m.id] || "").trim(); }).map(function (m) {
        return m.id.toUpperCase() + " – " + m.title + "\n" + state.notes[m.id].trim();
      }).join("\n\n");
      var msg = document.getElementById("copy-notes-msg");
      if (!txt) { msg.textContent = "Noch keine Notizen vorhanden."; return; }
      var done = function () { msg.textContent = A("Kopiert – du kannst die Notizen jetzt z. B. in ein Dokument einfügen."); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt).then(done, function () { fallbackCopy(txt); done(); });
      } else { fallbackCopy(txt); done(); }
    });
  }
  // Code-Feld auf der Übersicht: gesperrte Stufe direkt dort freischalten
  function codeFeld(nach, lv) {
    var f = el("form", { "class": "lp-codefeld" });
    f.innerHTML = '<label>🔒 ' + A("Gesperrt – Code eingeben:") + ' <input type="password" autocomplete="off" autocapitalize="off" spellcheck="false" required></label> ' +
      '<button class="btn secondary" type="submit">Öffnen</button><span class="lp-zugang-fehler" aria-live="polite"></span>';
    f.addEventListener("submit", function (e) {
      e.preventDefault();
      ZG.probiere(f.querySelector("input").value);
      if (ZG.stufeOffen(lv)) location.reload();
      else f.querySelector(".lp-zugang-fehler").textContent = " Der Code passt nicht.";
    });
    nach.parentNode.insertBefore(f, nach.nextSibling);
  }

  // :::schluessel – der Code für die nächste Stufe erscheint, sobald dieses Modul erledigt ist
  function buildSchluessel(id) {
    var boxen = document.querySelectorAll(".lp-schluessel");
    for (var i = 0; i < boxen.length; i++) {
      var b = boxen[i];
      if (PKG) { b.parentNode.removeChild(b); continue; }
      var extra = b.dataset.text ? "<p>" + esc(b.dataset.text) + "</p>" : "";
      b.innerHTML = state.done[id]
        ? '<div class="box-title">🔑 ' + A("Dein Code für ") + esc(b.dataset.name) + "</div>" + extra +
          '<p class="lp-code"><code>' + esc(b.dataset.code) + "</code></p>"
        : '<div class="box-title">🔒 ' + A("Code für ") + esc(b.dataset.name) + "</div>" + extra +
          "<p>" + A("Der Code erscheint, sobald du dieses Modul unten als erledigt markierst.") + "</p>";
    }
  }

  function fallbackCopy(txt) {
    var t = el("textarea"); t.value = txt; document.body.appendChild(t); t.select();
    try { document.execCommand("copy"); } catch (e) { /* ignorieren */ }
    document.body.removeChild(t);
  }

  // ---------- Abgabe-Kasten auf den Meilenstein-Seiten ----------
  // <div class="abgabe" data-option="Einsteiger: „Meilenstein: …“"></div>
  function buildAbgabe() {
    var boxes = document.querySelectorAll("div.abgabe");
    for (var i = 0; i < boxes.length; i++) {
      var option = boxes[i].dataset.option || "";
      if (PKG) {
        boxes[i].innerHTML = A('<p style="margin:0">Gib deine Dateien in der <strong>Moodle-Aufgabe</strong> ab, die im Kurs direkt unter diesem Lernpaket steht. Dort siehst du auch, worauf es ankommt, und später das Feedback deiner Lehrkraft.</p><p class="pkg-abgabe" style="margin:.6rem 0 0"></p>');
        continue;
      }
      var eigen = boxes[i].dataset.link || ""; // abgabe.link im Modulkopf: eigenes Formular nur für dieses Modul
      var link = eigen || ABGABE_LINK;
      boxes[i].innerHTML = link
        ? '<p style="margin:0 0 .5rem"><a class="btn" href="' + esc(link) + '" target="_blank" rel="noopener">Zum Abgabeformular ↗</a></p>' +
          (eigen ? "" : A('<p style="margin:0;font-size:.92rem">Melde dich mit deinem Schul-Konto an, lade deine Datei(en) hoch und wähle bei „Der abgegebene Meilenstein ist“: <strong>') + esc(option) + "</strong>.</p>")
        : A('<p style="margin:0">Den Link zum Abgabeformular bekommst du von deiner Lehrkraft.</p>');
    }
  }

  // ---------- Selbstcheck auf der Startseite ----------
  // <div id="selfcheck"> mit Radiogruppen name="q1".."q3" (Werte 0–2) und <p id="suggest">
  function buildSelfcheck() {
    var box = document.getElementById("selfcheck");
    if (!box) return;
    // K.selbstcheck = { fragen: 3, empfehlung: [{ bis: 1, stufe: "…", hinweis: "…" }, …, { stufe: "…" }] }
    var SCK = K.selbstcheck || { fragen: 0, empfehlung: [] };
    var qs = [];
    for (var qi = 1; qi <= SCK.fragen; qi++) qs.push("q" + qi);
    function evaluate() {
      var sum = 0, n = 0;
      qs.forEach(function (q) { if (state.selfcheck[q] != null) { sum += +state.selfcheck[q]; n++; } });
      if (!qs.length || n < qs.length) return;
      var emp = SCK.empfehlung.filter(function (e) { return e.bis == null || sum <= e.bis; })[0] || SCK.empfehlung[SCK.empfehlung.length - 1];
      var lv = emp.stufe;
      if (!LEVELS[lv]) return;
      if (PKG) { document.getElementById("suggest").innerHTML = pkgSuggest(lv); return; }
      var test = (K.einstufung || {})[lv];
      var hint = (test ? A("Prüf dich zuerst mit dem <a href=\"") + esc(test) + "\">🎯 Einstufungstest</a>. " : "") + (emp.hinweis || "");
      document.getElementById("suggest").innerHTML = "Mein Vorschlag: <b>" + esc(LEVELS[lv].name) + "</b> → <a href=\"" + LEVELS[lv].start + "\">zum Start</a>. " + hint +
        lehrkraftHinweis();
    }
    qs.forEach(function (q) {
      var radios = box.querySelectorAll('input[name="' + q + '"]');
      for (var i = 0; i < radios.length; i++) {
        if (state.selfcheck[q] === radios[i].value) radios[i].checked = true;
        radios[i].addEventListener("change", function () { state.selfcheck[this.name] = this.value; save(); evaluate(); });
      }
    });
    evaluate();
    selfcheckRefresh = evaluate;
  }
  var selfcheckRefresh = function () {};

  // ---------- Moodle-Startseite „Mein Lernpfad“ (start.html) ----------
  // Füllt sich mit dem Kursaufbau aus Moodle: Weitermachen, Stufen mit Fortschritt, Einstufungstests.
  function levelKey(title) {
    for (var k in LEVELS) if (title.indexOf(LEVELS[k].name) > -1) return k;
    return "";
  }
  function levelSections() {
    return (navData && navData.sections || []).filter(function (s) { return s.number > 0; });
  }
  function unitItems(it) {
    if (it.kind !== "sub") return [it];
    return it.locked ? [{ kind: "cm", name: it.title, locked: true }] : it.items;
  }
  function sectionItems(sec) {
    if (sec.locked) return [{ kind: "cm", name: sec.title, locked: true }];
    return [].concat.apply([], sec.items.map(unitItems));
  }
  function einstufungTests() {
    var s0 = (navData && navData.sections || []).filter(function (s) { return s.number === 0; })[0];
    return s0 ? s0.items.filter(function (it) { return it.kind === "cm" && /einstufung/i.test(it.name); }) : [];
  }
  function testFor(lv) {
    var name = LEVELS[lv] && LEVELS[lv].name;
    return einstufungTests().filter(function (t) { return name && t.name.indexOf(name) > -1; })[0];
  }
  function goLink(it, cls, text) {
    return it.url ? '<a class="' + (cls || "") + '" href="' + esc(it.url) + '" data-go="1">' + (text || esc(it.name)) + "</a>" : esc(it.name);
  }
  function nextItem() {
    var all = [].concat.apply([], levelSections().map(sectionItems));
    for (var i = 0; i < all.length; i++) if (!all[i].done) return all[i];
    return null;
  }
  function pkgSuggest(lv) {
    var cont = nextItem();
    var t = testFor(lv);
    var text = "Mein Vorschlag: <b>" + LEVELS[lv].name + "</b>. ";
    if (!t) {
      text += cont && cont.url ? A("Leg los: ") + goLink(cont, "", "▶ " + esc(cont.name)) + "." : A("Starte mit dem ersten Modul.");
    } else {
      text += A("Mach den ") + goLink(t, "", "🎯 Einstufungstest") + A(" – wenn du bestehst, wird ") + LEVELS[lv].name +
        A(" sofort für dich frei. Nicht bestanden? Dann arbeitest du die Module davor durch.");
    }
    return text + lehrkraftHinweis();
  }
  function renderStart() {
    var box = document.getElementById("pkg-continue");
    if (!box) return;
    if (!navData || !navData.sections) {
      box.innerHTML = '<p>Der Kurs konnte nicht geladen werden. ' + (navData && navData.courseUrl ? '<a href="' + esc(navData.courseUrl) + '" data-go="1">Zur Kursseite</a>' : "Geh zurück zur Kursseite.") + "</p>";
      return;
    }
    var n = nextItem();
    if (n && n.url) {
      box.innerHTML = '<div class="box-title">▶ Weitermachen</div><p class="continue-main">' + goLink(n, "btn big", (ICON[n.module] || "") + " " + esc(n.name)) + "</p>";
    } else if (n) {
      box.innerHTML = '<div class="box-title">🔒 Als Nächstes</div><p><strong>' + esc(n.name) + A("</strong> – wird frei, sobald du das Vorige abgeschlossen hast. Schau in der Kursübersicht, was noch fehlt.</p>");
    } else {
      box.innerHTML = A('<div class="box-title">🎉 Geschafft!</div><p>Du hast alle Module abgeschlossen. Stark!</p>');
    }
    var html = "";
    levelSections().forEach(function (sec, i) {
      var key = levelKey(sec.title);
      var units = sec.locked ? [] : sec.items;
      var done = units.filter(function (u) { return unitItems(u).every(function (x) { return x.done; }) && !u.locked; }).length;
      html += '<div class="level-card ' + key + '"><h2>' + esc(sec.title) + (sec.locked ? " 🔒" : "") + "</h2>";
      if (sec.locked) {
        var t = testFor(key);
        html += A("<p>Wird frei, sobald du den Meilenstein der vorigen Stufe abgegeben hast") + (t ? " – oder mit dem " + goLink(t, "", "🎯 Einstufungstest") : "") + ".</p>";
      } else {
        html += '<div class="progress"><span style="width:' + Math.round(done / Math.max(units.length, 1) * 100) + '%"></span></div>' +
          '<div class="progress-label">' + done + " von " + units.length + " erledigt</div><ul class=\"unit-list\">";
        units.forEach(function (u) {
          var items = unitItems(u), first = items.filter(function (x) { return x.url; })[0];
          var ok = !u.locked && items.every(function (x) { return x.done; });
          var title = u.kind === "sub" ? u.title : u.name;
          html += "<li>" + (ok ? "✓ " : u.locked || !first ? "🔒 " : "") + (first && !u.locked ? goLink(first, "", esc(title)) : '<span class="muted">' + esc(title) + "</span>") + "</li>";
        });
        html += "</ul>";
        var open = sectionItems(sec).filter(function (x) { return !x.done && x.url; })[0] || sectionItems(sec).filter(function (x) { return x.url; })[0];
        if (open) html += goLink(open, "btn", done ? "Weiter in dieser Stufe" : "Starten");
      }
      html += "</div>";
    });
    document.getElementById("pkg-levels").innerHTML = html;
    var tests = einstufungTests();
    document.getElementById("pkg-einstufung").innerHTML = tests.length
      ? A('<div class="box tip"><div class="box-title">🎯 Du kannst schon viel?</div><p>Mit einem Einstufungstest springst du direkt in eine höhere Stufe:</p><ul>') +
        tests.map(function (t) { return "<li>" + goLink(t) + "</li>"; }).join("") + "</ul></div>"
      : "";
    selfcheckRefresh();
  }

  // ---------- Einstufungstest (einstufung-*.html) ----------
  // Fragen erst am Ende auswerten; bestes Ergebnis zählt und geht als Punkte + bestanden/nicht bestanden an Moodle.
  function buildTest() {
    var form = document.getElementById("test");
    if (!form) return;
    var need = +document.body.dataset.bestehen || 80;
    var qs = form.querySelectorAll(".tq");
    for (var i = 0; i < qs.length; i++) {
      var lis = qs[i].querySelectorAll("ol > li");
      for (var j = 0; j < lis.length; j++) {
        lis[j].innerHTML = '<label><input type="radio" name="tq' + i + '" value="' + j + '"> <span>' + lis[j].innerHTML + "</span></label>";
      }
    }
    function showBest() {
      var b = document.getElementById("test-best");
      if (b && state.test.best != null) {
        b.innerHTML = '<div class="box ' + (state.test.passed ? "tip" : "note") + A('"><strong>Dein bestes Ergebnis bisher: ') + state.test.best + " %</strong> – " +
          (state.test.passed ? "bestanden ✓" : "noch nicht bestanden") + "</div>";
      }
    }
    showBest();
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var offen = 0, richtig = 0;
      for (var i = 0; i < qs.length; i++) if (!form.querySelector('input[name="tq' + i + '"]:checked')) offen++;
      var res = document.getElementById("test-result");
      if (offen) { res.innerHTML = '<div class="box warn">Noch ' + offen + (offen === 1 ? " Frage" : " Fragen") + " offen – beantworte bitte alle.</div>"; return; }
      for (var k = 0; k < qs.length; k++) {
        var q = qs[k], right = parseInt(q.dataset.right, 10) - 1;
        var pick = +form.querySelector('input[name="tq' + k + '"]:checked').value;
        var labels = q.querySelectorAll("ol > li label");
        for (var m = 0; m < labels.length; m++) {
          labels[m].classList.toggle("right", m === right);
          labels[m].classList.toggle("wrong", m === pick && pick !== right);
        }
        var fb = q.querySelector(".fb");
        if (pick === right) richtig++;
        fb.innerHTML = (pick === right ? "✅ " + (fb.dataset.ok || "Richtig.") : "❌ " + (fb.dataset.no || "Leider falsch.")) +
          ' <small class="muted">(' + esc(q.dataset.quelle || "") + ")</small>";
      }
      var pct = Math.round(richtig / qs.length * 100), passed = pct >= need;
      if (state.test.best == null || pct > state.test.best) { state.test.best = pct; state.test.raw = richtig; }
      state.test.passed = state.test.passed || passed;
      save();
      if (SC) {
        SC.score(state.test.raw, qs.length); SC.setSuccess(!!state.test.passed); SC.flushNow();
        // Moodle wertet die Freischaltung neu aus – Kursindex und eigene Navigation danach aktualisieren
        setTimeout(function () { loadCourseNav(); if (NAV && NAV.refreshMoodle) NAV.refreshMoodle(); }, 1500);
      }
      var back = PKG && navData ? (navData.sections.filter(function (s) { return s.number === 0; })[0] || { items: [] }).items.filter(function (it) { return it.module === "scorm" && !/einstufung/i.test(it.name); })[0] : null;
      res.innerHTML = '<div class="box ' + (passed ? "tip" : "warn") + '"><div class="box-title">' + (passed ? "🎉 Bestanden!" : "Noch nicht ganz") + "</div><p><strong>" +
        richtig + " von " + qs.length + " richtig (" + pct + " %)</strong> – nötig sind " + need + " %.</p><p>" +
        (passed ? "Die Stufe <strong>" + esc(document.body.dataset.stufe || "") + A("</strong> ist jetzt für dich frei.") + (back && back.url ? " " + goLink(back, "btn", "🧭 Zurück zu Mein Lernpfad") : "")
          : A("Schau dir die Fragen oben an – bei jeder steht, aus welchem Modul sie kommt. Du kannst es später noch einmal versuchen.")) +
        '</p><p><button class="btn secondary" type="button" id="test-again">Nochmal versuchen</button></p></div>';
      form.querySelector('button[type="submit"]').disabled = true;
      document.getElementById("test-again").addEventListener("click", function () {
        form.reset();
        var ls = form.querySelectorAll("label"); for (var z = 0; z < ls.length; z++) ls[z].classList.remove("right", "wrong");
        var fbs = form.querySelectorAll(".fb"); for (var y = 0; y < fbs.length; y++) fbs[y].innerHTML = "";
        form.querySelector('button[type="submit"]').disabled = false;
        res.innerHTML = ""; showBest(); form.scrollIntoView();
      });
      showBest();
      res.scrollIntoView({ behavior: "smooth" });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (document.body.dataset.page === "start" && !PKG) { location.replace("index.html"); return; }
    buildTopbar();
    buildSidebar();
    var id = document.body.dataset.module;
    var idx = id ? moduleById(id) : -1;
    if (idx > -1) { buildModuleHead(MODULES[idx]); buildFooter(MODULES[idx]); }
    buildPaths();
    buildRibbons();
    buildShots();
    buildMedia();
    buildSchluessel(id);
    buildChecks(id || currentFile());
    buildQuiz(id || currentFile());
    buildProgress();
    buildSelfcheck();
    buildAbgabe();
    buildTest();
    fixPackageLinks();
    loadCourseNav();
    if (SC) {
      var cbs = document.querySelectorAll("ul.check input[type=checkbox]");
      for (var c = 0; c < cbs.length; c++) cbs[c].addEventListener("change", function () {
        if (id) SC.setDone(!!state.done[id], state.done[id] ? 1 : checkProgress());
      });
    }
  });
})();
