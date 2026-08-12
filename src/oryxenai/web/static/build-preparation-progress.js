(function () {
  "use strict";
  var raw = sessionStorage.getItem("oryxenai.buildPreparationRun");
  var empty = document.getElementById("empty");
  var progress = document.getElementById("progress");
  if (!raw) { empty.hidden = false; return; }
  var data;
  try { data = JSON.parse(raw); } catch (error) { empty.hidden = false; return; }
  progress.hidden = false;
  var result = data.result || data;
  document.getElementById("run-id").textContent = data.run_id || "";
  var stats = document.getElementById("stats");
  function stat(value, label) { var node = document.createElement("div"); node.className = "stat"; var strong = document.createElement("strong"); strong.textContent = value; node.appendChild(strong); var span = document.createElement("span"); span.textContent = label; node.appendChild(span); stats.appendChild(node); }
  var materialization = data.materialization || result.materialization || {};
  var packageResult = data.package || result.package || {};
  stat(data.status || "ready", "status"); stat((data.events || []).length, "events"); stat((data.routes || []).length, "routes"); stat((data.resource_needs || []).length, "resource needs"); stat((data.fetched_candidates || []).length, "provider candidates"); stat((materialization.files || []).length, "materialized files");
  stat(packageResult.archive_sha256 ? "verified" : "missing", "ZIP");

  var candidatesById = {};
  (data.fetched_candidates || []).forEach(function (candidate) { candidatesById[candidate.resource_id] = candidate; });
  var resourceList = document.getElementById("resources");
  var resourceEntries = materialization.resources || [];
  if (!resourceEntries.length) {
    document.getElementById("resources-empty").hidden = false;
  } else {
    resourceEntries.forEach(function (entry) {
      var candidate = candidatesById[entry.id] || {};
      var item = document.createElement("li");
      item.className = "resource-item";

      var thumbSrc = candidate.preview_url || (entry.inspection_level === "metadata_only" ? entry.hotlink_url : "");
      if (thumbSrc) {
        var img = document.createElement("img");
        img.className = "resource-thumb"; img.src = thumbSrc; img.alt = candidate.title || entry.id; img.loading = "lazy";
        item.appendChild(img);
      } else {
        var placeholder = document.createElement("div");
        placeholder.className = "resource-thumb placeholder";
        placeholder.textContent = (entry.kind || "?").slice(0, 3);
        item.appendChild(placeholder);
      }

      var main = document.createElement("div");
      main.className = "resource-main";
      var title = document.createElement("strong");
      title.textContent = (candidate.title || candidate.icon_name || entry.id) + " · " + (entry.provider || "unknown provider");
      main.appendChild(title);
      var detail = document.createElement("span");
      detail.textContent = entry.local_path || entry.hotlink_url || entry.local_directory || (entry.fallback ? ("fallback: " + entry.fallback) : entry.need_id);
      main.appendChild(detail);
      item.appendChild(main);

      var status = document.createElement("span");
      var label = entry.inspection_level === "pixel_inspected" ? "pixel-verified"
        : entry.inspection_level === "metadata_only" ? "hotlink only"
        : entry.disposition === "adaptable_source" ? "component fetched"
        : entry.disposition === "custom_implementation_required" ? "dependency blocked"
        : entry.kind === "icon" ? "icon resolved"
        : "materialization failed";
      var statusClass = entry.inspection_level || entry.disposition === "adaptable_source" || entry.kind === "icon" ? "ok"
        : entry.disposition === "custom_implementation_required" ? "warn"
        : "fail";
      status.className = "resource-status " + statusClass;
      status.textContent = label;
      item.appendChild(status);

      resourceList.appendChild(item);
    });
  }

  var events = document.getElementById("events");
  (data.events || []).forEach(function (event) { var item = document.createElement("li"); var time = document.createElement("time"); time.textContent = event.timestamp || ""; item.appendChild(time); var message = document.createElement("span"); message.className = event.level || "info"; message.textContent = (event.stage || "") + " · " + (event.message || ""); item.appendChild(message); events.appendChild(item); });
  document.getElementById("raw").textContent = JSON.stringify(data, null, 2);
  document.getElementById("copy").addEventListener("click", async function () { await navigator.clipboard.writeText(JSON.stringify(data, null, 2)); this.textContent = "Copied"; });
})();
