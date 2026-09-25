/* ZeroForge client-side session log (zf-track.js)
 *
 * Why this exists: static GitHub Pages are served without server logs and
 * without any credentials for a third-party analytics product, so page-view
 * and intent events are recorded in the visitor's own browser instead.
 * Nothing is sent over the network; there are no third-party requests and
 * no cookies. The owner exports the JSON (Copy / Download) and imports it
 * into the engine with: python -m zeroforge track-session --experiment <id> --file <json>
 *
 * Allowlisted events (must match zeroforge.experiments.TRACKABLE):
 *   visitor, engaged, repeat, cta_click, pricing_view, checkout_start, lead, conversion
 * Ledger-only events (purchase / revenue) are deliberately NOT recordable here:
 * verified revenue can only come from confirmed transactions.
 */
(function () {
  "use strict";

  var cfg = window.ZF_TRACKING || {};
  var EXP = String(cfg.experiment || "");
  var PRODUCT = String(cfg.product || "");
  var STORE_KEY = "zf_events_v1";
  var SEEN_KEY = "zf_seen_v1";
  var ALLOWED = {
    visitor: 1,
    engaged: 1,
    repeat: 1,
    cta_click: 1,
    pricing_view: 1,
    checkout_start: 1,
    lead: 1,
    conversion: 1
  };

  function read() {
    try {
      var raw = window.localStorage.getItem(STORE_KEY);
      var list = raw ? JSON.parse(raw) : [];
      return Array.isArray(list) ? list : [];
    } catch (err) {
      return [];
    }
  }

  function write(list) {
    try {
      window.localStorage.setItem(STORE_KEY, JSON.stringify(list));
    } catch (err) {
      /* storage full or blocked: the session stays unlogged, never breaks the page */
    }
  }

  function seenBefore() {
    try {
      if (window.localStorage.getItem(SEEN_KEY)) return true;
      window.localStorage.setItem(SEEN_KEY, "1");
      return false;
    } catch (err) {
      return false;
    }
  }

  function record(event, count) {
    if (!ALLOWED[event]) return false;
    var n = parseInt(count, 10);
    if (!isFinite(n) || n < 1) n = 1;
    if (n > 1000) n = 1000;
    var list = read();
    list.push({
      event: event,
      count: n,
      at: new Date().toISOString(),
      page: String(window.location.pathname || "")
    });
    write(list);
    render();
    return true;
  }

  window.zfTrack = function (event, count) {
    return record(event, count);
  };

  window.zfSessionExport = function () {
    return {
      experiment: EXP,
      product: PRODUCT,
      exported_at: new Date().toISOString(),
      source: "client-side session log (no third-party analytics)",
      events: read()
    };
  };

  function totals() {
    var list = read();
    var out = {};
    for (var i = 0; i < list.length; i++) {
      out[list[i].event] = (out[list[i].event] || 0) + list[i].count;
    }
    return out;
  }

  /* ---- UI: a small session-log panel (no external assets) ---- */

  var panel = null;
  var badge = null;

  function ensureStyles() {
    if (document.getElementById("zf-style")) return;
    var style = document.createElement("style");
    style.id = "zf-style";
    style.textContent =
      "#zf-badge{position:fixed;right:12px;bottom:12px;z-index:9999;background:#111827;color:#e5e7eb;" +
      "border:1px solid #374151;border-radius:999px;padding:6px 12px;font:12px/1.4 system-ui,sans-serif;" +
      "cursor:pointer;opacity:.85}" +
      "#zf-badge:hover{opacity:1}" +
      "#zf-panel{position:fixed;right:12px;bottom:52px;z-index:9999;width:320px;max-height:60vh;overflow:auto;" +
      "background:#0b1220;color:#e5e7eb;border:1px solid #374151;border-radius:10px;padding:12px;" +
      "font:12px/1.5 ui-monospace,Consolas,monospace;box-shadow:0 8px 24px rgba(0,0,0,.35)}" +
      "#zf-panel h4{margin:0 0 6px;font:600 13px system-ui,sans-serif;color:#f9fafb}" +
      "#zf-panel .zf-note{color:#9ca3af;margin:0 0 8px;font:11px/1.5 system-ui,sans-serif}" +
      "#zf-panel table{width:100%;border-collapse:collapse;margin-bottom:8px}" +
      "#zf-panel td{padding:2px 0;color:#d1d5db}" +
      "#zf-panel td:last-child{text-align:right;color:#f9fafb}" +
      "#zf-panel button{background:#1f2937;color:#e5e7eb;border:1px solid #4b5563;border-radius:6px;" +
      "padding:5px 8px;margin:0 6px 6px 0;font:12px system-ui,sans-serif;cursor:pointer}" +
      "#zf-panel button:hover{background:#374151}" +
      "#zf-panel pre{display:none;white-space:pre-wrap;word-break:break-all;background:#111827;" +
      "border:1px solid #374151;border-radius:6px;padding:8px;margin:0 0 6px;max-height:30vh;overflow:auto}";
    document.head.appendChild(style);
  }

  function render() {
    if (!badge || !panel) return;
    var t = totals();
    var count = read().length;
    badge.textContent = "session log (" + count + ")";
    var rows = "";
    var keys = Object.keys(t).sort();
    for (var i = 0; i < keys.length; i++) {
      rows += "<tr><td>" + keys[i] + "</td><td>" + t[keys[i]] + "</td></tr>";
    }
    if (!rows) rows = '<tr><td>no events yet</td><td>0</td></tr>';
    panel.innerHTML =
      "<h4>Anonymous session log</h4>" +
      '<p class="zf-note">No third-party analytics and no cookies: events stay in this browser only. ' +
      "The site owner exports this JSON manually to count engagement.</p>" +
      "<table>" + rows + "</table>" +
      '<button type="button" data-zf="copy">Copy JSON</button>' +
      '<button type="button" data-zf="download">Download</button>' +
      '<button type="button" data-zf="clear">Clear</button>' +
      '<button type="button" data-zf="toggle">View raw</button>' +
      "<pre>" + JSON.stringify(window.zfSessionExport(), null, 2) + "</pre>";
  }

  function onClick(ev) {
    var el = ev.target;
    while (el && el !== document) {
      if (el.id === "zf-badge") {
        panel.style.display = panel.style.display === "none" ? "block" : "none";
        render();
        return;
      }
      if (el.getAttribute && el.getAttribute("data-zf")) {
        var action = el.getAttribute("data-zf");
        if (action === "copy" || action === "download") {
          var text = JSON.stringify(window.zfSessionExport(), null, 2);
          if (action === "download") {
            var blob = new Blob([text], { type: "application/json" });
            var a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = (PRODUCT || "session") + "-session.json";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(a.href);
          } else if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text);
          }
          return;
        }
        if (action === "clear") {
          write([]);
          render();
          return;
        }
        if (action === "toggle") {
          var pre = panel.querySelector("pre");
          if (pre) pre.style.display = pre.style.display === "block" ? "none" : "block";
          return;
        }
      }
      if (el.getAttribute && el.getAttribute("data-zf-event")) {
        record(el.getAttribute("data-zf-event"), el.getAttribute("data-zf-count") || 1);
        return;
      }
      el = el.parentNode;
    }
  }

  function boot() {
    ensureStyles();
    badge = document.createElement("button");
    badge.id = "zf-badge";
    badge.type = "button";
    badge.title = "Events recorded in this browser only";
    panel = document.createElement("div");
    panel.id = "zf-panel";
    panel.style.display = "none";
    document.body.appendChild(badge);
    document.body.appendChild(panel);
    document.addEventListener("click", onClick, false);
    record(seenBefore() ? "repeat" : "visitor", 1);
    render();
    if (window.ZF_TRACKING && window.ZF_TRACKING.onReady) {
      try {
        window.ZF_TRACKING.onReady(record);
      } catch (err) {
        /* page-specific hooks must never break the page */
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
