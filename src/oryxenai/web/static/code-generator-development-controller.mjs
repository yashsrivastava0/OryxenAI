export function createCodeGeneratorDevelopmentController({
  api,
  storage,
  location,
  history,
  schedule,
  render,
}) {
  let activeRun =
    new URLSearchParams(location.search).get("run") ||
    storage.getItem("oryxenai.codegen.run");

  const activate = async (run) => {
    activeRun = run.run_id;
    storage.setItem("oryxenai.codegen.run", activeRun);
    history.replaceState({}, "", `?run=${encodeURIComponent(activeRun)}`);
    await loadRun();
    return run;
  };

  const loadRun = async () => {
    if (!activeRun) return null;
    const run = await api.getRun(activeRun);
    const eventResponse = await api.getEvents(activeRun);
    const plan = ["planned", "acquiring", "acquired", "generating_foundation", "generating_routes", "integrating", "source_ready", "queued", "building", "smoke_testing", "repairing", "ready", "needs_attention"].includes(run.status)
      ? await api.getPlan(activeRun).catch(() => null)
      : null;
    const acquisition = ["acquired", "needs_attention"].includes(run.status) && api.getAcquisition
      ? await api.getAcquisition(activeRun).catch(() => null)
      : null;
    const dependencies = ["acquired", "needs_attention"].includes(run.status) && api.getDependencies
      ? await api.getDependencies(activeRun).catch(() => null)
      : null;
    const planDeltas = ["acquired", "needs_attention"].includes(run.status) && api.getPlanDeltas
      ? await api.getPlanDeltas(activeRun).catch(() => null)
      : null;
    const generation = api.getGeneration && ["queued", "generating_foundation", "generating_routes", "integrating", "source_ready", "building", "smoke_testing", "repairing", "ready", "needs_attention"].includes(run.status)
      ? await api.getGeneration(activeRun).catch(() => null)
      : null;
    const verification = api.getVerification && ["queued", "building", "smoke_testing", "repairing", "ready", "needs_attention"].includes(run.status)
      ? await api.getVerification(activeRun).catch(() => null)
      : null;
    const preview = api.getPreview && ["ready", "building", "smoke_testing", "repairing", "needs_attention"].includes(run.status)
      ? await api.getPreview(activeRun).catch(() => null)
      : null;
    const result = { run, events: eventResponse.events || [], plan, acquisition, dependencies, planDeltas, generation, verification, preview };
    render(result);
    if (!["planned", "acquired", "source_ready", "ready", "needs_attention"].includes(run.status)) schedule(loadRun, 1200);
    return result;
  };

  return {
    activeRun: () => activeRun,
    loadRun,
    startFixture: async (fixtureId) => activate(await api.createFixture(fixtureId)),
    startUpload: async (file) => activate(await api.createUpload(file)),
    acquire: async () => {
      if (!activeRun || !api.runAcquire) return null;
      const run = await api.runAcquire(activeRun);
      await loadRun();
      return run;
    },
    generate: async () => {
      if (!activeRun || !api.runGenerate) return null;
      const run = await api.runGenerate(activeRun);
      await loadRun();
      return run;
    },
    verify: async () => {
      if (!activeRun || !api.runVerify) return null;
      const run = await api.runVerify(activeRun);
      await loadRun();
      return run;
    },
  };
}
