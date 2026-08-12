(function () {
  "use strict";
  var query = new URLSearchParams(window.location.search);
  var runId = query.get("run");
  var empty = document.getElementById("empty");
  var progress = document.getElementById("progress");
  if (!runId) { empty.hidden = false; return; }
  function add(parent, tag, text, className) { var node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; parent.appendChild(node); return node; }
  function stat(parent, value, label) { var node = add(parent, "div", undefined, "stat"); add(node, "strong", value); add(node, "span", label); }
  function render(record) {
    progress.hidden = false;
    var stats = document.getElementById("stats"); while (stats.firstChild) stats.removeChild(stats.firstChild);
    var summary = record.summary || {}; var result = record.result || {}; var materialization = result.materialization || {};
    stat(stats, record.status || "unknown", "status"); stat(stats, (record.events || []).length, "events"); stat(stats, summary.route_count || 0, "routes"); stat(stats, summary.resource_need_count || 0, "resource needs"); stat(stats, summary.candidate_count || 0, "fetched"); stat(stats, summary.qualified_candidate_count || 0, "qualified"); stat(stats, summary.selected_resource_count || 0, "selected"); stat(stats, summary.materialized_file_count || 0, "files"); stat(stats, summary.handoff_eligible ? "eligible" : "blocked", "handoff"); stat(stats, summary.archive_sha256 ? "verified" : "pending", "ZIP");
    document.getElementById("run-id").textContent = record.run_id || "";
    var local = record.local_result || {}; var localDetail = document.getElementById("local-detail"); while (localDetail.firstChild) localDetail.removeChild(localDetail.firstChild);
    [["Result folder", local.result_folder], ["Extracted context", local.build_context_folder], ["ZIP", local.archive_path], ["R2", (record.storage || {}).r2 && (record.storage || {}).r2.message]].forEach(function (pair) { if (pair[1]) { var item = add(localDetail, "div"); add(item, "strong", pair[0]); add(item, "span", pair[1], "mono"); } });
    var actions = document.getElementById("detail-actions"); while (actions.firstChild) actions.removeChild(actions.firstChild); if (record.download_url) { var link = add(actions, "a", "Download ZIP", "button secondary"); link.href = record.download_url; }
    var issueSection = document.getElementById("detail-issue"); var issueDetail = document.getElementById("issue-detail"); while (issueDetail.firstChild) issueDetail.removeChild(issueDetail.firstChild); if (record.issue) { issueSection.hidden = false; add(issueDetail, "p", record.issue.code || "FIXTURE_RUN_FAILED", "mono"); add(issueDetail, "p", record.issue.message || ""); add(issueDetail, "p", record.issue.next_action || "", "muted"); } else { issueSection.hidden = true; }
    var candidatesById = {}; (result.fetched_candidates || []).forEach(function (candidate) { candidatesById[candidate.resource_id] = candidate; });
    var resourceList = document.getElementById("resources"); while (resourceList.firstChild) resourceList.removeChild(resourceList.firstChild); var resources = materialization.resources || []; document.getElementById("resources-empty").hidden = !!resources.length;
    resources.forEach(function (entry) { var candidate = candidatesById[entry.id] || {}; var item = add(resourceList, "li", undefined, "resource-item"); if (candidate.kind === "photo" && candidate.preview_url) { var image = add(item, "img", undefined, "resource-thumb"); image.src = candidate.preview_url; image.alt = ""; image.loading = "lazy"; } else { add(item, "div", (entry.kind || "?").slice(0, 3), "resource-thumb placeholder"); } var main = add(item, "div", undefined, "resource-main"); add(main, "strong", (candidate.title || candidate.icon_name || entry.id) + " · " + (entry.provider || "unknown provider")); add(main, "span", entry.local_path || entry.local_directory || entry.hotlink_url || entry.need_id || ""); add(item, "span", entry.disposition || entry.inspection_level || "materialized", "resource-status ok"); });
    var events = document.getElementById("events"); while (events.firstChild) events.removeChild(events.firstChild); (record.events || []).forEach(function (event) { var item = add(events, "li"); add(item, "time", event.timestamp || ""); add(item, "span", (event.stage || "") + " · " + (event.message || ""), event.level || "info"); });
    document.getElementById("raw").textContent = JSON.stringify(record, null, 2);
    document.getElementById("copy").onclick = async function () { await navigator.clipboard.writeText(JSON.stringify(record, null, 2)); this.textContent = "Copied"; };
    var rejected = (result.candidate_qualifications || []).filter(function (entry) { return !entry.eligible; });
    rejected.forEach(function (entry) { var candidate = candidatesById[entry.resource_id] || {}; var item = add(resourceList, "li", undefined, "resource-item"); add(item, "div", (candidate.kind || "?").slice(0, 3), "resource-thumb placeholder"); var main = add(item, "div", undefined, "resource-main"); add(main, "strong", (candidate.title || candidate.resource_id || entry.resource_id) + " / " + (candidate.provider || "provider")); add(main, "span", (entry.issue_codes || []).join(", ") || (entry.reasons || []).join(" ")); add(item, "span", "rejected", "resource-status rejected"); });
    if (rejected.length) document.getElementById("resources-empty").hidden = false;
    document.getElementById("copy-issue").onclick = async function () { await navigator.clipboard.writeText(JSON.stringify({run_id: record.run_id, issue: record.issue, local_result: record.local_result}, null, 2)); this.textContent = "Copied"; };
  }
  async function load() { try { var response = await fetch("/api/v1/build-preparation/fixture/runs/" + encodeURIComponent(runId)); var data = await response.json(); if (!response.ok) throw new Error(); render(data); if (data.status === "running") window.setTimeout(load, 900); } catch (error) { empty.hidden = false; } }
  load();
}());
