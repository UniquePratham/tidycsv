/* tidycsv.js - browser core for TidyCSV and its how-to pages.
 *
 * Same rules and semantics as tidycsv.py (the Python CLI twin, covered by
 * test_tidycsv.py): empty rows, duplicate rows, whitespace, header noise,
 * suspicious emails, mixed date formats. Dates are normalized to YYYY-MM-DD
 * only when the format is unambiguous; ambiguous values are never rewritten.
 * Runs entirely in the tab: no network, no upload, no third-party scripts.
 */
(function (global) {
  "use strict";

  var RULES = ["empty_rows", "duplicate_rows", "whitespace", "header_noise", "invalid_email", "mixed_dates"];
  var RULE_LABELS = {
    empty_rows: "Empty rows",
    duplicate_rows: "Duplicate rows",
    whitespace: "Whitespace",
    header_noise: "Header problems",
    invalid_email: "Suspicious emails",
    mixed_dates: "Mixed date formats"
  };
  var EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/;
  var DATE_PATTERNS = [
    ["iso", /^\d{4}-\d{2}-\d{2}$/],
    ["slash", /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/],
    ["dot", /^(\d{1,2})\.(\d{1,2})\.(\d{4})$/]
  ];

  var CANDIDATE_DELIMITERS = [",", "\t", ";", "|"];

  function detectDelimiter(text) {
    var counts = {};
    CANDIDATE_DELIMITERS.forEach(function (d) { counts[d] = 0; });
    var inQuotes = false, lineHasQuote = false;
    var sample = String(text).slice(0, 20000);
    for (var i = 0; i < sample.length; i++) {
      var ch = sample.charAt(i);
      if (ch === '"') { inQuotes = !inQuotes; lineHasQuote = true; continue; }
      if (!inQuotes && (ch === "\n" || ch === "\r")) {
        lineHasQuote = false;
        continue;
      }
      if (!inQuotes && counts.hasOwnProperty(ch)) counts[ch]++;
    }
    if (lineHasQuote) { /* unterminated quote: keep the counts we have */ }
    var best = ",", bestCount = 0;
    CANDIDATE_DELIMITERS.forEach(function (d) {
      if (counts[d] > bestCount) { best = d; bestCount = counts[d]; }
    });
    return bestCount > 0 ? best : ",";
  }

  function delimiterLabel(d) {
    return d === "\t" ? "tab" : d === "," ? "comma" : d === ";" ? "semicolon" : d === "|" ? "pipe" : d;
  }

  function parse(text, delimiter) {
    text = String(text);
    if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
    var delim = delimiter || detectDelimiter(text);
    var rows = [];
    var row = [], field = "", inQuotes = false;
    for (var i = 0; i < text.length; i++) {
      var ch = text.charAt(i);
      if (inQuotes) {
        if (ch === '"') {
          if (text.charAt(i + 1) === '"') { field += '"'; i++; }
          else inQuotes = false;
        } else field += ch;
      } else if (ch === '"') { inQuotes = true; }
      else if (ch === delim) { row.push(field); field = ""; }
      else if (ch === "\n" || ch === "\r") {
        if (ch === "\r" && text.charAt(i + 1) === "\n") i++;
        row.push(field); field = "";
        rows.push(row); row = [];
      } else field += ch;
    }
    if (field.length || row.length) { row.push(field); rows.push(row); }
    while (rows.length && rows[0].every(function (c) { return !String(c).trim(); })) rows.shift();
    if (!rows.length) return { headers: [], rows: [], delimiter: delim };
    var headers = rows[0].map(function (c) { return String(c).trim(); });
    var width = Math.max(headers.length, 1);
    var data = rows.slice(1).map(function (r) {
      var fixed = r.slice(0, width);
      while (fixed.length < width) fixed.push("");
      return fixed;
    });
    return { headers: headers, rows: data, delimiter: delim };
  }

  function dateKind(value) {
    var v = String(value).trim();
    for (var i = 0; i < DATE_PATTERNS.length; i++) {
      if (DATE_PATTERNS[i][1].test(v)) return DATE_PATTERNS[i][0];
    }
    return null;
  }

  function toISO(value) {
    var v = String(value).trim();
    for (var i = 0; i < DATE_PATTERNS.length; i++) {
      var name = DATE_PATTERNS[i][0];
      var m = DATE_PATTERNS[i][1].exec(v);
      if (!m) continue;
      if (name === "iso") return v;
      var first = parseInt(m[1], 10), second = parseInt(m[2], 10), year = m[3];
      var day, month;
      if (first > 12) { day = first; month = second; }
      else if (second > 12) { month = first; day = second; }
      else return null; // ambiguous: never guess
      if (!(month >= 1 && month <= 12 && day >= 1 && day <= 31)) return null;
      return year + "-" + String(month).padStart(2, "0") + "-" + String(day).padStart(2, "0");
    }
    return null;
  }

  function dateColumns(headers, rows) {
    var cols = {};
    for (var index = 0; index < headers.length; index++) {
      var cells = rows.map(function (r) { return String(r[index] || "").trim(); }).filter(Boolean);
      if (cells.length < 2) continue;
      var kinds = cells.map(dateKind).filter(Boolean);
      if (kinds.length && kinds.length / cells.length >= 0.6) cols[index] = kinds[0];
    }
    return cols;
  }

  function detect(headers, rows) {
    var issues = [];
    var seenHeaders = {};
    headers.forEach(function (raw, index) {
      var name = String(raw).trim();
      var column = "col" + (index + 1);
      if (!name) issues.push({ rule: "header_noise", row: 0, column: column, detail: "blank header" });
      else if (seenHeaders[name.toLowerCase()] !== undefined)
        issues.push({ rule: "header_noise", row: 0, column: column, detail: "duplicate header '" + name + "'" });
      if (name && seenHeaders[name.toLowerCase()] === undefined) seenHeaders[name.toLowerCase()] = index;
    });
    var seenRows = {};
    rows.forEach(function (r, i) {
      var number = i + 1;
      if (r.every(function (c) { return !String(c).trim(); })) {
        issues.push({ rule: "empty_rows", row: number, column: "-", detail: "entirely empty row" });
        return;
      }
      var key = r.map(function (c) { return String(c).trim(); }).join("\u0001");
      if (seenRows[key] !== undefined)
        issues.push({ rule: "duplicate_rows", row: number, column: "-", detail: "row duplicates line " + seenRows[key] });
      else seenRows[key] = number;
      r.forEach(function (cell, index) {
        var column = headers[index] ? headers[index] : "col" + (index + 1);
        var value = String(cell);
        if (value !== value.trim() && value.trim())
          issues.push({ rule: "whitespace", row: number, column: column, detail: "leading/trailing whitespace", original: value });
        var v = value.trim();
        if (!v) return;
        var emailish = column.toLowerCase().indexOf("email") >= 0 || column.toLowerCase().endsWith("mail");
        var hasAt = v.indexOf("@") >= 0;
        if ((emailish && !hasAt) || (hasAt && !EMAIL_RE.test(v)))
          issues.push({ rule: "invalid_email", row: number, column: column, detail: "does not look like a valid email", original: v });
      });
    });
    var dateCols = dateColumns(headers, rows);
    Object.keys(dateCols).forEach(function (key) {
      var index = parseInt(key, 10);
      var column = headers[index] ? headers[index] : "col" + (index + 1);
      var values = rows.map(function (r) { return String(r[index] || "").trim(); }).filter(Boolean);
      var kinds = {};
      values.forEach(function (v) { var k = dateKind(v); if (k) kinds[k] = true; });
      if (Object.keys(kinds).length >= 2)
        issues.push({ rule: "mixed_dates", row: 0, column: column,
          detail: values.length + " date cells use mixed formats (e.g. " + values.slice(0, 3).join(", ") + ")" });
    });
    return issues;
  }

  function clean(headers, rows) {
    var notes = [];
    var used = {};
    var newHeaders = headers.map(function (raw, index) {
      var name = String(raw).trim() || ("column_" + (index + 1));
      var base = name, suffix = 2;
      while (used[name.toLowerCase()]) { name = base + "_" + suffix; suffix++; }
      if (name !== raw) notes.push("header col" + (index + 1) + ": " + (String(raw).trim() || "(blank)") + " -> " + name);
      used[name.toLowerCase()] = true;
      return name;
    });
    var dateCols = dateColumns(headers, rows);
    var seen = {};
    var out = [];
    var droppedEmpty = 0, droppedDupes = 0, stripped = 0, converted = 0;
    rows.forEach(function (row) {
      var cells = row.map(function (c) { return String(c).trim(); });
      if (cells.every(function (c) { return !c; })) { droppedEmpty++; return; }
      var key = cells.join("\u0001");
      if (seen[key]) { droppedDupes++; return; }
      seen[key] = true;
      row.forEach(function (c) { if (String(c) !== String(c).trim()) stripped++; });
      var fixed = cells.map(function (value, index) {
        if (dateCols[index] !== undefined) {
          var iso = toISO(value);
          if (iso && iso !== value) { converted++; return iso; }
        }
        return value;
      });
      out.push(fixed);
    });
    if (stripped) notes.push("stripped whitespace from " + stripped + " cell(s)");
    if (droppedEmpty) notes.push("dropped " + droppedEmpty + " empty row(s)");
    if (droppedDupes) notes.push("dropped " + droppedDupes + " duplicate row(s)");
    if (converted) notes.push("normalized " + converted + " unambiguous date cell(s) to YYYY-MM-DD");
    if (!notes.length) notes.push("no changes needed");
    return { headers: newHeaders, rows: out, notes: notes };
  }

  function csvEscape(value) {
    var v = String(value);
    return /[",\n\r]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
  }

  function toCSV(headers, rows, delimiter) {
    var delim = delimiter || ",";
    var lines = [headers.map(csvEscape).join(delim)];
    rows.forEach(function (r) { lines.push(r.map(csvEscape).join(delim)); });
    return lines.join("\r\n") + "\r\n";
  }

  /* Common UTF-8 read as Latin-1 mojibake: the tell-tale byte pairs are
   * reversible for the frequent cases. Text we cannot prove is reversible is
   * reported instead of silently rewritten. */
  var MOJIBAKE = [
    ["â€™", "\u2019"], ["â€œ", "\u201c"], ["â€\u009d", "\u201d"],
    ["Ã©", "é"], ["Ã¨", "è"], ["Ãª", "ê"], ["Ã ", "à"], ["Ã¡", "á"],
    ["Ã¢", "â"], ["Ã¤", "ä"], ["Ã¶", "ö"], ["Ã¼", "ü"], ["Ã±", "ñ"],
    ["Ã§", "ç"], ["Ã¸", "ø"], ["Ã¥", "å"], ["ÃŸ", "ß"], ["â‚¬", "€"],
    ["â„¢", "™"], ["â€”", "—"], ["â€“", "–"], ["Â ", " "]
  ];

  function repairText(text) {
    var original = String(text);
    var out = original;
    var changes = [];
    if (out.charCodeAt(0) === 0xFEFF) {
      out = out.slice(1);
      changes.push("stripped UTF-8 BOM");
    }
    if (/\r\n|\r/.test(out)) {
      out = out.replace(/\r\n?/g, "\n");
      changes.push("normalized line endings to \\n");
    }
    var replaced = 0;
    MOJIBAKE.forEach(function (pair) {
      if (out.indexOf(pair[0]) >= 0) {
        replaced += out.split(pair[0]).length - 1;
        out = out.split(pair[0]).join(pair[1]);
      }
    });
    if (replaced) changes.push("repaired " + replaced + " mojibake sequence(s) to UTF-8");
    var unreadable = (out.match(/\uFFFD/g) || []).length;
    if (unreadable) {
      changes.push(unreadable + " replacement character(s) remain - re-export that file as UTF-8 at the source");
    }
    return { text: out, changes: changes, changed: out !== original };
  }

  global.TidyCSV = {
    RULES: RULES,
    RULE_LABELS: RULE_LABELS,
    parse: parse,
    detect: detect,
    clean: clean,
    toCSV: toCSV,
    toISO: toISO,
    dateKind: dateKind,
    detectDelimiter: detectDelimiter,
    delimiterLabel: delimiterLabel,
    repairText: repairText
  };
})(typeof window !== "undefined" ? window : globalThis);
