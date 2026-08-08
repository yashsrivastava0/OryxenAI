/* OryxenAI — chat-first Discovery UI, vanilla JS, no libraries.
 * Renders dynamic values with textContent and never stores resume text in
 * browser storage. */

(function () {
  "use strict";

  var API = "/api/v1";
  var selectedSessionId = null;
  var chatState = null;       // state.discovery from the last poll
  var lastIntake = null;      // {message, document_text, goal} for retries
  var chatQIndex = 0;         // current question index in the chat
  var chatAnswers = {};       // local map question_id -> {question_id, mode, value}
  var pollTimer = null;
  var elapsedTimer = null;
  var chatStartedAt = null;
  var analyzingBubbleId = null;
  var answeringQuestionId = null;
  var awaitingNextAgentConfirmation = null; // {startFn, label} while a "move to next agent?" prompt is active
  var selectedModelProfile = ""; // "" = default/enabled profile; other dropdown entries are disabled today

  var RUNNING_STATUSES = ["questions_queued", "questions_running", "brief_running", "answers_in_progress"];
  var TERMINAL_STATUSES = ["questions_ready", "brief_review", "approved", "needs_attention"];
  var lastRenderedOperationRunId = null;

  function prettyJson(obj) {
    try { return JSON.stringify(obj, null, 2); } catch (e) { return String(obj); }
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
    var controller = new AbortController();
    var timer = window.setTimeout(function () { controller.abort(); }, 30000);
    var requestOpts = opts || {};
    requestOpts.signal = controller.signal;
    var resp = null;
    try {
      resp = await fetch(url, requestOpts);
    } catch (e) {
      window.clearTimeout(timer);
      throw { status: 0, message: "Network error — the server did not respond.", body: null };
    }
    window.clearTimeout(timer);
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

  // ── Chat rendering ──────────────────────────────────────────────────────

  function chatEl() {
    return document.getElementById("chat-messages");
  }

  function addBubble(kind, content) {
    var bubble = document.createElement("div");
    bubble.className = "bubble " + kind;
    bubble.appendChild(content);
    chatEl().appendChild(bubble);
    chatEl().scrollTop = chatEl().scrollHeight;
    return bubble;
  }

  function textEl(text) {
    var p = document.createElement("p");
    p.className = "bubble-text";
    p.textContent = text;
    return p;
  }

  function chatWelcome() {
    var bubble = addBubble("assistant", textEl("Tell me about yourself. What should the portfolio be about? You can also attach a resume or notes."));
    bubble.id = "welcome-bubble";
  }

  function chatUser(text, meta) {
    var content = textEl(text);
    if (meta) {
      var small = document.createElement("small");
      small.className = "bubble-meta";
      small.textContent = meta;
      content.appendChild(document.createElement("br"));
      content.appendChild(small);
    }
    addBubble("user", content);
  }

  function chatAnalyzing(text) {
    var content = document.createElement("p");
    content.className = "bubble-text";
    var spinner = document.createElement("span");
    spinner.className = "spinner";
    content.appendChild(spinner);
    var label = document.createElement("span");
    label.className = "analyzing-label";
    label.textContent = text || "Analyzing your details…";
    content.appendChild(label);
    var bubble = addBubble("assistant", content);
    analyzingBubbleId = bubble.id = "analyzing-bubble";
    return bubble;
  }

  function updateAnalyzingBubble() {
    var bubble = document.getElementById("analyzing-bubble");
    if (!bubble) return;
    var label = bubble.querySelector(".analyzing-label");
    if (!label) return;
    var status = chatState ? chatState.status : "";
    var base = status === "brief_running" ? "Preparing your portfolio brief…" : "Analyzing your details…";
    var parts = [base];
    if (chatStartedAt) {
      parts.push(Math.round((Date.now() - chatStartedAt) / 1000) + "s");
    }
    if (chatState && chatState.attempt > 1) {
      parts.push("(attempt " + chatState.attempt + "/" + chatState.max_attempts + ")");
    }
    if (chatStartedAt && Date.now() - chatStartedAt > 300000) {
      label.textContent = parts.join(" — ") + " — still working…";
    } else {
      label.textContent = parts.join(" — ");
    }
  }

  function chatError(text, retryLabel, retryFn) {
    var content = textEl(text);
    content.className = "bubble-text bubble-error";
    if (retryLabel && retryFn) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "primary-action";
      button.textContent = retryLabel;
      button.addEventListener("click", function () {
        button.disabled = true;
        retryFn();
      });
      content.appendChild(document.createElement("br"));
      content.appendChild(button);
    }
    addBubble("assistant", content);
  }

  function chatDone(text) {
    addBubble("assistant", textEl(text));
  }

  // ── Chat flow ───────────────────────────────────────────────────────────

  function composerText() {
    return document.getElementById("composer").value.trim();
  }

  function setComposer(text) {
    document.getElementById("composer").value = text || "";
  }

  function disableComposer(disabled) {
    document.getElementById("composer").disabled = !!disabled;
    document.getElementById("btn-send").disabled = !!disabled;
  }

  // A short, unambiguous "this is fine as-is" message approves directly —
  // no reason to spend a model call regenerating a brief the user is happy
  // with. Anything else (a specific change, "I don't like it", vague
  // dissatisfaction) is a real revision request and goes to the same
  // /discovery/revise path as the "Ask for a revision" button.
  var APPROVAL_PATTERNS = [
    /\b(looks?|sounds?|seems?)\s+(good|great|perfect|nice|fine)\b/,
    /\b(yes|yeah|yep|yup|sure)\b/,
    /\b(it'?s|that'?s|this is)\s+(good|great|perfect|fine)\b/,
    /\b(good|great|perfect|nice|awesome|excellent)\s*[.!]*$/,
    /\bapprove(d)?\b/,
    /\blgtm\b/,
    /\b(all good|no changes?( needed)?|ready to go|go ahead|ship it|works for me|i'?m happy)\b/,
    /\b(move on|move ahead|next( step)?|let'?s (go|move|continue)|continue|proceed)\b/,
    /^(ok|okay|fine)\s*[.!]*$/,
  ];
  var APPROVAL_NEGATION = /\b(but|however|except|though|not|n't|instead|change|different|add|remove|fix|wrong|issue|problem|actually|rather)\b/;

  function looksLikeApproval(text) {
    var trimmed = text.trim();
    if (!trimmed || trimmed.length > 60) return false;
    var lower = trimmed.toLowerCase();
    if (APPROVAL_NEGATION.test(lower)) return false;
    return APPROVAL_PATTERNS.some(function (re) { return re.test(lower); });
  }

  async function sendMessage() {
    var text = composerText();
    if (!text) return;
    if (answeringQuestionId) {
      submitTextAnswer(text);
      return;
    }
    chatUser(text, null);
    setComposer("");

    if (awaitingNextAgentConfirmation) {
      if (looksLikeApproval(text)) {
        var pending = awaitingNextAgentConfirmation;
        awaitingNextAgentConfirmation = null;
        pending.startFn();
      } else {
        chatDone("No problem — let me know when you'd like to move on.");
      }
      return;
    }

    if (chatState && chatState.status === "brief_review") {
      if (looksLikeApproval(text)) {
        approveDiscovery();
      } else {
        requestRevision(text, null);
      }
      return;
    }

    if (!selectedSessionId) {
      var session = await createSessionQuiet("Portfolio chat");
      if (!session) {
        chatError("Could not create a session. Is the API running?", "Try again", sendMessageRetry);
        return;
      }
      selectedSessionId = session.id;
      sessionStorage.setItem("oryxenai.discovery.session", selectedSessionId);
      refreshSessionPanel(session);
    }

    var attached = window._attachedDocument || "";
    window._attachedDocument = null;
    await startDiscovery(text, attached);
  }

  function sendMessageRetry() {
    var text = composerText();
    chatUser(text, null);
    setComposer("");
    startDiscovery(text, window._attachedDocument || "");
  }

  async function createSessionQuiet(name) {
    try {
      var body = name ? { name: name } : {};
      return await fetchJson(API + "/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch (e) {
      return null;
    }
  }

  async function startDiscovery(message, documentText) {
    var goal = "create my portfolio";
    lastIntake = {
      message: message,
      document_text: documentText || "",
      goal: goal,
      model_profile: selectedModelProfile,
    };
    chatStartedAt = Date.now();
    chatAnalyzing("Analyzing your details…");
    setResult("chat-status", "Running with the live model — this can take a minute or two.");
    startElapsedTicker();
    var providerSelect = document.getElementById("provider-select");
    if (providerSelect) providerSelect.disabled = true; // the choice is sticky for the session
    try {
      await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(lastIntake),
      });
    } catch (e) {
      showChatFailure("Could not start Discovery: " + e.message, retryStart);
      return;
    }
    await loadDiscoveryAndPoll();
  }

  async function retryStart() {
    chatStartedAt = Date.now();
    chatAnalyzing("Analyzing your details…");
    startElapsedTicker();
    try {
      await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(lastIntake || {}),
      });
    } catch (e) {
      showChatFailure("Could not restart Discovery: " + e.message, retryStart);
      return;
    }
    await loadDiscoveryAndPoll();
  }

  function showChatFailure(message, retryFn) {
    stopPolling();
    chatError(message, "Try again", retryFn);
  }

  function startElapsedTicker() {
    if (elapsedTimer) window.clearInterval(elapsedTimer);
    elapsedTimer = window.setInterval(updateAnalyzingBubble, 1000);
  }

  function stopElapsedTicker() {
    if (elapsedTimer) { window.clearInterval(elapsedTimer); elapsedTimer = null; }
  }

  async function loadDiscoveryAndPoll() {
    try {
      var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery");
      chatState = data.discovery;
      renderChatState();
      pollDiscovery();
    } catch (e) {
      showChatFailure("Discovery state unavailable: " + e.message, retryStart);
    }
  }

  function pollDiscovery() {
    if (pollTimer) window.clearTimeout(pollTimer);
    if (!selectedSessionId || !chatState) return;
    if (TERMINAL_STATUSES.indexOf(chatState.status) >= 0) {
      renderChatState();
      return;
    }
    pollTimer = window.setTimeout(async function () {
      try {
        var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery");
        chatState = data.discovery;
      } catch (e) {
        stopPolling();
        chatError("Lost contact with the server while working: " + e.message, "Retry", retryStart);
        return;
      }
      renderChatState();
      pollDiscovery();
    }, 1200);
  }

  function stopPolling() {
    if (pollTimer) { window.clearTimeout(pollTimer); pollTimer = null; }
    stopElapsedTicker();
  }

  function renderChatState() {
    if (!chatState) return;
    var status = chatState.status;

    if (status === "questions_ready") {
      stopPolling();
      stopElapsedTicker();
      clearAnalyzingBubble();
      renderOperationAOutput();
    } else if (status === "answers_in_progress" || RUNNING_STATUSES.indexOf(status) >= 0) {
      updateAnalyzingBubble();
    } else if (status === "brief_review") {
      stopPolling();
      stopElapsedTicker();
      clearAnalyzingBubble();
      disableComposer(false);
      renderBrief();
    } else if (status === "approved") {
      stopPolling();
      stopElapsedTicker();
      clearAnalyzingBubble();
      renderBrief();
    } else if (status === "needs_attention") {
      stopPolling();
      stopElapsedTicker();
      clearAnalyzingBubble();
      var error = chatState.latest_error || {};
      var message = error.message || "Discovery needs attention.";
      if (chatState.attempt >= chatState.max_attempts && error.retryable) {
        message += " (all " + chatState.max_attempts + " attempts failed)";
      }
      if (status === "needs_attention" && chatState.brief && chatState.brief.run_id) {
        chatError(message, "Try again", retryBrief);
      } else {
        chatError(message, "Try again", retryStart);
      }
    }
  }

  function renderOperationAOutput() {
    var opA = chatState.operation_a || {};
    var mode = opA.mode || "";
    var items = Array.isArray(opA.items) ? opA.items : [];

    if (opA.run_id && opA.run_id !== lastRenderedOperationRunId) {
      lastRenderedOperationRunId = opA.run_id;
      chatQIndex = 0;
      chatAnswers = {};
    }

    if (mode === "NEEDS_DETAILS") {
      renderNeedsDetails(opA.assistant_message);
    } else if (mode === "READY_FOR_BRIEF") {
      renderReadyForBrief(opA.assistant_message);
    } else if (mode === "ASK_QUESTIONS" || items.length) {
      renderQuestions(items);
    } else {
      renderReadyForBrief(opA.assistant_message);
    }
  }

  function renderNeedsDetails(assistantMessage) {
    var content = textEl(assistantMessage || "Tell me anything you have about the person or work — you can paste it here or attach a readable document.");
    var actions = document.createElement("div");
    actions.className = "needs-details-actions";
    actions.appendChild(quickActionButton("Attach document", function () {
      document.getElementById("file-input").click();
    }));
    actions.appendChild(quickActionButton("Paste details", function () {
      document.getElementById("composer").focus();
    }));
    actions.appendChild(quickActionButton("Continue with a few questions", forceQuestionsOrBrief));
    content.appendChild(actions);
    addBubble("assistant", content);
  }

  function renderReadyForBrief(assistantMessage) {
    var content = textEl(assistantMessage || "I have enough information to prepare the portfolio brief.");
    var actions = document.createElement("div");
    actions.className = "needs-details-actions";
    actions.appendChild(quickActionButton("Generate the brief now", generateBriefNow));
    content.appendChild(actions);
    addBubble("assistant", content);
  }

  function quickActionButton(label, onAction) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "choice-btn";
    button.textContent = label;
    button.addEventListener("click", onAction);
    return button;
  }

  function forceQuestionsOrBrief() {
    generateBriefNow();
  }

  async function generateBriefNow() {
    disableComposer(true);
    chatStartedAt = Date.now();
    chatAnalyzing("Preparing your portfolio brief…");
    startElapsedTicker();
    try {
      var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/answers", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ complete: true, answers: [] }),
      });
      chatState = data.discovery;
      pollDiscovery();
    } catch (e) {
      disableComposer(false);
      showChatFailure("Could not start the brief: " + e.message, generateBriefNow);
    }
  }

  function clearAnalyzingBubble() {
    var bubble = document.getElementById("analyzing-bubble");
    if (bubble) bubble.remove();
    analyzingBubbleId = null;
  }

  // ── Questions ───────────────────────────────────────────────────────────

  function renderQuestions(questions) {
    if (chatQIndex >= questions.length) return;
    var question = questions[chatQIndex];
    var answered = chatAnswers[question.id];

    var content = document.createElement("div");
    var heading = document.createElement("p");
    heading.className = "bubble-text";
    heading.textContent = question.text;
    content.appendChild(heading);

    if (question.help_text) {
      var help = document.createElement("small");
      help.className = "bubble-meta";
      help.textContent = question.help_text;
      content.appendChild(help);
    }

    if (question.reason) {
      var reason = document.createElement("small");
      reason.className = "bubble-meta";
      reason.textContent = question.reason;
      content.appendChild(reason);
    }

    if (question.kind === "single_select") {
      var singleOptions = guardedOptions(question);
      singleOptions.forEach(function (option) {
        content.appendChild(choiceButton(question, option.id, option.label));
      });
      if (!singleOptions.length) content.appendChild(noOptionsNote());
      content.appendChild(otherAnswerRow(function (text) { submitAnswer(question, text); }).row);
    } else if (question.kind === "multi_select") {
      var selected = Array.isArray(answered && answered.value) ? answered.value : [];
      var multiOptions = guardedOptions(question);
      multiOptions.forEach(function (option) {
        var label = document.createElement("label");
        label.className = "choice-line";
        var checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = option.id;
        checkbox.checked = selected.indexOf(option.id) >= 0;
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(" " + option.label));
        content.appendChild(label);
      });
      if (!multiOptions.length) content.appendChild(noOptionsNote());
      var otherField = otherAnswerRow(null);
      content.appendChild(otherField.row);
      var submit = document.createElement("button");
      submit.type = "button";
      submit.className = "primary-action";
      submit.textContent = "Submit answer";
      submit.addEventListener("click", function () {
        var values = Array.prototype.slice.call(content.querySelectorAll("input[type=checkbox]:checked")).map(function (input) { return input.value; });
        var otherText = otherField.input.value.trim();
        if (otherText) values.push(otherText);
        submitAnswer(question, values);
      });
      content.appendChild(submit);
    } else if (question.kind === "boolean") {
      content.appendChild(choiceButton(question, "true", "Yes"));
      content.appendChild(choiceButton(question, "false", "No"));
    } else {
      answeringQuestionId = question.id;
      var prompt = document.createElement("p");
      prompt.className = "bubble-meta";
      prompt.textContent = "Type your answer in the box below, then press Send.";
      content.appendChild(prompt);
    }

    if (question.allow_skip !== false) {
      var skip = document.createElement("button");
      skip.type = "button";
      skip.className = "choice-btn skip-btn";
      skip.textContent = "Skip";
      skip.addEventListener("click", function () { submitAnswer(question, null); });
      content.appendChild(skip);
    }

    addBubble("assistant", content);
  }

  function choiceButton(question, value, label) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "choice-btn";
    button.textContent = label;
    button.addEventListener("click", function () { submitAnswer(question, value); });
    return button;
  }

  // At most 3 concrete options are ever rendered — the interface always
  // offers a free-text alternative (see otherAnswerRow) and a separate Skip
  // action, so a longer model-returned list is capped rather than dropped.
  function guardedOptions(question) {
    return Array.isArray(question.options) ? question.options.slice(0, 3) : [];
  }

  function noOptionsNote() {
    var note = document.createElement("small");
    note.className = "bubble-meta";
    note.textContent = "No preset options were available — type your own answer below.";
    return note;
  }

  // The always-present 4th "something else" affordance for select-kind
  // questions. If onSubmit is provided (single_select), the row gets its own
  // submit button/Enter handling; if null (multi_select), the caller reads
  // .input.value itself alongside the checked boxes.
  function otherAnswerRow(onSubmit) {
    var row = document.createElement("div");
    row.className = "other-answer-row";
    var input = document.createElement("input");
    input.type = "text";
    input.className = "other-answer-input";
    input.placeholder = "Something else… (type your own answer)";
    row.appendChild(input);
    if (onSubmit) {
      var fire = function () {
        var text = input.value.trim();
        if (!text) return;
        onSubmit(text);
      };
      var button = document.createElement("button");
      button.type = "button";
      button.className = "choice-btn";
      button.textContent = "Use this answer";
      button.addEventListener("click", fire);
      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") { e.preventDefault(); fire(); }
      });
      row.appendChild(button);
    }
    return { row: row, input: input };
  }

  function submitAnswer(question, value) {
    chatAnswers[question.id] = {
      question_id: question.id,
      mode: value === null ? "skipped" : "answered",
      value: value,
    };
    answeringQuestionId = null;
    var displayText = value === null
      ? "Skipped"
      : (value === true ? "Yes" : value === false ? "No" : (Array.isArray(value) ? value.join(", ") : String(value)));
    chatUser(displayText, null);
    advanceQuestion();
  }

  function submitTextAnswer(text) {
    if (!answeringQuestionId) return;
    var question = currentQuestions()[chatQIndex];
    chatAnswers[question.id] = { question_id: question.id, mode: "answered", value: text };
    answeringQuestionId = null;
    chatUser(text, null);
    setComposer("");
    advanceQuestion();
  }

  function currentQuestions() {
    return chatState && chatState.operation_a && Array.isArray(chatState.operation_a.items) ? chatState.operation_a.items : [];
  }

  function advanceQuestion() {
    chatQIndex += 1;
    if (chatQIndex < currentQuestions().length) {
      renderQuestions(currentQuestions());
      return;
    }
    chatDone("All questions answered. Preparing your portfolio brief…");
    submitAllAnswersAndEnqueueBrief();
  }

  async function submitAllAnswersAndEnqueueBrief() {
    disableComposer(true);
    try {
      var all = [];
      currentQuestions().forEach(function (q) {
        if (chatAnswers[q.id]) all.push(chatAnswers[q.id]);
      });
      chatState = null;
      var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/answers", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ complete: true, answers: all }),
      });
      chatState = data.discovery;
      chatAnalyzing("Preparing your portfolio brief…");
      chatStartedAt = Date.now();
      startElapsedTicker();
      pollDiscovery();
    } catch (e) {
      disableComposer(false);
      showChatFailure("Could not save answers: " + e.message, retryBrief);
    }
  }

  async function retryBrief() {
    disableComposer(true);
    chatStartedAt = Date.now();
    chatAnalyzing("Preparing your portfolio brief…");
    startElapsedTicker();
    try {
      var all = [];
      currentQuestions().forEach(function (q) {
        if (chatAnswers[q.id]) all.push(chatAnswers[q.id]);
      });
      var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/answers", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ complete: true, answers: all }),
      });
      chatState = data.discovery;
      pollDiscovery();
    } catch (e) {
      disableComposer(false);
      showChatFailure("Could not restart the brief: " + e.message, retryBrief);
    }
  }

  // ── Brief ───────────────────────────────────────────────────────────────

  var localBriefMarkdown = null;   // local edit of the brief (preview only)

  function renderBrief() {
    var brief = chatState.brief || null;
    if (!brief) return;
    if (chatState.status === "approved") {
      promptNextAgentPrompt("Discovery approved — the portfolio brief is ready for the next stage.", "Start Content Architect", startContentArchitect);
      return;
    }
    var content = document.createElement("div");
    content.className = "brief-review";

    var title = document.createElement("h2");
    title.textContent = brief.title || "Portfolio Discovery Brief";
    content.appendChild(title);

    var summaryNote = document.createElement("p");
    summaryNote.className = "bubble-meta";
    summaryNote.textContent = "Here's a quick summary — the full detailed brief is saved and available under Advanced.";
    content.appendChild(summaryNote);

    var markdownBox = document.createElement("div");
    markdownBox.className = "brief-markdown";
    markdownBox.setAttribute("aria-live", "polite");
    content.appendChild(markdownBox);

    if (Array.isArray(brief.open_items) && brief.open_items.length) {
      var openDetails = document.createElement("details");
      openDetails.className = "brief-open-items";
      var openSummary = document.createElement("summary");
      openSummary.textContent = "Open items (" + brief.open_items.length + ")";
      openDetails.appendChild(openSummary);
      var openList = document.createElement("ul");
      brief.open_items.forEach(function (item) {
        var li = document.createElement("li");
        li.textContent = item;
        openList.appendChild(li);
      });
      openDetails.appendChild(openList);
      content.appendChild(openDetails);
    }

    var actions = document.createElement("div");
    actions.className = "brief-actions";
    var editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "primary-action";
    editBtn.textContent = "Edit summary";
    actions.appendChild(editBtn);
    var viewFullBtn = document.createElement("button");
    viewFullBtn.type = "button";
    viewFullBtn.className = "choice-btn";
    viewFullBtn.textContent = "View full brief";
    actions.appendChild(viewFullBtn);
    var reviseBtn = document.createElement("button");
    reviseBtn.type = "button";
    reviseBtn.className = "choice-btn";
    reviseBtn.textContent = "Ask for a revision";
    actions.appendChild(reviseBtn);
    var approveBtn = document.createElement("button");
    approveBtn.type = "button";
    approveBtn.className = "primary-action";
    approveBtn.textContent = "NEXT: Approve";
    actions.appendChild(approveBtn);
    content.appendChild(actions);

    var raw = document.createElement("details");
    var rawSummary = document.createElement("summary");
    rawSummary.textContent = "Advanced — raw JSON";
    raw.appendChild(rawSummary);
    var pre = document.createElement("pre");
    pre.className = "json-view";
    pre.textContent = prettyJson(brief);
    raw.appendChild(pre);
    content.appendChild(raw);

    var bubble = addBubble("assistant", content);
    bubble.id = "brief-bubble";

    renderBriefMarkdown(markdownBox);
    editBtn.addEventListener("click", function () { toggleBriefEdit(markdownBox, editBtn); });
    viewFullBtn.addEventListener("click", openFullBriefSidebar);
    reviseBtn.addEventListener("click", function () { openRevisionForm(content); });
    approveBtn.addEventListener("click", approveDiscovery);
  }

  // ── Full-brief sidebar (complete brief_markdown + profile, as saved) ────

  function openFullBriefSidebar() {
    if (!chatState || !chatState.brief) return;
    var brief = chatState.brief;
    var box = document.getElementById("brief-sidebar-content");
    clearElement(box);
    box.appendChild(renderMarkdownToNodes(brief.markdown || "(no brief content yet)"));

    if (brief.profile) {
      var p = brief.profile;
      var hasProfile = !!(p.name || p.current_title || p.location ||
        (p.links && p.links.length) || (p.experience && p.experience.length) ||
        (p.education && p.education.length) || (p.projects && p.projects.length) ||
        (p.skills && p.skills.length) || (p.spoken_languages && p.spoken_languages.length));
      if (hasProfile) {
        var hr = document.createElement("hr");
        box.appendChild(hr);
        var profHeading = document.createElement("h3");
        profHeading.textContent = "Structured profile (as saved for the next stage)";
        box.appendChild(profHeading);
        var pre = document.createElement("pre");
        pre.className = "json-view";
        pre.textContent = prettyJson(brief.profile);
        box.appendChild(pre);
      }
    }

    document.getElementById("brief-sidebar-title").textContent = brief.title || "Full portfolio brief";
    document.getElementById("brief-sidebar-backdrop").hidden = false;
    document.getElementById("brief-sidebar").classList.add("open");
    document.getElementById("brief-sidebar").setAttribute("aria-hidden", "false");
  }

  function closeFullBriefSidebar() {
    document.getElementById("brief-sidebar-backdrop").hidden = true;
    document.getElementById("brief-sidebar").classList.remove("open");
    document.getElementById("brief-sidebar").setAttribute("aria-hidden", "true");
  }

  function briefDisplaySource() {
    if (localBriefMarkdown != null) return localBriefMarkdown;
    if (!chatState.brief) return "";
    return chatState.brief.user_summary || chatState.brief.markdown || "";
  }

  function renderBriefMarkdown(markdownBox) {
    markdownBox.replaceChildren(renderMarkdownToNodes(briefDisplaySource()));
  }

  function toggleBriefEdit(markdownBox, editBtn) {
    if (editBtn.textContent === "Edit summary") {
      var editor = document.createElement("textarea");
      editor.className = "brief-editor";
      editor.value = briefDisplaySource();
      markdownBox.replaceChildren(editor);
      editBtn.textContent = "Save";
      editor.focus();
    } else {
      var area = markdownBox.querySelector("textarea.brief-editor");
      if (area) localBriefMarkdown = area.value;
      renderBriefMarkdown(markdownBox);
      editBtn.textContent = "Edit summary";
    }
  }

  function openRevisionForm(content) {
    var existing = content.querySelector(".revision-form");
    if (existing) {
      existing.querySelector("textarea").focus();
      return;
    }
    var form = document.createElement("div");
    form.className = "revision-form";
    var label = document.createElement("p");
    label.className = "bubble-meta";
    label.textContent = "Describe what should change in the brief:";
    form.appendChild(label);
    var textarea = document.createElement("textarea");
    textarea.className = "revision-input";
    textarea.rows = 3;
    textarea.placeholder = "e.g. Lead with the QueueGuard story and darken the theme.";
    form.appendChild(textarea);
    var sendBtn = document.createElement("button");
    sendBtn.type = "button";
    sendBtn.className = "primary-action";
    sendBtn.textContent = "Send revision";
    sendBtn.addEventListener("click", function () {
      var value = textarea.value.trim();
      if (!value) return;
      sendBtn.disabled = true;
      requestRevision(value, sendBtn);
    });
    form.appendChild(sendBtn);
    content.insertBefore(form, content.querySelector(".brief-actions").nextSibling);
    textarea.focus();
  }

  async function requestRevision(revisionRequest, sendBtn) {
    disableComposer(true);
    chatStartedAt = Date.now();
    clearAnalyzingBubble();
    chatAnalyzing("Revising the brief…");
    startElapsedTicker();
    try {
      var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/revise", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ revision_request: revisionRequest }),
      });
      chatState = data.discovery;
      localBriefMarkdown = null;
      pollDiscovery();
    } catch (e) {
      disableComposer(false);
      clearAnalyzingBubble();
      if (sendBtn) sendBtn.disabled = false;
      if (e.status === 409) {
        chatError("Revision not possible: " + e.message, "Reload", loadDiscoveryAndPoll);
      } else {
        chatError("Revision failed: " + e.message, "Try again", function () { requestRevision(revisionRequest, sendBtn); });
      }
    }
  }

  async function approveDiscovery() {
    try {
      var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/discovery/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      chatState = data.discovery;
      if (chatState.status === "approved") {
        promptNextAgentPrompt("Discovery approved — the portfolio brief is ready for the next stage.", "Start Content Architect", startContentArchitect);
      } else {
        renderChatState(); // unexpected status; fall back to the normal render instead of assuming approved
      }
    } catch (e) {
      chatError("Approval failed: " + e.message, "Try again", approveDiscovery);
    }
  }

  // ── Content Architect (minimal — testing harness, not the full UI) ──────
  // Discovery stays fully separate from Content Architect: this is only the
  // chat's own trigger/view for the next stage, not a Discovery responsibility.

  var caState = null;
  var caPollTimer = null;

  // Approving a stage never auto-starts the next agent — it only finalizes
  // the current one. This renders a distinct confirmation prompt; only a
  // click on its button or a clear natural-language "yes" (handled in
  // sendMessage via awaitingNextAgentConfirmation) actually starts startFn.
  function promptNextAgentPrompt(message, buttonLabel, startFn) {
    awaitingNextAgentConfirmation = { startFn: startFn, label: buttonLabel };
    var content = textEl(message + " Would you like to move to the next agent?");
    var actions = document.createElement("div");
    actions.className = "needs-details-actions";
    actions.appendChild(quickActionButton(buttonLabel, function () {
      awaitingNextAgentConfirmation = null;
      startFn();
    }));
    content.appendChild(actions);
    addBubble("assistant", content);
  }

  async function startContentArchitect() {
    chatAnalyzing("Building content strategy and page copy…");
    try {
      var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/content-architect/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preferences: {}, model_profile: selectedModelProfile }),
      });
      caState = data.content_architect;
      pollContentArchitect();
    } catch (e) {
      clearAnalyzingBubble();
      chatError("Could not start Content Architect: " + e.message, "Try again", startContentArchitect);
    }
  }

  function pollContentArchitect() {
    if (caPollTimer) window.clearTimeout(caPollTimer);
    if (!caState) return;
    if (caState.status === "content_review" || caState.status === "approved" || caState.status === "needs_attention") {
      clearAnalyzingBubble();
      renderContentArchitectState();
      return;
    }
    caPollTimer = window.setTimeout(async function () {
      try {
        var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/content-architect");
        caState = data.content_architect;
      } catch (e) {
        chatError("Lost contact while building content: " + e.message, "Retry", startContentArchitect);
        return;
      }
      pollContentArchitect();
    }, 1500);
  }

  function renderContentArchitectState() {
    if (caState.status === "needs_attention") {
      var error = caState.latest_error || {};
      chatError(error.message || "Content Architect needs attention.", "Try again", startContentArchitect);
      return;
    }

    var content = document.createElement("div");
    content.className = "brief-review";

    var title = document.createElement("h2");
    title.textContent = "Content strategy" + (caState.status === "approved" ? " — approved" : "");
    content.appendChild(title);

    var strategy = caState.site_story_strategy || {};
    if (caState.user_summary) {
      content.appendChild(renderMarkdownToNodes(caState.user_summary));
    } else if (strategy.positioning) {
      content.appendChild(textEl(strategy.positioning));
    }

    var routes = Array.isArray(caState.route_plan) ? caState.route_plan : [];
    if (routes.length) {
      var routeList = document.createElement("ul");
      routes.forEach(function (r) {
        var li = document.createElement("li");
        li.textContent = (r.path || "") + " — " + (r.purpose || "");
        routeList.appendChild(li);
      });
      content.appendChild(routeList);
    }

    var unresolved = Array.isArray(caState.unresolved_issues) ? caState.unresolved_issues : [];
    if (unresolved.length) {
      var unresolvedNote = document.createElement("p");
      unresolvedNote.className = "bubble-meta";
      unresolvedNote.textContent = "Still open:";
      content.appendChild(unresolvedNote);
      var unresolvedList = document.createElement("ul");
      unresolved.forEach(function (item) {
        var li = document.createElement("li");
        li.textContent = item;
        unresolvedList.appendChild(li);
      });
      content.appendChild(unresolvedList);
    }

    var warningItems = Array.isArray(caState.warnings) ? caState.warnings : [];
    if (warningItems.length) {
      var warningsNote = document.createElement("p");
      warningsNote.className = "bubble-meta bubble-error";
      warningsNote.textContent = "Warnings:";
      content.appendChild(warningsNote);
      var warningsList = document.createElement("ul");
      warningItems.forEach(function (item) {
        var li = document.createElement("li");
        li.textContent = item;
        warningsList.appendChild(li);
      });
      content.appendChild(warningsList);
    }

    var privacyItems = Array.isArray(caState.privacy_and_confidentiality) ? caState.privacy_and_confidentiality : [];
    if (privacyItems.length) {
      content.appendChild(textEl(
        privacyItems.length + " privacy/confidentiality note" + (privacyItems.length === 1 ? "" : "s") +
        " were applied — see Advanced for details."
      ));
    }

    if (caState.status === "content_review") {
      var actions = document.createElement("div");
      actions.className = "brief-actions";
      var approveBtn = document.createElement("button");
      approveBtn.type = "button";
      approveBtn.className = "primary-action";
      approveBtn.textContent = "Approve content";
      approveBtn.addEventListener("click", approveContentArchitect);
      actions.appendChild(approveBtn);
      content.appendChild(actions);
    }

    var raw = document.createElement("details");
    var rawSummary = document.createElement("summary");
    rawSummary.textContent = "Advanced — raw JSON";
    raw.appendChild(rawSummary);
    var pre = document.createElement("pre");
    pre.className = "json-view";
    pre.textContent = prettyJson(caState);
    raw.appendChild(pre);
    content.appendChild(raw);

    addBubble("assistant", content);
  }

  async function approveContentArchitect() {
    try {
      var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/content-architect/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      caState = data.content_architect;
      promptNextAgentPrompt("Content Architect approved — the content is ready for the Visual Design Director.", "Start Visual Design Director", startVisualDesignDirector);
    } catch (e) {
      chatError("Approval failed: " + e.message, "Try again", approveContentArchitect);
    }
  }

  // ── Visual Design Director (minimal — testing harness, not the full UI) ─
  // Mirrors the Content Architect section above, one stage further down the
  // pipeline. Code Generation stays out of scope — it remains a deterministic
  // mock with no durable-job route, so the flow ends after approval here.

  var vddState = null;
  var vddPollTimer = null;

  async function startVisualDesignDirector() {
    chatAnalyzing("Establishing the visual direction…");
    try {
      var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/visual-design-director/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preferences: {}, model_profile: selectedModelProfile }),
      });
      vddState = data.visual_design_director;
      pollVisualDesignDirector();
    } catch (e) {
      clearAnalyzingBubble();
      chatError("Could not start Visual Design Director: " + e.message, "Try again", startVisualDesignDirector);
    }
  }

  function pollVisualDesignDirector() {
    if (vddPollTimer) window.clearTimeout(vddPollTimer);
    if (!vddState) return;
    if (vddState.status === "design_review" || vddState.status === "approved" || vddState.status === "needs_attention") {
      clearAnalyzingBubble();
      renderVisualDesignDirectorState();
      return;
    }
    vddPollTimer = window.setTimeout(async function () {
      try {
        var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/visual-design-director");
        vddState = data.visual_design_director;
      } catch (e) {
        chatError("Lost contact while establishing the visual direction: " + e.message, "Retry", startVisualDesignDirector);
        return;
      }
      pollVisualDesignDirector();
    }, 1500);
  }

  function renderVisualDesignDirectorState() {
    if (vddState.status === "needs_attention") {
      var error = vddState.latest_error || {};
      chatError(error.message || "Visual Design Director needs attention.", "Try again", startVisualDesignDirector);
      return;
    }

    var content = document.createElement("div");
    content.className = "brief-review";

    var title = document.createElement("h2");
    title.textContent = "Visual direction" + (vddState.status === "approved" ? " — approved" : "");
    content.appendChild(title);

    if (vddState.user_summary) {
      content.appendChild(renderMarkdownToNodes(vddState.user_summary));
    } else if (vddState.visual_language && vddState.visual_language.creative_thesis) {
      content.appendChild(textEl(vddState.visual_language.creative_thesis));
    }

    var pages = Array.isArray(vddState.pages) ? vddState.pages : [];
    if (pages.length) {
      var pageList = document.createElement("ul");
      pages.forEach(function (p) {
        var li = document.createElement("li");
        li.textContent = (p.path || p.route_id || "") + " — " + (p.purpose || "");
        pageList.appendChild(li);
      });
      content.appendChild(pageList);
    }

    var conflictItems = Array.isArray(vddState.conflicts) ? vddState.conflicts : [];
    if (conflictItems.length) {
      var conflictsNote = document.createElement("p");
      conflictsNote.className = "bubble-meta bubble-error";
      conflictsNote.textContent = "Conflicts:";
      content.appendChild(conflictsNote);
      var conflictsList = document.createElement("ul");
      conflictItems.forEach(function (item) {
        var li = document.createElement("li");
        li.textContent = item;
        conflictsList.appendChild(li);
      });
      content.appendChild(conflictsList);
    }

    var warningItems = Array.isArray(vddState.warnings) ? vddState.warnings : [];
    if (warningItems.length) {
      var warningsNote = document.createElement("p");
      warningsNote.className = "bubble-meta bubble-error";
      warningsNote.textContent = "Warnings:";
      content.appendChild(warningsNote);
      var warningsList = document.createElement("ul");
      warningItems.forEach(function (item) {
        var li = document.createElement("li");
        li.textContent = item;
        warningsList.appendChild(li);
      });
      content.appendChild(warningsList);
    }

    if (vddState.status === "design_review") {
      var actions = document.createElement("div");
      actions.className = "brief-actions";
      var approveBtn = document.createElement("button");
      approveBtn.type = "button";
      approveBtn.className = "primary-action";
      approveBtn.textContent = "Approve visual direction";
      approveBtn.addEventListener("click", approveVisualDesignDirector);
      actions.appendChild(approveBtn);
      content.appendChild(actions);
    }

    var raw = document.createElement("details");
    var rawSummary = document.createElement("summary");
    rawSummary.textContent = "Advanced — raw JSON";
    raw.appendChild(rawSummary);
    var pre = document.createElement("pre");
    pre.className = "json-view";
    pre.textContent = prettyJson(vddState);
    raw.appendChild(pre);
    content.appendChild(raw);

    addBubble("assistant", content);
  }

  async function approveVisualDesignDirector() {
    try {
      var data = await fetchJson(API + "/sessions/" + selectedSessionId + "/visual-design-director/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      vddState = data.visual_design_director;
      chatDone("Visual Design Director approved — the visual direction is ready for Code Generation (not yet implemented).");
    } catch (e) {
      chatError("Approval failed: " + e.message, "Try again", approveVisualDesignDirector);
    }
  }

  // ── Safe Markdown rendering (DOM nodes only, no HTML injection) ─────────

  function renderMarkdownToNodes(mdText) {
    var fragment = document.createDocumentFragment();
    var text = String(mdText || "");
    if (text.length > 200000) {
      text = text.slice(0, 200000);
      var trunc = document.createElement("p");
      trunc.className = "bubble-meta";
      trunc.textContent = "Brief output was truncated in the UI.";
      fragment.appendChild(trunc);
    }

    var lines = text.split(/\r?\n/);
    var i = 0;
    var para = [];

    function flushPara() {
      if (!para.length) return;
      var p = document.createElement("p");
      para.forEach(function (line, idx) {
        if (idx > 0) p.appendChild(document.createTextNode(" "));
        appendInline(p, line);
      });
      fragment.appendChild(p);
      para = [];
    }

    function appendList(items, ordered) {
      var list = document.createElement(ordered ? "ol" : "ul");
      items.forEach(function (item) {
        var li = document.createElement("li");
        appendInline(li, item);
        list.appendChild(li);
      });
      fragment.appendChild(list);
    }

    while (i < lines.length) {
      var line = lines[i];
      var heading = /^(#{1,4})\s+(.*)$/.exec(line);
      if (heading) {
        flushPara();
        var level = heading[1].length;
        var h = document.createElement("h" + level);
        appendInline(h, heading[2]);
        fragment.appendChild(h);
        i += 1;
        continue;
      }
      if (/^---+$/.test(line.trim())) {
        flushPara();
        fragment.appendChild(document.createElement("hr"));
        i += 1;
        continue;
      }
      var bullet = /^[-*]\s+(.*)$/.exec(line);
      if (bullet) {
        flushPara();
        var bullets = [bullet[1]];
        i += 1;
        while (i < lines.length) {
          var next = /^[-*]\s+(.*)$/.exec(lines[i]);
          if (next) { bullets.push(next[1]); i += 1; } else { break; }
        }
        appendList(bullets, false);
        continue;
      }
      var ordered = /^\d+\.\s+(.*)$/.exec(line);
      if (ordered) {
        flushPara();
        var items = [ordered[1]];
        i += 1;
        while (i < lines.length) {
          var nextOrdered = /^\d+\.\s+(.*)$/.exec(lines[i]);
          if (nextOrdered) { items.push(nextOrdered[1]); i += 1; } else { break; }
        }
        appendList(items, true);
        continue;
      }
      if (!line.trim()) {
        flushPara();
        i += 1;
        continue;
      }
      para.push(line);
      i += 1;
    }
    flushPara();
    return fragment;
  }

  function appendInline(parent, text) {
    var tokens = String(text).split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\((https?:\/\/[^)\s]+)\))/g);
    tokens.forEach(function (token) {
      if (!token) return;
      var bold = /^\*\*([^*]+)\*\*$/.exec(token);
      var italic = /^\*([^*]+)\*$/.exec(token);
      var code = /^`([^`]+)`$/.exec(token);
      var link = /^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/.exec(token);
      if (bold) {
        var b = document.createElement("strong");
        b.textContent = bold[1];
        parent.appendChild(b);
      } else if (italic) {
        var em = document.createElement("em");
        em.textContent = italic[1];
        parent.appendChild(em);
      } else if (code) {
        var c = document.createElement("code");
        c.textContent = code[1];
        parent.appendChild(c);
      } else if (link) {
        var a = document.createElement("a");
        a.href = link[2];
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.textContent = link[1];
        parent.appendChild(a);
      } else {
        parent.appendChild(document.createTextNode(token));
      }
    });
  }

  // ── File attachment ─────────────────────────────────────────────────────

  function onFileSelected(event) {
    var file = event.target.files && event.target.files[0];
    event.target.value = "";
    if (!file) return;
    var name = file.name || "attachment";
    if (name.toLowerCase().endsWith(".pdf")) {
      chatDone("PDF attached: " + name + ". PDF text extraction is not available yet — paste the content into the box or continue without it.");
      return;
    }
    if (file.size > 200000) {
      chatError("The file is larger than 200 KB — paste the text into the box instead.", null, null);
      return;
    }
    var reader = new FileReader();
    reader.onload = function () {
      var text = String(reader.result || "");
      chatUser("Attached " + name + " (" + text.length + " chars)", null);
      chatDone("Read " + name + ". Sending it with your next message.");
      window._attachedDocument = text;
    };
    reader.onerror = function () {
      chatError("Could not read the file. Paste the text into the box instead.", null, null);
    };
    reader.readAsText(file);
  }

  // ── Harness helpers (Advanced section) ──────────────────────────────────

  async function checkHealth() {
    setPill("health-live", "unknown");
    setPill("health-ready", "unknown");
    try { await fetchJson("/health/live"); setPill("health-live", "ok"); } catch (e) { setPill("health-live", "err"); }
    try { await fetchJson("/health/ready"); setPill("health-ready", "ok"); } catch (e) { setPill("health-ready", "err"); }
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
      sessionStorage.setItem("oryxenai.discovery.session", selectedSessionId);
      refreshSessionPanel(session);
      listRuns();
      await listSessions();
    } catch (e) {
      setResult("create-result", "Error: " + e.message, "error");
    }
  }

  function refreshSessionPanel(session) {
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
          sessionStorage.setItem("oryxenai.discovery.session", selectedSessionId);
          refreshSessionPanel(s);
          listRuns();
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
    var inputObj;
    try {
      inputObj = JSON.parse(document.getElementById("input-json").value.trim() || "{}");
    } catch (e) {
      setResult("run-result", "Invalid JSON input.", "error");
      return;
    }
    var idempKey = document.getElementById("idempotency-key").value.trim() || null;
    setResult("run-result", "Running mock…");
    try {
      var body = { agentKey: agentKey, input: inputObj };
      if (idempKey) body.idempotencyKey = idempKey;
      var run = await fetchJson(API + "/sessions/" + selectedSessionId + "/runs/mock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      showRunDetail(run);
      setResult("run-result", "Run " + run.status + ": " + run.id, run.status === "succeeded" ? "success" : "error");
      listRuns();
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
    document.getElementById("rd-output").textContent = JSON.stringify(run.output_payload, null, 2);
    document.getElementById("rd-state-after").textContent = JSON.stringify(run.state_after, null, 2);
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
      document.getElementById("pj-result").textContent = JSON.stringify(job.result || job.error || {}, null, 2);
      document.getElementById("probe-detail").hidden = false;
      if (job.status === "succeeded") {
        setResult("probe-status", "Probe succeeded on attempt " + job.attempt, "success");
      } else if (job.status === "failed") {
        setResult("probe-status", "Probe failed: " + ((job.error && job.error.message) || "unknown"), "error");
      } else {
        setResult("probe-status", "Probe " + job.status + " (attempt " + job.attempt + ")");
        setTimeout(pollProbe, 1500);
      }
    } catch (e) {
      setResult("probe-status", "Error polling: " + e.message, "error");
    }
  }

  // ── Boot ────────────────────────────────────────────────────────────────

  document.addEventListener("DOMContentLoaded", function () {
    chatWelcome();
    checkHealth();
    loadAgents();
    listSessions();
    loadSystemStatus();
    setInterval(loadSystemStatus, 15000);

    document.getElementById("btn-send").addEventListener("click", sendMessage);
    document.getElementById("provider-select").addEventListener("change", function () {
      selectedModelProfile = this.value;
    });
    document.getElementById("composer").addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });
    document.getElementById("btn-attach").addEventListener("click", function () {
      document.getElementById("file-input").click();
    });
    document.getElementById("file-input").addEventListener("change", onFileSelected);
    document.getElementById("btn-create-session").addEventListener("click", createSession);
    document.getElementById("btn-list-sessions").addEventListener("click", listSessions);
    document.getElementById("btn-run-mock").addEventListener("click", runMock);
    document.getElementById("btn-list-runs").addEventListener("click", listRuns);
    document.getElementById("btn-probe").addEventListener("click", enqueueProbe);
    document.getElementById("brief-sidebar-close").addEventListener("click", closeFullBriefSidebar);
    document.getElementById("brief-sidebar-backdrop").addEventListener("click", closeFullBriefSidebar);
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeFullBriefSidebar();
    });

    var rememberedSession = sessionStorage.getItem("oryxenai.discovery.session");
    if (rememberedSession) {
      fetchJson(API + "/sessions/" + rememberedSession).then(function (session) {
        selectedSessionId = session.id;
        refreshSessionPanel(session);
        return listRuns();
      }).catch(function () { sessionStorage.removeItem("oryxenai.discovery.session"); });
    }
  });
})();
