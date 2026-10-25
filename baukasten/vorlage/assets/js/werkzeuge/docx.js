/* Werkzeug „docx“: prüft ein Word-Dokument (.docx) direkt im Browser auf Formvorgaben.
 * Die Datei wird nur lokal gelesen (ZIP entpacken mit DecompressionStream, XML mit DOMParser) – nichts wird hochgeladen.
 *
 * Einstellungen (alle optional):
 *   pruefe: [raender, standard, silbentrennung, leerzeilen, ueberschriften, gliederung, abschnitte, seitenzahlen,
 *            deckblatt, inhaltsverzeichnis, zitate, literaturverzeichnis, beschriftungen, fussnoten, schluss, dateiname]
 *   raender: {oben: 2.5, unten: 2.5, links: 2.5, rechts: 3}     Zentimeter
 *   schrift: Arial · groesse: 12 · zeilenabstand: 1.5 · ausrichtung: blocksatz (links|blocksatz)
 *   ueberschrift: {groesse: 14, fett: true}  ·  fussnote: {groesse: 9, zeilenabstand: 1}
 *   deckblatt: [{name: Klasse, muster: "Klasse"}]               Regex, Groß-/Kleinschreibung egal
 *   zitate_min: 2 · ohne_nummer: Regex für Überschriften ohne Kapitelnummer (Literaturverzeichnis …)
 *   dateiname: {endungen: [docx], teile: 4}                     nur mit „dateiname“ in pruefe
 *   hinweis: Text über dem Ablagefeld
 */
(function () {
  "use strict";
  var W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
  var CM = 566.929; // Twips pro Zentimeter

  // ---------- ZIP lesen (nur das Nötigste: zentrales Verzeichnis, stored/deflate)
  function entpacken(buf) {
    var dv = new DataView(buf), u8 = new Uint8Array(buf), eocd = -1;
    for (var i = buf.byteLength - 22; i >= Math.max(0, buf.byteLength - 66000); i--) {
      if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
    }
    if (eocd < 0) throw new Error("keine ZIP-Datei");
    var n = dv.getUint16(eocd + 10, true), p = dv.getUint32(eocd + 16, true), dateien = {};
    var td = new TextDecoder("utf-8");
    for (var k = 0; k < n; k++) {
      if (dv.getUint32(p, true) !== 0x02014b50) break;
      var methode = dv.getUint16(p + 10, true), groesse = dv.getUint32(p + 20, true);
      var nl = dv.getUint16(p + 28, true), el = dv.getUint16(p + 30, true), cl = dv.getUint16(p + 32, true);
      var lokal = dv.getUint32(p + 42, true);
      var name = td.decode(u8.subarray(p + 46, p + 46 + nl));
      var start = lokal + 30 + dv.getUint16(lokal + 26, true) + dv.getUint16(lokal + 28, true);
      dateien[name] = { methode: methode, daten: u8.subarray(start, start + groesse) };
      p += 46 + nl + el + cl;
    }
    return dateien;
  }

  function lies(eintrag) {
    if (!eintrag) return Promise.resolve(null);
    if (eintrag.methode === 0) return Promise.resolve(new TextDecoder("utf-8").decode(eintrag.daten));
    if (eintrag.methode !== 8) return Promise.reject(new Error("unbekannte Kompression"));
    if (typeof DecompressionStream === "undefined") return Promise.reject(new Error("Browser zu alt"));
    var strom = new Blob([eintrag.daten]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
    return new Response(strom).text();
  }

  // ---------- XML-Helfer
  function xml(text) { return text ? new DOMParser().parseFromString(text, "application/xml") : null; }
  function alle(el, name) { return el ? Array.prototype.slice.call(el.getElementsByTagNameNS(W, name)) : []; }
  function kind(el, name) {
    if (!el) return null;
    for (var c = el.firstElementChild; c; c = c.nextElementSibling) if (c.localName === name && c.namespaceURI === W) return c;
    return null;
  }
  function attr(el, name) {
    if (!el) return null;
    var v = el.getAttributeNS(W, name);
    if (v == null || v === "") v = el.getAttribute("w:" + name);
    return v === "" ? null : v;
  }
  function an(el) { // Schalter wie <w:b/> oder <w:b w:val="0"/>
    if (!el) return null;
    var v = attr(el, "val");
    return !(v === "0" || v === "false" || v === "off");
  }

  // ---------- Formatvorlagen
  function Stile(stylesDoc, themeDoc) {
    var stile = {}, standardAbsatz = null;
    alle(stylesDoc, "style").forEach(function (s) {
      var id = attr(s, "styleId"), n = kind(s, "name"), b = kind(s, "basedOn");
      stile[id] = { id: id, typ: attr(s, "type"), name: n ? (attr(n, "val") || "") : id, basedOn: b ? attr(b, "val") : null,
        pPr: kind(s, "pPr"), rPr: kind(s, "rPr") };
      if (attr(s, "type") === "paragraph" && attr(s, "default") === "1") standardAbsatz = id;
    });
    var dd = alle(stylesDoc, "docDefaults")[0];
    var defR = dd ? kind(kind(dd, "rPrDefault"), "rPr") : null, defP = dd ? kind(kind(dd, "pPrDefault"), "pPr") : null;
    var themen = {};
    if (themeDoc) {
      ["majorFont", "minorFont"].forEach(function (f) {
        var el = themeDoc.getElementsByTagNameNS("http://schemas.openxmlformats.org/drawingml/2006/main", f)[0];
        var latin = el && el.getElementsByTagNameNS("http://schemas.openxmlformats.org/drawingml/2006/main", "latin")[0];
        if (latin) themen[f === "majorFont" ? "major" : "minor"] = latin.getAttribute("typeface");
      });
    }
    function kette(id) {
      var out = [], schutz = 0;
      while (id && stile[id] && schutz++ < 30) { out.push(stile[id]); id = stile[id].basedOn; }
      return out;
    }
    return {
      stile: stile, standard: standardAbsatz,
      stil: function (id) { return stile[id] || stile[standardAbsatz] || null; },
      // Wert aus der Kette: direkte Eigenschaften → Vorlage → Basisvorlagen → Dokument-Standard
      wert: function (direktP, direktR, stilId, holeP, holeR) {
        var v;
        if (direktR && holeR && (v = holeR(direktR)) != null) return v;
        if (direktP && holeP && (v = holeP(direktP)) != null) return v;
        var k = kette(stilId || standardAbsatz);
        for (var i = 0; i < k.length; i++) {
          if (holeR && k[i].rPr && (v = holeR(k[i].rPr)) != null) return v;
          if (holeP && k[i].pPr && (v = holeP(k[i].pPr)) != null) return v;
        }
        if (holeR && defR && (v = holeR(defR)) != null) return v;
        if (holeP && defP && (v = holeP(defP)) != null) return v;
        return null;
      },
      thema: function (t) { return /major/i.test(t || "") ? themen.major : themen.minor; },
      name: function (id) { var s = stile[id || standardAbsatz]; return s ? s.name : ""; },
      ebene: function (id) { // Überschriftenebene einer Vorlage (über Name oder Gliederungsebene)
        var k = kette(id);
        for (var i = 0; i < k.length; i++) {
          var m = /^(heading|überschrift)\s*(\d)$/i.exec(k[i].name);
          if (m) return +m[2];
          var ol = kind(k[i].pPr, "outlineLvl");
          if (ol && +attr(ol, "val") < 9) return +attr(ol, "val") + 1;
        }
        return 0;
      }
    };
  }

  // Eigenschafts-Leser
  function schrift(rPr, S) {
    var f = kind(rPr, "rFonts");
    if (!f) return null;
    return attr(f, "ascii") || attr(f, "hAnsi") || (attr(f, "asciiTheme") ? S.thema(attr(f, "asciiTheme")) : null);
  }
  function groesse(rPr) { var s = kind(rPr, "sz"); return s ? +attr(s, "val") / 2 : null; }
  function fett(rPr) { return an(kind(rPr, "b")); }
  function farbe(rPr) { var c = kind(rPr, "color"); return c ? (attr(c, "val") || "").toLowerCase() : null; }
  function ausrichtung(pPr) { var j = kind(pPr, "jc"); return j ? attr(j, "val") : null; }
  function zeile(pPr) {
    var s = kind(pPr, "spacing");
    if (!s || attr(s, "line") == null) return null;
    var regel = attr(s, "lineRule") || "auto";
    return regel === "auto" ? Math.round(+attr(s, "line") / 240 * 100) / 100 : "fest";
  }
  function haengend(pPr) { var i = kind(pPr, "ind"); return i && attr(i, "hanging") != null ? +attr(i, "hanging") : null; }
  function numPr(pPr) {
    var n = kind(pPr, "numPr");
    if (!n) return null;
    var id = kind(n, "numId"), lvl = kind(n, "ilvl");
    return { numId: id ? attr(id, "val") : null, ilvl: lvl ? +attr(lvl, "val") : null };
  }
  function seitenumbruchDavor(pPr) { return an(kind(pPr, "pageBreakBefore")); }

  // ---------- Dokument einlesen
  function analysiere(teile) {
    var doc = teile.doc, S = Stile(teile.styles, teile.theme);
    var body = alle(doc, "body")[0];
    var absaetze = [], abschnitte = [], felder = [], tabellen = 0;

    function sektion(sp) {
      var mar = kind(sp, "pgMar"), sz = kind(sp, "pgSz"), num = kind(sp, "pgNumType"), refs = {};
      alle(sp, "footerReference").forEach(function (r) {
        refs[attr(r, "type") || "default"] = r.getAttributeNS("http://schemas.openxmlformats.org/officeDocument/2006/relationships", "id") || r.getAttribute("r:id");
      });
      return {
        rand: mar ? { oben: +attr(mar, "top") / CM, unten: +attr(mar, "bottom") / CM, links: +attr(mar, "left") / CM, rechts: +attr(mar, "right") / CM,
          kopf: +(attr(mar, "header") || 0) / CM, fuss: +(attr(mar, "footer") || 0) / CM } : null,
        breite: sz ? +attr(sz, "w") : null, hoehe: sz ? +attr(sz, "h") : null,
        start: num && attr(num, "start") != null ? +attr(num, "start") : null,
        fuss: refs, titelseite: an(kind(sp, "titlePg"))
      };
    }

    var stapel = []; // offene Felder
    function absatz(p, ort) {
      var pPr = kind(p, "pPr"), styleEl = kind(pPr, "pStyle"), stilId = styleEl ? attr(styleEl, "val") : S.standard;
      var rec = { el: p, pPr: pPr, stil: stilId, stilName: S.name(stilId), text: "", instr: [], tabelle: ort.tabelle,
        verzeichnis: ort.verzeichnis, umbruch: false, bild: false, laeufe: [], abschnitt: abschnitte.length };
      var tocHier = false;
      alle(p, "*").forEach(function (e) {
        var n = e.localName;
        if (n === "t") rec.text += e.textContent;
        else if (n === "tab" && e.parentNode.localName === "r") rec.text += "\t";
        else if (n === "br" && attr(e, "type") === "page") rec.umbruch = true;
        else if (n === "drawing" || n === "pict") rec.bild = true;
        else if (n === "fldChar") {
          var typ = attr(e, "fldCharType");
          if (typ === "begin") stapel.push({ instr: "" });
          else if (typ === "separate" && stapel.length) { felder.push(stapel[stapel.length - 1].instr); rec.instr.push(stapel[stapel.length - 1].instr); }
          else if (typ === "end") stapel.pop();
        } else if (n === "instrText" && stapel.length) stapel[stapel.length - 1].instr += e.textContent;
        else if (n === "fldSimple") { var ins = attr(e, "instr") || ""; felder.push(ins); rec.instr.push(ins); }
        else if (n === "r" && kind(e, "t")) rec.laeufe.push(e);
        if (stapel.some(function (f) { return /^\s*TOC\b/.test(f.instr) && !/\\c\b/.test(f.instr); })) tocHier = true;
      });
      if (tocHier) rec.verzeichnis = true;
      if (/^(toc|verzeichnis|inhaltsverzeichnis)\s*\d/i.test(rec.stilName) || /^(TOC|Verzeichnis|Contents)\d/.test(stilId || "")) rec.verzeichnis = true;
      rec.ebene = S.ebene(stilId);
      var ol = kind(pPr, "outlineLvl");
      if (ol && +attr(ol, "val") < 9) rec.ebene = +attr(ol, "val") + 1;
      rec.leer = !rec.text.trim() && !rec.bild && !rec.umbruch && !rec.instr.length;
      var sp = kind(pPr, "sectPr");
      absaetze.push(rec);
      if (sp) abschnitte.push(sektion(sp));
    }
    function durch(el, ort) {
      for (var c = el.firstElementChild; c; c = c.nextElementSibling) {
        if (c.namespaceURI !== W) continue;
        if (c.localName === "p") absatz(c, ort);
        else if (c.localName === "tbl") { tabellen++; alle(c, "p").forEach(function (p) { absatz(p, { tabelle: true, verzeichnis: ort.verzeichnis }); }); }
        else if (c.localName === "sdt") {
          var gal = alle(kind(c, "sdtPr"), "docPartGallery")[0];
          var toc = gal && /Table of Contents/i.test(attr(gal, "val") || "");
          durch(kind(c, "sdtContent") || c, { tabelle: ort.tabelle, verzeichnis: ort.verzeichnis || toc });
        } else if (c.localName === "sectPr") abschnitte.push(sektion(c));
      }
    }
    durch(body, {});
    if (!abschnitte.length) abschnitte.push(sektion(null));
    return { S: S, absaetze: absaetze, abschnitte: abschnitte, felder: felder, tabellen: tabellen };
  }

  // ---------- Prüfungen
  var NAMEN = {
    dateiname: "Dateiname", raender: "Seite und Ränder", standard: "Fließtext", silbentrennung: "Silbentrennung",
    leerzeilen: "Leerzeilen & Leerzeichen", ueberschriften: "Überschriften", gliederung: "Gliederung",
    abschnitte: "Abschnitte", seitenzahlen: "Seitenzahlen", deckblatt: "Deckblatt", inhaltsverzeichnis: "Inhaltsverzeichnis",
    zitate: "Zitate & Belege", literaturverzeichnis: "Literaturverzeichnis", beschriftungen: "Abbildungen & Tabellen",
    fussnoten: "Fußnoten", schluss: "Schlussteile"
  };

  function pruefen(a, cfg, teile, dateiName, h) {
    var S = a.S, P = a.absaetze, ergebnis = {};
    var OHNE_NR = new RegExp(cfg.ohne_nummer || "^(literatur|quellen|übersicht verwendeter hilfsmittel|verwendete hilfsmittel|hilfsmittel|eigenständigkeit|selbstständigkeit|anhang|abbildungsverzeichnis|tabellenverzeichnis|abkürzungsverzeichnis|inhaltsverzeichnis)", "i");
    var kurz = function (t) { t = h.norm(t); return t.length > 45 ? t.slice(0, 42) + "…" : t; };
    var ohneNr = function (t) { return h.norm(t).replace(/^\d+(\.\d+)*\.?\s+/, ""); };

    // Überschriften (ohne Verzeichnistitel und Einträge im Verzeichnis)
    var ueber = P.filter(function (p) { return p.ebene && !p.verzeichnis && p.text.trim() && !/^inhalt(sverzeichnis)?$/i.test(ohneNr(p.text)); });
    var erste = ueber.filter(function (p) { return !OHNE_NR.test(ohneNr(p.text)); })[0] || ueber[0];
    var textAbschnitt = erste ? erste.abschnitt : 0;
    var idxErste = erste ? P.indexOf(erste) : 0;
    var vorspann = P.filter(function (p, i) { return i < idxErste; });
    var litIdx = -1;
    P.forEach(function (p, i) { if (litIdx < 0 && i >= idxErste && /^literatur(verzeichnis)?$|^quellenverzeichnis$/i.test(ohneNr(p.text))) litIdx = i; });
    var textteil = P.filter(function (p, i) { return i >= idxErste && (litIdx < 0 || i < litIdx) && !p.verzeichnis; });
    var istBeschriftung = function (p) { return p.instr.some(function (x) { return /\bSEQ\b/.test(x); }) || /caption|beschriftung/i.test(p.stilName); };
    var fliess = textteil.filter(function (p) { return !p.ebene && !p.tabelle && p.text.trim().length > 60 && !istBeschriftung(p); });

    // Effektive Werte eines Absatzes
    function wert(p, holeP, holeR, lauf) {
      return S.wert(kind(p.el, "pPr"), lauf ? kind(lauf, "rPr") : null, p.stil, holeP, holeR);
    }
    function stilWert(stilId, holeP, holeR) { return S.wert(null, null, stilId, holeP, holeR); }
    var schriftR = function (r) { return schrift(r, S); };
    function nummerierung(p) { // automatische Nummer (numPr am Absatz oder in der Vorlage); numId 0 = ausgeschaltet
      var n = numPr(kind(p.el, "pPr")) || S.wert(null, null, p.stil, function (pp) { return numPr(pp); });
      return n && n.numId && n.numId !== "0" ? n : null;
    }

    var R = {
      dateiname: function () {
        return h.dateiname(dateiName, cfg.dateiname || { endungen: ["docx"] });
      },

      raender: function () {
        var soll = cfg.raender || { oben: 2.5, unten: 2.5, links: 2.5, rechts: 3 }, out = [], falsch = [];
        a.abschnitte.forEach(function (s, i) {
          if (!s.rand) return;
          ["oben", "unten", "links", "rechts"].forEach(function (k) {
            // LibreOffice rechnet Kopf-/Fußzeile in den Rand ein: dann zählt der Abstand Seitenkante → Kopf-/Fußzeile
            var kf = k === "unten" ? s.rand.fuss : k === "oben" ? s.rand.kopf : 0;
            if (kf && s.rand[k] > soll[k] && Math.abs(kf - soll[k]) <= 0.05) return;
            if (Math.abs(s.rand[k] - soll[k]) > 0.05) falsch.push((a.abschnitte.length > 1 ? "Abschnitt " + (i + 1) + ": " : "") + k + " " + s.rand[k].toFixed(2).replace(".", ",") + " cm statt " + String(soll[k]).replace(".", ","));
          });
        });
        out.push(falsch.length ? { stufe: "bad", text: "Seitenränder weichen ab: " + falsch.join("; "), tipp: "Seitenränder neu einstellen und „Übernehmen für: Gesamtes Dokument“ wählen." }
          : { stufe: "ok", text: "Seitenränder stimmen (oben " + soll.oben + ", unten " + soll.unten + ", links " + soll.links + ", rechts " + soll.rechts + " cm)." });
        var a4 = function (s, quer) { return !s.breite || (Math.abs((quer ? s.hoehe : s.breite) - 11906) < 60 && Math.abs((quer ? s.breite : s.hoehe) - 16838) < 60); };
        var falschesFormat = a.abschnitte.filter(function (s) { return !a4(s, false) && !a4(s, true); });
        var quer = a.abschnitte.filter(function (s) { return a4(s, true) && !a4(s, false); });
        out.push(falschesFormat.length ? { stufe: "bad", text: "Das Papierformat ist nicht DIN A4 (z. B. „Letter“)." } : { stufe: "ok", text: "Papierformat DIN A4." });
        if (quer.length) out.push({ stufe: "info", text: quer.length + " Abschnitt(e) im Querformat – nur sinnvoll für eine breite Tabelle oder Abbildung." });
        return out;
      },

      standard: function () {
        var out = [], fSoll = (cfg.schrift || "Arial").toLowerCase(), gSoll = cfg.groesse || 12, zSoll = cfg.zeilenabstand || 1.5;
        var jSoll = (cfg.ausrichtung || "blocksatz") === "blocksatz" ? ["both", "distribute"] : ["left", "start"];
        if (!fliess.length) return [{ stufe: "warn", text: "Kein Fließtext gefunden (Absätze mit mehr als 60 Zeichen zwischen erster Überschrift und Literaturverzeichnis)." }];
        var fehler = { schrift: [], groesse: [], zeile: [], jc: [] }, direkt = 0;
        fliess.forEach(function (p) {
          var j = wert(p, ausrichtung) || "left", z = wert(p, zeile) || 1;
          if (jSoll.indexOf(j) < 0) fehler.jc.push(p);
          if (z !== zSoll) fehler.zeile.push(p);
          var fs = {}, gs = {};
          p.laeufe.forEach(function (r) {
            var f = (wert(p, null, schriftR, r) || "?").toLowerCase(), g = wert(p, null, groesse, r) || 10;
            fs[f] = 1; gs[g] = 1;
          });
          if (Object.keys(fs).some(function (f) { return f !== fSoll; })) fehler.schrift.push(p);
          if (Object.keys(gs).some(function (g) { return +g !== gSoll; })) fehler.groesse.push(p);
          // richtig, aber nur durch direkte Formatierung (Vorlage selbst falsch)?
          var sj = stilWert(p.stil, ausrichtung) || "left", sz = stilWert(p.stil, zeile) || 1;
          var sf = (stilWert(p.stil, null, schriftR) || "?").toLowerCase(), sg = stilWert(p.stil, null, groesse) || 10;
          if (jSoll.indexOf(sj) < 0 || sz !== zSoll || sf !== fSoll || sg !== gSoll) direkt++;
        });
        var bsp = function (l) { return l.length ? " – z. B. „" + kurz(l[0].text) + "“" : ""; };
        var zeig = function (l, ok, bad, tipp) {
          out.push(l.length ? { stufe: "bad", text: bad + " (" + l.length + " von " + fliess.length + " Absätzen)" + bsp(l), tipp: tipp } : { stufe: "ok", text: ok });
        };
        zeig(fehler.schrift, "Schriftart im Fließtext: " + (cfg.schrift || "Arial") + ".", "Andere Schriftart als " + (cfg.schrift || "Arial"), "Tipp: Absatz markieren, Strg+Leertaste setzt die Schrift auf die Vorlage zurück.");
        zeig(fehler.groesse, "Schriftgröße im Fließtext: " + gSoll + " pt.", "Andere Schriftgröße als " + gSoll + " pt");
        zeig(fehler.zeile, "Zeilenabstand " + String(zSoll).replace(".", ",") + ".", "Zeilenabstand ist nicht " + String(zSoll).replace(".", ","));
        zeig(fehler.jc, cfg.ausrichtung === "links" ? "Fließtext linksbündig." : "Fließtext im Blocksatz.", cfg.ausrichtung === "links" ? "Nicht linksbündig" : "Nicht im Blocksatz");
        if (direkt && !fehler.schrift.length && !fehler.groesse.length && !fehler.zeile.length && !fehler.jc.length)
          out.push({ stufe: "warn", text: "Sieht richtig aus – aber bei " + direkt + " Absätzen nur durch direkte Formatierung. Die Formatvorlage „" + S.name(fliess[0].stil) + "“ selbst hat andere Werte.",
            tipp: "Ändere die Formatvorlage (Rechtsklick › Ändern bzw. Formatvorlage bearbeiten). Dann reicht später ein Handgriff für alles." });
        return out;
      },

      silbentrennung: function () {
        var st = teile.settings ? alle(teile.settings, "autoHyphenation")[0] : null;
        var ein = st ? an(st) : false;
        if (!ein) { // LibreOffice: Silbentrennung hängt an der Absatzvorlage
          var aus = fliess.filter(function (p) { var v = wert(p, function (pp) { var x = kind(pp, "suppressAutoHyphens"); return x ? an(x) : null; }); return v !== false; });
          if (fliess.length && !aus.length) ein = true;
        }
        return [ein ? { stufe: "ok", text: "Automatische Silbentrennung ist eingeschaltet." }
          : { stufe: "bad", text: "Die automatische Silbentrennung ist aus.", tipp: "Word: Layout › Silbentrennung › Automatisch. LibreOffice: Absatzvorlage › Textfluss › Automatisch." }];
      },

      leerzeilen: function () {
        var out = [], kette = 0, ketten = [], leer = 0, doppelt = 0, tabs = 0;
        P.forEach(function (p, i) {
          if (p.leer && !p.tabelle) { leer++; kette++; } else { if (kette >= 3) ketten.push(i); kette = 0; }
          if (!p.verzeichnis) {
            doppelt += (p.text.replace(/\t/g, "").match(/ {2,}/g) || []).length;
            if (/^\s+\S/.test(p.text) && !p.tabelle) tabs++;
          }
        });
        if (kette >= 3) ketten.push(P.length);
        out.push(ketten.length ? { stufe: "bad", text: ketten.length + "× drei oder mehr leere Absätze hintereinander – da wurde mit Enter „geblättert“.",
          tipp: "Neue Seite: Seitenumbruch (Strg+Enter) oder Abschnittswechsel. Abstand: „Abstand vor/nach“ im Absatz." }
          : { stufe: "ok", text: "Keine Enter-Ketten zum Blättern." });
        if (leer > 6) out.push({ stufe: "warn", text: leer + " leere Absätze im Dokument.", tipp: "Abstände besser über „Abstand vor/nach“ einstellen – mit eingeschalteten Formatierungszeichen (¶) findest du sie." });
        out.push(doppelt ? { stufe: "warn", text: doppelt + "× doppelte Leerzeichen.", tipp: "Suchen und Ersetzen: zwei Leerzeichen durch eins ersetzen, bis 0 Treffer kommen." }
          : { stufe: "ok", text: "Keine doppelten Leerzeichen." });
        if (tabs) out.push({ stufe: "warn", text: tabs + " Absätze beginnen mit Leerzeichen oder Tabulator.", tipp: "Einzüge macht man über den Absatz-Dialog, nicht mit der Leertaste." });
        return out;
      },

      ueberschriften: function () {
        var out = [];
        if (!ueber.length) return [{ stufe: "bad", text: "Keine einzige Überschrift mit Formatvorlage gefunden.", tipp: "Überschriften brauchen die Formatvorlage „Überschrift 1/2/3“ – sonst bleibt das Inhaltsverzeichnis leer." }];
        var proEbene = {};
        ueber.forEach(function (p) { proEbene[p.ebene] = (proEbene[p.ebene] || 0) + 1; });
        out.push({ stufe: "ok", text: ueber.length + " Überschriften mit Formatvorlage (" + Object.keys(proEbene).sort().map(function (e) { return proEbene[e] + "× Ebene " + e; }).join(", ") + ")." });
        // unechte Überschriften im Textteil
        var unecht = textteil.filter(function (p) {
          var t = p.text.trim();
          if (p.ebene || p.tabelle || !t || t.length > 90 || /[.,;:!?"“]$/.test(t) || istBeschriftung(p)) return false;
          if (/^#{1,6}\s/.test(t)) return true;
          var dick = p.laeufe.length && p.laeufe.every(function (r) { return !r.textContent.trim() || wert(p, null, fett, r); });
          var gross = p.laeufe.some(function (r) { return (wert(p, null, groesse, r) || 0) >= 13; });
          return dick || gross;
        });
        out.push(unecht.length ? { stufe: "bad", text: unecht.length + " Zeile(n) sehen aus wie Überschriften, haben aber keine Überschriften-Vorlage: " + unecht.slice(0, 4).map(function (p) { return "„" + kurz(p.text) + "“"; }).join(", "),
          tipp: "Cursor in die Zeile, Formatvorlage „Überschrift 1/2/3“ anklicken – nicht von Hand fett machen." }
          : { stufe: "ok", text: "Keine „von Hand fett gemachten“ Überschriften gefunden." });
        var rauten = P.filter(function (p) { return /^\s*#{1,6}\s/.test(p.text); });
        if (rauten.length) out.push({ stufe: "bad", text: rauten.length + " Zeile(n) beginnen noch mit # (Rauten aus dem Rohtext).", tipp: "Rauten und das Leerzeichen dahinter löschen." });
        // Aussehen der Überschriften-Vorlagen
        var u = cfg.ueberschrift || { groesse: 14, fett: true }, abw = [];
        Object.keys(proEbene).forEach(function (e) {
          var p = ueber.filter(function (x) { return x.ebene === +e; })[0];
          var g = stilWert(p.stil, null, groesse) || 10, b = !!stilWert(p.stil, null, fett), f = stilWert(p.stil, null, schriftR) || "?";
          var c = stilWert(p.stil, null, farbe);
          var feh = [];
          if (u.groesse && g !== u.groesse) feh.push(g + " pt statt " + u.groesse);
          if (u.fett && !b) feh.push("nicht fett");
          if (cfg.schrift && f.toLowerCase() !== cfg.schrift.toLowerCase()) feh.push(f + " statt " + cfg.schrift);
          if (c && c !== "auto" && c !== "000000") feh.push("farbig (#" + c + ")");
          // direkte Formatierung auf den Überschriften
          var direkt = ueber.filter(function (x) { return x.ebene === +e; }).filter(function (x) {
            return x.laeufe.some(function (r) { var gg = wert(x, null, groesse, r); return u.groesse && gg !== u.groesse; });
          });
          if (feh.length) abw.push("Vorlage „" + S.name(p.stil) + "“: " + feh.join(", "));
          if (direkt.length) abw.push(direkt.length + "× Ebene " + e + " von Hand umformatiert");
        });
        out.push(abw.length ? { stufe: "bad", text: "Überschriften entsprechen nicht der Vorgabe (" + (u.groesse || "") + " pt" + (u.fett ? ", fett" : "") + "): " + abw.join("; "),
          tipp: "Die Vorlage ändern (Rechtsklick › Ändern), nicht die einzelne Überschrift. Farbe: Automatisch/Schwarz." }
          : { stufe: "ok", text: "Alle Überschriften-Vorlagen: " + (u.groesse ? u.groesse + " pt" : "") + (u.fett ? ", fett" : "") + ", schwarz." });
        return out;
      },

      gliederung: function () {
        var auto = 0, liste = [], out = [];
        var num = teile.numbering;
        function lvlText(numId, ilvl) {
          if (!num) return null;
          var n = alle(num, "num").filter(function (x) { return attr(x, "numId") === numId; })[0];
          if (!n) return null;
          var abs = attr(kind(n, "abstractNumId"), "val");
          var an_ = alle(num, "abstractNum").filter(function (x) { return attr(x, "abstractNumId") === abs; })[0];
          var lvl = alle(an_, "lvl").filter(function (x) { return +attr(x, "ilvl") === ilvl; })[0];
          var lt = lvl ? kind(lvl, "lvlText") : null;
          return lt ? attr(lt, "val") : null;
        }
        var zaehler = [], numFalsch = [];
        ueber.forEach(function (p) {
          var t = h.norm(p.text), nr = "", n = nummerierung(p);
          if (OHNE_NR.test(ohneNr(t))) {
            if (n || /^\d/.test(t)) numFalsch.push(ohneNr(t));
            return;
          }
          if (n) {
            auto++;
            zaehler.length = p.ebene; zaehler[p.ebene - 1] = (zaehler[p.ebene - 1] || 0) + 1;
            var muster = lvlText(n.numId, n.ilvl == null ? p.ebene - 1 : n.ilvl) || "";
            nr = muster.replace(/%(\d)/g, function (_, k) { return zaehler[k - 1] || 1; }).trim();
          } else {
            var m = /^(\d+(?:\.\d+)*\.?)\s+/.exec(t);
            if (m) nr = m[1];
          }
          liste.push({ ebene: p.ebene, nummer: nr, text: ohneNr(t) });
        });
        if (!liste.length) return [{ stufe: "warn", text: "Keine nummerierbaren Überschriften gefunden." }];
        out.push(auto ? { stufe: "ok", text: "Kapitelnummern kommen automatisch aus der Nummerierung (" + auto + " von " + liste.length + ")." }
          : { stufe: "info", text: "Kapitelnummern sind von Hand getippt.", tipp: "Geht – aber mit „Liste mit mehreren Ebenen“ nummeriert das Programm beim Umbauen von selbst neu." });
        if (auto) liste = liste.filter(function (e) { return e.nummer; }); // Ebenen ohne Nummernformat nicht bemängeln
        out = out.concat(h.gliederung(liste, cfg.gliederung));
        if (numFalsch.length) out.push({ stufe: "bad", text: "Haben eine Kapitelnummer, dürfen aber keine: " + numFalsch.join(", "), tipp: "Literaturverzeichnis, Hilfsmittel, Eigenständigkeitserklärung und Anhang bleiben ohne Nummer – z. B. Nummerierung für diese Zeile ausschalten." });
        return out;
      },

      abschnitte: function () {
        var out = [], n = a.abschnitte.length, umbr = P.filter(function (p) { return p.umbruch || wert(p, seitenumbruchDavor); }).length;
        out.push(n > 1 ? { stufe: "ok", text: "Das Dokument hat " + n + " Abschnitte." }
          : { stufe: "bad", text: "Das Dokument besteht aus nur einem Abschnitt.", tipp: "Nach dem Inhaltsverzeichnis gehört ein Abschnittsumbruch „Nächste Seite“ – sonst lassen sich die Seitenzahlen nicht trennen." });
        if (n > 1 && textAbschnitt === 0) out.push({ stufe: "bad", text: "Deckblatt/Inhaltsverzeichnis und der Text liegen im selben Abschnitt.", tipp: "Den Abschnittsumbruch direkt vor die erste Kapitelüberschrift setzen (ans Ende der Inhaltsverzeichnis-Seite)." });
        if (umbr) out.push({ stufe: "info", text: umbr + " normale Seitenumbrüche gefunden – für neue Seiten innerhalb eines Abschnitts völlig in Ordnung." });
        return out;
      },

      seitenzahlen: function () {
        var out = [], fuss = {};
        function hatSeite(rid) {
          var f = rid && teile.fuss[rid];
          if (!f) return false;
          var instr = alle(f, "instrText").map(function (e) { return e.textContent; }).join(" ") + " " +
            alle(f, "fldSimple").map(function (e) { return attr(e, "instr") || ""; }).join(" ");
          return /\bPAGE\b/.test(instr);
        }
        // geerbte Fußzeilen: ohne eigenen Verweis gilt die des vorigen Abschnitts („Mit vorheriger verknüpfen“)
        var gerbt = { "default": null, first: null };
        var eff = a.abschnitte.map(function (s) {
          ["default", "first"].forEach(function (t) { if (s.fuss[t]) gerbt[t] = s.fuss[t]; });
          return { def: hatSeite(gerbt["default"]), first: s.titelseite ? hatSeite(gerbt.first) : hatSeite(gerbt["default"]), s: s };
        });
        if (!eff.some(function (e) { return e.def || e.first; }))
          return [{ stufe: "bad", text: "Es gibt keine Seitenzahl (kein Seitenzahl-Feld in einer Fußzeile).", tipp: "Einfügen › Seitenzahl › Seitenende (Word) bzw. Einfügen › Fußzeile, dann Feld › Seitennummer (LibreOffice)." }];
        var t = eff[textAbschnitt];
        if (textAbschnitt === 0) {
          out.push({ stufe: "bad", text: "Die Seitenzahl „1“ kann so nicht auf der ersten Textseite stehen – es fehlt der Abschnittswechsel vor dem Text." });
          return out;
        }
        out.push(t.def || t.first ? { stufe: "ok", text: "Der Textteil hat Seitenzahlen." } : { stufe: "bad", text: "Ab der ersten Kapitelüberschrift fehlen die Seitenzahlen." });
        out.push(t.s.start === 1 ? { stufe: "ok", text: "Die Zählung beginnt im Textteil bei 1." }
          : { stufe: "bad", text: "Die Seitenzählung im Textteil beginnt nicht bei 1" + (t.s.start != null ? " (sondern bei " + t.s.start + ")" : " – sie läuft vom Deckblatt aus weiter") + ".",
            tipp: "Word: Seitenzahl › Seitenzahlen formatieren › Beginnen bei: 1. LibreOffice: Absatz › Textfluss › Umbrüche › Seitennummer 1." });
        // Abschnitt mit „Erste Seite anders“ und ohne Seitenumbruch darin = nur eine Seite → es zählt die Fußzeile der ersten Seite
        // (so exportiert LibreOffice Seitenvorlagen wie „Erste Seite“)
        var einseitig = function (i) {
          return !P.some(function (p, k) { return p.abschnitt === i && (p.umbruch || wert(p, seitenumbruchDavor)) && !(k > 0 && P[k - 1].abschnitt !== i); });
        };
        var vorn = eff.slice(0, textAbschnitt).filter(function (e, i) { return e.s.titelseite && einseitig(i) ? e.first : (e.def || e.first); });
        out.push(vorn.length ? { stufe: "bad", text: "Deckblatt bzw. Inhaltsverzeichnis zeigen eine Seitenzahl.",
          tipp: "Im Textteil die Fußzeile von der vorherigen lösen („Mit vorheriger verknüpfen“ aus) und dann vorne die Seitenzahl löschen." }
          : { stufe: "ok", text: "Deckblatt und Inhaltsverzeichnis sind ohne Seitenzahl." });
        return out;
      },

      deckblatt: function () {
        var text = vorspann.filter(function (p) { return !p.verzeichnis; }).map(function (p) { return p.text; }).join("\n");
        var punkte = cfg.deckblatt || [
          { name: "Name der Schule", muster: "berufsbildungszentrum|bbz|schule" },
          { name: "Adresse der Schule", muster: "\\d{5}\\s+\\S+" },
          { name: "Art der Arbeit", muster: "hausarbeit|probe|methodik|praxisbericht|bericht|ausarbeitung|übung" },
          { name: "verfassende Person(en)", muster: "eingereicht von|vorgelegt von|verfasst von|name" },
          { name: "Klasse", muster: "klasse" },
          { name: "betreuende Lehrkraft", muster: "lehrkraft|lehrer|betreu" },
          { name: "Ort, Datum", muster: "\\d{1,2}\\.\\s?(\\d{1,2}\\.|[a-zäöü]+)\\s?\\d{4}|datum" }
        ];
        if (!text.trim()) return [{ stufe: "bad", text: "Vor der ersten Kapitelüberschrift steht nichts – das Deckblatt fehlt." }];
        var fehlt = punkte.filter(function (x) { return !new RegExp(x.muster, "i").test(text); });
        var out = [fehlt.length ? { stufe: "warn", text: "Auf dem Deckblatt nicht gefunden: " + fehlt.map(function (x) { return x.name; }).join(", "), tipp: "Der Prüfer sucht nach Stichworten – schau selbst, ob es wirklich fehlt." }
          : { stufe: "ok", text: "Alle " + punkte.length + " Pflichtangaben auf dem Deckblatt gefunden." }];
        if (/\[[^\]]+\]|TT\.MM\.JJJJ|Vorname Nachname/.test(text)) out.push({ stufe: "bad", text: "Auf dem Deckblatt stehen noch Platzhalter wie [Name] oder TT.MM.JJJJ." });
        var ueberDeck = vorspann.filter(function (p) { return p.ebene && !p.verzeichnis && !/^inhalt/i.test(ohneNr(p.text)); });
        if (ueberDeck.length) out.push({ stufe: "bad", text: "Auf dem Deckblatt steht eine Überschriften-Vorlage („" + kurz(ueberDeck[0].text) + "“) – die landet im Inhaltsverzeichnis.", tipp: "Für den Titel eine andere Vorlage (z. B. „Titel“) oder normalen Text nehmen." });
        return out;
      },

      inhaltsverzeichnis: function () {
        var out = [], toc = a.felder.filter(function (f) { return /^\s*TOC\b/.test(f) && !/\\c\b/.test(f); });
        var eintraege = P.filter(function (p) { return p.verzeichnis && p.text.trim() && !/^inhalt/i.test(ohneNr(p.text)); });
        if (!toc.length && !eintraege.length) {
          var vonHand = vorspann.filter(function (p) { return /\.{4,}|\t\s*\d+\s*$/.test(p.text); });
          return [vonHand.length ? { stufe: "bad", text: "Das Inhaltsverzeichnis ist von Hand getippt.", tipp: "Löschen und automatisch einfügen: Word: Referenzen › Inhaltsverzeichnis. LibreOffice: Einfügen › Verzeichnis." }
            : { stufe: "bad", text: "Kein automatisches Inhaltsverzeichnis gefunden." }];
        }
        out.push({ stufe: "ok", text: "Automatisches Inhaltsverzeichnis vorhanden." });
        var ebenen = toc.length ? /\\o\s*"(\d)-(\d)"/.exec(toc[0]) : null;
        var maxE = Math.max.apply(null, ueber.map(function (p) { return p.ebene; }).concat([1]));
        if (ebenen && +ebenen[2] < maxE) out.push({ stufe: "warn", text: "Das Verzeichnis zeigt nur Ebene " + ebenen[1] + "–" + ebenen[2] + ", im Text gibt es Ebene " + maxE + ".", tipp: "Verzeichnis anpassen: „Ebenen anzeigen“ auf " + maxE + " stellen." });
        var vz = eintraege.map(function (p) { return ohneNr(p.text.replace(/\t.*$/, "").replace(/\s*\d+\s*$/, "")).toLowerCase(); });
        var fehlen = ueber.filter(function (p) { return vz.indexOf(ohneNr(p.text).toLowerCase()) < 0; });
        var zuviel = vz.filter(function (t) { return !ueber.some(function (p) { return ohneNr(p.text).toLowerCase() === t; }); });
        out.push(fehlen.length || zuviel.length ? { stufe: "bad", text: "Das Verzeichnis passt nicht zum Text – es wurde nicht aktualisiert." +
          (fehlen.length ? " Fehlt: " + fehlen.slice(0, 3).map(function (p) { return "„" + kurz(ohneNr(p.text)) + "“"; }).join(", ") + "." : "") +
          (zuviel.length ? " Veraltet: " + zuviel.slice(0, 3).map(function (t) { return "„" + kurz(t) + "“"; }).join(", ") + "." : ""),
          tipp: "Rechtsklick ins Verzeichnis › Felder aktualisieren › Gesamtes Verzeichnis (Word) bzw. Verzeichnis aktualisieren (LibreOffice)." }
          : { stufe: "ok", text: "Alle Überschriften stehen im Verzeichnis, nichts Veraltetes." });
        out.push({ stufe: "info", text: "Ob die Seitenzahlen im Verzeichnis stimmen, kann der Prüfer nicht sehen – vor der Abgabe immer aktualisieren!" });
        return out;
      },

      zitate: function () {
        var out = [], txt = textteil.filter(function (p) { return !p.ebene; }).map(function (p) { return h.norm(p.text); }).join("\n");
        var JAHR = "(?:1[89]\\d\\d|20\\d\\d|o\\.\\s?J\\.)[a-z]?";
        var klammer = new RegExp("\\(([^()]*?" + JAHR + "[^()]*)\\)", "g"), belege = [], m;
        while ((m = klammer.exec(txt))) if (/[A-ZÄÖÜ]/.test(m[1]) && !/^(Abb|Tab)/.test(m[1])) belege.push(m[1]);
        var erzaehlt = txt.match(new RegExp("[A-ZÄÖÜ][a-zäöüß]+(?: (?:und|&) [A-ZÄÖÜ][a-zäöüß]+| et al\\.)? \\(" + JAHR + "\\)", "g")) || [];
        var anzahl = belege.length + erzaehlt.length, min = cfg.zitate_min == null ? 2 : cfg.zitate_min;
        out.push(anzahl >= min ? { stufe: "ok", text: anzahl + " Beleg(e) im Text gefunden, z. B. (" + (belege[0] || erzaehlt[0]) + ")." }
          : { stufe: "bad", text: (anzahl ? "Nur " + anzahl : "Kein") + " Beleg im APA-Stil (Name, Jahr, S. X) gefunden – erwartet: mindestens " + min + "." });
        var vgl = (txt.match(/\b(vgl|Vgl)\./g) || []).length, ebd = (txt.match(/\b(ebd|Ebd|a\.a\.O)\./g) || []).length;
        if (vgl) out.push({ stufe: "bad", text: vgl + "× „vgl.“ – das gibt es bei APA nicht.", tipp: "Indirektes Zitat: einfach (Name, Jahr, S. X) ohne „vgl.“." });
        if (ebd) out.push({ stufe: "bad", text: ebd + "× „ebd.“ bzw. „a. a. O.“ – bei APA wird der Beleg jedes Mal wiederholt." });
        if (!vgl && !ebd) out.push({ stufe: "ok", text: "Kein „vgl.“ und kein „ebd.“." });
        var direkt = txt.match(/"[^"]{3,}"\s*\(([^()]*)\)/g) || [];
        var ohneS = direkt.filter(function (z) { return !/S\.\s?\d/.test(z.slice(z.lastIndexOf("("))); });
        if (direkt.length) out.push(ohneS.length ? { stufe: "bad", text: ohneS.length + " direkte(s) Zitat(e) ohne Seitenangabe: " + kurz(ohneS[0]), tipp: "Bei direkten Zitaten gehört die Seite dazu: (Name, Jahr, S. X)." }
          : { stufe: "ok", text: direkt.length + " direkte(s) Zitat(e) in Anführungszeichen mit Seitenangabe." });
        var fn = teile.footnotes ? alle(teile.footnotes, "footnote").filter(function (f) { return !attr(f, "type") || attr(f, "type") === "normal"; }) : [];
        var fnBeleg = fn.filter(function (f) { return new RegExp(JAHR).test(f.textContent) && /[A-ZÄÖÜ][a-zäöü]+/.test(f.textContent); });
        if (fnBeleg.length) out.push({ stufe: "warn", text: fnBeleg.length + " Fußnote(n) enthalten offenbar Quellenangaben.", tipp: "Nach APA stehen Belege im Text in Klammern – Fußnoten nur für Anmerkungen." });
        R._belege = belege.concat(erzaehlt);
        return out;
      },

      literaturverzeichnis: function () {
        var out = [];
        if (litIdx < 0) return [{ stufe: "bad", text: "Kein Literaturverzeichnis gefunden (Überschrift „Literaturverzeichnis“)." }];
        var kopf = P[litIdx];
        out.push(kopf.ebene ? { stufe: "ok", text: "Überschrift „Literaturverzeichnis“ gefunden." } : { stufe: "warn", text: "„Literaturverzeichnis“ ist keine Überschrift (Formatvorlage) – dann fehlt es im Inhaltsverzeichnis." });
        out.push(nummerierung(kopf) || /^\d/.test(kopf.text.trim()) ? { stufe: "bad", text: "Das Literaturverzeichnis hat eine Kapitelnummer.", tipp: "Ohne Nummer: Nummerierung für diese Überschrift ausschalten." }
          : { stufe: "ok", text: "Ohne Kapitelnummer." });
        var vorher = P[litIdx - 1];
        var neueSeite = wert(kopf, seitenumbruchDavor) || (vorher && (vorher.umbruch || kind(vorher.pPr, "sectPr"))) ||
          P.slice(Math.max(0, litIdx - 3), litIdx).some(function (p) { return p.leer ? false : p.umbruch; });
        out.push(neueSeite ? { stufe: "ok", text: "Beginnt auf einer neuen Seite." } : { stufe: "warn", text: "Beginnt vermutlich nicht auf einer neuen Seite.", tipp: "Davor einen Seitenumbruch setzen (Strg+Enter)." });
        var eintraege = [];
        for (var i = litIdx + 1; i < P.length && !(P[i].ebene && !P[i].verzeichnis) && !(i > litIdx + 1 && P[i - 1].pPr && kind(P[i - 1].pPr, "sectPr")); i++) if (P[i].text.trim()) eintraege.push(P[i]);
        if (!eintraege.length) return out.concat([{ stufe: "bad", text: "Das Literaturverzeichnis ist leer." }]);
        var ohneHaengend = eintraege.filter(function (p) { return !(wert(p, haengend) > 0); });
        out.push(ohneHaengend.length ? { stufe: "bad", text: ohneHaengend.length + " von " + eintraege.length + " Einträgen ohne hängenden Einzug.", tipp: "Absatz › Einzug › Sondereinzug „Hängend“, ca. 1,25 cm." }
          : { stufe: "ok", text: "Alle " + eintraege.length + " Einträge mit hängendem Einzug." });
        var namen = eintraege.map(function (p) { return h.norm(p.text); });
        var unsort = [];
        for (var k = 1; k < namen.length; k++) if (namen[k - 1].localeCompare(namen[k], "de", { sensitivity: "base" }) > 0) unsort.push("„" + kurz(namen[k]) + "“ steht nach „" + kurz(namen[k - 1]) + "“");
        out.push(unsort.length ? { stufe: "bad", text: "Nicht alphabetisch: " + unsort[0] + "." } : { stufe: "ok", text: "Alphabetisch sortiert." });
        var ohneJahr = namen.filter(function (t) { return !/\((?:1[89]\d\d|20\d\d|o\.\s?J\.)[a-z]?(?:,[^)]*)?\)/.test(t); });
        if (ohneJahr.length) out.push({ stufe: "warn", text: ohneJahr.length + " Eintrag/Einträge ohne (Jahr) direkt nach dem Namen, z. B. „" + kurz(ohneJahr[0]) + "“." });
        if (R._belege) {
          var fehlend = [];
          R._belege.forEach(function (b) {
            var nm = (/([A-ZÄÖÜ][a-zäöüß-]+)/.exec(b) || [])[1];
            if (nm && !namen.some(function (t) { return t.indexOf(nm) > -1; }) && fehlend.indexOf(nm) < 0) fehlend.push(nm);
          });
          if (fehlend.length) out.push({ stufe: "bad", text: "Im Text belegt, aber nicht im Literaturverzeichnis: " + fehlend.join(", ") + "." });
          else if (R._belege.length) out.push({ stufe: "ok", text: "Zu allen Belegen im Text gibt es einen Eintrag." });
        }
        return out;
      },

      beschriftungen: function () {
        var out = [], caps = P.filter(istBeschriftung);
        var bilder = P.filter(function (p) { return p.bild; }).length, tab = a.tabellen;
        var label = function (p) { var x = p.instr.join(" "); var m = /\bSEQ\s+"?([^\s"\\]+)/.exec(x); return m ? m[1] : (/^(\S+)/.exec(p.text.trim()) || [])[1]; };
        var abb = caps.filter(function (p) { return /^(abb|fig|illus|bild|zeichnung)/i.test(label(p) || ""); });
        var tabc = caps.filter(function (p) { return /^tab/i.test(label(p) || ""); });
        var vonHand = P.filter(function (p) { return !istBeschriftung(p) && /^(Abbildung|Abb\.|Tabelle|Tab\.)\s*\d+\s*:/.test(p.text.trim()); });
        if (!bilder && !tab && !caps.length) return [{ stufe: "info", text: "Keine Abbildungen oder Tabellen im Dokument." }];
        if (vonHand.length) out.push({ stufe: "bad", text: vonHand.length + " Beschriftung(en) von Hand getippt („" + kurz(vonHand[0].text) + "“).", tipp: "Word: Referenzen › Beschriftung einfügen. LibreOffice: Einfügen › Beschriftung. Dann zählt das Programm selbst." });
        if (bilder) out.push(abb.length >= bilder ? { stufe: "ok", text: bilder + " Abbildung(en), " + abb.length + " automatische Beschriftung(en)." }
          : { stufe: "bad", text: bilder + " Abbildung(en), aber nur " + abb.length + " automatische Abbildungs-Beschriftung(en)." });
        if (tab) out.push(tabc.length >= tab ? { stufe: "ok", text: tab + " Tabelle(n), " + tabc.length + " automatische Beschriftung(en)." }
          : { stufe: "warn", text: tab + " Tabelle(n), aber nur " + tabc.length + " automatische Tabellen-Beschriftung(en).", tipp: "Tabellen, die nur zum Layout dienen (z. B. auf dem Deckblatt), brauchen keine Beschriftung." });
        var fliesstext = P.filter(function (p) { return !istBeschriftung(p) && !p.verzeichnis; }).map(function (p) { return p.text; }).join(" ");
        var ohneVerweis = [], ohneQuelle = [];
        caps.forEach(function (p) {
          var m = /^(\S+)\s+(\d+)/.exec(h.norm(p.text)), nach = P[P.indexOf(p) + 1];
          if (m) {
            var kurzform = m[1].slice(0, 3);
            if (!new RegExp("\\b(" + m[1] + "|" + kurzform + "\\.)\\s*" + m[2] + "\\b", "i").test(fliesstext) && !p.instr.some(function (x) { return /REF/.test(x); })) ohneVerweis.push(m[1] + " " + m[2]);
          }
          var umfeld = p.text + " " + (nach ? nach.text : "");
          if (!/\(([^()]*\d{4}[^()]*|eigene Darstellung[^()]*)\)/i.test(umfeld)) ohneQuelle.push(kurz(p.text));
        });
        if (caps.length) {
          out.push(ohneVerweis.length ? { stufe: "warn", text: "Im Text wird nicht verwiesen auf: " + ohneVerweis.join(", "), tipp: "Im Fließtext z. B. „(siehe Abbildung 1)“ schreiben – am besten als Querverweis." }
            : { stufe: "ok", text: "Auf jede Abbildung/Tabelle wird im Text verwiesen." });
          out.push(ohneQuelle.length ? { stufe: "warn", text: "Ohne Quelle bzw. „(eigene Darstellung)“: " + ohneQuelle.join("; ") }
            : { stufe: "ok", text: "Jede Beschriftung nennt eine Quelle oder „eigene Darstellung“." });
        }
        return out;
      },

      fussnoten: function () {
        var fn = teile.footnotes ? alle(teile.footnotes, "footnote").filter(function (f) { return !attr(f, "type") || attr(f, "type") === "normal"; }) : [];
        if (!fn.length) return [{ stufe: "info", text: "Keine Fußnoten im Dokument – bei APA auch nicht nötig." }];
        var soll = cfg.fussnote || { groesse: 9, zeilenabstand: 1 }, id = null;
        Object.keys(S.stile).forEach(function (k) { if (/^(footnote text|fußnotentext|funotentext)$/i.test(S.stile[k].name)) id = k; });
        var out = [{ stufe: "ok", text: fn.length + " automatische Fußnote(n)." }];
        if (!id) return out.concat([{ stufe: "warn", text: "Formatvorlage für Fußnotentext nicht gefunden – Größe bitte selbst prüfen." }]);
        var g = stilWert(id, null, groesse) || 10, z = stilWert(id, zeile) || 1;
        var direkt = fn.filter(function (f) { return alle(f, "sz").some(function (s) { var p = s.parentNode; return p.parentNode.localName === "r" && !alle(p.parentNode, "footnoteRef").length && +attr(s, "val") / 2 !== soll.groesse; }); });
        out.push(g === soll.groesse && !direkt.length ? { stufe: "ok", text: "Fußnoten in " + soll.groesse + " pt." } : { stufe: "bad", text: "Fußnoten nicht in " + soll.groesse + " pt (Vorlage: " + g + " pt" + (direkt.length ? ", " + direkt.length + "× von Hand anders" : "") + ").", tipp: "Formatvorlage „Fußnotentext“ ändern." });
        out.push(z === soll.zeilenabstand ? { stufe: "ok", text: "Fußnoten einzeilig." } : { stufe: "bad", text: "Zeilenabstand der Fußnoten ist " + z + " statt " + soll.zeilenabstand + "." });
        return out;
      },

      schluss: function () {
        var out = [], texte = P.map(function (p) { return p.verzeichnis ? "" : h.norm(p.text); });
        var eig = -1, hilf = -1;
        texte.forEach(function (t, i) {
          if (eig < 0 && /^(eigenständigkeits|selbstständigkeits|selbständigkeits)erklärung/i.test(ohneNr(t))) eig = i;
          if (hilf < 0 && /^(übersicht )?(der )?verwendete(n)? hilfsmittel|^hilfsmittel/i.test(ohneNr(t))) hilf = i;
        });
        if (eig < 0) texte.forEach(function (t, i) { if (eig < 0 && /hiermit versicher/i.test(t)) eig = i; });
        out.push(eig < 0 ? { stufe: "bad", text: "Keine Eigenständigkeitserklärung gefunden.", tipp: "Sie steht ganz am Ende, auf einer eigenen Seite, mit Ort, Datum und Unterschrift." }
          : eig < litIdx ? { stufe: "warn", text: "Die Eigenständigkeitserklärung steht vor dem Literaturverzeichnis – sie gehört ans Ende." }
            : { stufe: "ok", text: "Eigenständigkeitserklärung vorhanden" + (litIdx > -1 ? ", nach dem Literaturverzeichnis." : ".") });
        if (eig > -1 && (nummerierung(P[eig]) || /^\d/.test(texte[eig]))) out.push({ stufe: "bad", text: "Die Eigenständigkeitserklärung hat eine Kapitelnummer." });
        if (eig > -1 && !/versicher/i.test(texte.slice(eig, eig + 6).join(" "))) out.push({ stufe: "warn", text: "Der Text der Erklärung fehlt oder weicht ab („Hiermit versichere ich …“ bzw. „versichern wir“)." });
        out.push(hilf < 0 ? { stufe: "info", text: "Keine „Übersicht verwendeter Hilfsmittel“ gefunden.", tipp: "Pflicht, sobald du KI-Werkzeuge o. Ä. genutzt hast – mit Werkzeug, Bezugsquelle, Funktion und Prompts." }
          : { stufe: "ok", text: "„Übersicht verwendeter Hilfsmittel“ vorhanden." });
        return out;
      }
    };

    var reihen = cfg.pruefe || ["raender", "standard", "silbentrennung", "leerzeilen", "ueberschriften", "gliederung", "abschnitte",
      "seitenzahlen", "deckblatt", "inhaltsverzeichnis", "zitate", "literaturverzeichnis", "beschriftungen", "fussnoten", "schluss"];
    if (reihen.indexOf("literaturverzeichnis") > -1 && reihen.indexOf("zitate") > -1) { // Zitate zuerst (liefert die Belege)
      reihen = reihen.filter(function (r) { return r !== "zitate"; });
      reihen.splice(reihen.indexOf("literaturverzeichnis"), 0, "zitate");
    }
    reihen.forEach(function (r) {
      if (!R[r]) { ergebnis[r] = [{ stufe: "info", text: "Unbekannter Prüfpunkt „" + r + "“." }]; return; }
      try { ergebnis[r] = R[r](); } catch (e) {
        ergebnis[r] = [{ stufe: "warn", text: "Diesen Punkt konnte der Prüfer nicht auswerten (" + e.message + ") – bitte selbst prüfen." }];
        if (window.console) console.error(e);
      }
    });
    return { reihen: reihen, ergebnis: ergebnis };
  }

  // ---------- Oberfläche
  LPW.registriere("docx", function (box, cfg, h) {
    var id = "lpw-docx-" + box.dataset.nr;
    box.insertAdjacentHTML("beforeend",
      (cfg.hinweis ? "<p>" + h.esc(cfg.hinweis) + "</p>" : "") +
      '<label class="lpw-drop" for="' + id + '"><strong>Word-Datei (.docx) hierher ziehen</strong> oder klicken und auswählen' +
      '<input type="file" id="' + id + '" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"></label>' +
      '<p class="lpw-klein" style="font-size:.9rem;color:var(--muted)">🔒 Deine Datei bleibt auf deinem Gerät – sie wird nur in diesem Browserfenster gelesen, nicht hochgeladen. ' +
      "Mit LibreOffice: erst <em>Datei › Speichern unter</em> im Format „Word 2007–365 (.docx)“ speichern.</p>" +
      '<div class="lpw-ergebnis" aria-live="polite"></div>');
    var drop = box.querySelector(".lpw-drop"), input = box.querySelector("input"), aus = box.querySelector(".lpw-ergebnis");

    function zeige(datei) {
      if (!datei) return;
      aus.innerHTML = "<p>Lese „" + h.esc(datei.name) + "“ …</p>";
      if (/\.(odt|doc)$/i.test(datei.name)) {
        aus.innerHTML = h.meldungen([{ stufe: "bad", text: "Das ist keine .docx-Datei.", tipp: "Speichere eine Kopie als „Word 2007–365 (.docx)“ und zieh diese hierher." }]);
        return;
      }
      datei.arrayBuffer().then(function (buf) {
        var z = entpacken(buf);
        if (!z["word/document.xml"]) throw new Error("keine Word-Datei");
        var rels = {};
        return lies(z["word/_rels/document.xml.rels"]).then(function (relText) {
          var r = xml(relText);
          Array.prototype.forEach.call(r ? r.getElementsByTagName("Relationship") : [], function (e) { rels[e.getAttribute("Id")] = e.getAttribute("Target"); });
          var namen = ["word/document.xml", "word/styles.xml", "word/settings.xml", "word/numbering.xml", "word/footnotes.xml", "word/theme/theme1.xml"];
          var fussIds = Object.keys(rels).filter(function (k) { return /footer/i.test(rels[k]); });
          return Promise.all(namen.map(function (n) { return lies(z[n]); }).concat(fussIds.map(function (k) {
            return lies(z["word/" + rels[k].replace(/^\/?word\//, "")]);
          }))).then(function (t) {
            var teile = { doc: xml(t[0]), styles: xml(t[1]), settings: xml(t[2]), numbering: xml(t[3]), footnotes: xml(t[4]), theme: xml(t[5]), fuss: {} };
            fussIds.forEach(function (k, i) { teile.fuss[k] = xml(t[6 + i]); });
            var a = analysiere(teile), erg = pruefen(a, cfg, teile, datei.name, h);
            var html = "", n = { ok: 0, bad: 0, warn: 0 };
            erg.reihen.forEach(function (r) {
              var liste = erg.ergebnis[r];
              liste.forEach(function (m) { if (n[m.stufe] != null) n[m.stufe]++; });
              html += "<h4 style=\"margin:1rem 0 .2rem\">" + h.esc(NAMEN[r] || r) + "</h4>" + h.meldungen(liste);
            });
            aus.innerHTML = '<p class="lpw-zusammenfassung">„' + h.esc(datei.name) + "“: " + n.ok + " in Ordnung · " + n.bad + " Fehler · " + n.warn + " Hinweise</p>" +
              (n.bad ? "<p>Arbeite die roten Punkte ab, speichere und zieh die Datei einfach noch einmal hierher.</p>" : "<p>Stark – keine Fehler gefunden! Schau dir die Hinweise trotzdem kurz an.</p>") + html +
              '<p style="font-size:.9rem;color:var(--muted)">Der Prüfer ist eine Hilfe, keine Note: Er liest die Datei, nicht die gedruckten Seiten. Was er nicht sehen kann (z. B. Seitenumbrüche an der richtigen Stelle), prüfst du am besten in der PDF.</p>';
          });
        });
      }).catch(function (e) {
        aus.innerHTML = h.meldungen([{ stufe: "bad", text: "Die Datei ließ sich nicht lesen (" + e.message + ").",
          tipp: /Browser/.test(e.message) ? "Bitte einen aktuellen Browser nutzen (Chrome, Edge, Firefox oder Safari ab 16.4)." : "Ist es wirklich eine .docx-Datei? Ist sie vielleicht noch in Word geöffnet und gesperrt?" }]);
      });
    }
    input.addEventListener("change", function () { zeige(input.files[0]); });
    ["dragenter", "dragover"].forEach(function (ev) { drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add("over"); }); });
    ["dragleave", "drop"].forEach(function (ev) { drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove("over"); }); });
    drop.addEventListener("drop", function (e) { if (e.dataTransfer.files[0]) zeige(e.dataTransfer.files[0]); });
  });
})();
