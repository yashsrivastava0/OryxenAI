import { createCodeGeneratorDevelopmentController } from './code-generator-development-controller.mjs';

const root = document.querySelector('[data-code-generator-development]');

if (root) {
  const apiRoot = '/api/v1/development/code-generator';
  const view = (name) => root.querySelector(`[data-${name}]`);
  const all = (name) => root.querySelectorAll(`[data-${name}]`);
  const viewportButtons = () => all('preview-viewport');
  const activeStatuses = new Set([
    'queued', 'planning', 'planned', 'acquiring', 'generating_foundation',
    'generating_routes', 'integrating', 'source_ready', 'building',
    'smoke_testing', 'repairing',
  ]);
  const stageStatuses = {
    prepare: new Set(['queued', 'planning', 'planned']),
    resources: new Set(['acquiring', 'acquired']),
    source: new Set(['generating_foundation', 'generating_routes', 'integrating', 'source_ready']),
    verify: new Set(['building', 'smoke_testing', 'repairing', 'ready']),
  };
  const stageOrder = ['prepare', 'resources', 'source', 'verify'];
  const statusLabels = {
    queued: 'Queued', planning: 'Admitting pack', planned: 'Plan ready',
    acquiring: 'Preparing resources', acquired: 'Resources ready',
    generating_foundation: 'Building visual foundation', generating_routes: 'Building routes',
    integrating: 'Connecting the portfolio', source_ready: 'Source ready',
    building: 'Building production output', smoke_testing: 'Testing the preview',
    repairing: 'Applying bounded repair', ready: 'Preview promoted',
    needs_attention: 'Needs attention',
  };
  const request = async (path, options = {}) => {
    const response = await fetch(`${apiRoot}${path}`, options);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.message || body.detail || 'The development request failed.');
    return body;
  };
  const requestKey = () => globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;

  let readinessReady = false;
  let selectedPack = '';
  let activeRunStatus = '';
  let selectedRoutePath = '';
  let selectedViewport = 'fit';
  let currentPreview = null;

  const setError = (message = '') => {
    const error = view('start-error');
    error.textContent = message;
    error.hidden = !message;
  };

  const updateLaunchButton = () => {
    const button = view('start-build-preparation');
    const busy = activeStatuses.has(activeRunStatus);
    button.disabled = !selectedPack || !readinessReady || busy;
    button.textContent = busy ? 'Generating...' : activeRunStatus === 'ready' ? 'Generate again' : 'Generate portfolio';
  };

  const renderReadiness = (readiness) => {
    const fallbackBlockers = [];
    if (!readiness.planning_ready) fallbackBlockers.push('planner configuration');
    if (!readiness.generation_ready) fallbackBlockers.push('generation profiles');
    if (!readiness.package_manager_ready) fallbackBlockers.push('npm');
    if (!readiness.browser_ready) fallbackBlockers.push('verification browser');
    if (!readiness.build_preparation_pack_ready) fallbackBlockers.push('eligible Build Preparation pack');
    readinessReady = readiness.can_start_latest ?? fallbackBlockers.length === 0;
    const blockers = Array.isArray(readiness.readiness_blockers) && readiness.readiness_blockers.length
      ? readiness.readiness_blockers
      : fallbackBlockers;
    const target = readiness.build_preparation_latest?.pack_dir;
    view('readiness').textContent = readinessReady
      ? `Ready to run${target ? ` with ${target}` : ''}.`
      : `Waiting for ${blockers.join(', ')}.`;
    view('readiness').dataset.state = readinessReady ? 'ready' : 'waiting';
    updateLaunchButton();
  };

  const renderPacks = (packs) => {
    const entries = Array.isArray(packs) ? packs : [];
    const eligible = entries.filter((pack) => pack.eligible);
    const invalid = entries.filter((pack) => !pack.eligible);
    selectedPack = eligible[0]?.pack_dir || '';
    const select = view('pack');
    select.replaceChildren(
      ...eligible.map((pack) => new Option(
        `${pack.pack_dir} - expires ${String(pack.expires_at || '').slice(0, 16).replace('T', ' ')}`,
        pack.pack_dir,
      )),
      ...invalid.map((pack) => new Option(`${pack.pack_dir} - ${pack.issue || 'not eligible'}`, '')),
    );
    select.value = selectedPack;
    select.disabled = entries.length === 0;
    if (!entries.length) {
      view('pack-status').textContent = 'No eligible Build Preparation output found. Run Build Preparation first.';
    } else if (selectedPack) {
      view('pack-status').textContent = `Using newest eligible pack ${selectedPack}.`;
    } else {
      view('pack-status').textContent = `No eligible pack is available (${entries[0].issue || 'unknown reason'}).`;
    }
    updateLaunchButton();
  };

  const card = (className, title, status, detail) => {
    const item = document.createElement('li');
    item.className = className;
    const strong = document.createElement('strong');
    strong.textContent = title;
    const badge = document.createElement('span');
    badge.className = 'cg-dev__badge';
    badge.textContent = status;
    const small = document.createElement('small');
    small.textContent = detail;
    item.append(strong, badge, small);
    return item;
  };

  const stageForRun = (run) => {
    if (run.status !== 'needs_attention') {
      return stageOrder.findIndex((stage) => stageStatuses[stage].has(run.status));
    }
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
    if (!currentPreview?.url) {
      frame.removeAttribute('src');
      frame.hidden = true;
      empty.hidden = false;
      refresh.disabled = true;
      view('preview-open').hidden = true;
      routeSelect.disabled = true;
      return;
    }
    const routePath = selectedRoutePath.replace(/^\/+/, '');
    frame.src = routePath ? new URL(routePath, currentPreview.url).toString() : currentPreview.url;
    frame.hidden = false;
    empty.hidden = true;
    refresh.disabled = false;
    frame.style.width = viewportSizes[selectedViewport].width;
    frame.style.height = viewportSizes[selectedViewport].height;
    view('preview-open').href = frame.src;
    view('preview-open').hidden = false;
    routeSelect.disabled = false;
  };

  const render = ({ run, events, plan, acquisition, dependencies, generation, verification, preview }) => {
    activeRunStatus = run.status;
    const label = statusLabels[run.status] || run.status;
    view('status').textContent = label;
    view('status-pill').textContent = label;
    view('status-pill').dataset.state = run.status === 'ready' ? 'ready' : run.status === 'needs_attention' ? 'error' : 'active';
    view('receipt').textContent = run.input_receipt?.admitted_identity ? `Receipt ${run.input_receipt.admitted_identity}` : '';
    const latestEvent = events.at(-1);
    view('event').textContent = latestEvent ? latestEvent.message : '';
    view('events').replaceChildren(...events.map((event) => Object.assign(document.createElement('li'), { textContent: `${event.sequence}. ${event.message}` })));
    view('status').setAttribute('aria-live', 'polite');
    renderStages(run);
    updateLaunchButton();

    const issues = run.issues || [];
    if (run.status === 'needs_attention' && issues.length) {
      setError(`${issues[0].code}: ${issues[0].message}`);
    } else if (run.status !== 'needs_attention') {
      setError();
    }
    view('plan-issues').textContent = issues.length ? `${issues.length} issue(s) reported` : '';
    view('plan-issues-list').replaceChildren(...issues.map((issue) => Object.assign(document.createElement('li'), { textContent: `${issue.code}: ${issue.message}` })));
    if (plan) view('summary').textContent = `${plan.routes.length} route(s), ${plan.work_graph.units.length} planned work unit(s).`;

    const acquireButton = view('acquire');
    acquireButton.disabled = !plan || !['planned', 'needs_attention'].includes(run.status) || Boolean(run.acquire_summary);
    view('acquire-status').textContent = run.acquire_summary
      ? `${run.acquire_summary.request_count} request(s), ${run.acquire_summary.admitted_resource_count} admitted, ${run.acquire_summary.fallback_resource_count} fallback.`
      : run.status === 'acquiring' ? 'Resource acquisition is running.' : 'Idle.';
    view('acquire-issues').replaceChildren(...(run.acquire_summary ? issues.map((issue) => Object.assign(document.createElement('li'), { textContent: `${issue.code}: ${issue.message}` })) : []));
    view('resources').replaceChildren(...((acquisition?.receipts || []).map((receipt) => card('cg-dev__resource-card', receipt.request_hash, receipt.disposition, receipt.provider_key || receipt.fallback?.implementation || 'No external resource selected.'))));
    view('dependencies').replaceChildren(...((dependencies?.receipts || []).map((receipt) => card('cg-dev__dependency-card', receipt.package_name || 'No package', receipt.decision, receipt.resolved_version || receipt.fallback?.strategy || 'No package mutation.'))));

    const generateButton = view('generate');
    generateButton.disabled = !(run.status === 'acquired' || (run.status === 'needs_attention' && Boolean(run.acquire_summary))) || Boolean(run.source_checkpoint) || Boolean(run.generation_job_id);
    view('generate-status').textContent = generation ? `${generation.phase || run.status} - ${generation.active_work_unit_id || 'no active unit'}` : 'Waiting for a resource-complete plan.';
    if (generation) {
      const checkpoint = generation.accepted_checkpoint;
      view('generation-summary').textContent = checkpoint
        ? `${generation.source_file_count || checkpoint.file_count} generated file(s), checkpoint ${checkpoint.checkpoint_hash.slice(0, 16)}.`
        : `${generation.work_units?.length || 0} work unit(s), ${generation.request_rounds || 0} request round(s), ${generation.repair_rounds || 0} repair round(s).`;
      view('work-units').replaceChildren(...(generation.work_units || []).map((unit) => card('cg-dev__resource-card', unit.unit_id, unit.status, `${unit.kind} - ${unit.checkpoint_after ? unit.checkpoint_after.slice(0, 12) : 'pending'}`)));
      view('generation-diagnostics').replaceChildren(...(generation.diagnostics || []).map((issue) => Object.assign(document.createElement('li'), { textContent: `${issue.code}: ${issue.normalized_message}` })));
    } else {
      view('generation-summary').textContent = 'No source checkpoint yet.';
      view('work-units').replaceChildren();
      view('generation-diagnostics').replaceChildren();
    }

    const verifyButton = view('verify');
    verifyButton.disabled = run.status !== 'source_ready' || Boolean(run.verification_job_id);
    view('verify-status').textContent = verification ? `${verification.phase || run.status} - ${verification.active_gate || 'complete'}` : 'Final verification has not started.';
    view('verification-gates').replaceChildren(...((verification?.gate_results || []).map((gate) => card('cg-dev__gate-card', gate.gate_id, gate.status, `${gate.diagnostics?.length || 0} diagnostic(s)`))));
    view('verification-diagnostics').replaceChildren(...((verification?.diagnostics || []).map((issue) => Object.assign(document.createElement('li'), { textContent: `${issue.code}: ${issue.normalized_message}` }))));

    currentPreview = preview?.active_preview || run.active_preview;
    const routeSelect = view('preview-route');
    const routes = (plan?.routes || []).filter((route) => route.path);
    routeSelect.replaceChildren(...routes.map((route) => new Option(route.purpose || route.route_id, route.path)));
    if (routes.length && !routes.some((route) => route.path === selectedRoutePath)) selectedRoutePath = routes[0].path;
    if (!routes.length) selectedRoutePath = '';
    routeSelect.value = selectedRoutePath;
    view('preview-status').textContent = currentPreview?.url ? 'Verified preview promoted' : run.status === 'needs_attention' ? 'Preview unavailable for this run' : 'No preview yet';
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
      createBuildPreparation: (pack) => request('/runs/from-build-preparation', { method: 'POST', headers: { 'content-type': 'application/json', 'Idempotency-Key': requestKey() }, body: JSON.stringify({ pack: pack || 'latest' }) }),
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
  view('start-build-preparation').addEventListener('click', () => runAction(() => controller.startBuildPreparation(selectedPack || 'latest')));
  view('pack').addEventListener('change', (event) => { selectedPack = event.target.value; updateLaunchButton(); });
  view('start-fixture').addEventListener('click', () => runAction(() => controller.startFixture(view('fixture').value)));
  view('start-upload').addEventListener('click', () => {
    const file = view('upload').files[0];
    if (file) runAction(() => controller.startUpload(file));
  });
  view('acquire').addEventListener('click', () => runAction(() => controller.acquire()));
  view('generate').addEventListener('click', () => runAction(() => controller.generate()));
  view('verify').addEventListener('click', () => runAction(() => controller.verify()));
  view('preview-route').addEventListener('change', (event) => {
    selectedRoutePath = event.target.value;
    updatePreviewFrame();
  });
  viewportButtons().forEach((button) => button.addEventListener('click', () => {
    selectedViewport = button.dataset.previewViewport;
    viewportButtons().forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
    updatePreviewFrame();
  }));
  view('preview-refresh').addEventListener('click', () => {
    const frame = view('preview-frame');
    if (!frame.hidden) frame.contentWindow?.location.reload();
  });

  const previewFrame = view('preview-frame');
  const previewBridgeVersion = 'preview-bridge-v1';
  const sendPreviewInit = () => {
    if (previewFrame.hidden || !previewFrame.src || !previewFrame.contentWindow) return;
    const origin = new URL(previewFrame.src, location.href).origin;
    previewFrame.contentWindow.postMessage({ type: 'preview:init', version: previewBridgeVersion }, origin);
  };
  previewFrame.addEventListener('load', sendPreviewInit);
  window.addEventListener('message', (event) => {
    if (event.source !== previewFrame.contentWindow || previewFrame.hidden || !previewFrame.src) return;
    const origin = new URL(previewFrame.src, location.href).origin;
    if (event.origin !== origin) return;
    if (event.data?.type === 'preview:ready' && event.data?.version === previewBridgeVersion) sendPreviewInit();
  });
  controller.loadRun().catch((error) => setError(error.message));
}
