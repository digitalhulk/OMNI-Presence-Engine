<?php
/**
 * OMNI-PRESENCE ENGINE — Command Center (Hostinger shared-hosting shell).
 *
 * A presentation layer over the canonical Python engine. It renders canonical
 * results and states what this runtime can do; it performs no audit, computes
 * no score, and contains no engine logic. Everything numeric on screen comes
 * from a canonical result produced by `ope`.
 */

declare(strict_types=1);

require_once __DIR__ . '/api/_bootstrap.php';

$live = ope_has_live_runtime();
$runtime = ope_runtime();

/** Escape for HTML text/attribute context. */
function h(?string $v): string
{
    return htmlspecialchars((string) $v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
?>
<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OMNI-PRESENCE ENGINE // COMMAND CENTER</title>
<meta name="description" content="OMNI-Presence-Engine Command Center — evidence-first digital presence auditing.">
<meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Mono:wght@400;700&family=Work+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/css/rawblock.css">
</head>
<body>

<header style="border-bottom:var(--rb-border-heavy);">
  <div class="rb-shell" style="border:0;display:flex;flex-wrap:wrap;gap:var(--rb-sp-3);align-items:center;justify-content:space-between;">
    <div>
      <p class="rb-mono rb-tiny rb-uppercase" style="margin:0;">EVIDENCE-FIRST DIGITAL PRESENCE</p>
      <h1 style="font-size:clamp(28px,5vw,48px);margin:0;">OMNI-PRESENCE ENGINE</h1>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <span class="rb-chip rb-chip--status rb-mono">ENGINE <?= h(OPE_ENGINE_VERSION) ?></span>
      <span class="rb-chip rb-chip--status rb-mono"><?= h((string) OPE_MODULE_COUNT) ?> MODULES</span>
      <span class="rb-chip rb-chip--status rb-mono"><?= h((string) OPE_CHECK_COUNT) ?> CHECKS</span>
      <button id="themeToggle" class="rb-btn rb-btn--sm rb-btn--primary" type="button">INVERT</button>
    </div>
  </div>
</header>

<!-- ENGINE RUNTIME STATUS -------------------------------------------------- -->
<section class="rb-shell" style="padding-bottom:var(--rb-sp-4);">
  <div class="rb-card <?= $live ? '' : 'rb-card--elevated' ?>" id="runtimeCard"
       style="<?= $live ? '' : 'border-color:var(--rb-warning);' ?>">
    <p class="rb-label" style="margin-top:0;">OPE ENGINE RUNTIME</p>
    <?php if ($live): ?>
      <h2 style="margin:0 0 var(--rb-sp-2);font-size:28px;">LIVE ENGINE — CONNECTED</h2>
      <p class="rb-small" style="margin:0;">
        A Python-capable OPE API is configured for this deployment. Audits run on the
        canonical engine and results are returned unchanged.
      </p>
    <?php else: ?>
      <h2 class="rb-txt-warning" style="margin:0 0 var(--rb-sp-2);font-size:28px;">LIVE ENGINE — UNAVAILABLE ON THIS RUNTIME</h2>
      <p class="rb-small" style="margin:0 0 var(--rb-sp-2);">
        The engine itself is healthy. This hosting runtime simply has no Python execution,
        so a live audit cannot be started from here. Connect a Python-capable OPE API to
        enable live audits — the interface below does not change when you do.
      </p>
      <p class="rb-mono rb-tiny" style="margin:0;">
        RUNTIME <?= h($runtime) ?> · ENGINE <?= h(OPE_ENGINE) ?> · LIVE_EXECUTION FALSE
      </p>
    <?php endif; ?>
  </div>
</section>

<!-- AUDIT CONSOLE ---------------------------------------------------------- -->
<section id="console" class="rb-shell" style="padding-bottom:var(--rb-sp-4);">
  <h2>AUDIT CONSOLE</h2>
  <div class="rb-stack" style="border:var(--rb-border-thick);padding:var(--rb-sp-3);">
    <p class="rb-label" style="margin-top:0;">Enter website URL</p>
    <form id="auditForm" style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;" novalidate>
      <input class="rb-input" id="urlInput" name="url" type="url" inputmode="url"
             placeholder="https://example.com" autocomplete="url" required
             style="flex:1 1 320px;">
      <button class="rb-btn rb-btn--primary" id="runBtn" type="submit">RUN OPE AUDIT</button>
    </form>
    <p class="rb-help" id="auditHelp" aria-live="polite">
      <?= $live
        ? 'Runs the canonical engine through the configured OPE API.'
        : 'This runtime cannot execute a live audit — submitting will report the runtime state, never a fabricated result.' ?>
    </p>
  </div>
</section>

<!-- REPORT SOURCES --------------------------------------------------------- -->
<section class="rb-shell" style="padding-bottom:var(--rb-sp-4);">
  <h2>LOAD AN EXISTING REPORT</h2>
  <div class="rb-grid rb-grid-2">
    <div class="rb-card">
      <p class="rb-label" style="margin-top:0;">Upload report JSON</p>
      <p class="rb-small">
        Generate one with the canonical engine on any Python-capable machine — nothing
        leaves your browser when you load it here:
      </p>
      <pre>ope audit https://example.com --json &gt; audit.report.json</pre>
      <input class="rb-input" id="fileInput" type="file" accept="application/json,.json" style="width:auto;">
      <p class="rb-help" id="loadHelp" aria-live="polite">Rendered entirely in your browser.</p>
    </div>
    <div class="rb-card">
      <p class="rb-label" style="margin-top:0;">Published reports</p>
      <p class="rb-small">
        Static reports published with this deployment, rendered by the canonical
        Python reporter.
      </p>
      <div id="reportList"><p class="rb-mono rb-tiny rb-uppercase">LOADING…</p></div>
    </div>
  </div>
</section>

<!-- RENDERED REPORT MOUNT -------------------------------------------------- -->
<section class="rb-shell" style="padding-bottom:var(--rb-sp-6);">
  <div id="report"></div>
</section>

<!-- ENGINE COVERAGE -------------------------------------------------------- -->
<section class="rb-shell" style="padding-bottom:var(--rb-sp-6);">
  <h2>ENGINE COVERAGE</h2>
  <p class="rb-small">
    The canonical engine's audit surface — the layers a real run evaluates. These are
    coverage labels, not results: scores and statuses appear only when an actual report
    is loaded above.
  </p>
  <div class="rb-grid rb-grid-4 rb-grid-6">
    <?php foreach (OPE_MODULES as $module): ?>
      <div style="border:var(--rb-border-thin);padding:8px;">
        <span class="rb-mono rb-tiny rb-uppercase"><?= h((string) $module) ?></span>
      </div>
    <?php endforeach; ?>
  </div>
</section>

<footer style="border-top:var(--rb-border-heavy);">
  <div class="rb-shell rb-inverted" style="border:0;padding-top:var(--rb-sp-4);padding-bottom:var(--rb-sp-4);">
    <p class="rb-mono rb-tiny" style="margin:0;">
      OMNI-PRESENCE ENGINE · CANONICAL ENGINE <?= h(OPE_ENGINE_VERSION) ?> ·
      CONTRACT <?= h(OPE_WEB_CONTRACT_VERSION) ?> · RUNTIME <?= h($runtime) ?> ·
      SHARP EDGES ONLY
    </p>
  </div>
</footer>

<!-- Canonical shared renderer — identical file to web/assets/ope-render.js. -->
<script src="assets/js/ope-render.js"></script>
<script>
(function () {
  "use strict";
  var mount = document.getElementById("report");
  var esc = window.OPERender.esc;

  document.getElementById("themeToggle").addEventListener("click", function () {
    var root = document.documentElement;
    root.setAttribute("data-theme", root.getAttribute("data-theme") === "dark" ? "light" : "dark");
  });

  /* ---- Live audit request ------------------------------------------------
     The shell only ever reports what /api/audit returns. A runtime_unavailable
     response is displayed as exactly that — never as an audit, never as a
     failure of the site being checked. */
  var form = document.getElementById("auditForm");
  var help = document.getElementById("auditHelp");
  var runBtn = document.getElementById("runBtn");

  function say(text, isError) {
    help.textContent = text;
    help.classList.toggle("is-error", !!isError);
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var url = document.getElementById("urlInput").value.trim();
    if (!url) { say("Enter a website URL first.", true); return; }
    runBtn.disabled = true;
    say("Contacting OPE…");
    // Direct .php paths so the UI works even if mod_rewrite is unavailable;
    // .htaccess also exposes /api/audit as a clean alias for API consumers.
    fetch("api/audit.php", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ url: url })
    }).then(function (res) {
      return res.json().catch(function () { return { status: "error", message: "Malformed response from the API." }; });
    }).then(function (payload) {
      runBtn.disabled = false;
      if (payload && payload.status === "success" && payload.result) {
        say("Audit complete — canonical result rendered below.");
        window.OPERender.render(payload.result, mount, { scroll: true });
        return;
      }
      if (payload && payload.status === "runtime_unavailable") {
        say(payload.message || "Live OPE execution requires a Python-capable runtime.");
        showRuntimeState(payload);
        return;
      }
      say((payload && payload.message) ? String(payload.message) : "The request could not be completed.", true);
      mount.innerHTML = "";
    }).catch(function (e) {
      runBtn.disabled = false;
      say("Could not reach the API: " + e.message, true);
    });
  });

  /* An explicit, non-alarming runtime panel — no scores, no findings, nothing
     that could read as an audit of the target. */
  function showRuntimeState(p) {
    mount.innerHTML =
      '<hr class="rb-rule">' +
      '<div class="rb-card rb-card--elevated" style="border-color:var(--rb-warning);">' +
      '<p class="rb-label rb-txt-warning" style="margin-top:0;">LIVE AUDIT NOT EXECUTED</p>' +
      '<h3 style="margin:0 0 var(--rb-sp-2);">' + esc(p.message || "") + '</h3>' +
      (p.target ? '<p class="rb-small" style="margin:0 0 var(--rb-sp-2);">Requested target: <code class="rb-mono">' + esc(p.target) + '</code> — not audited.</p>' : "") +
      '<p class="rb-mono rb-tiny" style="margin:0;">STATUS ' + esc(p.status) +
      ' · RUNTIME ' + esc(p.runtime) + ' · ENGINE ' + esc(p.engine) + ' · LIVE_EXECUTION FALSE</p>' +
      '<p class="rb-small" style="margin:var(--rb-sp-2) 0 0;">The engine is healthy. Load an existing report above, ' +
      'or connect a Python-capable OPE API to run audits from here.</p></div>';
    mount.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /* ---- Upload a canonical report JSON ---------------------------------- */
  document.getElementById("fileInput").addEventListener("change", function (ev) {
    var file = ev.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      var loadHelp = document.getElementById("loadHelp");
      try {
        var parsed = JSON.parse(reader.result);
        // Accept either a bare canonical result or the ope-web-v1 envelope.
        var result = (parsed && parsed.result && typeof parsed.result === "object") ? parsed.result : parsed;
        window.OPERender.render(result, mount, { scroll: true });
        loadHelp.textContent = "Rendered " + file.name + ".";
        loadHelp.classList.remove("is-error");
      } catch (e) {
        loadHelp.textContent = "Invalid OPE JSON report: " + e.message;
        loadHelp.classList.add("is-error");
      }
    };
    reader.readAsText(file);
  });

  /* ---- Published static reports ---------------------------------------- */
  fetch("api/status.php", { headers: { "Accept": "application/json" } })
    .then(function (r) { return r.json(); })
    .then(function (s) {
      var box = document.getElementById("reportList");
      var reports = (s && s.reports) || [];
      if (!reports.length) {
        box.innerHTML = '<p class="rb-mono rb-tiny rb-uppercase">NO REPORTS PUBLISHED YET</p>';
        return;
      }
      box.innerHTML = "<ul>" + reports.map(function (rep) {
        var label = rep.target || rep.file;
        var meta = [rep.generated_at, rep.engine_version ? "OPE " + rep.engine_version : null]
          .filter(Boolean).map(esc).join(" · ");
        return '<li><a href="reports/' + encodeURIComponent(rep.file) + '">' + esc(label) + "</a>" +
          (meta ? ' <span class="rb-mono rb-tiny">' + meta + "</span>" : "") + "</li>";
      }).join("") + "</ul>";
    })
    .catch(function () {
      document.getElementById("reportList").innerHTML =
        '<p class="rb-mono rb-tiny rb-uppercase">REPORT INDEX UNAVAILABLE</p>';
    });
})();
</script>
</body>
</html>
