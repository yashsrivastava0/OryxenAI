import assert from 'node:assert/strict';
import test from 'node:test';

import { createCodeGeneratorDevelopmentController } from '../../src/oryxenai/web/static/code-generator-development-controller.mjs';

function harness({ search = '', storedRun = null, status = 'planned' } = {}) {
  const calls = [];
  const renders = [];
  const scheduled = [];
  const storage = new Map(storedRun ? [['oryxenai.codegen.run', storedRun]] : []);
  const api = {
    getRun: async (id) => {
      calls.push(['getRun', id]);
      return { run_id: id, status };
    },
    getEvents: async (id) => {
      calls.push(['getEvents', id]);
      return { events: [{ sequence: 1, message: 'admitted' }] };
    },
    getPlan: async (id) => {
      calls.push(['getPlan', id]);
      return { plan_id: `plan-${id}`, routes: [], work_graph: { units: [] } };
    },
    getAcquisition: async (id) => {
      calls.push(['getAcquisition', id]);
      return { receipts: [], bindings: [], requests: [] };
    },
    getDependencies: async (id) => {
      calls.push(['getDependencies', id]);
      return { receipts: [] };
    },
    getPlanDeltas: async (id) => {
      calls.push(['getPlanDeltas', id]);
      return { count: 0, deltas: [] };
    },
    getGeneration: async (id) => {
      calls.push(['getGeneration', id]);
      return { phase: 'generating_routes', active_work_unit_id: 'route-home', work_units: [] };
    },
    getVerification: async (id) => {
      calls.push(['getVerification', id]);
      return { phase: 'smoke_testing', active_gate: 'dom_runtime', gate_results: [] };
    },
    getPreview: async (id) => {
      calls.push(['getPreview', id]);
      return { active_preview: null };
    },
    runAcquire: async (id) => {
      calls.push(['runAcquire', id]);
      return { run_id: id, status: 'acquiring' };
    },
    runGenerate: async (id) => {
      calls.push(['runGenerate', id]);
      return { run_id: id, status: 'queued' };
    },
    runVerify: async (id) => {
      calls.push(['runVerify', id]);
      return { run_id: id, status: 'queued' };
    },
    createFixture: async (fixtureId) => {
      calls.push(['createFixture', fixtureId]);
      return { run_id: 'fixture-run', status: 'queued' };
    },
    createUpload: async (file) => {
      calls.push(['createUpload', file.name]);
      return { run_id: 'upload-run', status: 'queued' };
    },
  };
  return {
    calls,
    renders,
    scheduled,
    controller: createCodeGeneratorDevelopmentController({
      api,
      storage: {
        getItem: (key) => storage.get(key) || null,
        setItem: (key, value) => storage.set(key, value),
      },
      location: { search },
      history: { replaceState: (_state, _title, url) => calls.push(['replaceState', url]) },
      schedule: (callback, delay) => scheduled.push([callback, delay]),
      render: (value) => renders.push(value),
    }),
  };
}

test('fixture start persists the run, updates the URL, and renders its event stream', async () => {
  const subject = harness();
  await subject.controller.startFixture('privacy-safe-v3');
  assert.equal(subject.controller.activeRun(), 'fixture-run');
  assert.deepEqual(subject.calls.slice(0, 4), [
    ['createFixture', 'privacy-safe-v3'],
    ['replaceState', '?run=fixture-run'],
    ['getRun', 'fixture-run'],
    ['getEvents', 'fixture-run'],
  ]);
  assert.equal(subject.renders[0].events[0].message, 'admitted');
});

test('upload start uses the same restoration and polling path', async () => {
  const subject = harness({ status: 'planning' });
  await subject.controller.startUpload({ name: 'portfolio.zip' });
  assert.equal(subject.controller.activeRun(), 'upload-run');
  assert.deepEqual(subject.calls.slice(0, 2), [
    ['createUpload', 'portfolio.zip'],
    ['replaceState', '?run=upload-run'],
  ]);
  assert.equal(subject.scheduled[0][1], 1200);
});

test('query-string restoration fetches the accepted plan before rendering', async () => {
  const subject = harness({ search: '?run=restored-run' });
  const result = await subject.controller.loadRun();
  assert.equal(subject.controller.activeRun(), 'restored-run');
  assert.equal(result.plan.plan_id, 'plan-restored-run');
  assert.deepEqual(subject.calls, [
    ['getRun', 'restored-run'],
    ['getEvents', 'restored-run'],
    ['getPlan', 'restored-run'],
  ]);
});

test('acquired restoration loads resource, dependency, and delta projections', async () => {
  const subject = harness({ search: '?run=acquired-run', status: 'acquired' });
  const result = await subject.controller.loadRun();
  assert.equal(result.run.status, 'acquired');
  assert.deepEqual(subject.calls, [
    ['getRun', 'acquired-run'],
    ['getEvents', 'acquired-run'],
    ['getPlan', 'acquired-run'],
    ['getAcquisition', 'acquired-run'],
    ['getDependencies', 'acquired-run'],
    ['getPlanDeltas', 'acquired-run'],
  ]);
});

test('acquire action invokes the durable endpoint and schedules polling', async () => {
  const subject = harness({ storedRun: 'planned-run', status: 'planning' });
  await subject.controller.acquire();
  assert.deepEqual(subject.calls.slice(0, 4), [
    ['runAcquire', 'planned-run'],
    ['getRun', 'planned-run'],
    ['getEvents', 'planned-run'],
  ]);
  assert.equal(subject.scheduled[0][1], 1200);
});

test('generation restoration loads the durable generation projection', async () => {
  const subject = harness({ search: '?run=generating-run', status: 'generating_routes' });
  const result = await subject.controller.loadRun();
  assert.equal(result.generation.active_work_unit_id, 'route-home');
  assert.equal(subject.calls.at(-1)[0], 'getGeneration');
});

test('generate action invokes the durable endpoint', async () => {
  const subject = harness({ storedRun: 'acquired-run', status: 'acquired' });
  await subject.controller.generate();
  assert.deepEqual(subject.calls.slice(0, 4), [
    ['runGenerate', 'acquired-run'],
    ['getRun', 'acquired-run'],
    ['getEvents', 'acquired-run'],
    ['getPlan', 'acquired-run'],
  ]);
});

test('verification restoration loads final gate and preview projections', async () => {
  const subject = harness({ search: '?run=verify-run', status: 'smoke_testing' });
  const result = await subject.controller.loadRun();
  assert.equal(result.verification.active_gate, 'dom_runtime');
  assert.deepEqual(subject.calls.slice(-2), [
    ['getVerification', 'verify-run'],
    ['getPreview', 'verify-run'],
  ]);
});

test('verify action invokes the durable verification endpoint', async () => {
  const subject = harness({ storedRun: 'source-ready-run', status: 'source_ready' });
  await subject.controller.verify();
  assert.equal(subject.calls[0][0], 'runVerify');
});
