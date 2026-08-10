(function () {
  "use strict";

  var root = window.location.pathname.split("/build-preparation-fixture")[0] || "";
  var runButtons = [document.getElementById("run-fixture"), document.getElementById("run-console")];
  var status = document.getElementById("fixture-status");
  var output = document.getElementById("fixture-output");
  var summary = document.getElementById("fixture-summary");
  var jsonInput = document.getElementById("fixture-json");
  var fileInput = document.getElementById("fixture-file");
  var inputState = document.getElementById("input-state");
  var inputSize = document.getElementById("input-size");
  var eventLog = document.getElementById("event-log");
  var copyButton = document.getElementById("copy-result");
  var downloadButton = document.getElementById("download-result");
  var persistenceNote = document.getElementById("persistence-note");
  var lastResponse = null;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function logEvent(kind, message) {
    var row = el("div");
    row.appendChild(el("span", "", kind));
    row.appendChild(document.createTextNode(message));
    eventLog.appendChild(row);
    eventLog.scrollTop = eventLog.scrollHeight;
  }

  function setSummary(index, value) {
    var cards = summary.querySelectorAll(".summary-card");
    if (cards[index]) cards[index].querySelector("strong").textContent = value;
  }

  function panel(title) {
    var node = el("section", "result-panel");
    node.appendChild(el("h3", "", title));
    return node;
  }

  function updateInputMeta() {
    var value = jsonInput.value.trim();
    if (!value) {
      inputState.textContent = "Using checked-in fixture";
      inputSize.textContent = "No browser-provided input";
      return;
    }
    inputState.textContent = "Browser-provided JSON";
    inputSize.textContent = value.length.toLocaleString() + " characters ready";
  }

  function setRunning(running) {
    runButtons.forEach(function (button) {
      if (button) button.disabled = running;
    });
  }

  function renderResult(data) {
    lastResponse = data;
    setSummary(0, data.input.visual_status || "Loaded");
    setSummary(1, String((data.blueprint.route_map || []).length) + " route");
    setSummary(2, String((data.manifest.entries || []).length) + " entries");
    setSummary(3, data.bundle ? "Stored" : "Built");
    output.textContent = "";

    var grid = el("div", "result-grid");
    var routePanel = panel("Experience map");
    var routeList = el("ul");
    (data.blueprint.route_map || []).forEach(function (route) {
      var sceneCount = (route.scenes || []).length;
      routeList.appendChild(el("li", "", (route.path || route.route_id) + " · " + sceneCount + " scenes"));
    });
    routePanel.appendChild(routeList);
    grid.appendChild(routePanel);

    var resourcePanel = panel("Resource decisions");
    var resourceList = el("ul");
    (data.manifest.entries || []).forEach(function (entry) {
      resourceList.appendChild(el("li", "", entry.manifest_resource_id + " — " + entry.disposition));
    });
    resourcePanel.appendChild(resourceList);
    grid.appendChild(resourcePanel);

    var warningPanel = panel("Warnings and fallbacks");
    var warningList = el("ul", "warning-list");
    (data.warnings || []).forEach(function (warning) {
      warningList.appendChild(el("li", "", warning));
    });
    if (!warningList.children.length) warningList.appendChild(el("li", "", "No warnings"));
    warningPanel.appendChild(warningList);
    grid.appendChild(warningPanel);

    var bundlePanel = panel("Bundle receipt");
    var receipt = {
      sha256: data.bundle_sha256 || "",
      size_bytes: data.bundle_size || 0,
      object_key: data.bundle ? data.bundle.object_key : "memory fixture store",
      expires_at: data.bundle ? data.bundle.expires_at : "process lifetime",
      publishable: data.publishable
    };
    bundlePanel.appendChild(el("pre", "", JSON.stringify(receipt, null, 2)));
    grid.appendChild(bundlePanel);
    output.appendChild(grid);

    var rawDetails = document.createElement("details");
    rawDetails.className = "result-panel";
    rawDetails.style.marginTop = "1rem";
    rawDetails.appendChild(el("summary", "", "Inspect complete response JSON"));
    rawDetails.appendChild(el("pre", "", JSON.stringify(data, null, 2)));
    output.appendChild(rawDetails);

    copyButton.disabled = false;
    downloadButton.disabled = false;
    persistenceNote.textContent = data.bundle ? "Bundle metadata saved; fixture input and response are not persisted." : "Response is in memory only; no bundle object was stored.";
  }

  function renderError(error, responseData) {
    lastResponse = responseData || null;
    output.textContent = "";
    var errorPanel = panel("Preparation error");
    errorPanel.appendChild(el("p", "", error.message || "The fixture could not be prepared."));
    if (error.code) errorPanel.appendChild(el("pre", "", JSON.stringify({ code: error.code, details: error.details || {} }, null, 2)));
    output.appendChild(errorPanel);
    copyButton.disabled = !lastResponse;
    downloadButton.disabled = !lastResponse;
    persistenceNote.textContent = "No successful package was saved.";
  }

  function currentRequestBody() {
    var value = jsonInput.value.trim();
    if (!value) return {};
    var parsed;
    try {
      parsed = JSON.parse(value);
    } catch (error) {
      error.code = "LOCAL_JSON_INVALID";
      throw error;
    }
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
      var shapeError = new Error("Input must be a JSON object containing the complete Visual Design output.");
      shapeError.code = "LOCAL_JSON_INVALID";
      throw shapeError;
    }
    return { output: parsed };
  }

  async function run() {
    setRunning(true);
    status.textContent = "Compiling fixture…";
    output.textContent = "Compiling the supplied output into a deterministic preparation package…";
    try {
      var body = currentRequestBody();
      logEvent("request", body.output ? "Sending browser-provided JSON." : "Using the checked-in fixture file.");
      var response = await fetch(root + "/api/v1/build-preparation/fixture/run", {
        method: "POST",
        headers: { "Accept": "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      var data = await response.json();
      logEvent(response.ok ? "success" : "error", "HTTP " + response.status + " returned.");
      if (!response.ok) {
        var apiError = data && data.error ? data.error : {};
        var failure = new Error(apiError.message || "Fixture preparation failed.");
        failure.code = apiError.code || "FIXTURE_FAILED";
        failure.details = apiError.details || {};
        throw failure;
      }
      status.textContent = "Package ready · fixture only";
      renderResult(data);
      logEvent("bundle", data.bundle ? "Temporary object reference verified." : "Bundle built without object storage.");
    } catch (error) {
      status.textContent = "Needs attention";
      logEvent("error", error.message || "The fixture could not be prepared.");
      renderError(error);
    } finally {
      setRunning(false);
    }
  }

  async function copyResponse() {
    if (!lastResponse) return;
    var value = JSON.stringify(lastResponse, null, 2);
    try {
      await navigator.clipboard.writeText(value);
      logEvent("copied", "Response JSON copied to the clipboard.");
    } catch (error) {
      logEvent("error", "Clipboard access was unavailable; use Download response JSON.");
    }
  }

  function downloadResponse() {
    if (!lastResponse) return;
    var blob = new Blob([JSON.stringify(lastResponse, null, 2)], { type: "application/json" });
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "build-preparation-fixture-result.json";
    link.click();
    window.setTimeout(function () { URL.revokeObjectURL(link.href); }, 1000);
    logEvent("saved", "Response JSON downloaded locally.");
  }

  fileInput.addEventListener("change", function () {
    var file = fileInput.files && fileInput.files[0];
    if (!file) return;
    file.text().then(function (text) {
      jsonInput.value = text;
      updateInputMeta();
      logEvent("input", file.name + " loaded into the editor.");
    }).catch(function () {
      logEvent("error", "The selected file could not be read.");
    });
  });
  jsonInput.addEventListener("input", updateInputMeta);
  document.getElementById("use-default-fixture").addEventListener("click", function () {
    jsonInput.value = "";
    fileInput.value = "";
    updateInputMeta();
    logEvent("input", "Switched back to the checked-in fixture.");
  });
  runButtons.forEach(function (button) {
    if (button) button.addEventListener("click", run);
  });
  copyButton.addEventListener("click", copyResponse);
  downloadButton.addEventListener("click", downloadResponse);
  updateInputMeta();
})();
