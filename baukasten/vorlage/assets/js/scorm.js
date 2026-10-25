/* SCORM-Anbindung für den Lernpfad (nur im Moodle-Paket eingebunden, nicht in der Web-Version).
 *
 * Findet die SCORM-Schnittstelle der Lernplattform (SCORM 2004: API_1484_11, SCORM 1.2: API)
 * und stellt window.LP_SCORM bereit. app.js nutzt das, wenn es vorhanden und aktiv ist:
 *   load()                  gespeicherten Stand (Objekt) oder null
 *   save(state)             Stand speichern (gebündelt, dann Commit)
 *   setDone(done, progress) Modul erledigt / noch nicht erledigt, progress 0..1
 *   answer(id, text, choice, rightChoice, correct)  Kurz-Check-Antwort (nur erster Versuch)
 *   score(raw, max)         Punkte aus den Kurz-Checks (an Moodle als Prozent)
 *
 * Konfiguration kommt aus scorm-config.js (vom Build-Skript erzeugt):
 *   window.LP_SCORM_CONFIG = { module: "e3", launch: "e3-text.html", files: [...] }
 * Nur die Startseite (launch) meldet sich bei der Plattform an. Zusatzseiten (Spickzettel, Videos)
 * öffnen sich in einem neuen Tab und arbeiten ohne SCORM.
 */
(function () {
  "use strict";
  var cfg = window.LP_SCORM_CONFIG || {};
  var page = location.pathname.split("/").pop() || "";
  var api = null, v2004 = false, started = false, finished = false;
  var t0 = Date.now(), timer = null, pending = null;

  function findIn(win) {
    for (var i = 0; win && i < 10; i++) {
      try {
        if (win.API_1484_11) { v2004 = true; return win.API_1484_11; }
        if (win.API) { v2004 = false; return win.API; }
      } catch (e) { /* fremde Herkunft: weiter nach oben */ }
      if (!win.parent || win.parent === win) break;
      win = win.parent;
    }
    return null;
  }

  if (cfg.launch && page === cfg.launch) {
    api = findIn(window) || (window.opener ? findIn(window.opener) : null);
  }

  function call(fn2004, fn12, a, b) {
    try { return api[v2004 ? fn2004 : fn12](a, b); } catch (e) { return ""; }
  }
  function get(k) { return String(call("GetValue", "LMSGetValue", k)); }
  function set(k, v) { return call("SetValue", "LMSSetValue", k, String(v)); }
  function commit() { call("Commit", "LMSCommit", ""); }

  // SCORM 1.2 und 2004 benennen die Felder unterschiedlich
  var F = {
    status: function () { return v2004 ? "cmi.completion_status" : "cmi.core.lesson_status"; },
    exit: function () { return v2004 ? "cmi.exit" : "cmi.core.exit"; },
    entry: function () { return v2004 ? "cmi.entry" : "cmi.core.entry"; },
    time: function () { return v2004 ? "cmi.session_time" : "cmi.core.session_time"; },
    score: function (k) { return v2004 ? "cmi.score." + k : "cmi.core.score." + k; }
  };
  var MAXLEN = function () { return v2004 ? 64000 : 4096; };

  function sessionTime() {
    var s = Math.round((Date.now() - t0) / 1000);
    if (v2004) return "PT" + s + "S";
    var h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60, r = s % 60;
    return (h < 10 ? "000" : h < 100 ? "00" : h < 1000 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m + ":" + (r < 10 ? "0" : "") + r;
  }

  if (api) {
    var ok = call("Initialize", "LMSInitialize", "");
    started = ok === true || ok === "true";
  }

  if (started) {
    var st = get(F.status());
    if (st === "not attempted" || st === "unknown" || st === "") set(F.status(), "incomplete");
    set(F.exit(), "suspend");
    commit();
  }

  function flush() {
    if (!started || finished) return;
    if (pending != null) {
      var s = pending;
      if (s.length > MAXLEN()) {
        // Notfall: Notizen kürzen, damit wenigstens Häkchen und Status gespeichert werden
        try {
          var o = JSON.parse(s);
          o.notes = {};
          s = JSON.stringify(o);
          if (window.console) console.warn("Lernpfad: Speicher der Lernplattform voll – Notizen wurden nicht übertragen.");
        } catch (e) { /* ignorieren */ }
      }
      set("cmi.suspend_data", s);
      pending = null;
    }
    commit();
  }
  function soon() {
    clearTimeout(timer);
    timer = setTimeout(flush, 800);
  }

  function finish() {
    if (!started || finished) return;
    clearTimeout(timer);
    flush();
    set(F.time(), sessionTime());
    set(F.exit(), "suspend");
    commit();
    call("Terminate", "LMSFinish", "");
    finished = true;
  }
  window.addEventListener("pagehide", finish);
  window.addEventListener("beforeunload", finish);

  // ---------- Kursnavigation aus Moodle ----------
  // Das Paket läuft auf derselben Adresse wie Moodle und darf deshalb die Moodle-Seite drumherum fragen.
  // Es nutzt dieselbe Schnittstelle wie der Kursindex von Moodle (core_courseformat_get_state).
  // Klappt das nicht (andere Plattform, Paket außerhalb von Moodle), liefert courseNav null.
  function moodleTop() {
    try {
      var t = window.top;
      if (t !== window && t.M && t.M.cfg && t.M.cfg.courseId && typeof t.require === "function") return t;
    } catch (e) { /* fremde Herkunft */ }
    return null;
  }
  function decode(s) {
    var ta = document.createElement("textarea");
    ta.innerHTML = s || "";
    return ta.value;
  }
  // Moodle-Daten → { courseUrl, current, sections: [{ title, locked, items: [...] }] }
  // item: { kind: "cm", id, name, module, url, done, locked, current } oder { kind: "sub", title, locked, items }
  function normalize(st, M) {
    var secs = {}, cms = {};
    st.section.forEach(function (s) { secs[s.id] = s; });
    st.cm.forEach(function (c) { cms[c.id] = c; });
    var current = String(M.cfg.contextInstanceId || "");
    var tracking = null;
    function items(sec) {
      var out = [];
      (sec.cmlist || []).forEach(function (id) {
        var c = cms[id];
        if (!c) return;
        if (c.module === "subsection" || c.hasdelegatedsection) {
          // Gesperrte Unterabschnitte liefert Moodle teils ohne Verweis auf ihren Inhalt
          var sub = c.delegatesectionid ? secs[c.delegatesectionid] : null;
          out.push({ kind: "sub", title: decode(sub ? sub.title : c.name), locked: !c.uservisible, items: sub ? items(sub) : [] });
          return;
        }
        if (!c.url && c.uservisible) return; // z. B. Textfelder ohne eigene Seite
        if (String(c.id) === current) {
          // Zeigt Moodle hier einen Abschluss an? (nur für Teilnehmer:innen und nur mit Aktivitätsabschluss)
          tracking = { tracked: !!c.istrackeduser, enabled: c.completionstate != null || c.isoverallcomplete != null };
        }
        out.push({
          kind: "cm", id: String(c.id), name: decode(c.name), module: c.module, modname: c.modname,
          url: c.uservisible ? c.url : null, locked: !c.uservisible,
          // Moodle 5: isoverallcomplete; Moodle 4.x: completionstate (1 = erledigt, 2 = bestanden, teils als Text)
          done: c.isoverallcomplete != null ? !!c.isoverallcomplete : (+c.completionstate === 1 || +c.completionstate === 2),
          current: String(c.id) === current
        });
      });
      return out;
    }
    var sections = [];
    st.section.forEach(function (s) {
      if (s.component) return; // Unterabschnitte hängen an ihrer Aktivität
      var it = items(s);
      if (s.number === 0) it = it.filter(function (x) { return x.module !== "forum"; });
      if (!it.length && !s.hasrestrictions) return;
      sections.push({ number: s.number, title: decode(s.title), locked: s.hasrestrictions && !it.length, items: it });
    });
    return { courseUrl: M.cfg.wwwroot + "/course/view.php?id=" + M.cfg.courseId, current: current, sections: sections, tracking: tracking };
  }
  function courseNav(cb) {
    var t = moodleTop();
    if (!t) { cb(null); return; }
    try {
      t.require(["core/ajax"], function (ajax) {
        ajax.call([{ methodname: "core_courseformat_get_state", args: { courseid: t.M.cfg.courseId } }])[0]
          .then(function (raw) { cb(normalize(typeof raw === "string" ? JSON.parse(raw) : raw, t.M)); })
          .catch(function () { cb({ courseUrl: t.M.cfg.wwwroot + "/course/view.php?id=" + t.M.cfg.courseId, sections: null }); });
      });
    } catch (e) { cb(null); }
  }
  // Moodles Kursindex (linke Leiste) neu laden – er aktualisiert sich sonst erst beim nächsten Seitenaufruf
  function refreshMoodle() {
    var t = moodleTop();
    if (!t) return;
    try {
      t.require(["core_courseformat/courseeditor"], function (ce) {
        var ed = ce.getCurrentCourseEditor();
        if (ed && ed.dispatch) ed.dispatch("courseState");
      });
    } catch (e) { /* ältere oder andere Plattform: nichts tun */ }
  }

  // Kompaktmodus: Moodle-Kopf (Brotkrumen, Titel, „Beenden“), Fußzeile und Ränder um das Lernpaket ausblenden,
  // damit es – vor allem auf dem Handy – den ganzen Platz bekommt. Die Moodle-Menüleiste oben bleibt.
  var KOMPAKT_CSS =
    "body.path-mod-scorm #page-header, body.path-mod-scorm .activity-header, body.path-mod-scorm #page-footer," +
    "body.path-mod-scorm .drawer-toggles, body.path-mod-scorm #region-main .d-flex.flex-row-reverse.mb-2" +
    "{display:none !important}" +
    "body.path-mod-scorm #topofscroll{padding:0 !important;margin-top:0 !important}" +
    "body.path-mod-scorm #page-content{padding-bottom:0 !important}";
  function compact(on) {
    var t = moodleTop();
    if (!t) return false;
    try {
      var d = t.document, st = d.getElementById("lp-kompakt");
      if (on && !st) {
        st = d.createElement("style");
        st.id = "lp-kompakt";
        st.textContent = KOMPAKT_CSS;
        d.head.appendChild(st);
      } else if (!on && st) {
        st.parentNode.removeChild(st);
      }
      // Moodle berechnet die Höhe des Lernpakets beim Ändern der Fenstergröße neu
      t.dispatchEvent(new t.Event("resize"));
      return true;
    } catch (e) { return false; }
  }
  function compactWanted() {
    var saved = null;
    try { saved = localStorage.getItem("lp-kompakt"); } catch (e) { /* ignorieren */ }
    if (saved != null) return saved === "1";
    var t = moodleTop();
    return !!t && t.innerWidth < 900; // Standard: auf Handy und kleinem Tablet kompakt
  }

  // Ganze Moodle-Seite wechseln (nicht nur den Rahmen des Pakets); vorher alles speichern
  function go(url) {
    finish();
    var t = moodleTop() || window.top;
    try { t.location.href = url; } catch (e) { window.open(url, "_top"); }
  }

  var answered = {};
  window.LP_SCORM = {
    active: started,
    version: started ? (v2004 ? "2004" : "1.2") : "",
    config: cfg,
    courseNav: courseNav,
    refreshMoodle: refreshMoodle,
    inMoodle: function () { return !!moodleTop(); },
    compact: compact,
    compactWanted: compactWanted,
    go: go,
    flushNow: function () { clearTimeout(timer); flush(); },
    load: function () {
      if (!started) return null;
      var raw = get("cmi.suspend_data");
      if (!raw) return null;
      try { return JSON.parse(raw); } catch (e) { return null; }
    },
    save: function (state) {
      if (!started) return;
      pending = JSON.stringify(state);
      soon();
    },
    // Einstufungstest: bestanden / nicht bestanden (SCORM 1.2 kennt dafür nur lesson_status)
    setSuccess: function (passed) {
      if (!started) return;
      if (v2004) {
        set("cmi.success_status", passed ? "passed" : "failed");
        set("cmi.completion_status", "completed");
      } else {
        set("cmi.core.lesson_status", passed ? "passed" : "failed");
      }
      soon();
    },
    setDone: function (done, progress) {
      if (!started) return;
      set(F.status(), done ? "completed" : "incomplete");
      if (v2004 && typeof progress === "number") set("cmi.progress_measure", Math.max(0, Math.min(1, progress)).toFixed(2));
      soon();
    },
    answer: function (id, text, choice, rightChoice, correct) {
      if (!started || answered[id]) return;
      answered[id] = true;
      var n = parseInt(get("cmi.interactions._count"), 10) || 0;
      var p = "cmi.interactions." + n + ".";
      set(p + "id", id);
      set(p + "type", "choice");
      if (v2004) {
        set(p + "description", String(text).slice(0, 250));
        set(p + "correct_responses.0.pattern", rightChoice);
        set(p + "learner_response", choice);
        set(p + "result", correct ? "correct" : "incorrect");
      } else {
        set(p + "correct_responses.0.pattern", rightChoice);
        set(p + "student_response", choice);
        set(p + "result", correct ? "correct" : "wrong");
      }
      soon();
    },
    score: function (raw, max) {
      // In Prozent melden: Moodle übernimmt cmi.score.raw direkt in die Bewertung (max. 100)
      if (!started || !max) return;
      set(F.score("min"), 0);
      set(F.score("max"), 100);
      set(F.score("raw"), Math.round(raw / max * 100));
      if (v2004) set("cmi.score.scaled", (raw / max).toFixed(4));
      soon();
    }
  };
})();
