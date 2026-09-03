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
    var resources = data.resources || {};
    var pexels = resources.pexels || {};
    if (pexels.message) list.appendChild(element("li", "Pexels: " + pexels.message, pexels.status === "ready" ? "ok" : "warn"));
    var pixabay = resources.pixabay || {};
    if (pixabay.message) list.appendChild(element("li", "Pixabay: " + pixabay.message, pixabay.status === "ready" ? "ok" : "warn"));
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
    localResult.textContent = result.result_folder + (result.content_brief_available ? " · both briefs ready." : " · preparing briefs.");
    localActions.hidden = false;
    var details = record.details_url || "/dev/build-preparation-fixture/progress";
    document.getElementById("view-details").href = details;
    var contentLink = document.getElementById("download-content-brief");
    contentLink.href = record.content_brief_download_url || "#";
    contentLink.hidden = !record.content_brief_download_url;
    var visualLink = document.getElementById("download-visual-brief");
    visualLink.href = record.visual_brief_download_url || "#";
    visualLink.hidden = !record.visual_brief_download_url;
  }
  function renderSummary(record) {
    var summary = document.getElementById("summary");
    var body = document.getElementById("summary-body");
    if (!record.result) { summary.hidden = true; return; }
    summary.hidden = false;
    while (body.firstChild) body.removeChild(body.firstChild);
    var value = record.summary || {};
    body.appendChild(element("p", "Resource roles: " + (value.resource_role_count || 0) + " total · " + (value.resource_roles_with_candidates || 0) + " with real candidates"));
    body.appendChild(element("p", "Component roles: " + (value.component_role_count || 0) + " total · " + (value.component_roles_with_suggestions || 0) + " with suggestions", "muted"));
    body.appendChild(element("p", "Calls: " + (value.model_calls || 0) + " model · " + (value.provider_calls || 0) + " provider · input mode: " + (value.visual_input_mode || "approved_vdd"), "muted"));
    if (value.warning_count) body.appendChild(element("p", value.warning_count + " warning(s) -- see the diagnostics view for details.", "muted"));
    var assumptions = record.result && record.result.assumptions ? record.result.assumptions : [];
    if (assumptions.length) body.appendChild(element("p", "Assumptions applied: " + assumptions.join(" · "), "muted"));
    body.appendChild(element("p", "Status: " + record.status + " · Routes: " + (value.route_count || 0)));
    body.appendChild(element("p", "Content brief: " + (value.content_brief_length || 0) + " chars · Visual brief: " + (value.visual_brief_length || 0) + " chars", "mono"));
    document.getElementById("summary-details").href = record.details_url || "/dev/build-preparation-fixture/progress";
  }
  function render(record) {
    current = record;
    var tone = record.status === "ready" ? "ok" : record.status === "needs_attention" || record.status === "failed" ? "warn" : "running";
    setStatus(record.status, tone);
    status.textContent = record.status === "running" ? "Running " + (record.current_stage || "Build Preparation") + "…" : record.status === "ready" ? "Both Markdown briefs composed." : record.status === "needs_attention" ? "Run completed; review the issue card." : "Run failed; review the issue card.";
    setStages(record); setEvents(record.events); renderLocal(record); renderIssue(record.issue); renderSummary(record);
    renderPreflight(record.storage || {});
  }
  async function poll() {
    if (!current || !current.run_id) return;
    try {
      var response = await window.OryxenAIProtectedFetch("/api/v1/build-preparation/fixture/runs/" + encodeURIComponent(current.run_id));
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
      var response = await window.OryxenAIProtectedFetch("/api/v1/build-preparation/fixture/preflight");
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
      var response = await window.OryxenAIProtectedFetch("/api/v1/build-preparation/fixture/runs", { method: "POST", headers: {"Accept":"application/json", "Content-Type":"application/json"}, body: JSON.stringify(body) });
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
