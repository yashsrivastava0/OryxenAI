(function () {
  "use strict";
  var query = new URLSearchParams(window.location.search);
  var runId = query.get("run");
  var empty = document.getElementById("empty");
  var progress = document.getElementById("progress");
  if (!runId) { empty.hidden = false; return; }
  function add(parent, tag, text, className) { var node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; parent.appendChild(node); return node; }
  function stat(parent, value, label) { var node = add(parent, "div", undefined, "stat"); add(node, "strong", value); add(node, "span", label); }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
  function render(record) {
    progress.hidden = false;
    var stats = document.getElementById("stats"); clear(stats);
    var summary = record.summary || {}; var result = record.result || {};
    stat(stats, record.status || "unknown", "status");
    stat(stats, (record.events || []).length, "events");
    stat(stats, summary.route_count || 0, "routes");
    stat(stats, summary.resource_role_count || 0, "resource roles");
    stat(stats, summary.resource_roles_with_candidates || 0, "with candidates");
    stat(stats, summary.component_role_count || 0, "component roles");
    stat(stats, summary.model_calls || 0, "model calls");
    stat(stats, summary.provider_calls || 0, "provider calls");
    document.getElementById("run-id").textContent = record.run_id || "";
    var local = record.local_result || {}; var localDetail = document.getElementById("local-detail"); clear(localDetail);
    [["Result folder", local.result_folder], ["Content brief", local.content_brief_path], ["Visual brief", local.visual_brief_path]].forEach(function (pair) { if (pair[1]) { var item = add(localDetail, "div"); add(item, "strong", pair[0]); add(item, "span", pair[1], "mono"); } });
    var contentActions = document.getElementById("content-brief-actions"); clear(contentActions);
    if (record.content_brief_download_url) { var contentLink = add(contentActions, "a", "Download .md", "button secondary"); contentLink.href = record.content_brief_download_url; }
    var visualActions = document.getElementById("visual-brief-actions"); clear(visualActions);
    if (record.visual_brief_download_url) { var visualLink = add(visualActions, "a", "Download .md", "button secondary"); visualLink.href = record.visual_brief_download_url; }
    document.getElementById("content-brief").textContent = result.content_brief_markdown || "(not yet produced)";
    document.getElementById("visual-brief").textContent = result.visual_brief_markdown || "(not yet produced)";
    var issueSection = document.getElementById("detail-issue"); var issueDetail = document.getElementById("issue-detail"); clear(issueDetail); if (record.issue) { issueSection.hidden = false; add(issueDetail, "p", record.issue.code || "FIXTURE_RUN_FAILED", "mono"); add(issueDetail, "p", record.issue.message || ""); add(issueDetail, "p", record.issue.next_action || "", "muted"); } else { issueSection.hidden = true; }
    var resourceList = document.getElementById("resources"); clear(resourceList);
    var resourceIndex = result.resource_index || []; var componentIndex = result.component_index || [];
    document.getElementById("resources-empty").hidden = !!(resourceIndex.length || componentIndex.length);
    resourceIndex.forEach(function (entry) {
      var candidates = entry.candidates || [];
      var primary = entry.primary_candidate_index !== null && entry.primary_candidate_index !== undefined ? candidates[entry.primary_candidate_index] : null;
      var item = add(resourceList, "li", undefined, "resource-item");
      if (primary && primary.preview_url) { var image = add(item, "img", undefined, "resource-thumb"); image.src = primary.preview_url; image.alt = ""; image.loading = "lazy"; }
      else { add(item, "div", (entry.category || "?").slice(0, 3), "resource-thumb placeholder"); }
      var main = add(item, "div", undefined, "resource-main");
      add(main, "strong", entry.role_id + " · " + entry.category);
      add(main, "span", primary ? (primary.provider + " · " + primary.url) : entry.purpose || "");
      add(item, "span", entry.status, "resource-status " + (entry.status === "candidates_found" ? "ok" : "rejected"));
    });
    componentIndex.forEach(function (entry) {
      var suggestions = entry.suggestions || [];
      var primary = entry.primary_suggestion_index !== null && entry.primary_suggestion_index !== undefined ? suggestions[entry.primary_suggestion_index] : null;
      var item = add(resourceList, "li", undefined, "resource-item");
      add(item, "div", "cmp", "resource-thumb placeholder");
      var main = add(item, "div", undefined, "resource-main");
      add(main, "strong", entry.role_id + " · component");
      add(main, "span", primary ? (primary.provider + " · " + primary.name) : entry.purpose || "");
      add(item, "span", suggestions.length ? "suggested" : "no_suggestion", "resource-status " + (suggestions.length ? "ok" : "rejected"));
    });
    var events = document.getElementById("events"); clear(events); (record.events || []).forEach(function (event) { var item = add(events, "li"); add(item, "time", event.timestamp || ""); add(item, "span", (event.stage || "") + " · " + (event.message || ""), event.level || "info"); });
    document.getElementById("raw").textContent = JSON.stringify(record, null, 2);
    document.getElementById("copy").onclick = async function () { await navigator.clipboard.writeText(JSON.stringify(record, null, 2)); this.textContent = "Copied"; };
    document.getElementById("copy-issue").onclick = async function () { await navigator.clipboard.writeText(JSON.stringify({run_id: record.run_id, issue: record.issue, local_result: record.local_result}, null, 2)); this.textContent = "Copied"; };
  }
  async function load() { try { var response = await window.OryxenAIProtectedFetch("/api/v1/build-preparation/fixture/runs/" + encodeURIComponent(runId)); var data = await response.json(); if (!response.ok) throw new Error(); render(data); if (data.status === "running") window.setTimeout(load, 900); } catch (error) { empty.hidden = false; } }
  load();
}());
