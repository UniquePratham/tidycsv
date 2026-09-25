/* seo-tool.js - the shared, genuinely functional tool behind every TidyCSV
 * how-to page. Each page sets window.ZF_PAGE = {focus: [...rules], sample: "..."}
 * and this script renders: input -> real run of tidycsv.js -> before/after
 * result -> cleaned CSV download -> $9 unlock CTA -> done-for-you service link.
 *
 * Free result first, paid explanation second: the visitor always gets the
 * cleaned output in the tab before any price is mentioned.
 */
(function () {
  "use strict";

  var cfg = window.ZF_PAGE || {};
  var focus = Array.isArray(cfg.focus) && cfg.focus.length ? cfg.focus : TidyCSV.RULES;
  var mode = cfg.mode || "clean"; // clean | delimiter | encoding
  var mount = document.getElementById("tool");
  if (!mount) return;

  function esc(text) {
    return String(text).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  var delimiterPicker = "";
  if (mode === "delimiter") {
    delimiterPicker =
      '<label for="zcDelim">Delimiter your file uses (or should use)</label>' +
      '<select id="zcDelim">' +
      '<option value=",">comma (,)</option>' +
      '<option value=";">semicolon (;)</option>' +
      '<option value="\t">tab</option>' +
      '<option value="|">pipe (|)</option>' +
      "</select>";
  }

  mount.innerHTML =
    '<div class="zc-input">' +
    '<label for="zcText">Paste your CSV (header row first)</label>' +
    '<textarea id="zcText" rows="8" spellcheck="false">' + esc(cfg.sample || "") + "</textarea>" +
    delimiterPicker +
    '<div class="zc-row">' +
    '<button type="button" id="zcRun" class="zc-btn primary">Clean it now</button>' +
    '<label class="zc-btn ghost" for="zcFile">or choose a .csv file</label>' +
    '<input type="file" id="zcFile" accept=".csv,text/csv" class="zc-hidden">' +
    '<button type="button" id="zcSample" class="zc-btn ghost">Load a messy sample</button>' +
    "</div>" +
    '<p class="zc-note">Runs in this tab. Nothing is uploaded, no account, no third-party scripts.</p>' +
    "</div>" +
    '<div id="zcOut" class="zc-out zc-hidden">' +
    "<h2>Result</h2>" +
    '<div class="zc-stats" id="zcStats"></div>' +
    '<ul class="zc-notes" id="zcPreflight"></ul>' +
    '<div class="zc-pre"><table id="zcTable"></table></div>' +
    '<ul class="zc-notes" id="zcNotes"></ul>' +
    '<div class="zc-row">' +
    '<button type="button" id="zcDownload" class="zc-btn primary" data-zf-event="engaged">Download cleaned CSV</button>' +
    "</div>" +
    '<div class="zc-upsell">' +
    "<p><strong>Want the whole file cleaned and checked in one pass?</strong> " +
    'TidyCSV\'s $9 one-time unlock covers every rule plus a change report - ' +
    '<a href="index.html" data-zf-event="pricing_view">open the full tool</a>.</p>' +
    "<p>Short on time or handling a big export? " +
    '<a href="../csv-fix-service/index.html" data-zf-event="cta_click">CSV Fix Service</a> ' +
    "repairs the file for you from $8.99, free preview first.</p>" +
    "</div>" +
    "</div>";

  var last = null;
  var lastDelimiter = ",";

  function focusIssues(issues) {
    return issues.filter(function (i) { return focus.indexOf(i.rule) >= 0; });
  }

  function run(text) {
    if (mode === "encoding") {
      var repaired = TidyCSV.repairText(text);
      text = repaired.text;
      var pre = document.getElementById("zcPreflight");
      pre.innerHTML = repaired.changes.length
        ? repaired.changes.map(function (c) { return "<li>" + esc(c) + "</li>"; }).join("")
        : "<li>No encoding problems detected (file is already UTF-8 with clean line endings).</li>";
    }
    var parsed = TidyCSV.parse(text);
    if (mode === "delimiter") {
      var chosen = document.getElementById("zcDelim").value;
      parsed = TidyCSV.parse(text, chosen);
    }
    if (!parsed.headers.length) {
      alert("No header row found - is this a CSV file?");
      return;
    }
    lastDelimiter = parsed.delimiter || ",";
    var issues = TidyCSV.detect(parsed.headers, parsed.rows);
    var cleaned = TidyCSV.clean(parsed.headers, parsed.rows);
    var wanted = focusIssues(issues);
    last = cleaned;
    document.getElementById("zcOut").classList.remove("zc-hidden");

    var byRule = {};
    issues.forEach(function (i) { byRule[i.rule] = (byRule[i.rule] || 0) + 1; });
    var statHtml = "";
    TidyCSV.RULES.forEach(function (rule) {
      var n = byRule[rule] || 0;
      if (!n) return;
      statHtml += '<span class="zc-chip ' + (focus.indexOf(rule) >= 0 ? "on" : "") + '">' +
        esc(TidyCSV.RULE_LABELS[rule]) + ": " + n + "</span>";
    });
    if (mode === "delimiter") {
      statHtml += '<span class="zc-chip on">reading as ' +
        esc(TidyCSV.delimiterLabel(lastDelimiter)) + "-separated</span>";
    }
    if (!statHtml) {
      statHtml = '<span class="zc-chip on">No issues found - your file is already clean.</span>';
    }
    document.getElementById("zcStats").innerHTML = statHtml;

    var html = "<thead><tr>";
    cleaned.headers.forEach(function (h) { html += "<th>" + esc(h) + "</th>"; });
    html += "</tr></thead><tbody>";
    cleaned.rows.slice(0, 50).forEach(function (r) {
      html += "<tr>" + r.map(function (c) { return "<td>" + esc(c) + "</td>"; }).join("") + "</tr>";
    });
    html += "</tbody></html>";
    document.getElementById("zcTable").innerHTML = html;
    document.getElementById("zcNotes").innerHTML =
      cleaned.notes.map(function (n) { return "<li>" + esc(n) + "</li>"; }).join("") +
      (wanted.length ? "" : "<li>This page's focus checks passed.</li>");
    if (typeof window.zfTrack === "function") window.zfTrack("engaged");
    document.getElementById("zcOut").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  document.getElementById("zcRun").addEventListener("click", function () {
    run(document.getElementById("zcText").value);
  });
  document.getElementById("zcSample").addEventListener("click", function () {
    document.getElementById("zcText").value = cfg.messySample ||
      "name,email,joined\n Alice ,alice@example.com,2024-01-05\n" +
      "\n" +
      " Alice ,alice@example.com,13/01/2024\n" +
      "bob ,bob@example,05.02.2024\n";
    run(document.getElementById("zcText").value);
  });
  document.getElementById("zcFile").addEventListener("change", function (e) {
    var file = e.target.files && e.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      document.getElementById("zcText").value = String(reader.result);
      run(String(reader.result));
    };
    reader.readAsText(file);
  });
  document.getElementById("zcDownload").addEventListener("click", function () {
    if (!last) return;
    var blob = new Blob([TidyCSV.toCSV(last.headers, last.rows, lastDelimiter)], { type: "text/csv;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "cleaned.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  });
})();
