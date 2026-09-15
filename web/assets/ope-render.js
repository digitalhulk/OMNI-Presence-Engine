/* OPE canonical client-side report renderer (RawBlock).
 *
 * ONE renderer, many hosts: web/index.html (local preview) and the Hostinger
 * shared-hosting shell (deploy/hostinger/) both load THIS file. Do not fork it.
 *
 * It is a pure presentation layer over a canonical normalized OPE result:
 * it renders only fields the engine actually emitted and derives nothing that
 * the engine is responsible for. It contains NO audit logic, NO scoring, NO
 * dependency-graph construction and NO root-cause analysis — every number and
 * every cause shown here was computed by the canonical Python engine. Counting
 * checks by status for a tally is display arithmetic, not diagnosis.
 *
 * Every interpolated value passes through esc(); nothing from a report reaches
 * the DOM unescaped.
 *
 * Exposes: window.OPERender.render(result, mountEl, opts)
 */
(function (global) {
  "use strict";

  var SEV_CHIP = {
    critical: "rb-chip--error", high: "rb-chip--error", medium: "rb-chip--warning",
    low: "", info: "rb-chip--info"
  };
  var STATUS_CHIP = {
    PASS: "rb-chip--success", FAIL: "rb-chip--error", OBSERVED: "rb-chip--error",
    HYPOTHESIS: "rb-chip--warning", UNKNOWN: "", "N/A": "rb-chip--info",
    BLOCKED: "rb-chip--warning"
  };
  var STATUS_ORDER = ["PASS", "FAIL", "UNKNOWN", "N/A", "BLOCKED"];

  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function chip(label, variant) {
    return '<span class="rb-chip rb-chip--status ' + (variant || "") + '">' + esc(label) + "</span>";
  }

  /* Health is produced by the canonical scorer; shown only when present so a
     report without a score never displays an invented one. */
  function healthBlock(r) {
    if (typeof r.health !== "number") return "";
    var basis = r.health_basis || {};
    var scored = basis.modules_scored;
    var method = basis.method ? esc(basis.method) : "";
    return '<div class="rb-card rb-card--elevated" style="margin-bottom:var(--rb-sp-5);text-align:center;padding:var(--rb-sp-4);">' +
      '<div class="rb-mono rb-tiny rb-uppercase">OMNI HEALTH</div>' +
      '<div style="font-family:var(--rb-font-headline);font-size:64px;line-height:1.05;">' + esc(r.health) + "</div>" +
      '<p class="rb-mono rb-tiny" style="margin:0;">' +
      (method ? "METHOD " + method : "") +
      (scored != null ? " · " + esc(scored) + " MODULES SCORED" : "") + "</p></div>";
  }

  function summaryCards(r) {
    var s = r.summary || {};
    var items = [["finding_count", "TOTAL"], ["critical", "CRITICAL"], ["high", "HIGH"],
                 ["medium", "MEDIUM"], ["low", "LOW"], ["info", "INFO"]];
    return '<div class="rb-grid rb-grid-3" style="margin-bottom:var(--rb-sp-5);">' + items.map(function (it) {
      var v = s[it[0]] || 0, extra = "", elevated = "";
      if ((it[0] === "critical" || it[0] === "high") && v) { elevated = " rb-card--elevated"; extra = " rb-txt-error"; }
      if (it[0] === "medium" && v) { extra = " rb-txt-warning"; }
      return '<div class="rb-card' + elevated + '" style="text-align:center;padding:var(--rb-sp-3);">' +
        '<div class="rb-mono rb-tiny rb-uppercase">' + it[1] + '</div>' +
        '<div style="font-family:var(--rb-font-headline);font-size:48px;line-height:1.1;"' + extra + '>' + v + '</div></div>';
    }).join("") + "</div>";
  }

  // A module can FAIL on a registry check that produced no legacy finding
  // record, so the card reports failing checks alongside the finding count.
  function moduleCheckTally(r, key) {
    var checks = r.checks || {}, failed = 0, total = 0;
    Object.keys(checks).forEach(function (id) {
      if (id.indexOf(key + "-") !== 0) return;
      total += 1;
      if (checks[id].status === "FAIL") failed += 1;
    });
    return { failed: failed, total: total };
  }

  function moduleGrid(r) {
    var keys = Object.keys(r.modules || {}).sort();
    if (!keys.length) return "";
    return '<h2>MODULES</h2><div class="rb-grid rb-grid-4 rb-grid-6" style="margin-bottom:var(--rb-sp-5);">' +
      keys.map(function (k) {
        var m = r.modules[k], n = (m.findings || []).length, tally = moduleCheckTally(r, k);
        var detail = tally.total
          ? tally.failed + "/" + tally.total + " CHECKS FAILING"
          : n + " FINDING" + (n === 1 ? "" : "S");
        var score = (typeof m.score === "number") ? '<div class="rb-mono rb-tiny">SCORE ' + esc(m.score) + "</div>" : "";
        return '<div style="border:var(--rb-border-thick);padding:8px;">' +
          '<div class="rb-mono rb-tiny rb-uppercase" style="margin-bottom:6px;">MODULE ' + esc(k) + '</div>' +
          chip(m.status, STATUS_CHIP[m.status] || "") +
          ' <span class="rb-mono rb-tiny">' + esc(detail) + "</span>" + score + "</div>";
      }).join("") + "</div>";
  }

  /* Dependency state + root causes come straight from the canonical graph
     (cascade_blocked / find_root_causes). Nothing is recomputed here. */
  function dependencyBlock(r) {
    var roots = r.dependency_root_causes || {};
    var keys = Object.keys(roots).sort();
    var blocked = Object.keys(r.modules || {}).filter(function (k) {
      return (r.modules[k] || {}).status === "BLOCKED";
    }).sort();
    if (!keys.length && !blocked.length) return "";
    var rows = keys.map(function (k) {
      var causes = roots[k] || [];
      return "<tr><th style='white-space:nowrap;'>MODULE " + esc(k) + "</th><td>" +
        (causes.length
          ? causes.map(function (c) { return chip("ROOT CAUSE " + c, "rb-chip--error"); }).join(" ")
          : "<span class='rb-mono rb-tiny'>NO UPSTREAM FAIL RECORDED</span>") + "</td></tr>";
    }).join("");
    return "<h2>DEPENDENCY STATE</h2>" +
      '<p class="rb-small">BLOCKED is a dependency-derived module state, never a direct failure of that module. ' +
      'Each blocked module traces back to the upstream module that actually holds FAIL evidence.</p>' +
      (blocked.length
        ? '<p class="rb-mono rb-tiny rb-uppercase" style="margin-bottom:var(--rb-sp-2);">BLOCKED: ' +
          blocked.map(esc).join(" · ") + "</p>"
        : "") +
      (rows ? '<table class="rb-table" style="margin-bottom:var(--rb-sp-5);">' + rows + "</table>" : "");
  }

  /* The canonical remediation planner's output, rendered in its own order. */
  function planBlock(r) {
    var plan = r.remediation_plan;
    if (!plan) return "";
    var buckets = Object.keys(plan);
    var out = buckets.map(function (bucket) {
      var steps = plan[bucket];
      if (!steps || !steps.length) return "";
      var items = steps.map(function (s) {
        if (s == null) return "";
        if (typeof s !== "object") return "<li>" + esc(s) + "</li>";
        var head = esc(s.action || s.symptom || s.id || "step");
        var meta = [];
        if (s.module) meta.push("MODULE " + esc(s.module));
        if (s.id) meta.push(esc(s.id));
        if (typeof s.priority === "number") meta.push("PRIORITY " + esc(s.priority));
        return "<li>" + head +
          (meta.length ? ' <span class="rb-mono rb-tiny">(' + meta.join(" · ") + ")</span>" : "") +
          (s.root_cause ? '<div class="rb-small">ROOT CAUSE — ' + esc(s.root_cause) + "</div>" : "") +
          "</li>";
      }).join("");
      return '<div class="rb-card" style="margin-bottom:var(--rb-sp-3);">' +
        '<p class="rb-label">' + esc(String(bucket).toUpperCase()) + "</p><ul>" + items + "</ul></div>";
    }).join("");
    if (!out) return "";
    return "<h2>REMEDIATION PLAN</h2>" +
      '<p class="rb-small">Ordered by the canonical planner — fix upstream causes before downstream symptoms.</p>' +
      out;
  }

  // Inventory entries are no longer all scalars: robots, TLS, cookies,
  // citability, run history and PageSpeed are nested objects, so a plain
  // string cast would print [object Object].
  function fmtValue(v) {
    if (v === null || v === undefined || v === "") return "—";
    if (typeof v !== "object") return esc(v);
    var json = JSON.stringify(v);
    if (json.length <= 120) return '<code class="rb-mono rb-tiny">' + esc(json) + "</code>";
    return "<details><summary class='rb-mono rb-tiny rb-uppercase'>" + (Array.isArray(v) ? v.length + " ITEMS" : "OBJECT") +
      "</summary><pre style='margin-top:var(--rb-sp-2);'>" + esc(JSON.stringify(v, null, 2)) + "</pre></details>";
  }

  function inventoryTable(r) {
    var keys = Object.keys(r.inventory || {});
    if (!keys.length) return "";
    var rows = keys.sort().map(function (k) {
      return "<tr><th>" + esc(k.replace(/_/g, " ")) + '</th><td>' + fmtValue(r.inventory[k]) + "</td></tr>";
    }).join("");
    return '<h2>INVENTORY</h2><table class="rb-table" style="margin-bottom:var(--rb-sp-5);">' + rows + "</table>";
  }

  function checkSection(r) {
    var checks = r.checks || {};
    var ids = Object.keys(checks);
    if (!ids.length) return "";
    var totals = {};
    ids.forEach(function (id) { var s = checks[id].status; totals[s] = (totals[s] || 0) + 1; });
    var cards = STATUS_ORDER.filter(function (s) { return totals[s]; }).map(function (s) {
      return '<div class="rb-card" style="text-align:center;padding:var(--rb-sp-3);">' +
        '<div class="rb-mono rb-tiny rb-uppercase">' + esc(s) + "</div>" +
        '<div style="font-family:var(--rb-font-headline);font-size:40px;line-height:1.1;">' + totals[s] + "</div></div>";
    }).join("");
    var failing = ids.filter(function (id) { return checks[id].status === "FAIL"; }).sort().map(function (id) {
      var c = checks[id];
      var value = c.evidence && c.evidence.length ? c.evidence[0].value : null;
      return "<tr><th style='white-space:nowrap;'>" + esc(id) + "</th><td>" + fmtValue(value) +
        (c.reason ? '<div class="rb-mono rb-tiny">' + esc(c.reason) + "</div>" : "") + "</td></tr>";
    }).join("");
    return "<h2>CHECKS</h2>" +
      '<p class="rb-small">' + ids.length + ' registry checks executed. A check with no bound evidence provider reports UNKNOWN rather than passing.</p>' +
      '<div class="rb-grid rb-grid-3" style="margin-bottom:var(--rb-sp-5);">' + cards + "</div>" +
      (failing ? '<h3 class="rb-uppercase">Failing checks</h3><table class="rb-table" style="margin-bottom:var(--rb-sp-5);">' + failing + "</table>" : "");
  }

  function findingCard(f) {
    var rem = (f.remediation || []).map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("");
    var val = (f.validation || []).map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("");
    var root = f.root_cause
      ? '<p class="rb-small"><strong class="rb-uppercase">Root cause — </strong>' + esc(f.root_cause) + "</p>" : "";
    var evidence = f.evidence && f.evidence.length
      ? "<details style='margin-top:var(--rb-sp-3);'><summary class='rb-btn rb-btn--sm rb-btn--secondary' style='display:inline-flex;'>EVIDENCE (DIRECT)</summary>" +
        '<pre style="margin-top:var(--rb-sp-2);">' + esc(JSON.stringify(f.evidence, null, 2)) + "</pre></details>" : "";
    return '<article class="rb-card rb-card--elevated rb-finding" data-severity="' + esc((f.severity || "info").toLowerCase()) +
      '" style="margin-bottom:var(--rb-sp-3);">' +
      '<div style="display:flex;flex-wrap:wrap;gap:var(--rb-sp-2);align-items:center;border-bottom:var(--rb-border-thick);padding-bottom:var(--rb-sp-2);margin-bottom:var(--rb-sp-2);">' +
      '<span class="rb-mono rb-small">' + esc(f.id) + "</span>" +
      chip(f.severity, SEV_CHIP[(f.severity || "").toLowerCase()] || "") +
      chip("PRIORITY " + f.priority) +
      '<span style="flex:1 1 auto;"></span>' +
      '<span class="rb-mono rb-tiny">MODULE ' + esc(f.module) + "</span>" +
      chip(f.status, STATUS_CHIP[f.status] || "") + "</div>" +
      '<h3 style="font-size:22px;font-family:var(--rb-font-body);font-weight:600;">' + esc(f.symptom) + "</h3>" +
      root +
      '<div class="rb-grid rb-grid-2"><div><p class="rb-label">Remediation</p><ul>' + (rem || "<li>—</li>") + "</ul></div>" +
      '<div><p class="rb-label">Validation</p><ul>' + (val || "<li>—</li>") + "</ul></div></div>" +
      evidence + "</article>";
  }

  /* Render a canonical normalized result into mount.
     opts.scroll  — scroll the mount into view.
     opts.notice  — optional HTML-escaped plain-text banner (e.g. fixture warning). */
  function render(r, mount, opts) {
    opts = opts || {};
    mount = mount || document.getElementById("report");
    if (!mount) return;
    if (!r || typeof r !== "object") {
      mount.innerHTML = '<div class="rb-card rb-card--elevated"><p class="rb-label rb-txt-error">NO REPORT DATA</p>' +
        '<p class="rb-small">Nothing was rendered because no canonical OPE result was supplied.</p></div>';
      return;
    }
    var notice = opts.notice
      ? '<div class="rb-card rb-card--elevated" style="margin-bottom:var(--rb-sp-4);border-color:var(--rb-warning);">' +
        '<p class="rb-label rb-txt-warning" style="margin:0;">' + esc(opts.notice) + "</p></div>"
      : "";
    mount.innerHTML =
      notice +
      '<hr class="rb-rule"><h2>REPORT // ' + esc(r.run_id || "") + "</h2>" +
      '<div class="rb-card rb-card--inverted" style="margin-bottom:var(--rb-sp-5);">' +
      '<p class="rb-mono rb-tiny" style="margin:0;">TARGET</p><h3 style="margin:0;word-break:break-all;">' + esc(r.target) + "</h3></div>" +
      healthBlock(r) + summaryCards(r) + moduleGrid(r) + dependencyBlock(r) +
      checkSection(r) + planBlock(r) + inventoryTable(r) +
      "<h2>FINDINGS</h2><hr class='rb-rule'>" +
      ((r.findings || []).slice().sort(function (a, b) { return b.priority - a.priority; }).map(findingCard).join("") || "<p>No findings.</p>");
    if (opts.scroll) mount.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  global.OPERender = { render: render, esc: esc };
})(typeof window !== "undefined" ? window : this);
