(function () {
  "use strict";
  var input = document.getElementById("fixture-input");
  var file = document.getElementById("fixture-file");
  var contentInput = document.getElementById("content-architect-input");
  var contentFile = document.getElementById("content-architect-file");
  var runButton = document.getElementById("run-phase3");
  var status = document.getElementById("status");
  var runStatus = document.getElementById("run-status");
  var stageList = document.getElementById("stage-list");
  var eventList = document.getElementById("live-events");
  var localResult = document.getElementById("local-result");
  var localActions = document.getElementById("local-actions");
  var issueCard = document.getElementById("issue-card");
  var current = null;
  var pollTimer = null;
  var localFolder = "";
  if (!input || !contentInput || !runButton) return;

  function element(tag, text, className) {
    var node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function apiError(data) {
    return data && data.error && data.error.message ? data.error.message : "Build Preparation run failed.";
  }
  function setStatus(value, tone) {
    runStatus.textContent = value;
    runStatus.className = "status-badge " + (tone || "");
  }
  function setStages(record) {
    var currentStage = record.current_stage || "";
    var completed = {};
    (record.events || []).forEach(function (event) {
      if (event.level !== "error") completed[event.stage] = true;
    });
    Array.prototype.forEach.call(stageList.querySelectorAll("li"), function (item) {
      var stage = item.getAttribute("data-stage");
      item.className = "";
      if (stage === currentStage && record.status === "running") item.className = "active";
      else if (completed[stage]) item.className = "complete";
      if (record.issue && (stage === currentStage || stage === "artifact_storage" && record.issue.code.indexOf("ARTIFACT_") === 0)) item.className = "failed";
    });
  }
  function setEvents(events) {
    while (eventList.firstChild) eventList.removeChild(eventList.firstChild);
    var newest = (events || []).slice(-8).reverse();
    if (!newest.length) { eventList.appendChild(element("li", "No run started.", "muted")); return; }
    newest.forEach(function (event) {
      var item = element("li", undefined, event.level || "info");
      item.appendChild(element("strong", event.stage || "run"));
      item.appendChild(element("span", event.message || ""));
      eventList.appendChild(item);
    });
  }
  function renderPreflight(data) {
    var list = document.getElementById("preflight");
    while (list.firstChild) list.removeChild(list.firstChild);
    var local = data.local || {};
    var r2 = data.r2 || {};
    var resources = data.resources || {};
    list.appendChild(element("li", "Local timestamped result: " + (local.status === "ready" ? "ready" : "checking"), local.status === "ready" ? "ok" : ""));
    var r2Text = "R2: " + (r2.message || r2.status || "checking");
    list.appendChild(element("li", r2Text, r2.status === "ready" || r2.status === "verified" ? "ok" : r2.status === "not_configured" ? "warn" : ""));
    var pexels = resources.pexels || {};
    if (pexels.message) list.appendChild(element("li", "Editorial images: " + pexels.message, pexels.status === "ready" ? "ok" : "warn"));
    var inputs = data.inputs || {};
    Object.keys(inputs).forEach(function (key) {
      var item = inputs[key] || {};
      var label = key === "visual_design_director" ? "Visual Design Director input" : "Content Architect input";
      list.appendChild(element("li", label + ": " + (item.status === "ready" ? "auto-picked" : "not found"), item.status === "ready" ? "ok" : "warn"));
    });
  }
  function renderIssue(issue) {
    if (!issue) { issueCard.hidden = true; return; }
    issueCard.hidden = false;
    document.getElementById("issue-code").textContent = issue.code || "FIXTURE_RUN_FAILED";
    document.getElementById("issue-message").textContent = issue.message || "Build Preparation needs attention.";
    document.getElementById("issue-action").textContent = issue.next_action || "Review diagnostics.json.";
  }
  function renderLocal(record) {
    var result = record.local_result || {};
    localFolder = result.result_folder || "";
    if (!localFolder) { localResult.textContent = "Creating timestamped local result folder…"; localActions.hidden = true; return; }
    localResult.textContent = result.result_folder + (result.archive_available ? " · ZIP and extracted build-context ready." : " · Preparing files.");
    localActions.hidden = false;
    var details = record.details_url || "/build-preparation-fixture/progress";
    document.getElementById("view-details").href = details;
    document.getElementById("download-zip").href = record.download_url || "#";
    document.getElementById("download-zip").hidden = !record.download_url;
  }
  function renderSummary(record) {
    var summary = document.getElementById("summary");
    var body = document.getElementById("summary-body");
    if (!record.result) { summary.hidden = true; return; }
    summary.hidden = false;
    while (body.firstChild) body.removeChild(body.firstChild);
    var value = record.summary || {};
    body.appendChild(element("p", "Real material: " + (value.real_image_count || 0) + " images · " + (value.real_component_count || 0) + " components · " + (value.execution_gap_count || 0) + " execution gaps"));
    body.appendChild(element("p", "Targets: " + (value.image_target || 0) + " images · " + (value.component_target || 0) + " components · input: " + (value.visual_input_mode || "approved_vdd"), "muted"));
    body.appendChild(element("p", "Calls: " + (value.model_calls || 0) + " model · " + (value.provider_calls || 0) + " provider · " + (value.provider_cache_hits || 0) + " cache hits · " + (value.provider_rate_limit_events || 0) + " rate-limit events", "muted"));
    if (value.deferred_optional_roles && value.deferred_optional_roles.length) body.appendChild(element("p", "Deferred optional roles: " + value.deferred_optional_roles.join(", "), "muted"));
    var assumptions = record.result && record.result.assumptions ? record.result.assumptions : [];
    if (assumptions.length) body.appendChild(element("p", "Assumptions applied: " + assumptions.join(" · "), "muted"));
    var receipts = record.result && record.result.provider_receipts ? record.result.provider_receipts : [];
    if (receipts.length) {
      var receiptDetails = document.createElement("details");
      receiptDetails.appendChild(element("summary", "Provider receipts (" + receipts.length + ")"));
      receipts.slice(-12).forEach(function (receipt) {
        receiptDetails.appendChild(element("p", (receipt.provider || "provider") + " · " + (receipt.query || "") + " · HTTP " + (receipt.http_status || "n/a") + " · " + (receipt.candidate_count || 0) + " candidates · " + (receipt.cache_state || "unknown"), "muted mono"));
      });
      body.appendChild(receiptDetails);
    }
    var issues = record.result && record.result.handoff_report && record.result.handoff_report.issues ? record.result.handoff_report.issues : [];
    if (issues.length) {
      var issueDetails = document.createElement("details");
      issueDetails.appendChild(element("summary", "Role diagnostics (" + issues.length + ")"));
      issues.forEach(function (issue) {
        issueDetails.appendChild(element("p", (issue.code || "issue") + (issue.need_id ? " · " + issue.need_id : "") + " · " + (issue.message || ""), "muted"));
      });
      body.appendChild(issueDetails);
    }
    body.appendChild(element("p", "Status: " + record.status + " · Routes: " + (value.route_count || 0) + " · Needs: " + (value.resource_need_count || 0)));
    body.appendChild(element("p", "ZIP: " + (value.archive_sha256 || "not available") + " · " + (value.archive_size_bytes || 0) + " bytes", "mono"));
    document.getElementById("summary-details").href = record.details_url || "/build-preparation-fixture/progress";
  }
  function render(record) {
    current = record;
    var tone = record.status === "ready" || record.status === "ready_for_handoff" ? "ok" : record.status === "needs_attention" || record.status === "failed" ? "warn" : "running";
    setStatus(record.status === "needs_attention" ? "Local ready · R2 attention" : record.status, tone);
    status.textContent = record.status === "running" ? "Running " + (record.current_stage || "Build Preparation") + "…" : record.status === "ready" ? "Phase 3 completed." : record.status === "needs_attention" ? "Local result completed; review the issue card." : "Run failed; review the issue card.";
    if (record.status === "ready_for_handoff") { setStatus("Ready for Code Generator", "ok"); status.textContent = "Package verified and eligible for Code Generator."; }
    if (record.status === "needs_attention" && record.result && record.result.handoff_report) { setStatus("Handoff blocked", "warn"); status.textContent = "Package retained for review; Code Generator handoff is blocked."; }
    setStages(record); setEvents(record.events); renderLocal(record); renderIssue(record.issue); renderSummary(record);
    renderPreflight(record.storage || {});
  }
  async function poll() {
    if (!current || !current.run_id) return;
    try {
      var response = await fetch("/api/v1/build-preparation/fixture/runs/" + encodeURIComponent(current.run_id));
      var data = await response.json();
      if (!response.ok) throw new Error(apiError(data));
      render(data);
      if (data.status === "running") { pollTimer = window.setTimeout(poll, 900); }
    } catch (error) {
      status.textContent = error.message || "Could not refresh the live run monitor.";
      pollTimer = window.setTimeout(poll, 2000);
    }
  }
  async function preflight() {
    try {
      var response = await fetch("/api/v1/build-preparation/fixture/preflight");
      var data = await response.json();
      if (response.ok) renderPreflight(data);
    } catch (error) { /* The run itself will surface any configuration issue. */ }
  }
  function readFile(selected, target, label) {
    if (!selected) return;
    selected.text().then(function (text) { target.value = text; status.textContent = label + " loaded."; });
  }
  file.addEventListener("change", function () { readFile(file.files && file.files[0], input, "VDD JSON"); });
  contentFile.addEventListener("change", function () { readFile(contentFile.files && contentFile.files[0], contentInput, "Content Architect JSON"); });
  document.getElementById("use-default").addEventListener("click", function () { input.value = ""; file.value = ""; contentInput.value = ""; contentFile.value = ""; status.textContent = "Auto-picking the attached Content Architect and Visual Design Director outputs."; });
  document.getElementById("copy-path").addEventListener("click", async function () { if (!localFolder) return; await navigator.clipboard.writeText(localFolder); this.textContent = "Copied"; });
  document.getElementById("copy-issue").addEventListener("click", async function () { if (!current || !current.issue) return; await navigator.clipboard.writeText(JSON.stringify({run_id: current.run_id, issue: current.issue, local_result: current.local_result}, null, 2)); this.textContent = "Copied"; });
  runButton.addEventListener("click", async function () {
    if (pollTimer) { window.clearTimeout(pollTimer); pollTimer = null; }
    runButton.disabled = true; issueCard.hidden = true; status.textContent = "Starting Build Preparation…";
    var body = { live_model: document.getElementById("live-model").checked, live_providers: document.getElementById("live-providers").checked };
    if (input.value.trim()) body.output_json = input.value.trim();
    if (contentInput.value.trim()) body.content_architect_json = contentInput.value.trim();
    try {
      var response = await fetch("/api/v1/build-preparation/fixture/runs", { method: "POST", headers: {"Accept":"application/json", "Content-Type":"application/json"}, body: JSON.stringify(body) });
      var data = await response.json();
      if (!response.ok) throw new Error(apiError(data));
      render(data); poll();
    } catch (error) {
      status.textContent = error.message || "Could not start Build Preparation.";
      setStatus("Start failed", "warn");
    } finally { runButton.disabled = false; }
  });
  preflight();
}());
