import { createCodeGeneratorDevelopmentController } from './code-generator-development-controller.mjs';

const API_ROOT = '/api/v1/development/code-generator';

export const READINESS_BLOCKER_LABELS = Object.freeze({
  planner: 'planner configuration',
  generation_profiles: 'generation profiles',
  npm: 'npm',
  verification_browser: 'verification browser',
  preview_storage: 'preview storage',
  provider_wire_schema: 'provider wire schemas',
  build_preparation_pack: 'eligible Build Preparation pack',
  preview_gateway_not_configured: 'preview gateway is not configured',
  preview_gateway_unreachable: 'preview gateway is unreachable',
});

export function formatReadinessBlocker(code) {
  return READINESS_BLOCKER_LABELS[code] || String(code || 'local readiness checks');
}

export async function bootCodeGeneratorDevelopment({ request: requestImpl } = {}) {
  if (typeof requestImpl !== 'function') throw new Error('An authorized request function is required.');
  const root = document.querySelector('[data-code-generator-development]');
  if (!root) return null;

  const view = (name) => root.querySelector(`[data-${name}]`);
  const all = (name) => root.querySelectorAll(`[data-${name}]`);
  const viewportButtons = () => all('preview-viewport');
  const activeStatuses = new Set([
    'queued', 'planning', 'planned', 'acquiring', 'acquired', 'generating_foundation',
    'generating_routes', 'integrating', 'source_ready', 'building', 'smoke_testing',
    'repairing', 'preview_pending',
  ]);
  const stageStatuses = {
    prepare: new Set(['queued', 'planning', 'planned']),
    resources: new Set(['acquiring', 'acquired']),
    source: new Set(['generating_foundation', 'generating_routes', 'integrating', 'source_ready']),
    verify: new Set(['building', 'smoke_testing', 'repairing', 'preview_pending', 'ready']),
  };
  const stageOrder = ['prepare', 'resources', 'source', 'verify'];
  const statusLabels = {
    created: 'Created', queued: 'Queued', planning: 'Admitting pack', planned: 'Plan ready',
    acquiring: 'Preparing resources', acquired: 'Resources ready',
    generating_foundation: 'Building visual foundation', generating_routes: 'Building routes',
    integrating: 'Connecting the portfolio', source_ready: 'Source ready',
    building: 'Building production output', smoke_testing: 'Testing the preview',
    repairing: 'Applying bounded repair', preview_pending: 'Verified; waiting for preview publication',
    ready: 'Preview promoted', needs_attention: 'Needs attention',
  };

  const request = async (path, options = {}) => {
    const response = await requestImpl(`${API_ROOT}${path}`, options);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = body.error || body;
      const code = error.code ? `${error.code}: ` : '';
      const message = error.message || error.detail || 'The development request failed.';
      throw new Error(`${code}${message}`);
    }
    return body;
  };
  const requestKey = () => globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;

  let readinessReady = false;
  let selectedPack = '';
  let activeRunStatus = '';
  let selectedRoutePath = '';
  let selectedViewport = 'fit';
  let currentPreview = null;
  let activeRunId = '';
  let previewLoadSequence = 0;
  let previewLoadTimer = 0;
  let previewBridgeReady = false;
  let sourceManifestLoadedFor = '';

  const clearPreviewLoadTimer = () => {
    if (previewLoadTimer) window.clearTimeout(previewLoadTimer);
    previewLoadTimer = 0;
  };

  const setError = (message = '') => {
    const error = view('start-error');
    error.textContent = message;
    error.hidden = !message;
  };

  const updateLaunchButton = () => {
    const button = view('start-build-preparation');
    const busy = activeStatuses.has(activeRunStatus);
    button.disabled = !selectedPack || !readinessReady || busy;
    button.querySelector('span').textContent = busy ? 'Generation in progress' : activeRunStatus === 'ready' ? 'Generate again' : 'Generate portfolio';
  };

  const renderReadiness = (readiness) => {
    const blockerCodesFromServer = Array.isArray(readiness.readiness_blockers)
      ? readiness.readiness_blockers
      : [];
    const fallbackBlockers = [];
    if (!readiness.planning_ready) fallbackBlockers.push('planner');
    if (!readiness.generation_ready) fallbackBlockers.push('generation_profiles');
    if (!readiness.package_manager_ready) fallbackBlockers.push('npm');
    if (!readiness.browser_ready) fallbackBlockers.push('verification_browser');
    if (readiness.preview_storage_ready === false) fallbackBlockers.push('preview_storage');
    if (readiness.provider_wire_ready === false) fallbackBlockers.push('provider_wire_schema');
    if (readiness.preview_gateway_ready === false && !blockerCodesFromServer.some(
      (item) => item === 'preview_gateway_not_configured' || item === 'preview_gateway_unreachable',
    )) fallbackBlockers.push('preview_gateway_unreachable');
    if (!readiness.build_preparation_pack_ready) fallbackBlockers.push('build_preparation_pack');
    const staticReady = readiness.can_start_best ?? fallbackBlockers.length === 0;
    const preflightRequired = readiness.provider_preflight?.status === 'required';
    readinessReady = Boolean(staticReady || (preflightRequired && fallbackBlockers.length === 0));
    const blockerCodes = blockerCodesFromServer.length
      ? blockerCodesFromServer.filter((item) => item !== 'provider_preflight_required')
      : fallbackBlockers;
    const blockers = blockerCodes.map(formatReadinessBlocker);
    const status = view('readiness');
    if (readinessReady && !blockers.length) {
      status.textContent = 'Ready to run. The first model preflight happens when you start.';
    } else if (readinessReady) {
      status.textContent = `Static checks ready; preflight will confirm the provider (${blockers.join(', ')}).`;
    } else {
      status.textContent = `Blocked by ${blockers.join(', ') || 'local readiness checks'}.`;
    }
    updateLaunchButton();
  };

  const renderPacks = (entries) => {
    const eligible = entries.filter((pack) => pack.eligible);
    const invalid = entries.filter((pack) => !pack.eligible);
    const compareRank = (a, b) => {
      const left = a.selection_rank || [];
      const right = b.selection_rank || [];
      for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
        const delta = Number(right[index] || 0) - Number(left[index] || 0);
        if (delta) return delta;
      }
      return String(b.pack_dir || '').localeCompare(String(a.pack_dir || ''));
    };
    selectedPack = eligible.slice().sort(compareRank)[0]?.pack_dir || '';
    const select = view('pack');
    const labelFor = (pack) => {
      const counts = pack.resource_counts || {};
      const resources = Number(pack.resource_coverage || counts.resource_coverage || 0);
      const visuals = Number(pack.visual_readiness || counts.visual_readiness || 0);
      return `${pack.pack_dir} · ${resources} resources · ${visuals} visual routes`;
    };
    select.replaceChildren(
      ...eligible.map((pack) => new Option(labelFor(pack), pack.pack_dir)),
      ...invalid.map((pack) => new Option(`${pack.pack_dir} · ${pack.issue || 'not eligible'}`, '')),
    );
    select.value = selectedPack;
    select.disabled = entries.length === 0;
    const status = view('pack-status');
    if (!entries.length) status.textContent = 'No eligible Build Preparation output found. Run Build Preparation first.';
    else if (selectedPack) status.textContent = `Selected ${selectedPack} · server will bind this immutable ZIP.`;
    else status.textContent = `No eligible pack is available (${entries[0].issue || 'unknown reason'}).`;
    updateLaunchButton();
  };

  const renderList = (target, items, emptyText, mapper) => {
    target.replaceChildren();
    if (!items?.length) {
      const empty = document.createElement('li');
      empty.className = 'cg-dev__empty-list';
      empty.textContent = emptyText;
      target.append(empty);
      return;
    }
    target.append(...items.map(mapper));
  };

  const diagnosticButton = (issue) => {
    if (!issue.file) return null;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'cg-dev__source-link';
    button.dataset.sourcePath = issue.file;
    button.dataset.sourceLine = String(issue.line || 1);
    button.textContent = 'Open source';
    return button;
  };

  const renderDiagnostics = (target, issues) => {
    renderList(target, issues, 'No diagnostics recorded.', (issue) => {
      const item = document.createElement('li');
      const location = issue.file ? ` · ${issue.file}${issue.line ? `:${issue.line}` : ''}` : '';
      const text = document.createElement('span');
      text.textContent = `${issue.code || 'DIAGNOSTIC'}: ${issue.normalized_message || issue.message || 'No detail'}${location}`;
      item.append(text);
      const link = diagnosticButton(issue);
      if (link) item.append(document.createTextNode(' '), link);
      return item;
    });
  };

  const renderCardList = (target, items, emptyText, title, detail) => {
    renderList(target, items, emptyText, (itemData) => {
      const item = document.createElement('li');
      const strong = document.createElement('strong');
      strong.textContent = title(itemData);
      const small = document.createElement('small');
      small.textContent = detail(itemData);
      item.append(strong, small);
      return item;
    });
  };

  const loadSource = async (path, line) => {
    const panel = view('source-debug');
    const status = view('source-debug-status');
    const code = view('source-code');
    panel.hidden = false;
    status.textContent = `Loading ${path}...`;
    code.textContent = '';
    const query = new URLSearchParams({ path, start_line: String(Math.max(1, Number(line) - 8)) });
    try {
      const result = await request(`/runs/${encodeURIComponent(activeRunId)}/source-file?${query.toString()}`);
      const first = result.start_line || 1;
      code.textContent = result.content.split('\n').map((sourceLine, index) => `${String(first + index).padStart(5, ' ')} | ${sourceLine}`).join('\n');
      status.textContent = `${result.path} · checkpoint ${String(result.checkpoint_hash || '').slice(0, 16)}`;
    } catch (error) {
      status.textContent = error.message;
    }
  };

  const loadSourceManifest = async () => {
    if (!activeRunId || sourceManifestLoadedFor === activeRunId) return;
    const status = view('source-manifest-status');
    try {
      const result = await request(`/runs/${encodeURIComponent(activeRunId)}/source-manifest`);
      sourceManifestLoadedFor = activeRunId;
      const files = result.manifest?.files || [];
      renderList(view('source-manifest'), files, 'No accepted source files recorded.', (file) => {
        const item = document.createElement('li');
        const label = document.createElement('strong');
        label.textContent = file.path || 'unknown file';
        const meta = document.createElement('small');
        meta.textContent = `${file.size_bytes || file.size || 0} bytes${file.sha256 ? ` · ${String(file.sha256).slice(0, 12)}` : ''}`;
        item.append(label, meta);
        if (file.path) {
          const button = document.createElement('button');
          button.type = 'button';
          button.dataset.sourcePath = file.path;
          button.dataset.sourceLine = '1';
          button.textContent = 'Inspect';
          item.append(button);
        }
        return item;
      });
      status.textContent = `${files.length} accepted file(s) · click Inspect for a bounded source slice.`;
    } catch (error) {
      status.textContent = error.message;
    }
  };

  const stageForRun = (run) => {
    if (run.status !== 'needs_attention') return stageOrder.findIndex((stage) => stageStatuses[stage].has(run.status));
    if (run.source_checkpoint || run.verification) return 3;
    if (run.acquire_summary || run.resource_ledger) return 1;
    return 0;
  };

  const renderStages = (run) => {
    const current = stageForRun(run);
    all('stage').forEach((item) => {
      const index = stageOrder.indexOf(item.dataset.stage);
      let state = index < current ? 'done' : index === current ? 'active' : 'pending';
      if (run.status === 'needs_attention' && index === current) state = 'error';
      if (run.status === 'ready') state = 'done';
      item.dataset.state = state;
    });
  };

  const viewportSizes = {
    mobile: { width: '390px', height: '844px' },
    tablet: { width: '768px', height: '1024px' },
    desktop: { width: '1440px', height: '900px' },
    fit: { width: '100%', height: '42rem' },
  };

  const updatePreviewFrame = () => {
    const frame = view('preview-frame');
    const routeSelect = view('preview-route');
    const empty = view('preview-empty');
    const refresh = view('preview-refresh');
    const emptyMessage = view('preview-empty-message');
    const embedStatus = view('preview-embed-status');
    if (!currentPreview?.url) {
      previewLoadSequence += 1;
      clearPreviewLoadTimer();
      previewBridgeReady = false;
      frame.removeAttribute('src');
      frame.hidden = true;
      empty.hidden = false;
      emptyMessage.textContent = 'The verified portfolio will appear here.';
      embedStatus.textContent = '';
      refresh.disabled = true;
      view('preview-open').hidden = true;
      routeSelect.disabled = true;
      return;
    }
    const routePath = selectedRoutePath.replace(/^\/+/, '');
    let nextSrc = currentPreview.url;
    try { nextSrc = routePath ? new URL(routePath, currentPreview.url).toString() : currentPreview.url; } catch { /* server supplied URL is shown as-is */ }
    const sourceChanged = frame.src !== nextSrc;
    if (sourceChanged) {
      previewLoadSequence += 1;
      clearPreviewLoadTimer();
      previewBridgeReady = false;
      frame.src = nextSrc;
    }
    const loadSequence = previewLoadSequence;
    frame.hidden = false;
    empty.hidden = true;
    emptyMessage.textContent = '';
    if (sourceChanged) embedStatus.textContent = 'Loading the embedded verified preview...';
    refresh.disabled = false;
    frame.style.width = viewportSizes[selectedViewport].width;
    frame.style.height = viewportSizes[selectedViewport].height;
    view('preview-open').href = frame.src;
    view('preview-open').hidden = false;
    routeSelect.disabled = false;
    if (sourceChanged || (!previewBridgeReady && !previewLoadTimer)) {
      previewLoadTimer = window.setTimeout(() => {
        if (loadSequence !== previewLoadSequence || previewBridgeReady) return;
        embedStatus.textContent = 'Embedded preview did not respond. Use Open preview to inspect the verified output.';
      }, 5000);
    }
  };

  const renderOutput = (run, events) => {
    const fallback = events.slice().reverse().find((event) => event.event_type === 'exported');
    const receipt = run.export_receipt || (fallback ? {
      status: 'exported',
      relative_path: fallback.details?.relative_path || '',
      folder: fallback.details?.folder || '',
      report_path: fallback.details?.report_path || 'generation-report.md',
    } : null);
    const state = view('output-state');
    const status = receipt?.status || 'not_started';
    state.dataset.state = status === 'exported' ? 'ready' : status === 'failed' ? 'error' : 'waiting';
    state.textContent = status === 'exported'
      ? 'Exported and ready for the evaluator agent.'
      : status === 'failed'
        ? `Export failed safely${receipt.error_code ? ` · ${receipt.error_code}` : ''}.`
        : run.status === 'ready' ? 'Run is ready; export receipt is still syncing.' : 'Waiting for a completed run.';
    const base = receipt?.relative_path || '';
    view('output-folder').textContent = base || '—';
    view('output-source').textContent = base && receipt.source_path ? `${base}/${receipt.source_path}` : '—';
    view('output-dist').textContent = base && receipt.dist_path ? `${base}/${receipt.dist_path}` : '—';
    view('output-report').textContent = base && receipt.report_path ? `${base}/${receipt.report_path}` : '—';
    view('output-run').textContent = run.run_id || '—';
    view('output-trace').textContent = run.trace_id || 'not assigned';
  };

  const render = ({ run, events, plan, acquisition, dependencies, generation, verification, preview }) => {
    activeRunId = run.run_id;
    activeRunStatus = run.status;
    view('status').textContent = statusLabels[run.status] || run.status;
    view('status-pill').textContent = statusLabels[run.status] || run.status;
    view('status-pill').dataset.state = run.status === 'ready' ? 'ready' : run.status === 'needs_attention' ? 'error' : 'active';
    const selectedPackReceipt = run.selected_pack_receipt;
    view('receipt').textContent = selectedPackReceipt?.pack_id
      ? `Pack ${selectedPackReceipt.pack_id} · ${selectedPackReceipt.pack_version || 'unknown'} · ${String(selectedPackReceipt.pack_sha256 || 'hash pending').slice(0, 18)}`
      : run.input_receipt?.admitted_identity ? `Receipt ${run.input_receipt.admitted_identity}` : '';
    const latestEvent = events.at(-1);
    view('event').textContent = latestEvent ? latestEvent.message : '';
    renderList(view('events'), events, 'No persisted events yet.', (event) => {
      const item = document.createElement('li');
      const sequence = document.createElement('b');
      sequence.textContent = String(event.sequence || '—').padStart(2, '0');
      const copy = document.createElement('span');
      copy.textContent = event.message || event.event_type || 'Event recorded';
      const meta = document.createElement('small');
      const detailKeys = Object.keys(event.details || {});
      meta.textContent = `${event.event_type || 'event'}${event.created_at ? ` · ${String(event.created_at).slice(11, 19)}` : ''}${detailKeys.length ? ` · ${detailKeys.length} detail(s)` : ''}`;
      const body = document.createElement('div');
      body.append(copy, meta);
      item.append(sequence, body);
      return item;
    });
    renderOutput(run, events);
    renderStages(run);
    updateLaunchButton();

    const issues = run.issues || [];
    if (run.status === 'needs_attention' && issues.length) setError(`${issues[0].code}: ${issues[0].message}`);
    else if (run.status !== 'needs_attention') setError();
    view('plan-issues').textContent = issues.length ? `${issues.length} issue(s) reported` : '';
    renderList(view('plan-issues-list'), issues, 'No plan issues recorded.', (issue) => {
      const item = document.createElement('li');
      item.textContent = `${issue.code || 'ISSUE'}: ${issue.message || 'No detail'}`;
      return item;
    });
    if (plan) view('summary').textContent = `${plan.routes?.length || 0} route(s), ${plan.work_graph?.units?.length || 0} planned work unit(s).`;

    const acquireButton = view('acquire');
    acquireButton.disabled = !plan || !['planned', 'needs_attention'].includes(run.status) || Boolean(run.acquire_summary);
    view('acquire-status').textContent = run.acquire_summary
      ? `${run.acquire_summary.request_count} request(s), ${run.acquire_summary.admitted_resource_count} admitted, ${run.acquire_summary.fallback_resource_count} fallback.`
      : run.status === 'acquiring' ? 'Resource acquisition is running.' : 'Idle.';
    renderList(view('acquire-issues'), run.acquire_summary ? issues : [], 'No acquisition issues recorded.', (issue) => {
      const item = document.createElement('li'); item.textContent = `${issue.code || 'ISSUE'}: ${issue.message || 'No detail'}`; return item;
    });
    renderCardList(view('resources'), acquisition?.receipts, 'No resource receipts yet.', (item) => item.request_hash || 'resource', (item) => `${item.disposition || 'unknown'} · ${item.provider_key || item.fallback?.implementation || 'fallback'}`);
    renderCardList(view('dependencies'), dependencies?.receipts, 'No dependency receipts yet.', (item) => item.package_name || 'No package', (item) => `${item.decision || 'unknown'} · ${item.resolved_version || item.fallback?.strategy || 'existing stack'}`);

    const generateButton = view('generate');
    generateButton.disabled = !(run.status === 'acquired' || (run.status === 'needs_attention' && Boolean(run.acquire_summary))) || Boolean(run.source_checkpoint) || Boolean(run.generation_job_id);
    view('generate-status').textContent = generation ? `${generation.phase || run.status} · ${generation.active_work_unit_id || 'no active unit'}` : 'Waiting for a resource-complete plan.';
    if (generation) {
      const checkpoint = generation.accepted_checkpoint;
      view('generation-summary').textContent = checkpoint
        ? `${generation.source_file_count || checkpoint.file_count || 0} generated file(s) · checkpoint ${String(checkpoint.checkpoint_hash || '').slice(0, 16)}.`
        : `${generation.work_units?.length || 0} work unit(s) · ${generation.request_rounds || 0} request round(s) · ${generation.repair_rounds || 0} repair round(s).`;
      renderCardList(view('work-units'), generation.work_units, 'No work units recorded yet.', (item) => item.unit_id || 'work unit', (item) => `${item.status || 'pending'} · ${item.kind || 'unit'}`);
      renderDiagnostics(view('generation-diagnostics'), generation.diagnostics || []);
    } else {
      view('generation-summary').textContent = 'No source checkpoint yet.';
      renderList(view('work-units'), [], 'No work units recorded yet.', () => document.createElement('li'));
      renderDiagnostics(view('generation-diagnostics'), []);
    }

    const verifyButton = view('verify');
    verifyButton.disabled = run.status !== 'source_ready' || Boolean(run.verification_job_id);
    view('verify-status').textContent = verification ? `${verification.phase || run.status} · ${verification.active_gate || 'complete'}` : 'Final verification has not started.';
    const quality = run.quality_review || generation?.quality_review;
    view('quality-summary').textContent = quality
      ? `Quality review: ${quality.status || 'recorded'}${quality.review_id ? ` · ${quality.review_id}` : ''}`
      : 'Quality review has not started.';
    renderCardList(view('verification-gates'), verification?.gate_results, 'No verification gates recorded yet.', (item) => item.gate_id || 'gate', (item) => `${item.status || 'pending'} · ${item.diagnostics?.length || 0} diagnostic(s)`);
    renderDiagnostics(view('verification-diagnostics'), verification?.diagnostics || []);

    currentPreview = preview?.active_preview || run.active_preview;
    const routeSelect = view('preview-route');
    const routes = (plan?.routes || []).filter((route) => route.path);
    routeSelect.replaceChildren(...routes.map((route) => new Option(route.purpose || route.route_id, route.path)));
    if (routes.length && !routes.some((route) => route.path === selectedRoutePath)) selectedRoutePath = routes[0].path;
    if (!routes.length) selectedRoutePath = '';
    routeSelect.value = selectedRoutePath;
    const latestIssue = issues[0];
    const previewStatus = view('preview-status');
    if (currentPreview?.url && run.status === 'preview_pending') previewStatus.textContent = 'Previous preview retained · new publication pending';
    else if (currentPreview?.url) previewStatus.textContent = 'Verified preview promoted';
    else if (run.status === 'preview_pending') previewStatus.textContent = 'Candidate retained · public read-back pending';
    else if (run.status === 'needs_attention') previewStatus.textContent = `Preview unavailable${latestIssue?.code ? ` · ${latestIssue.code}` : ''}`;
    else previewStatus.textContent = 'No preview yet';
    previewStatus.dataset.state = currentPreview?.url ? 'ready' : run.status === 'needs_attention' ? 'error' : 'waiting';
    const emptyMessage = view('preview-empty-message');
    if (!currentPreview?.url && run.status === 'preview_pending') emptyMessage.textContent = 'The build passed local verification, but preview publication is pending.';
    else if (!currentPreview?.url && run.status === 'needs_attention') emptyMessage.textContent = latestIssue?.message || 'The verified preview is unavailable for this run.';
    viewportButtons().forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.previewViewport === selectedViewport)));
    updatePreviewFrame();
  };

  const controller = createCodeGeneratorDevelopmentController({
    api: {
      getRun: (id) => request(`/runs/${id}`),
      getEvents: (id) => request(`/runs/${id}/events`),
      getPlan: (id) => request(`/runs/${id}/plan`),
      getAcquisition: (id) => request(`/runs/${id}/acquisition`),
      getDependencies: (id) => request(`/runs/${id}/dependencies`),
      getPlanDeltas: (id) => request(`/runs/${id}/plan-deltas`),
      getGeneration: (id) => request(`/runs/${id}/generation`),
      getVerification: (id) => request(`/runs/${id}/verification`),
      getPreview: (id) => request(`/runs/${id}/preview`),
      runAcquire: (id) => request(`/runs/${id}/acquire`, { method: 'POST', headers: { 'Idempotency-Key': requestKey() } }),
      runGenerate: (id) => request(`/runs/${id}/generate`, { method: 'POST', headers: { 'Idempotency-Key': requestKey() } }),
      runVerify: (id) => request(`/runs/${id}/verify`, { method: 'POST', headers: { 'Idempotency-Key': requestKey() } }),
      createFixture: (fixture_id) => request('/runs', { method: 'POST', headers: { 'content-type': 'application/json', 'Idempotency-Key': requestKey() }, body: JSON.stringify({ fixture_id }) }),
      createUpload: (file) => request('/runs/upload', { method: 'POST', headers: { 'content-type': 'application/zip', 'X-Upload-Filename': file.name, 'Idempotency-Key': requestKey() }, body: file }),
      getBuildPreparationPacks: () => request('/build-preparation-packs'),
      providerPreflight: () => request('/provider-preflight', { method: 'POST' }),
      createBuildPreparation: async (pack) => {
        await request('/provider-preflight', { method: 'POST' });
        return request('/runs/from-build-preparation', { method: 'POST', headers: { 'content-type': 'application/json', 'Idempotency-Key': requestKey() }, body: JSON.stringify({ pack: pack || 'best' }) });
      },
    },
    storage: localStorage,
    location,
    history,
    schedule: setTimeout,
    render,
  });

  const runAction = (action) => action().catch((error) => setError(error.message));
  request('/fixtures').then(({ fixtures }) => view('fixture').replaceChildren(...fixtures.map((item) => new Option(item.label, item.fixture_id)))).catch(() => {});
  request('/readiness').then(renderReadiness).catch(() => {
    readinessReady = false;
    view('readiness').textContent = 'Readiness could not be loaded. Check server diagnostics before starting.';
    updateLaunchButton();
  });
  controller.loadPacks().then(renderPacks).catch(() => {
    selectedPack = '';
    view('pack-status').textContent = 'Build Preparation output could not be loaded.';
    updateLaunchButton();
  });
  view('auto-advance').checked = controller.autoAdvance();
  view('auto-advance').addEventListener('change', (event) => controller.setAutoAdvance(event.target.checked));
  view('start-build-preparation').addEventListener('click', () => runAction(() => controller.startBuildPreparation(selectedPack || 'best')));
  view('pack').addEventListener('change', (event) => { selectedPack = event.target.value; updateLaunchButton(); });
  view('start-fixture').addEventListener('click', () => runAction(() => controller.startFixture(view('fixture').value)));
  view('start-upload').addEventListener('click', () => {
    const file = view('upload').files[0];
    if (file) runAction(() => controller.startUpload(file));
  });
  view('acquire').addEventListener('click', () => runAction(() => controller.acquire()));
  view('generate').addEventListener('click', () => runAction(() => controller.generate()));
  view('verify').addEventListener('click', () => runAction(() => controller.verify()));
  view('preview-route').addEventListener('change', (event) => { selectedRoutePath = event.target.value; updatePreviewFrame(); });
  viewportButtons().forEach((button) => button.addEventListener('click', () => {
    selectedViewport = button.dataset.previewViewport;
    viewportButtons().forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
    updatePreviewFrame();
  }));
  view('preview-refresh').addEventListener('click', () => {
    const frame = view('preview-frame');
    if (!frame.hidden) frame.contentWindow?.location.reload();
  });
  all('inspector-tab').forEach((tab) => tab.addEventListener('click', () => {
    const selected = tab.dataset.inspectorTab;
    all('inspector-tab').forEach((item) => item.setAttribute('aria-selected', String(item === tab)));
    all('inspector-panel').forEach((panel) => { panel.hidden = panel.dataset.inspectorPanel !== selected; });
    if (selected === 'files') loadSourceManifest();
  }));
  root.addEventListener('click', (event) => {
    const button = event.target.closest('[data-source-path]');
    if (button) loadSource(button.dataset.sourcePath, button.dataset.sourceLine);
  });

  const previewFrame = view('preview-frame');
  const previewBridgeVersion = 'preview-bridge-v1';
  const sendPreviewInit = () => {
    if (previewFrame.hidden || !previewFrame.src || !previewFrame.contentWindow) return;
    let origin;
    try { origin = new URL(previewFrame.src, location.href).origin; } catch { return; }
    previewFrame.contentWindow.postMessage({ type: 'preview:init', version: previewBridgeVersion }, origin);
  };
  previewFrame.addEventListener('load', () => { previewBridgeReady = false; sendPreviewInit(); });
  previewFrame.addEventListener('error', () => { view('preview-embed-status').textContent = 'Preview frame could not load. Use Open preview to inspect the verified output.'; });
  window.addEventListener('message', (event) => {
    if (event.source !== previewFrame.contentWindow || previewFrame.hidden || !previewFrame.src) return;
    let origin;
    try { origin = new URL(previewFrame.src, location.href).origin; } catch { return; }
    if (event.origin !== origin) return;
    if (event.data?.type === 'preview:ready' && event.data?.version === previewBridgeVersion) {
      previewBridgeReady = true;
      clearPreviewLoadTimer();
      view('preview-embed-status').textContent = 'Embedded preview connected.';
      sendPreviewInit();
    }
  });
  controller.loadRun().catch((error) => setError(error.message));
  return controller;
}
