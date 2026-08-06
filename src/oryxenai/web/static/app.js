/* OryxenAI developer harness — vanilla JS, no libraries.
 * Renders dynamic values with textContent and never stores resume text in
 * browser storage. */

(function () {
  "use strict";

  var API = "/api/v1";
  var selectedSessionId = null;

   function prettyJson(obj) {
     try {
       return JSON.stringify(obj, null, 2);
     } catch (e) {
       return String(obj);
     }
   }

   function clearElement(el) {
     while (el && el.firstChild) el.removeChild(el.firstChild);
   }

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function setResult(id, msg, kind) {
    var el = document.getElementById(id);
    if (!el) return;
    el.textContent = msg;
    el.className = "result" + (kind ? " " + kind : "");
  }

  function setPill(id, status) {
    var el = document.getElementById(id);
    if (!el) return;
    el.className = "status pill " + status;
    el.textContent = status === "ok" ? "up" : status === "err" ? "down" : "checking…";
  }

  async function fetchJson(url, opts) {
    var resp = await fetch(url, opts);
    var body = null;
    var ct = resp.headers.get("content-type") || "";
    if (ct.indexOf("application/json") >= 0) {
      body = await resp.json();
    } else {
      body = await resp.text();
    }
    if (!resp.ok) {
      var msg = (body && body.error && body.error.message) || resp.statusText;
      throw { status: resp.status, message: msg, body: body };
    }
    return body;
  }

  async function checkHealth() {
    setPill("health-live", "unknown");
    setPill("health-ready", "unknown");
    try {
      await fetchJson("/health/live");
      setPill("health-live", "ok");
    } catch (e) {
      setPill("health-live", "err");
    }
    try {
      await fetchJson("/health/ready");
      setPill("health-ready", "ok");
    } catch (e) {
      setPill("health-ready", "err");
    }
  }

  async function loadAgents() {
    try {
      var agents = await fetchJson(API + "/agents");
      var select = document.getElementById("agent-select");
       clearElement(select);
      agents.forEach(function (a) {
        var opt = document.createElement("option");
        opt.value = a.key;
        opt.textContent = a.name + " — " + a.description;
        select.appendChild(opt);
      });
    } catch (e) {
       setResult("run-result", "Failed to load agents: " + e.message, "error");
    }
  }

  async function createSession() {
    var name = document.getElementById("session-name").value.trim();
    setResult("create-result", "Creating…");
    try {
      var body = name ? { name: name } : {};
      var session = await fetchJson(API + "/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setResult("create-result", "Created session: " + session.id, "success");
      selectedSessionId = session.id;
       showSession(session);
       enableRunControls();
       loadDiscovery();
      await listRuns();
      await listSessions();
    } catch (e) {
       setResult("create-result", "Error: " + e.message, "error");
    }
  }

  function showSession(session) {
    var box = document.getElementById("current-session");
    box.hidden = false;
    setText("cs-id", session.id);
    setText("cs-name", session.name);
    setText("cs-status", session.status);
    setText("cs-revision", session.revision);
    var stateEl = document.getElementById("cs-state");
    stateEl.textContent = JSON.stringify(session.current_state, null, 2);
  }

  async function listSessions() {
    var list = document.getElementById("session-list");
     clearElement(list);
    try {
      var sessions = await fetchJson(API + "/sessions");
      if (!sessions.length) {
        var li = document.createElement("li");
        li.className = "empty";
        li.textContent = "No sessions yet.";
        list.appendChild(li);
        return;
      }
      sessions.forEach(function (s) {
        var li = document.createElement("li");
        li.textContent = s.name + " — " + s.id.substring(0, 8) + "… (rev " + s.revision + ")";
        li.addEventListener("click", function () {
          selectedSessionId = s.id;
           showSession(s);
           enableRunControls();
           listRuns();
           loadDiscovery();
        });
        list.appendChild(li);
      });
    } catch (e) {
      var errLi = document.createElement("li");
      errLi.className = "empty";
       errLi.textContent = "Error: " + e.message;
      list.appendChild(errLi);
    }
  }

  function enableRunControls() {
    document.getElementById("btn-run-mock").disabled = false;
    document.getElementById("btn-list-runs").disabled = false;
    document.getElementById("btn-discovery-intake").disabled = false;
  }

  async function runMock() {
    if (!selectedSessionId) {
      setResult("run-result", "Select or create a session first.", "error");
      return;
    }
    var agentKey = document.getElementById("agent-select").value;
    if (!agentKey) {
      setResult("run-result", "Select an agent.", "error");
      return;
    }
    var inputText = document.getElementById("input-json").value.trim() || "{}";
    var inputObj;
    try {
      inputObj = JSON.parse(inputText);
    } catch (e) {
      setResult("run-result", "Invalid JSON input.", "error");
      return;
    }
    var idempKey = document.getElementById("idempotency-key").value.trim() || null;

    setResult("run-result", "Running mock…");
    try {
      var body = {
        agentKey: agentKey,
        input: inputObj,
      };
      if (idempKey) body.idempotencyKey = idempKey;
      var run = await fetchJson(API + "/sessions/" + selectedSessionId + "/runs/mock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      showRunDetail(run);
      setResult("run-result", "Run " + run.status + ": " + run.id, run.status === "succeeded" ? "success" : "error");
      await listRuns();
      await refreshCurrentSession();
    } catch (e) {
       setResult("run-result", "Error: " + e.message, "error");
    }
  }

  function showRunDetail(run) {
    var box = document.getElementById("run-detail");
    box.hidden = false;
    setText("rd-id", run.id);
    setText("rd-agent", run.agent_key);
    setText("rd-status", run.status);
    setText("rd-attempt", run.attempt);
    var outEl = document.getElementById("rd-output");
    outEl.textContent = JSON.stringify(run.output_payload, null, 2);
    var saEl = document.getElementById("rd-state-after");
    saEl.textContent = JSON.stringify(run.state_after, null, 2);
  }

  async function listRuns() {
    if (!selectedSessionId) return;
    var list = document.getElementById("run-list");
     clearElement(list);
    try {
      var runs = await fetchJson(API + "/sessions/" + selectedSessionId + "/runs");
      if (!runs.length) {
        var li = document.createElement("li");
        li.className = "empty";
        li.textContent = "No runs yet.";
        list.appendChild(li);
        return;
      }
      runs.forEach(function (r) {
        var li = document.createElement("li");
        li.textContent = r.agent_key + " — " + r.status + " — " + r.id.substring(0, 8) + "…";
        list.appendChild(li);
      });
    } catch (e) {
      var errLi = document.createElement("li");
      errLi.className = "empty";
      errLi.textContent = "Error: " + e.message;
      list.appendChild(errLi);
    }
  }

  async function refreshCurrentSession() {
    if (!selectedSessionId) return;
    try {
      var session = await fetchJson(API + "/sessions/" + selectedSessionId);
      showSession(session);
    } catch (e) { /* ignore */ }
  }

  // ── Infrastructure diagnostics ────────────────────────────────────────

  var probeJobId = null;

  async function loadSystemStatus() {
    try {
      var status = await fetchJson(API + "/system/status");
      setPill("worker-status", status.worker === "ok" ? "ok" : status.worker === "stale" ? "warn" : "err");
      setText("mig-revision", status.migration_revision);
      setText("hb-age", status.latest_heartbeat_age != null ? status.latest_heartbeat_age.toFixed(1) + " s" : "—");
      setText("worker-instance", status.worker_instance || "—");
    } catch (e) {
      setPill("worker-status", "err");
      setText("mig-revision", "—");
    }
  }

  async function enqueueProbe() {
    setResult("probe-status", "Enqueuing…");
    document.getElementById("probe-detail").hidden = true;
    try {
      var job = await fetchJson(API + "/system/worker-probes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_kind: "system.worker_probe", payload: { message: "harness-probe" }, idempotency_key: Date.now().toString() }),
      });
      probeJobId = job.id;
      setText("probe-id", job.id.substring(0, 12) + "…");
      setResult("probe-status", "Probe enqueued: " + job.status, "success");
      pollProbe();
    } catch (e) {
       setResult("probe-status", "Error: " + e.message, "error");
    }
  }

  async function pollProbe() {
    if (!probeJobId) return;
    try {
      var job = await fetchJson(API + "/system/worker-probes/" + probeJobId);
      setText("pj-id", job.id);
      setText("pj-status", job.status);
      setText("pj-attempt", job.attempt);
      setText("pj-worker", job.worker_instance || "—");
      var resultEl = document.getElementById("pj-result");
      resultEl.textContent = JSON.stringify(job.result || job.error || {}, null, 2);
      document.getElementById("probe-detail").hidden = false;
      if (job.status === "succeeded") {
        setResult("probe-status", "Probe succeeded on attempt " + job.attempt, "success");
      } else if (job.status === "failed") {
        setResult("probe-status", "Probe failed: " + (job.error && job.error.message || "unknown"), "error");
      } else {
        setResult("probe-status", "Probe " + job.status + " (attempt " + job.attempt + ")");
        setTimeout(pollProbe, 1500);
      }
    } catch (e) {
       setResult("probe-status", "Error polling: " + e.message, "error");
    }
  }

  // ── Discovery flow ─────────────────────────────────────────────────────

  var discoveryState = null;
  var discoveryLinks = [];
  var discoveryIndex = 0;
  var discoveryPollTimer = null;

  function discoveryResult() {
    return discoveryState && discoveryState.discovery ? discoveryState.discovery : null;
  }

  function setDiscoveryStatus(message, kind) {
    setResult("discovery-status", message, kind);
  }

  function setDiscoveryVisible(id, visible) {
    var el = document.getElementById(id);
    if (el) el.hidden = !visible;
  }

  function discoveryInputsFromServer(data) {
    var intake = data && data.intake;
    if (!intake) return;
    document.getElementById("discovery-prompt").value = intake.main_prompt || "";
    document.getElementById("discovery-resume").value = intake.resume_text || "";
    document.getElementById("discovery-language").value = intake.output_language || "en";
    document.getElementById("discovery-resume-source").value = intake.resume_source || "none";
    discoveryLinks = Array.isArray(intake.links) ? intake.links.slice() : [];
    renderDiscoveryLinks();
  }

  async function loadDiscovery() {
    if (!selectedSessionId) return;
    try {
      var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery");
      discoveryState = data;
      discoveryInputsFromServer(data);
      renderDiscoveryState();
      sessionStorage.setItem("oryxenai.discovery.session", selectedSessionId);
    } catch (e) {
      setDiscoveryStatus("Discovery state unavailable: " + e.message, "error");
    }
  }

  function renderDiscoveryLinks() {
    var list = document.getElementById("discovery-link-list");
    clearElement(list);
    discoveryLinks.forEach(function (link, index) {
      var item = document.createElement("li");
      item.textContent = (link.label || link.kind || "link") + " — " + link.url;
      var remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Remove";
      remove.addEventListener("click", function () {
        discoveryLinks.splice(index, 1);
        renderDiscoveryLinks();
      });
      item.appendChild(remove);
      list.appendChild(item);
    });
  }

  function addDiscoveryLink() {
    var rawUrl = document.getElementById("discovery-link-url").value.trim();
    if (!rawUrl) return;
    try {
      var parsed = new URL(rawUrl);
      if (parsed.protocol !== "http:" && parsed.protocol !== "https:") throw new Error("Only HTTP and HTTPS links are accepted.");
      if (discoveryLinks.some(function (link) { return link.url === parsed.toString().replace(/\/$/, ""); })) {
        setDiscoveryStatus("That link is already listed.", "error");
        return;
      }
      discoveryLinks.push({
        id: "link-" + String(Date.now()),
        url: parsed.toString().replace(/\/$/, ""),
        label: document.getElementById("discovery-link-label").value.trim() || null,
        kind: document.getElementById("discovery-link-kind").value,
      });
      document.getElementById("discovery-link-url").value = "";
      document.getElementById("discovery-link-label").value = "";
      renderDiscoveryLinks();
    } catch (e) {
      setDiscoveryStatus(e.message || "Enter a valid HTTP or HTTPS link.", "error");
    }
  }

  function discoveryIntakePayload() {
    var resume = document.getElementById("discovery-resume").value;
    return {
      expected_revision: discoveryState ? discoveryState.session_revision : 0,
      main_prompt: document.getElementById("discovery-prompt").value,
      resume_text: resume || null,
      resume_source: document.getElementById("discovery-resume-source").value,
      links: discoveryLinks,
      output_language: document.getElementById("discovery-language").value.trim() || "en",
      product_constraints: {},
      source_revision: discoveryResult() ? discoveryResult().source_revision : 0,
    };
  }

  async function saveDiscoveryInputAndQueue() {
    if (!selectedSessionId) return;
    var button = document.getElementById("btn-discovery-intake");
    button.disabled = true;
    setDiscoveryStatus("Saving intake…");
    try {
      var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/input", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(discoveryIntakePayload()),
      });
      discoveryState = data;
      setDiscoveryStatus("Intake saved. Queueing analysis…");
      var queued = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/questions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_revision: data.session_revision }),
      });
      setDiscoveryStatus("Questions " + queued.status + ". The worker is processing the request.");
      await loadDiscovery();
      pollDiscovery();
    } catch (e) {
      setDiscoveryStatus("Could not start Discovery: " + e.message, "error");
    } finally {
      button.disabled = false;
    }
  }

  function pollDiscovery() {
    if (discoveryPollTimer) window.clearTimeout(discoveryPollTimer);
    if (!selectedSessionId) return;
    var state = discoveryResult();
    if (state && ["questions_ready", "answers_in_progress", "answers_ready", "brief_review", "approved", "needs_attention"].indexOf(state.status) >= 0) {
      renderDiscoveryState();
      return;
    }
    discoveryPollTimer = window.setTimeout(async function () {
      await loadDiscovery();
      pollDiscovery();
    }, 1200);
  }

  function renderDiscoveryState() {
    var state = discoveryResult();
    if (!state) return;
    var status = state.status;
    setText("discovery-resume-status", state.latest_error ? state.latest_error.message : (status === "input_ready" ? "Input ready for analysis." : ""));
    setDiscoveryVisible("discovery-questions", false);
    setDiscoveryVisible("discovery-zero", false);
    setDiscoveryVisible("discovery-brief", false);
    if (status === "needs_attention") {
      setDiscoveryStatus((state.latest_error && state.latest_error.message) || "Discovery needs attention.", "error");
    } else if (status === "questions_queued" || status === "questions_running" || status === "brief_queued" || status === "brief_running") {
      setDiscoveryStatus("Discovery is " + status.replaceAll("_", " ") + "…");
    } else if (status === "questions_ready" || status === "answers_in_progress" || status === "answers_ready") {
      var questions = state.questions && state.questions.items ? state.questions.items : [];
      if (!questions.length) {
        setDiscoveryVisible("discovery-zero", true);
        setText("discovery-profile-summary", prettyJson(discoveryState.analysis && discoveryState.analysis.normalized_profile || {}));
        setDiscoveryStatus("Analysis complete. Review the summary before creating a brief.", "success");
      } else {
        setDiscoveryVisible("discovery-questions", true);
        renderDiscoveryQuestion();
        setDiscoveryStatus("Answer the focused questions. No model call happens between questions.", "success");
      }
    } else if (status === "brief_review" || status === "approved") {
      setDiscoveryVisible("discovery-brief", true);
      renderDiscoveryBrief();
      setDiscoveryStatus(status === "approved" ? "Discovery approved." : "Review the strategic brief, then click NEXT.", status === "approved" ? "success" : "success");
    } else {
      setDiscoveryStatus("Add an intake to begin Discovery.");
    }
  }

  function currentDiscoveryQuestion() {
    var state = discoveryResult();
    return state && state.questions && state.questions.items ? state.questions.items[discoveryIndex] : null;
  }

  function currentDiscoveryAnswer(question) {
    var state = discoveryResult();
    return state && state.answers && state.answers.items ? state.answers.items[question.local_key] : null;
  }

  function renderDiscoveryQuestion() {
    var state = discoveryResult();
    var questions = state && state.questions ? state.questions.items : [];
    if (!questions.length) return;
    discoveryIndex = Math.max(0, Math.min(discoveryIndex, questions.length - 1));
    var question = questions[discoveryIndex];
    var answer = currentDiscoveryAnswer(question);
    setText("discovery-question-progress", "Question " + (discoveryIndex + 1) + " of " + questions.length);
    var body = document.getElementById("discovery-question-body");
    clearElement(body);
    var heading = document.createElement("h4");
    heading.textContent = question.text;
    body.appendChild(heading);
    if (question.help_text) {
      var help = document.createElement("p");
      help.className = "help-text";
      help.textContent = question.help_text;
      body.appendChild(help);
    }
    var value = answer ? answer.value : null;
    if (question.kind === "single_select") {
      question.options.forEach(function (option) {
        body.appendChild(questionChoice(question, option, value, "radio"));
      });
    } else if (question.kind === "multi_select") {
      question.options.forEach(function (option) {
        body.appendChild(questionChoice(question, option, value || [], "checkbox"));
      });
    } else if (question.kind === "boolean") {
      var bool = document.createElement("input");
      bool.type = "checkbox";
      bool.id = "discovery-answer-boolean";
      bool.checked = value === true;
      body.appendChild(bool);
      var boolLabel = document.createElement("label");
      boolLabel.htmlFor = bool.id;
      boolLabel.textContent = "Yes";
      body.appendChild(boolLabel);
    } else {
      var field = document.createElement(question.kind === "long_text" ? "textarea" : "input");
      field.id = "discovery-answer-text";
      field.maxLength = 10000;
      field.value = value == null ? "" : String(value);
      if (question.kind === "long_text") field.rows = 6;
      body.appendChild(field);
    }
    setDiscoveryVisible("btn-discovery-auto", !!question.allows_auto);
    setDiscoveryVisible("btn-discovery-skip", !!question.allows_skip);
    document.getElementById("btn-discovery-back").disabled = discoveryIndex === 0;
    document.getElementById("btn-discovery-create-brief").hidden = state.status !== "answers_ready";
  }

  function questionChoice(question, option, value, type) {
    var label = document.createElement("label");
    label.className = "question-option";
    var input = document.createElement("input");
    input.type = type;
    input.name = "discovery-answer-" + question.local_key;
    input.value = option.id;
    input.checked = type === "checkbox" ? Array.isArray(value) && value.indexOf(option.id) >= 0 : value === option.id;
    label.appendChild(input);
    var text = document.createElement("span");
    text.textContent = option.label;
    label.appendChild(text);
    return label;
  }

  function readDiscoveryValue(question) {
    if (question.kind === "single_select") {
      var selected = document.querySelector("input[name='discovery-answer-" + question.local_key + "']:checked");
      return selected ? selected.value : null;
    }
    if (question.kind === "multi_select") {
      return Array.prototype.slice.call(document.querySelectorAll("input[name='discovery-answer-" + question.local_key + "']:checked")).map(function (input) { return input.value; });
    }
    if (question.kind === "boolean") return document.getElementById("discovery-answer-boolean").checked;
    return document.getElementById("discovery-answer-text").value;
  }

  function answerListWith(question, answer) {
    var map = {};
    var existing = discoveryResult() && discoveryResult().answers ? discoveryResult().answers.items : {};
    Object.keys(existing || {}).forEach(function (key) { map[key] = existing[key]; });
    map[question.local_key] = answer;
    return Object.keys(map).map(function (key) { return map[key]; });
  }

  async function saveDiscoveryAnswers(answer, complete) {
    var state = discoveryResult();
    var question = currentDiscoveryQuestion();
    if (!state || !question) return false;
    try {
      var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/answers", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          expected_revision: discoveryState.session_revision,
          question_version: state.questions.version,
          complete: complete,
          answers: answerListWith(question, answer),
        }),
      });
      discoveryState = data;
      return true;
    } catch (e) {
      setDiscoveryStatus("Could not save answer: " + e.message, "error");
      await loadDiscovery();
      return false;
    }
  }

  async function nextDiscoveryQuestion() {
    var question = currentDiscoveryQuestion();
    if (!question) return;
    var value = readDiscoveryValue(question);
    var answer = { question_id: question.local_key, mode: "answered", value: value, answer_revision: 0 };
    var complete = discoveryIndex === discoveryResult().questions.items.length - 1;
    if (await saveDiscoveryAnswers(answer, complete)) {
      if (!complete) {
        discoveryIndex += 1;
        renderDiscoveryQuestion();
      } else {
        setDiscoveryStatus("Answers saved. Create the brief when ready.", "success");
        renderDiscoveryState();
      }
    }
  }

  async function chooseDiscoveryAuto() {
    var question = currentDiscoveryQuestion();
    if (!question || !question.allows_auto) return;
    await saveDiscoveryAnswers({ question_id: question.local_key, mode: "auto", value: question.auto_answer, answer_revision: 0 }, discoveryIndex === discoveryResult().questions.items.length - 1);
    renderDiscoveryQuestion();
  }

  async function skipDiscoveryQuestion() {
    var question = currentDiscoveryQuestion();
    if (!question || !question.allows_skip) return;
    var complete = discoveryIndex === discoveryResult().questions.items.length - 1;
    if (await saveDiscoveryAnswers({ question_id: question.local_key, mode: "skipped", value: null, answer_revision: 0 }, complete)) {
      if (!complete) { discoveryIndex += 1; renderDiscoveryQuestion(); } else { renderDiscoveryState(); }
    }
  }

  async function autofillDiscovery() {
    var state = discoveryResult();
    if (!state) return;
    var answers = state.answers.items || {};
    var completeAnswers = Object.keys(answers).map(function (key) { return answers[key]; });
    for (var index = 0; index < state.questions.items.length; index += 1) {
      var question = state.questions.items[index];
      if (answers[question.local_key]) continue;
      if (question.allows_auto) completeAnswers.push({ question_id: question.local_key, mode: "auto", value: question.auto_answer, answer_revision: 0 });
      else if (question.allows_skip) completeAnswers.push({ question_id: question.local_key, mode: "skipped", value: null, answer_revision: 0 });
    }
    try {
      discoveryState = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/answers", {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_revision: discoveryState.session_revision, question_version: state.questions.version, complete: true, answers: completeAnswers }),
      });
      setDiscoveryStatus("Remaining presentation choices were automated; factual gaps were skipped.", "success");
      renderDiscoveryState();
    } catch (e) { setDiscoveryStatus("Could not auto-fill answers: " + e.message, "error"); }
  }

  async function enqueueDiscoveryBrief() {
    if (!discoveryState) return;
    try {
      var queued = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/brief", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_revision: discoveryState.session_revision }),
      });
      setDiscoveryStatus("Brief " + queued.status + ". Waiting for the worker…");
      pollDiscovery();
    } catch (e) { setDiscoveryStatus("Could not create brief: " + e.message, "error"); }
  }

  function renderDiscoveryBrief() {
    var state = discoveryResult();
    var brief = state && state.brief ? state.brief.draft : null;
    if (!brief) return;
    var idg = brief.identity_and_goal || {};
    var pos = brief.positioning_strategy || {};
    var cs = brief.content_strategy || {};
    var pd = brief.presentation_direction || {};
    var cc = brief.cta_and_contact || {};
    document.getElementById("discovery-brief-role").value = idg.primary_target_role ? idg.primary_target_role.label || "" : "";
    document.getElementById("discovery-brief-audience").value = (idg.audiences || []).map(function (a) { return a.label || a; }).join(", ");
    document.getElementById("discovery-brief-goal").value = idg.portfolio_goal ? idg.portfolio_goal.summary || "" : "";
    document.getElementById("discovery-brief-positioning").value = pos.positioning_direction || "";
    document.getElementById("discovery-brief-tone").value = pd.tone ? pd.tone.value || "" : "";
    document.getElementById("discovery-brief-theme").value = pd.theme_preference ? pd.theme_preference.value || "" : "";
    document.getElementById("discovery-brief-motion").value = pd.motion_preference ? pd.motion_preference.value || "" : "";
    document.getElementById("discovery-brief-cta").value = cc.primary_cta_intent || "";
    document.getElementById("discovery-brief-projects").value = (cs.featured_projects || []).map(function (p) { return p.project_id || ""; }).join("\n");
    document.getElementById("discovery-brief-emphasize").value = (cs.capability_clusters || []).map(function (c) { return c.label || ""; }).join("\n");
    document.getElementById("discovery-brief-omit").value = (cs.items_to_omit || []).map(function (o) { return o.item || o.reason || ""; }).join("\n");
    document.getElementById("discovery-brief-json").textContent = prettyJson({
      confidentiality: brief.confidentiality_and_omissions || {},
      unresolved_items: brief.unresolved_items || [],
      claim_policy: brief.claim_policy || {},
      warnings: brief.warnings || [],
    });
    var approved = state.status === "approved";
    document.getElementById("discovery-brief-notice").textContent = approved ? "Discovery approved. This is the immutable approved snapshot." : "Manual edits are recorded as user-provided provenance.";
    document.getElementById("btn-discovery-approve").disabled = approved;
  }

  function discoveryBriefEdits() {
    var state = discoveryResult();
    var old = state.brief.draft;
    var idg = old.identity_and_goal || {};
    var pd = old.presentation_direction || {};
    var cs = old.content_strategy || {};
    var cc = old.cta_and_contact || {};
    return {
      identity_and_goal: {
        primary_target_role: Object.assign({}, idg.primary_target_role || {}, { label: document.getElementById("discovery-brief-role").value, decision_source: "user_edit" }),
        audiences: document.getElementById("discovery-brief-audience").value.split(",").map(function (item) { return { label: item.trim(), priority: "primary" }; }).filter(function (a) { return a.label; }),
        portfolio_goal: Object.assign({}, idg.portfolio_goal || {}, { summary: document.getElementById("discovery-brief-goal").value, basis: "user_edit" }),
        secondary_strengths: (idg.secondary_strengths || []),
        career_stage: (idg.career_stage || {}),
      },
      positioning_strategy: Object.assign({}, old.positioning_strategy || {}, { positioning_direction: document.getElementById("discovery-brief-positioning").value }),
      presentation_direction: Object.assign({}, pd, {
        tone: Object.assign({}, pd.tone || {}, { value: document.getElementById("discovery-brief-tone").value, source: "user_edit" }),
        theme_preference: Object.assign({}, pd.theme_preference || {}, { value: document.getElementById("discovery-brief-theme").value, source: "user_edit" }),
        motion_preference: Object.assign({}, pd.motion_preference || {}, { value: document.getElementById("discovery-brief-motion").value, source: "user_edit" }),
      }),
      cta_and_contact: Object.assign({}, cc, { primary_cta_intent: document.getElementById("discovery-brief-cta").value || "" }),
      content_strategy: Object.assign({}, cs, {
        featured_projects: document.getElementById("discovery-brief-projects").value.split("\n").filter(Boolean).map(function (line) { return Object.assign({}, (cs.featured_projects || [])[0] || {}, { project_id: line.trim() }); }),
        capability_clusters: document.getElementById("discovery-brief-emphasize").value.split("\n").filter(Boolean).map(function (line) { return Object.assign({}, (cs.capability_clusters || [])[0] || {}, { label: line.trim() }); }),
        items_to_omit: document.getElementById("discovery-brief-omit").value.split("\n").filter(Boolean).map(function (line) { return Object.assign({}, (cs.items_to_omit || [])[0] || {}, { item: line.trim() }); }),
      }),
    };
  }

  async function saveDiscoveryBriefEdits() {
    try {
      discoveryState = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/brief", {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_revision: discoveryState.session_revision, edits: discoveryBriefEdits() }),
      });
      setDiscoveryStatus("Brief edits saved. Approval is invalidated until NEXT is clicked again.", "success");
      renderDiscoveryBrief();
    } catch (e) { setDiscoveryStatus("Could not save brief edits: " + e.message, "error"); }
  }

  async function approveDiscovery() {
    try {
      discoveryState = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/approve", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_revision: discoveryState.session_revision }),
      });
      setDiscoveryStatus("Discovery approved. No later agent was started.", "success");
      renderDiscoveryState();
    } catch (e) { setDiscoveryStatus("Approval failed: " + e.message, "error"); }
  }

  document.addEventListener("DOMContentLoaded", function () {
    checkHealth();
    loadAgents();
    listSessions();
    loadSystemStatus();
    setInterval(loadSystemStatus, 15000);

    document.getElementById("btn-create-session").addEventListener("click", createSession);
    document.getElementById("btn-list-sessions").addEventListener("click", listSessions);
    document.getElementById("btn-run-mock").addEventListener("click", runMock);
    document.getElementById("btn-list-runs").addEventListener("click", listRuns);
     document.getElementById("btn-probe").addEventListener("click", enqueueProbe);
     document.getElementById("btn-add-discovery-link").addEventListener("click", addDiscoveryLink);
     document.getElementById("btn-discovery-intake").addEventListener("click", saveDiscoveryInputAndQueue);
     document.getElementById("btn-discovery-back").addEventListener("click", function () {
       discoveryIndex = Math.max(0, discoveryIndex - 1);
       renderDiscoveryQuestion();
     });
     document.getElementById("btn-discovery-next").addEventListener("click", nextDiscoveryQuestion);
     document.getElementById("btn-discovery-auto").addEventListener("click", chooseDiscoveryAuto);
     document.getElementById("btn-discovery-skip").addEventListener("click", skipDiscoveryQuestion);
     document.getElementById("btn-discovery-autofill").addEventListener("click", autofillDiscovery);
     document.getElementById("btn-discovery-create-brief").addEventListener("click", enqueueDiscoveryBrief);
     document.getElementById("btn-discovery-zero-brief").addEventListener("click", async function () {
       var state = discoveryResult();
       if (state && state.status === "questions_ready") {
         try {
           discoveryState = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/answers", {
             method: "PUT", headers: { "Content-Type": "application/json" },
             body: JSON.stringify({ expected_revision: discoveryState.session_revision, question_version: state.questions.version, complete: true, answers: [] }),
           });
         } catch (e) { setDiscoveryStatus("Could not continue: " + e.message, "error"); return; }
       }
       enqueueDiscoveryBrief();
     });
     document.getElementById("btn-discovery-change-answers").addEventListener("click", function () {
       discoveryIndex = 0;
       setDiscoveryVisible("discovery-brief", false);
       setDiscoveryVisible("discovery-questions", true);
       renderDiscoveryQuestion();
     });
     document.getElementById("btn-discovery-regenerate").addEventListener("click", enqueueDiscoveryBrief);
     document.getElementById("btn-discovery-save-brief").addEventListener("click", saveDiscoveryBriefEdits);
     document.getElementById("btn-discovery-approve").addEventListener("click", approveDiscovery);

     var rememberedSession = sessionStorage.getItem("oryxenai.discovery.session");
     if (rememberedSession) {
       fetchJson(API + "/sessions/" + rememberedSession).then(function (session) {
         selectedSessionId = session.id;
         showSession(session);
         enableRunControls();
         return loadDiscovery();
       }).catch(function () { sessionStorage.removeItem("oryxenai.discovery.session"); });
     }
  });
})();
