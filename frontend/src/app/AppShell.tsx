import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "preact/hooks";
import { AppStoreContext, appReducer, initialAppState } from "./store";
import { createApiClient, type AuthorizedFetch, type CacheReceipt, type MeProjection, type StageEnvelope } from "../data/api-client";
import { adaptDiscovery } from "../data/adapters/discovery";
import { adaptContentArchitect } from "../data/adapters/content";
import type { DiscoveryAnswerSubmission } from "../data/discovery-answer";
import { clearIdempotencyKey, getOrCreateIdempotencyKey } from "../data/idempotency";
import { ApiError } from "../data/errors";
import { createInvalidationChannel, type InvalidationChannel } from "../data/invalidation";
import { PollCoordinator } from "../data/polling";
import { ConnectionBanner } from "../components/ConnectionBanner";
import { CacheNotice } from "../components/CacheNotice";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { JourneyRail, type JourneyStageVM } from "../components/JourneyRail";
import { StartSurface } from "../components/StartSurface";
import { StatusAnnouncer } from "../components/StatusAnnouncer";
import { ContentStage } from "../stages/content/ContentStage";
import { DiscoveryStage } from "../stages/discovery/DiscoveryStage";
import { parseAppUrlState, serializeAppUrlState, type JourneyStageId } from "./url-state";
import { safeSessionStorage } from "../data/safe-storage";
import { getClientTraceId, recordClientEvent } from "../data/client-diagnostics";
import { ClientTraceNotice } from "../components/ClientTraceNotice";
import { OutputInspector } from "../components/OutputInspector";
import { StageContextStrip } from "../components/StageContextStrip";

export interface AppShellProps {
  authorizedFetch: AuthorizedFetch;
  me: MeProjection;
  serverSessionId: string | null;
  developer?: boolean;
}

function viewForStage(stage: JourneyStageId): "work" | "artifact" {
  return stage === "discover" ? "work" : "artifact";
}

function stageDisplayName(stage: JourneyStageId): string {
  switch (stage) {
    case "discover": return "Discover";
    case "content": return "Content";
    default: return "Studio";
  }
}

function stagePurposeText(stage: JourneyStageId): string {
  switch (stage) {
    case "discover": return "Capture your goal, audience, key message and any reference material.";
    case "content": return "Define routes, narrative positioning, and section copy.";
    default: return "Creative portfolio studio.";
  }
}

function activeSessionStorageKey(userId: string): string {
  return `oryxenai.active_session_id:${userId}`;
}

// Reconciles the stage requested by the URL (or the "discover" default)
// against what the server just confirmed is actually approved, on the very
// first load. Two independent corrections can be needed, in either
// direction:
//   - backward: the URL asked for a stage ahead of approved progress (e.g.
//     a stale bookmark, or a direct link to a stage that got locked again).
//   - forward: the URL asked for "discover" (or nothing) but the server
//     shows later stages are already approved, so "discover" is stale and
//     the user should land on the furthest stage that is actually
//     actionable right now.
// Pure and exported so it can be unit tested the same way url-state.ts's
// parse/serialize helpers are, without needing to render AppShell itself.
export function resolveInitialStage(
  requested: JourneyStageId | null,
  discoveryApproved: boolean,
): { stage: JourneyStageId | null; corrected: boolean } {
  let fallback: JourneyStageId | null = null;
  if (requested === "content" && !discoveryApproved) fallback = "discover";
  if (fallback) return { stage: fallback, corrected: true };

  // None of the backward branches fired, so the requested stage was never
  // ahead of approved progress. Now check the opposite: the requested/
  // default stage sitting on "discover" after the Discovery brief is
  // approved, which otherwise leaves the user stranded on stale Discovery
  // content even though Content is available.
  if (requested === null || requested === "discover") {
    let furthest: JourneyStageId = "discover";
    if (discoveryApproved) furthest = "content";
    if (furthest !== "discover") return { stage: furthest, corrected: true };
  }

  return { stage: null, corrected: false };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function hasCopyableOutput(stage: JourneyStageId, value: unknown): boolean {
  if (!isRecord(value)) return false;
  if (stage !== "discover") return true;
  return isRecord(value.build_or_revise_brief);
}

export function AppShell({
  authorizedFetch,
  me,
  serverSessionId,
  developer = false,
}: AppShellProps) {
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
      ? `${cachedStages} of ${totalStages} model calls`
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

    const [sessionResult, discoveryResult, contentResult] = await Promise.allSettled([
      api.getSession(sessionId),
      api.getDiscovery(sessionId),
      api.getContentArchitect(sessionId),
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

    if (contentResult.status === "fulfilled") {
      inspectCacheReceipt("content_architect", contentResult.value);
      const view = adaptContentArchitect(
        contentResult.value.content_architect,
        discoveryApproved,
        contentResult.value.jobs,
      );
      dispatch({ type: "content/set", view });
    }

    if (!initialNormalizationDone.current) {
      initialNormalizationDone.current = true;
      const requested = initialUrl.stage;
      const resolved = resolveInitialStage(requested, discoveryApproved);
      if (resolved.corrected && resolved.stage) {
        selectStage(resolved.stage, true);
        dispatch({
          type: "announce",
          message: requested === null || requested === "discover"
            ? "Continuing from where you left off."
            : "That stage is locked. Showing Discover instead.",
        });
      } else if (!requested && window.location.search) {
        selectStage("discover", true);
      }
    }

    const results = [sessionResult, discoveryResult, contentResult];
    dispatch({
      type: "connection/set",
      state: results.every((result) => result.status === "fulfilled") ? "confirmed" : "stale",
    });
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

    return () => {
      poller.unsubscribe("discovery");
      poller.unsubscribe("content_architect");
    };
  }, [
    api,
    inspectCacheReceipt,
    state.content?.state,
    state.discovery?.state,
    state.sessionId,
  ]);

  const journey = useMemo<JourneyStageVM[]>(() => {
    const discoveryState = state.discovery?.state ?? "available";
    const discoveryApproved = discoveryState === "complete";
    const contentState = state.content?.state ?? (discoveryApproved ? "available" : "locked");
    return [
      { id: "discover", ordinal: 1, label: "Discover", sublabel: "UNDERSTAND YOUR STORY", state: discoveryState, isSelectable: true },
      { id: "content", ordinal: 2, label: "Content", sublabel: "SHAPE NARRATIVE", state: contentState, isSelectable: contentState !== "locked" },
    ];
  }, [state.content, state.discovery]);

  const outputEntries = useMemo(() => [
    {
      id: "discover",
      label: "Discovery Agent",
      state: state.discovery?.state ?? "available",
      agentOutput: state.discovery?.agentOutput ?? null,
      available: hasCopyableOutput("discover", state.discovery?.agentOutput),
    },
    {
      id: "content",
      label: "Content Architect",
      state: state.content?.state ?? "locked",
      agentOutput: state.content?.agentOutput ?? null,
      available: hasCopyableOutput("content", state.content?.agentOutput),
    },
  ], [state.content, state.discovery]);

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
    answer: DiscoveryAnswerSubmission,
    isComplete: boolean,
  ) => {
    if (!state.sessionId) return;
    const result = await api.putDiscoveryAnswers(state.sessionId, {
      complete: isComplete,
      answers: [{ question_id: answer.questionId, mode: answer.mode, value: answer.value }],
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

  const handleReviseBrief = async (request: string) => {
    if (!state.sessionId) return;
    const result = await api.reviseDiscovery(state.sessionId, request);
    inspectCacheReceipt("discovery", result);
    dispatch({ type: "discovery/set", view: adaptDiscovery(result.discovery, result.jobs) });
    dispatch({ type: "announce", message: "Brief revision requested." });
    notifyMutation(state.sessionId);
  };

  const handleApproveBrief = async () => {
    if (!state.sessionId || mutatingStage) return;
    const sessionId = state.sessionId;
    setMutatingStage("discover");
    try {
      const approved = await api.approveDiscovery(sessionId);
      inspectCacheReceipt("discovery", approved);
      dispatch({ type: "discovery/set", view: adaptDiscovery(approved.discovery, approved.jobs) });
      dispatch({
        type: "session/set",
        sessionId: approved.session_id,
        revision: approved.session_revision,
      });
      notifyMutation(sessionId);
    } catch (error) {
      void refetchCurrentSession();
      throw error;
    } finally {
      setMutatingStage(null);
    }
  };

  // Returns the operation that actually completed so callers can tell a
  // genuine approval apart from the silent safety-repair fallback without depending on a
  // fresh render of `state` — this function's own `state` closure is fixed
  // to the render that created it, so a post-await read of React state here
  // would still reflect pre-mutation values.
  const runContentMutation = async (
    operation: "start" | "approve" | "revise",
    revisionRequest = "",
  ): Promise<"start" | "approve" | "revise" | "repair" | null> => {
    if (!state.sessionId || mutatingStage) return null;
    setMutatingStage("content");
    try {
      const action = `content-${operation}`;
      let completedOperation: "start" | "approve" | "revise" | "repair" = operation;
      let result: StageEnvelope;
      try {
        result = operation === "start"
          ? await api.startContentArchitect(
              state.sessionId,
              { preferences: {} },
              getOrCreateIdempotencyKey(state.sessionId, action),
            )
          : operation === "approve"
            ? await api.approveContentArchitect(state.sessionId)
            : await api.reviseContentArchitect(state.sessionId, revisionRequest);
      } catch (error) {
        if (
          operation !== "approve" ||
          !(error instanceof ApiError) ||
          error.code !== "CONTENT_ARCHITECT_PUBLIC_SCOPE_INCOMPLETE"
        ) {
          throw error;
        }
        completedOperation = "repair";
        result = await api.reviseContentArchitect(
          state.sessionId,
          "Resolve every deterministic public-scope approval error. Preserve valid content and the approved route plan. Every approved route must contain complete visitor-facing copy and may reference only claims whose publication_status is approved. Safely rewrite or omit pending or blocked exact details instead of changing their publication status.",
        );
      }
      if (operation === "start") clearIdempotencyKey(state.sessionId, action);
      inspectCacheReceipt("content_architect", result);
      dispatch({
        type: "content/set",
        view: adaptContentArchitect(result.content_architect, true, result.jobs),
      });
      dispatch({
        type: "announce",
        message: completedOperation === "approve"
          ? "Content plan approved."
          : completedOperation === "repair"
            ? "Content safety revision started. Review the corrected plan when it is ready."
            : completedOperation === "revise"
              ? "Content revision requested."
              : "Content Architect started.",
      });
      notifyMutation(state.sessionId);
      if (completedOperation === "approve") await refetchCurrentSession();
      return completedOperation;
    } catch (error) {
      void refetchCurrentSession();
      throw error;
    } finally {
      setMutatingStage(null);
    }
  };

  // If approval routes into the safety repair path (public-scope validation
  // failure), stay on Content so the user can review the corrected plan.
  // Never treat a repaired, unapproved result as complete.
  const handleApproveContent = async () => {
    await runContentMutation("approve");
  };

  const startContentAfterApproval = async () => {
    try {
      await runContentMutation("start");
      selectStage("content");
    } catch (error) {
      dispatch({ type: "announce", message: `Content Architect could not start: ${error instanceof Error ? error.message : "try again."}` });
    }
  };



  return (
    <AppStoreContext.Provider value={{ state, dispatch }}>
      <a className="skip-link" href="#workspace-stage">Skip to current stage</a>
      <div className="app-shell">
        <header className="app-topbar">
          <a className="app-brand" href="/app" aria-label="OryxenAI workspace">
            <img
              className="brand-logo-img"
              src="/auth-static/brand-mark.png"
              width="24"
              height="24"
              alt="OryxenAI logo"
            />
            <span className="brand-wordmark">OryxenAI</span>
            <span className="header-pipe" aria-hidden="true">|</span>
            <span className="header-descriptor">IDEAS TO IMPACT</span>
          </a>

          {/* The journey ends when the approved content plan is ready. */}
          <JourneyRail journey={journey} selectedStageId={activeStage} onSelect={selectStage} />

          <div className="app-topbar-actions">
            <span className="topbar-motto" aria-hidden="true">A MORE THOUGHTFUL CREATIVE FUTURE</span>
            <span className="topbar-dot" aria-hidden="true">●</span>
            <details className="account-menu">
              <summary aria-label="Open account menu">
                <span className="account-monogram" aria-hidden="true">{(me.username ?? "U").slice(0, 1).toUpperCase()}</span>
                <span className="account-chevron" aria-hidden="true">▾</span>
              </summary>
              <div className="account-popover">
                <p><strong>{me.username ?? "OryxenAI account"}</strong><span>{me.role === "admin" ? "Administrator" : "Portfolio owner"}</span></p>
                {me.role === "admin" ? <a id="app-admin-link" href="/admin">Administration</a> : null}
                <button id="app-logout" type="button">Sign out</button>
              </div>
            </details>
          </div>
        </header>

        <ConnectionBanner state={state.connection} />
        <CacheNotice key={cacheNotice?.id ?? "empty"} message={cacheNotice?.message ?? null} />
        {developer ? (
          <ClientTraceNotice traceId={getClientTraceId()} />
        ) : null}

        {/* In-flow Stage Context Strip matching 01-shell-overview.png */}
        <StageContextStrip
          stageName={stageDisplayName(activeStage)}
          stagePurpose={stagePurposeText(activeStage)}
          tagline="A STRONG START LEADS FURTHER"
        />

        <main className="app-work-surface">
          <div className="app-stage-layout">
            <ErrorBoundary fallbackTitle="Unable to display this stage" onReset={refetchCurrentSession}>
              <section id="workspace-stage" className="stage-frame" data-stage={activeStage} tabIndex={-1}>
              <div key={activeStage} className="stage-transition-layer">
              {!state.sessionId ? (
                <StartSurface
                  onStart={handleStartPortfolio}
                  disabled={me.can_create_portfolio === false || mutatingStage === "discover"}
                  disabledReason={me.can_create_portfolio === false ? "Your account cannot start another portfolio." : undefined}
                />
              ) : null}

              {state.sessionId && activeStage === "discover" ? (
                <DiscoveryStage
                  view={state.discovery}
                  history={state.discovery?.answeredTurns ?? []}
                  canMutate={mutatingStage === null}
                  onStartDiscovery={handleStartPortfolio}
                  onSubmitAnswer={handleSubmitDiscoveryAnswer}
                  onGenerateBriefNow={handleGenerateBrief}
                  onRetryDiscovery={handleRetryDiscovery}
                  onStopDiscovery={handleStopDiscovery}
                  inFlight={mutatingStage === "discover"}
                  onApproveAndContinue={handleApproveBrief}
                  onStartNextStage={startContentAfterApproval}
                  onReviseBrief={handleReviseBrief}
                />
              ) : null}

              {state.sessionId && activeStage === "content" ? (
                <ContentStage
                  view={state.content}
                  canMutate={true}
                  inFlight={mutatingStage === "content"}
                  onStart={async () => { await runContentMutation("start"); }}
                  onApproveAndContinue={handleApproveContent}
                  onRevise={async (request) => { await runContentMutation("revise", request); }}
                  onStop={handleStopContent}
                />
              ) : null}


              </div>
              </section>
            </ErrorBoundary>
            <OutputInspector entries={outputEntries} activeStage={activeStage} enabled={Boolean(developer && state.sessionId)} />
          </div>
        </main>
        <footer className="app-footer"><span>Private working space</span><span>Nothing advances without approval</span></footer>
        <StatusAnnouncer message={state.announcement} />
      </div>
    </AppStoreContext.Provider>
  );
}
