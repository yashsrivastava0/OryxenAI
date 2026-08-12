(function () {
  "use strict";
  var input = document.getElementById("fixture-input");
  var file = document.getElementById("fixture-file");
  var contentArchitectInput = document.getElementById("content-architect-input");
  var contentArchitectFile = document.getElementById("content-architect-file");
  var run = document.getElementById("run-phase2");
  var status = document.getElementById("status");
  var summary = document.getElementById("summary");
  var summaryBody = document.getElementById("summary-body");
  if (!input || !contentArchitectInput || !run) return;

  function add(parent, tag, text, className) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    parent.appendChild(node);
    return node;
  }
  function render(data) {
    summary.hidden = false;
    while (summaryBody.firstChild) summaryBody.removeChild(summaryBody.firstChild);
    var result = data.result || data;
    var materialization = data.materialization || result.materialization || {};
    var packageResult = data.package || result.package || {};
    add(summaryBody, "p", "Status: " + (data.status || "ready") + " · Stage: " + (data.stage || "phase_3"), "mono");
    add(summaryBody, "p", "Routes: " + (data.routes || []).length + " · Needs: " + (data.resource_needs || []).length + " · Candidates: " + (data.fetched_candidates || []).length + " · Model calls: " + (data.model_calls || 0));
    add(summaryBody, "p", "Materialized: " + (materialization.files || []).length + " files · " + (materialization.relative_root || materialization.root_path || "no output"), "mono");
    add(summaryBody, "p", "ZIP: " + (packageResult.archive_sha256 || "not available") + " / " + (packageResult.archive_size_bytes || 0) + " bytes", "mono");
    if (packageResult.mirror_relative_root) add(summaryBody, "p", "Debug mirror: " + packageResult.mirror_relative_root, "mono");
    if ((data.warnings || []).length) add(summaryBody, "p", "Warnings: " + data.warnings.join(" | "), "warning");
    var link = add(summaryBody, "a", "Open progress and every log", "link");
    link.href = "/build-preparation-fixture/progress";
  }
  function errorMessage(body) { return body && body.error && body.error.message ? body.error.message : "Phase 3 failed."; }
  file.addEventListener("change", function () {
    var selected = file.files && file.files[0];
    if (!selected) return;
    selected.text().then(function (text) { input.value = text; status.textContent = selected.name + " loaded."; });
  });
  contentArchitectFile.addEventListener("change", function () {
    var selected = contentArchitectFile.files && contentArchitectFile.files[0];
    if (!selected) return;
    selected.text().then(function (text) { contentArchitectInput.value = text; status.textContent = selected.name + " loaded."; });
  });
  document.getElementById("use-default").addEventListener("click", function () { input.value = ""; file.value = ""; status.textContent = "Using checked-in fixture."; });
  run.addEventListener("click", async function () {
    run.disabled = true; status.textContent = "Running Stage 0 through Phase 3…";
    var body = {
      live_model: document.getElementById("live-model").checked,
      live_providers: document.getElementById("live-providers").checked
    };
    if (input.value.trim()) body.output_json = input.value.trim();
    if (contentArchitectInput.value.trim()) body.content_architect_json = contentArchitectInput.value.trim();
    try {
      var response = await fetch("/api/v1/build-preparation/fixture/run", { method:"POST", headers:{"Accept":"application/json","Content-Type":"application/json"}, body:JSON.stringify(body) });
      var data = await response.json();
      if (!response.ok) throw new Error(errorMessage(data));
      sessionStorage.setItem("oryxenai.buildPreparationRun", JSON.stringify(data));
      render(data); status.textContent = "Phase 3 complete.";
    } catch (error) { status.textContent = error.message || "Phase 3 failed."; }
    finally { run.disabled = false; }
  });
})();
