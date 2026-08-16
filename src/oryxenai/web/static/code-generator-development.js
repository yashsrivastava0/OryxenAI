import { createCodeGeneratorDevelopmentController } from './code-generator-development-controller.mjs';

const root = document.querySelector('[data-code-generator-development]');
if (root) {
  const apiRoot = '/api/v1/development/code-generator';
  const view = (name) => root.querySelector(`[data-${name}]`);
  const viewportButtons = () => root.querySelectorAll('[data-preview-viewport]');
  const request = async (path, options = {}) => {
    const response = await fetch(`${apiRoot}${path}`, options);
    const body = await response.json();
    if (!response.ok) throw new Error(body.message || 'The development request failed.');
    return body;
  };
  const requestKey = () => crypto.randomUUID();
  const renderReadiness = (readiness) => {
    const planner = readiness.planning_ready ? 'planner ready' : 'planner configuration required';
    const generation = readiness.generation_ready ? 'generation profiles ready' : 'generation profile configuration required';
    const packageManager = readiness.package_manager_ready ? 'package manager ready' : 'package manager unavailable';
    const offline = readiness.offline_install_policy ? 'offline installs enforced' : 'network installs enabled by policy';
    const browser = readiness.browser_ready ? 'verification browser ready' : 'verification browser missing';
    const pack = readiness.build_preparation_pack_ready
      ? `Build Preparation pack ready (${readiness.build_preparation_latest.pack_dir})`
      : 'no eligible Build Preparation pack';
    view('readiness').textContent = planner + '; ' + generation + '; ' + packageManager + '; ' + offline + '; ' + browser + '; ' + pack + '.';
  };
  const renderPacks = (packs) => {
    const select = view('pack');
    const eligible = packs.filter((pack) => pack.eligible);
    const ineligible = packs.filter((pack) => !pack.eligible);
    const option = (pack, suffix) => new Option(
      `${pack.pack_dir}${suffix ? ` — ${suffix}` : ''}`,
      pack.eligible ? pack.pack_dir : ''
    );
    select.replaceChildren(
      ...eligible.map((pack) => option(pack, `expires ${String(pack.expires_at || '').slice(0, 16).replace('T', ' ')}`)),
      ...ineligible.map((pack) => option(pack, pack.issue || 'not eligible'))
    );
    select.disabled = eligible.length === 0;
    const newest = eligible[0] || packs[0];
    view('pack-status').textContent = packs.length === 0
      ? 'No Build Preparation output found in the local mirror. Run Build Preparation first.'
      : newest && newest.eligible
        ? `${eligible.length} eligible pack(s); newest ${newest.pack_dir} expires ${String(newest.expires_at || '').slice(0, 16).replace('T', ' ')}.`
        : `Newest pack is not eligible: ${newest ? newest.issue : 'unknown'}. Re-run Build Preparation.`;
    view('start-build-preparation').disabled = eligible.length === 0;
  };
  const viewportSizes = {
    mobile: { width: '390px', height: '844px' },
    tablet: { width: '768px', height: '1024px' },
    desktop: { width: '1440px', height: '900px' },
    fit: { width: '100%', height: '42rem' },
  };
  let selectedRoutePath = '';
  let selectedViewport = 'fit';
  let currentPreview = null;
  const updatePreviewFrame = () => {
    const frame = view('preview-frame');
    const routeSelect = view('preview-route');
    if (!currentPreview?.url) {
      frame.removeAttribute('src');
      frame.hidden = true;
      view('preview-open').hidden = true;
      routeSelect.disabled = true;
      return;
    }
    const routePath = selectedRoutePath.replace(/^\/+/, '');
    frame.src = routePath ? new URL(routePath, currentPreview.url).toString() : currentPreview.url;
    frame.hidden = false;
    frame.style.width = viewportSizes[selectedViewport].width;
    frame.style.height = viewportSizes[selectedViewport].height;
    view('preview-open').href = frame.src;
    view('preview-open').hidden = false;
    routeSelect.disabled = false;
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
  const render = ({ run, events, plan, acquisition, dependencies, generation, verification, preview }) => {
    view('status').textContent = `${run.status} - ${run.run_id}`;
    view('receipt').textContent = run.input_receipt?.admitted_identity || '';
    view('plan-issues').replaceChildren(...(run.status === 'needs_attention' && !run.acquire_summary ? (run.issues || []).map((issue) => Object.assign(document.createElement('li'), { textContent: `${issue.code}: ${issue.message}` })) : []));
    view('acquire-issues').replaceChildren(...(run.acquire_summary ? (run.issues || []).map((issue) => Object.assign(document.createElement('li'), { className: 'cg-dev__issue-card', textContent: `${issue.code}: ${issue.message}` })) : []));
    view('events').replaceChildren(...events.map((event) => Object.assign(document.createElement('li'), { textContent: `${event.sequence}. ${event.message}` })));
    if (plan) view('summary').textContent = `${plan.routes.length} route(s), ${plan.work_graph.units.length} planned work unit(s).`;
    const acquireButton = view('acquire');
    acquireButton.disabled = !plan || !['planned', 'needs_attention'].includes(run.status) || Boolean(run.acquire_summary);
    view('acquire-status').textContent = run.acquire_summary ? `${run.acquire_summary.request_count} request(s), ${run.acquire_summary.admitted_resource_count} admitted, ${run.acquire_summary.fallback_resource_count} fallback.` : run.status === 'acquiring' ? 'Acquisition is running.' : 'Idle.';
    view('resources').replaceChildren(...((acquisition?.receipts || []).map((receipt) => card('cg-dev__resource-card', receipt.request_hash, receipt.disposition, receipt.provider_key || receipt.fallback?.implementation || 'No external resource selected.'))));
    view('dependencies').replaceChildren(...((dependencies?.receipts || []).map((receipt) => card('cg-dev__dependency-card', receipt.package_name || 'No package', receipt.decision, receipt.resolved_version || receipt.fallback?.strategy || 'No package mutation.'))));
    const generateButton = view('generate');
    generateButton.disabled = !(run.status === 'acquired' || (run.status === 'needs_attention' && Boolean(run.acquire_summary))) || Boolean(run.source_checkpoint) || Boolean(run.generation_job_id);
    view('generate-status').textContent = generation
      ? `${generation.phase || run.status} - ${generation.active_work_unit_id || 'no active unit'}`
      : run.status === 'queued' ? 'Generation is queued.' : 'Waiting for a resource-complete plan.';
    if (generation) {
      const checkpoint = generation.accepted_checkpoint;
      view('generation-summary').textContent = checkpoint
        ? `${generation.source_file_count || checkpoint.file_count} generated file(s), checkpoint ${checkpoint.checkpoint_hash.slice(0, 16)}. Source is ready; final build/preview has not run.`
        : `${generation.work_units?.length || 0} work unit(s), ${generation.request_rounds || 0} resource request round(s), ${generation.repair_rounds || 0} repair round(s).`;
      view('work-units').replaceChildren(...(generation.work_units || []).map((unit) => card('cg-dev__resource-card', unit.unit_id, unit.status, `${unit.kind} - ${unit.checkpoint_after ? unit.checkpoint_after.slice(0, 12) : 'pending'}`)));
      view('generation-diagnostics').replaceChildren(...(generation.diagnostics || []).map((issue) => Object.assign(document.createElement('li'), { className: 'cg-dev__issue-card', textContent: `${issue.code}: ${issue.normalized_message}` })));
    } else {
      view('generation-summary').textContent = 'No source checkpoint yet.';
      view('work-units').replaceChildren();
      view('generation-diagnostics').replaceChildren();
    }
    const verifyButton = view('verify');
    verifyButton.disabled = run.status !== 'source_ready' || Boolean(run.verification_job_id);
    view('verify-status').textContent = verification
      ? `${verification.phase || run.status} - ${verification.active_gate || 'complete'}`
      : run.status === 'source_ready' ? 'Source is ready for final build and smoke verification.' : 'Final verification has not started.';
    const gateList = view('verification-gates');
    gateList.replaceChildren(...((verification?.gate_results || []).map((gate) => card('cg-dev__gate-card', gate.gate_id, gate.status, `${gate.diagnostics?.length || 0} diagnostic(s)`))));
    view('verification-diagnostics').replaceChildren(...((verification?.diagnostics || []).map((issue) => Object.assign(document.createElement('li'), { className: 'cg-dev__issue-card', textContent: `${issue.code}: ${issue.normalized_message}` }))));
    const activePreview = preview?.active_preview || run.active_preview;
    currentPreview = activePreview;
    const routeSelect = view('preview-route');
    const routes = (plan?.routes || []).filter((route) => route.path);
    routeSelect.replaceChildren(...routes.map((route) => new Option(route.purpose || route.route_id, route.path)));
    if (routes.length && !routes.some((route) => route.path === selectedRoutePath)) selectedRoutePath = routes[0].path;
    if (!routes.length) selectedRoutePath = '';
    routeSelect.value = selectedRoutePath;
    view('preview-status').textContent = activePreview
      ? `Promoted ${activePreview.build_hash?.slice(0, 16) || 'preview'} - ${activePreview.url}`
      : 'No verified preview has been promoted yet.';
    viewportButtons().forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.previewViewport === selectedViewport));
    });
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
  request('/fixtures').then(({ fixtures }) => view('fixture').replaceChildren(...fixtures.map((item) => new Option(item.label, item.fixture_id))));
  request('/readiness').then(renderReadiness).catch(() => {
    view('readiness').textContent = 'Readiness could not be loaded. Review the server diagnostics before starting a run.';
  });
  controller.loadPacks().then(renderPacks).catch(() => {
    view('pack-status').textContent = 'Build Preparation packs could not be loaded.';
  });
  view('auto-advance').checked = controller.autoAdvance();
  view('auto-advance').addEventListener('change', (event) => controller.setAutoAdvance(event.target.checked));
  view('start-build-preparation').addEventListener('click', () => controller.startBuildPreparation(view('pack').value || 'latest'));
  view('start-fixture').addEventListener('click', () => controller.startFixture(view('fixture').value));
  view('start-upload').addEventListener('click', () => { const file = view('upload').files[0]; if (file) controller.startUpload(file); });
  view('acquire').addEventListener('click', () => controller.acquire());
  view('generate').addEventListener('click', () => controller.generate());
  view('verify').addEventListener('click', () => controller.verify());
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
  controller.loadRun();
}
