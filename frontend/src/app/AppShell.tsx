import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "preact/hooks";
import { AppStoreContext, appReducer, initialAppState } from "./store";
import { createApiClient, type AuthorizedFetch, type CacheReceipt, type MeProjection, type StageEnvelope } from "../data/api-client";
import { adaptDiscovery } from "../data/adapters/discovery";
import { adaptContentArchitect } from "../data/adapters/content";
import { adaptVisualDesignDirector } from "../data/adapters/design";
import { clearIdempotencyKey, getOrCreateIdempotencyKey } from "../data/idempotency";
import { createInvalidationChannel, type InvalidationChannel } from "../data/invalidation";
import { PollCoordinator } from "../data/polling";
import { ConnectionBanner } from "../components/ConnectionBanner";
import { CacheNotice } from "../components/CacheNotice";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { JourneyRail, type JourneyStageVM } from "../components/JourneyRail";
import { LivingDraftMark } from "../components/LivingDraftMark";
import { StartSurface } from "../components/StartSurface";
import { StatusAnnouncer } from "../components/StatusAnnouncer";
import { ContentStage } from "../stages/content/ContentStage";
import { DesignStage } from "../stages/design/DesignStage";
import { DiscoveryStage } from "../stages/discovery/DiscoveryStage";
import { parseAppUrlState, serializeAppUrlState, type JourneyStageId } from "./url-state";
import { safeSessionStorage } from "../data/safe-storage";
import { getClientTraceId, recordClientEvent } from "../data/client-diagnostics";
import { ClientTraceNotice } from "../components/ClientTraceNotice";

export interface AppShellProps {
  authorizedFetch: AuthorizedFetch;
  me: MeProjection;
  serverSessionId: string | null;
  readOnly: boolean;
}

function viewForStage(stage: JourneyStageId): "work" | "artifact" {
  return stage === "discover" ? "work" : "artifact";
}

function activeSessionStorageKey(userId: string): string {
  return `oryxenai.active_session_id:${userId}`;
}

export function AppShell({ authorizedFetch, me, serverSessionId, readOnly }: AppShellProps) {
  const initialUrl = useMemo(
    () => parseAppUrlState(typeof window === "undefined" ? "" : window.location.search),
    [],
  );
  const initialStage = initialUrl.stage ?? "discover";
  const [activeStage, setActiveStage] = useState<JourneyStageId>(initialStage);
  const [mutatingStage, setMutatingStage] = useState<JourneyStageId | null>(null);

  // Normal users receive their single owner-scoped session from /me. Admins
  // can work across explicitly created sessions, so retain only an
  // account-scoped hint for that developer/admin workflow.
  const scopedSessionKey = useMemo(() => activeSessionStorageKey(me.id), [me.id]);
  const initialSessionId = useMemo(() => {
    if (serverSessionId || me.role !== "admin") return serverSessionId;
    return safeSessionStorage.getItem(scopedSessionKey);
  }, [me.role, scopedSessionKey, serverSessionId]);

  const [state, dispatch] = useReducer(appReducer, {
    ...initialAppState,
    me,
    readOnly,
    sessionId: initialSessionId,
    activeStage: initialStage,
  });

  const api = useMemo(() => createApiClient(authorizedFetch), [authorizedFetch]);
  const pollerRef = useRef<PollCoordinator | null>(null);
  const invalidationChannelRef = useRef<InvalidationChannel | null>(null);
  const initialNormalizationDone = useRef(false);
  const seenCacheReceipts = useRef(new Set<string>());
  const cacheNoticeId = useRef(0);
  const [cacheNotice, setCacheNotice] = useState<{ id: number; message: string } | null>(null);

  const inspectCacheReceipt = useCallback((stage: string, envelope: StageEnvelope) => {
    const stageValue = envelope[stage];
    if (!stageValue || typeof stageValue !== "object" || Array.isArray(stageValue)) return;
    const receipt = (stageValue as { cache_receipt?: CacheReceipt }).cache_receipt;
    if (!receipt || receipt.cache_hit !== true) return;
    const receiptKey = `${stage}:${receipt.run_id ?? "unknown"}`;
    if (seenCacheReceipts.current.has(receiptKey)) return;
    seenCacheReceipts.current.add(receiptKey);
    cacheNoticeId.current += 1;
    const cachedStages = Number(receipt.cached_stage_count ?? 0);
    const totalStages = Number(receipt.stage_count ?? 0);
    const detail = cachedStages > 0 && totalStages > cachedStages
      ? `${cachedStages} of ${totalStages} generation steps`
      : "this response";
    setCacheNotice({
      id: cacheNoticeId.current,
      message: `Served from cache — ${detail} was prepared earlier, so it arrived faster.`,
    });
  }, []);

  useEffect(() => {
    if (!cacheNotice) return;
    const timer = window.setTimeout(() => setCacheNotice(null), 6500);
    return () => window.clearTimeout(timer);
  }, [cacheNotice]);

  const selectStage = useCallback((stage: JourneyStageId, replace = false) => {
    setActiveStage(stage);
    dispatch({ type: "stage/select", stage });
    const query = serializeAppUrlState({ stage, view: viewForStage(stage) });
    const method = replace ? "replaceState" : "pushState";
    window.history[method]({}, "", `${window.location.pathname}${query}`);
  }, []);

  const refetchCurrentSession = useCallback(async () => {
    if (!state.sessionId) return;
    dispatch({ type: "connection/set", state: "checking" });
    const sessionId = state.sessionId;

    try {
      const [sessionResult, discoveryResult, contentResult, designResult] = await Promise.allSettled([
        api.getSession(sessionId),
        api.getDiscovery(sessionId),
        api.getContentArchitect(sessionId),
        api.getVisualDesignDirector(sessionId),
      ]);

      if (sessionResult.status === "fulfilled") {
        dispatch({
          type: "session/set",
          sessionId: sessionResult.value.id,
          revision: sessionResult.value.revision,
        });
      }

      let discoveryApproved = false;
      if (discoveryResult.status === "fulfilled") {
        inspectCacheReceipt("discovery", discoveryResult.value);
        const view = adaptDiscovery(discoveryResult.value.discovery, discoveryResult.value.jobs);
        discoveryApproved = view.state === "complete";
        dispatch({ type: "discovery/set", view });
      }

      let contentApproved = false;
      if (contentResult.status === "fulfilled") {
        inspectCacheReceipt("content_architect", contentResult.value);
        const view = adaptContentArchitect(
          contentResult.value.content_architect,
          discoveryApproved,
          contentResult.value.jobs,
        );
        contentApproved = view.state === "complete";
        dispatch({ type: "content/set", view });
      }

      if (designResult.status === "fulfilled") {
        inspectCacheReceipt("visual_design_director", designResult.value);
        dispatch({
          type: "design/set",
          view: adaptVisualDesignDirector(
            designResult.value.visual_design_director,
            contentApproved,
            designResult.value.jobs,
          ),
        });
      }

      if (!initialNormalizationDone.current) {
        initialNormalizationDone.current = true;
        const requested = initialUrl.stage;
        let fallback: JourneyStageId | null = null;
        if (requested === "content" && !discoveryApproved) fallback = "discover";
        if (requested === "design" && !contentApproved) {
          fallback = discoveryApproved ? "content" : "discover";
        }
        if (fallback) {
          selectStage(fallback, true);
          dispatch({
            type: "announce",
            message: `That stage is locked. Showing ${fallback} instead.`,
          });
        } else if (!requested && window.location.search) {
          selectStage("discover", true);
        }
      }

      const results = [sessionResult, discoveryResult, contentResult, designResult];
      dispatch({
        type: "connection/set",
        state: results.every((result) => result.status === "fulfilled") ? "confirmed" : "stale",
      });
    } catch {
      dispatch({ type: "connection/set", state: navigator.onLine ? "stale" : "offline" });
    }
  }, [api, initialUrl.stage, inspectCacheReceipt, selectStage, state.sessionId]);

  useEffect(() => {
    const poller = new PollCoordinator();
    pollerRef.current = poller;
    const channel = createInvalidationChannel((message) => {
      if (message.sessionId === state.sessionId) void refetchCurrentSession();
    });
    invalidationChannelRef.current = channel;
    return () => {
      poller.teardown();
      channel.close();
    };
  }, [refetchCurrentSession, state.sessionId]);

  useEffect(() => {
    if (state.sessionId) {
      if (me.role === "admin") safeSessionStorage.setItem(scopedSessionKey, state.sessionId);
      void refetchCurrentSession();
    } else {
      dispatch({ type: "connection/set", state: "confirmed" });
    }
  }, [me.role, refetchCurrentSession, scopedSessionKey, state.sessionId]);

  useEffect(() => {
    const onPopState = () => {
      const parsed = parseAppUrlState(window.location.search);
      const stage = parsed.stage ?? "discover";
      setActiveStage(stage);
      dispatch({ type: "stage/select", stage });
    };
    const onOnline = () => void refetchCurrentSession();
    const onOffline = () => dispatch({ type: "connection/set", state: "offline" });
    window.addEventListener("popstate", onPopState);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("popstate", onPopState);
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, [refetchCurrentSession]);

  useEffect(() => {
    const poller = pollerRef.current;
    if (!poller || !state.sessionId) return;
    const sessionId = state.sessionId;

    if (state.discovery?.state === "working") {
      poller.subscribe("discovery", async () => {
        try {
          const result = await api.getDiscovery(sessionId);
          inspectCacheReceipt("discovery", result);
          const view = adaptDiscovery(result.discovery, result.jobs);
          dispatch({ type: "discovery/set", view });
          dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
          dispatch({ type: "connection/set", state: "confirmed" });
          if (view.state === "review") {
            dispatch({ type: "announce", message: "Portfolio brief ready for review." });
          }
        } catch (error) {
          dispatch({ type: "connection/set", state: navigator.onLine ? "stale" : "offline" });
          throw error;
        }
      });
    } else poller.unsubscribe("discovery");

    if (state.content?.state === "working") {
      poller.subscribe("content_architect", async () => {
        try {
          const result = await api.getContentArchitect(sessionId);
          inspectCacheReceipt("content_architect", result);
          const view = adaptContentArchitect(
            result.content_architect,
            state.discovery?.state === "complete",
            result.jobs,
          );
          dispatch({ type: "content/set", view });
          dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
          dispatch({ type: "connection/set", state: "confirmed" });
          if (view.state === "review") {
            dispatch({ type: "announce", message: "Content plan ready for review." });
          }
        } catch (error) {
          dispatch({ type: "connection/set", state: navigator.onLine ? "stale" : "offline" });
          throw error;
        }
      });
    } else poller.unsubscribe("content_architect");

    if (state.design?.state === "working") {
      poller.subscribe("visual_design_director", async () => {
        try {
          const result = await api.getVisualDesignDirector(sessionId);
          inspectCacheReceipt("visual_design_director", result);
          const view = adaptVisualDesignDirector(
            result.visual_design_director,
            state.content?.state === "complete",
            result.jobs,
          );
          dispatch({ type: "design/set", view });
          dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
          dispatch({ type: "connection/set", state: "confirmed" });
          if (view.state === "review") {
            dispatch({ type: "announce", message: "Visual direction ready for review." });
          }
        } catch (error) {
          dispatch({ type: "connection/set", state: navigator.onLine ? "stale" : "offline" });
          throw error;
        }
      });
    } else poller.unsubscribe("visual_design_director");

    return () => {
      poller.unsubscribe("discovery");
      poller.unsubscribe("content_architect");
      poller.unsubscribe("visual_design_director");
    };
  }, [api, inspectCacheReceipt, state.content?.state, state.design?.state, state.discovery?.state, state.sessionId]);

  const journey = useMemo<JourneyStageVM[]>(() => {
    const discoveryState = state.discovery?.state ?? "available";
    const discoveryApproved = discoveryState === "complete";
    const contentState = state.content?.state ?? (discoveryApproved ? "available" : "locked");
    const contentApproved = contentState === "complete";
    const designState = state.design?.state ?? (contentApproved ? "available" : "locked");
    return [
      { id: "discover", ordinal: 1, label: "Discovery", state: discoveryState, isSelectable: true },
      { id: "content", ordinal: 2, label: "Content", state: contentState, isSelectable: contentState !== "locked" },
      { id: "design", ordinal: 3, label: "Direction", state: designState, isSelectable: designState !== "locked" },
    ];
  }, [state.content, state.design, state.discovery]);

  const notifyMutation = (sessionId: string) => invalidationChannelRef.current?.broadcast(sessionId);

  const handleStartPortfolio = async (intakeText: string) => {
    if (mutatingStage) return;
    recordClientEvent({
      kind: "user_action",
      stage: "discovery",
      action: "start",
      input_characters: intakeText.length,
    });
    setMutatingStage("discover");
    try {
      let sessionId = state.sessionId;
      if (!sessionId) {
        const created = await api.createSession("Portfolio workspace");
        sessionId = created.id;
        dispatch({ type: "session/set", sessionId, revision: created.revision });
      }
      const action = "discovery-start";
      const result = await api.startDiscovery(
        sessionId,
        { message: intakeText, goal: "create my portfolio" },
        getOrCreateIdempotencyKey(sessionId, action),
      );
      clearIdempotencyKey(sessionId, action);
      inspectCacheReceipt("discovery", result);
      dispatch({ type: "discovery/set", view: adaptDiscovery(result.discovery, result.jobs) });
      dispatch({ type: "announce", message: "Discovery started." });
      notifyMutation(sessionId);
    } finally {
      setMutatingStage(null);
    }
  };

  const handleSubmitDiscoveryAnswer = async (
    questionId: string,
    mode: string,
    value: unknown,
    isComplete: boolean,
  ) => {
    if (!state.sessionId) return;
    const result = await api.putDiscoveryAnswers(state.sessionId, {
      complete: isComplete,
      answers: [{ question_id: questionId, mode, value }],
    });
    inspectCacheReceipt("discovery", result);
    dispatch({ type: "discovery/set", view: adaptDiscovery(result.discovery, result.jobs) });
    dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
    notifyMutation(state.sessionId);
  };

  const handleGenerateBrief = async () => {
    if (!state.sessionId) return;
    const result = await api.putDiscoveryAnswers(state.sessionId, { complete: true, answers: [] });
    inspectCacheReceipt("discovery", result);
    dispatch({ type: "discovery/set", view: adaptDiscovery(result.discovery, result.jobs) });
    dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
    notifyMutation(state.sessionId);
  };

  const handleRetryDiscovery = async () => {
    if (!state.sessionId || !state.discovery) return;
    if (state.discovery.job?.status === "queued" || state.discovery.job?.status === "running") {
      await refetchCurrentSession();
      return;
    }
    if (state.discovery.safeError?.retryOperation !== "questions") {
      await handleGenerateBrief();
      return;
    }

    const raw = state.discovery.raw;
    const rawIntake =
      typeof raw === "object" && raw !== null && "intake" in raw &&
      typeof raw.intake === "object" && raw.intake !== null
        ? raw.intake as Record<string, unknown>
        : {};
    const sessionId = state.sessionId;
    const action = "discovery-retry-questions";
    const result = await api.startDiscovery(
      sessionId,
      {
        message: typeof rawIntake.message === "string" ? rawIntake.message : "",
        document_text: typeof rawIntake.document_text === "string" ? rawIntake.document_text : "",
        goal: typeof rawIntake.goal === "string" ? rawIntake.goal : "",
      },
      getOrCreateIdempotencyKey(sessionId, action),
    );
    clearIdempotencyKey(sessionId, action);
    inspectCacheReceipt("discovery", result);
    dispatch({ type: "discovery/set", view: adaptDiscovery(result.discovery, result.jobs) });
    dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
    dispatch({ type: "announce", message: "Discovery retry started." });
    notifyMutation(sessionId);
  };

  const handleStopDiscovery = async () => {
    if (!state.sessionId || mutatingStage) return;
    const sessionId = state.sessionId;
    recordClientEvent({ kind: "user_action", stage: "discovery", action: "stop" });
    setMutatingStage("discover");
    try {
      pollerRef.current?.unsubscribe("discovery");
      const result = await api.stopDiscovery(sessionId);
      inspectCacheReceipt("discovery", result);
      dispatch({ type: "discovery/set", view: adaptDiscovery(result.discovery, result.jobs) });
      dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
      dispatch({ type: "announce", message: "Discovery stopped. Your input is preserved." });
      notifyMutation(sessionId);
    } catch (error) {
      // The stop request is itself a mutation. If it fails, immediately
      // restore the durable poller so a transient response/network error does
      // not leave the UI looking frozen with no way to observe recovery.
      void refetchCurrentSession();
      throw error;
    } finally {
      setMutatingStage(null);
    }
  };

  const handleStopContent = async () => {
    if (!state.sessionId || mutatingStage) return;
    const sessionId = state.sessionId;
    recordClientEvent({ kind: "user_action", stage: "content_architect", action: "stop" });
    setMutatingStage("content");
    try {
      pollerRef.current?.unsubscribe("content_architect");
      const result = await api.stopContentArchitect(sessionId);
      inspectCacheReceipt("content_architect", result);
      dispatch({
        type: "content/set",
        view: adaptContentArchitect(result.content_architect, state.discovery?.state === "complete", result.jobs),
      });
      dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
      dispatch({ type: "announce", message: "Content Architect stopped. Your approved Discovery brief is preserved." });
      notifyMutation(sessionId);
    } catch (error) {
      void refetchCurrentSession();
      throw error;
    } finally {
      setMutatingStage(null);
    }
  };

  const handleStopDesign = async () => {
    if (!state.sessionId || mutatingStage) return;
    const sessionId = state.sessionId;
    recordClientEvent({ kind: "user_action", stage: "visual_design_director", action: "stop" });
    setMutatingStage("design");
    try {
      pollerRef.current?.unsubscribe("visual_design_director");
      const result = await api.stopVisualDesignDirector(sessionId);
      inspectCacheReceipt("visual_design_director", result);
      dispatch({
        type: "design/set",
        view: adaptVisualDesignDirector(result.visual_design_director, state.content?.state === "complete", result.jobs),
      });
      dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
      dispatch({ type: "announce", message: "Visual Design Director stopped. Your approved Content Plan is preserved." });
      notifyMutation(sessionId);
    } catch (error) {
      void refetchCurrentSession();
      throw error;
    } finally {
      setMutatingStage(null);
    }
  };

  const handleReviseBrief = async (request: string) => {
    if (!state.sessionId) return;
    const result = await api.reviseDiscovery(state.sessionId, request);
    inspectCacheReceipt("discovery", result);
    dispatch({ type: "discovery/set", view: adaptDiscovery(result.discovery, result.jobs) });
    dispatch({ type: "announce", message: "Brief revision requested." });
    notifyMutation(state.sessionId);
  };

  const handleApproveBrief = async () => {
    if (!state.sessionId) return;
    const result = await api.approveDiscovery(state.sessionId);
    inspectCacheReceipt("discovery", result);
    dispatch({ type: "discovery/set", view: adaptDiscovery(result.discovery, result.jobs) });
    dispatch({ type: "announce", message: "Portfolio brief approved." });
    notifyMutation(state.sessionId);
    await refetchCurrentSession();
  };

  const runContentMutation = async (
    operation: "start" | "approve" | "revise",
    revisionRequest = "",
  ) => {
    if (!state.sessionId || mutatingStage) return;
    setMutatingStage("content");
    try {
      const action = `content-${operation}`;
      const result = operation === "start"
        ? await api.startContentArchitect(
            state.sessionId,
            { preferences: {} },
            getOrCreateIdempotencyKey(state.sessionId, action),
          )
        : operation === "approve"
          ? await api.approveContentArchitect(state.sessionId)
          : await api.reviseContentArchitect(state.sessionId, revisionRequest);
      if (operation === "start") clearIdempotencyKey(state.sessionId, action);
      inspectCacheReceipt("content_architect", result);
      dispatch({
        type: "content/set",
        view: adaptContentArchitect(result.content_architect, true, result.jobs),
      });
      dispatch({
        type: "announce",
        message: operation === "approve" ? "Content plan approved." : operation === "revise" ? "Content revision requested." : "Content Architect started.",
      });
      notifyMutation(state.sessionId);
      if (operation === "approve") await refetchCurrentSession();
    } catch (error) {
      void refetchCurrentSession();
      throw error;
    } finally {
      setMutatingStage(null);
    }
  };

  const runDesignMutation = async (
    operation: "start" | "approve" | "revise",
    revisionRequest = "",
  ) => {
    if (!state.sessionId || mutatingStage) return;
    setMutatingStage("design");
    try {
      const action = `design-${operation}`;
      const result = operation === "start"
        ? await api.startVisualDesignDirector(
            state.sessionId,
            { preferences: {} },
            getOrCreateIdempotencyKey(state.sessionId, action),
          )
        : operation === "approve"
          ? await api.approveVisualDesignDirector(state.sessionId)
          : await api.reviseVisualDesignDirector(state.sessionId, revisionRequest);
      if (operation === "start") clearIdempotencyKey(state.sessionId, action);
      inspectCacheReceipt("visual_design_director", result);
      dispatch({
        type: "design/set",
        view: adaptVisualDesignDirector(result.visual_design_director, true, result.jobs),
      });
      dispatch({
        type: "announce",
        message: operation === "approve" ? "Creative handoff saved." : operation === "revise" ? "Visual direction revision requested." : "Visual Design Director started.",
      });
      notifyMutation(state.sessionId);
      if (operation === "approve") await refetchCurrentSession();
    } catch (error) {
      void refetchCurrentSession();
      throw error;
    } finally {
      setMutatingStage(null);
    }
  };

  return (
    <AppStoreContext.Provider value={{ state, dispatch }}>
      <a className="skip-link" href="#workspace-stage">Skip to current stage</a>
      <div className="app-shell">
        <header className="app-topbar">
          <a className="app-brand" href="/app" aria-label="OryxenAI workspace">
            <LivingDraftMark active={false} />
            <span><strong>OryxenAI</strong><small>portfolio editorial room</small></span>
          </a>
          <div className="app-topbar-context" aria-label="Workspace status">
            <span className="context-label">Current proof</span>
            <strong>{journey.find((stage) => stage.id === activeStage)?.label ?? "Discovery"}</strong>
          </div>
          <details className="account-menu">
            <summary aria-label="Open account menu">
              <span className="account-monogram" aria-hidden="true">{(me.username ?? "U").slice(0, 1).toUpperCase()}</span>
              <span className="account-name">{me.username ?? "Account"}</span>
            </summary>
            <div className="account-popover">
              <p><strong>{me.username ?? "OryxenAI account"}</strong><span>{me.role === "admin" ? "Administrator" : "Portfolio owner"}</span></p>
              {state.readOnly ? <span className="read-only-tag">Read-only workspace</span> : null}
              {me.role === "admin" ? <a id="app-admin-link" href="/admin">Administration</a> : null}
              <button id="app-logout" type="button">Sign out</button>
            </div>
          </details>
        </header>

        <ConnectionBanner state={state.connection} />
        <CacheNotice key={cacheNotice?.id ?? "empty"} message={cacheNotice?.message ?? null} />
        {typeof window !== "undefined" && ["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname) ? (
          <ClientTraceNotice traceId={getClientTraceId()} />
        ) : null}

        <div className="app-work-surface">
          {state.sessionId ? (
            <div className="workspace-heading compact">
              <p className="eyebrow">Authenticated workspace</p>
              <h1>Shape the evidence. Approve the story.</h1>
              <p>Three deliberate passes turn your source material into an approved portfolio brief, content architecture, and visual direction.</p>
            </div>
          ) : null}

          {state.sessionId ? (
            <JourneyRail journey={journey} selectedStageId={activeStage} onSelect={selectStage} />
          ) : null}

          <ErrorBoundary fallbackTitle="Unable to display this stage" onReset={refetchCurrentSession}>
            <section id="workspace-stage" className="stage-frame" data-stage={activeStage} tabIndex={-1}>
              {!state.sessionId ? (
                <StartSurface
                  onStart={handleStartPortfolio}
                  disabled={state.readOnly || me.can_create_portfolio === false || mutatingStage === "discover"}
                  disabledReason={me.can_create_portfolio === false ? "Your account cannot start another portfolio." : undefined}
                />
              ) : null}

              {state.sessionId && activeStage === "discover" ? (
                <DiscoveryStage
                  view={state.discovery}
                  history={state.discovery?.answeredTurns ?? []}
                  canMutate={!state.readOnly && mutatingStage === null}
                  onStartDiscovery={handleStartPortfolio}
                  onSubmitAnswer={handleSubmitDiscoveryAnswer}
                  onGenerateBriefNow={handleGenerateBrief}
                  onRetryDiscovery={handleRetryDiscovery}
                  onStopDiscovery={handleStopDiscovery}
                  onApproveBrief={handleApproveBrief}
                  onReviseBrief={handleReviseBrief}
                  onContinueToContent={() => selectStage("content")}
                />
              ) : null}

              {state.sessionId && activeStage === "content" ? (
                <ContentStage
                  view={state.content}
                  canMutate={!state.readOnly}
                  inFlight={mutatingStage === "content"}
                  onStart={() => runContentMutation("start")}
                  onApprove={() => runContentMutation("approve")}
                  onRevise={(request) => runContentMutation("revise", request)}
                  onStop={handleStopContent}
                  onContinueToDesign={() => selectStage("design")}
                />
              ) : null}

              {state.sessionId && activeStage === "design" ? (
                <DesignStage
                  view={state.design}
                  canMutate={!state.readOnly}
                  inFlight={mutatingStage === "design"}
                  onStart={() => runDesignMutation("start")}
                  onApprove={() => runDesignMutation("approve")}
                  onRevise={(request) => runDesignMutation("revise", request)}
                  onStop={handleStopDesign}
                />
              ) : null}
            </section>
          </ErrorBoundary>
        </div>
        <footer className="app-footer"><span>Private working space</span><span>Nothing advances without approval</span></footer>
        <StatusAnnouncer message={state.announcement} />
      </div>
    </AppStoreContext.Provider>
  );
}
