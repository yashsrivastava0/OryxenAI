import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "preact/hooks";
import { AppStoreContext, appReducer, initialAppState } from "./store";
import { createApiClient, type AuthorizedFetch, type CacheReceipt, type ExtractedDocument, type MeProjection, type StageEnvelope } from "../data/api-client";
import { adaptDiscovery } from "../data/adapters/discovery";
import { adaptContentArchitect } from "../data/adapters/content";
import { adaptStudio } from "../data/adapters/studio";
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
import { StudioStage } from "../stages/studio/StudioStage";
import { parseAppUrlState, serializeAppUrlState, type JourneyStageId, type WorkspaceScreenId } from "./url-state";
import { safeSessionStorage } from "../data/safe-storage";
import { getClientTraceId, recordClientEvent } from "../data/client-diagnostics";
import { ClientTraceNotice } from "../components/ClientTraceNotice";
import { OutputInspector } from "../components/OutputInspector";
import { StageContextStrip } from "../components/StageContextStrip";
import { captureFailure, type FailureDiagnosticInput } from "../data/failure-diagnostics";
import { CopyDiagnosticsButton } from "../components/CopyDiagnosticsButton";
import { WorkspaceGuide, WorkspaceHome } from "../components/WorkspacePages";

export interface AppShellProps {
  authorizedFetch: AuthorizedFetch;
  me: MeProjection;
  serverSessionId: string | null;
  developer?: boolean;
}

function viewForStage(stage: JourneyStageId): "work" | "artifact" {
  return stage === "content" ? "artifact" : "work";
}

function stageDisplayName(stage: JourneyStageId): string {
  switch (stage) {
    case "discover": return "Explore";
    case "content": return "Content";
    case "studio": return "Studio";
    default: return "Studio";
  }
}

function stagePurposeText(stage: JourneyStageId): string {
  switch (stage) {
    case "discover": return "Capture your goal, audience, key message and any reference material.";
    case "content": return "Write the finished copy for every section of your page.";
    case "studio": return "Review your live page and ask for changes to its words.";
    default: return "Creative portfolio studio.";
  }
}

function activeSessionStorageKey(userId: string): string {
  return `oryxenai.active_session_id:${userId}`;
}

interface StudioPresentationMarker { startedAt: number; versionId: string }
function presentationKey(sessionId: string): string { return `oryxenai.studio_presentation:${sessionId}`; }
function readPresentation(sessionId: string | null): StudioPresentationMarker | null {
  if (!sessionId) return null;
  try {
    const value: unknown = JSON.parse(safeSessionStorage.getItem(presentationKey(sessionId)) ?? "null");
    if (!isRecord(value) || typeof value.startedAt !== "number" || typeof value.versionId !== "string") return null;
    if (value.startedAt > Date.now() || Date.now() - value.startedAt > 86_400_000) return null;
    return { startedAt: value.startedAt, versionId: value.versionId };
  } catch { return null; }
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
  contentApproved = false,
): { stage: JourneyStageId | null; corrected: boolean } {
  let fallback: JourneyStageId | null = null;
  if (requested === "content" && !discoveryApproved) fallback = "discover";
  if (requested === "studio" && !contentApproved) fallback = discoveryApproved ? "content" : "discover";
  if (fallback) return { stage: fallback, corrected: true };

  // None of the backward branches fired, so the requested stage was never
  // ahead of approved progress. Now check the opposite: the requested/
  // default stage sitting on "discover" after the Explorer brief is
  // approved, which otherwise leaves the user stranded on stale Explorer
  // content even though Content is available.
  if (requested === null || requested === "discover") {
    let furthest: JourneyStageId = "discover";
    if (discoveryApproved) furthest = "content";
    if (contentApproved) furthest = "studio";
    if (furthest !== "discover") return { stage: furthest, corrected: true };
  }

  return { stage: null, corrected: false };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function readyDiscoveryRunKey(sessionId: string | null, raw: unknown): string | null {
  if (!sessionId || !isRecord(raw) || raw.status !== "questions_ready") return null;
  const operation = raw.operation_a;
  if (!isRecord(operation) || operation.mode !== "READY_FOR_BRIEF") return null;
  return typeof operation.run_id === "string" && operation.run_id
    ? `${sessionId}:${operation.run_id}`
    : null;
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
  const [activeScreen, setActiveScreen] = useState<WorkspaceScreenId | null>(initialUrl.screen);
  const [mutatingStage, setMutatingStage] = useState<JourneyStageId | null>(null);
  const [resetting, setResetting] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);
  const [resetFailure, setResetFailure] = useState<FailureDiagnosticInput | null>(null);
  const [connectionFailure, setConnectionFailure] = useState<FailureDiagnosticInput | null>(null);
  const [shellFailure, setShellFailure] = useState<FailureDiagnosticInput | null>(null);

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
  const [presentation, setPresentation] = useState<StudioPresentationMarker | null>(() => readPresentation(initialSessionId));
  useEffect(() => { setPresentation(readPresentation(state.sessionId)); }, [state.sessionId]);

  const api = useMemo(() => createApiClient(authorizedFetch), [authorizedFetch]);
  const pollerRef = useRef<PollCoordinator | null>(null);
  // The Studio polls a little slower than the planning stages and only while a build runs.
  const studioPollerRef = useRef<PollCoordinator | null>(null);
  const studioLock = useRef(false);
  const [studioBusy, setStudioBusy] = useState(false);
  const [studioStartError, setStudioStartError] = useState<string | null>(null);
  const [studioStartFailure, setStudioStartFailure] = useState<FailureDiagnosticInput | null>(null);
  const invalidationChannelRef = useRef<InvalidationChannel | null>(null);
  const initialNormalizationDone = useRef(false);
  const seenCacheReceipts = useRef(new Set<string>());
  const autoBriefAttempts = useRef(new Set<string>());
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
    if (!replace) initialNormalizationDone.current = true;
    setActiveScreen(null);
    setActiveStage(stage);
    dispatch({ type: "stage/select", stage });
    const query = serializeAppUrlState({ stage, view: viewForStage(stage) });
    const method = replace ? "replaceState" : "pushState";
    window.history[method]({}, "", `${window.location.pathname}${query}`);
  }, []);

  const selectScreen = useCallback((screen: WorkspaceScreenId, replace = false) => {
    if (!replace) initialNormalizationDone.current = true;
    setActiveScreen(screen);
    const method = replace ? "replaceState" : "pushState";
    window.history[method]({}, "", `${window.location.pathname}${serializeAppUrlState({ screen })}`);
  }, []);

  const refetchCurrentSession = useCallback(async () => {
    if (!state.sessionId) return;
    dispatch({ type: "connection/set", state: "checking" });
    const sessionId = state.sessionId;

    const [sessionResult, discoveryResult] = await Promise.allSettled([
      api.getSession(sessionId),
      api.getDiscovery(sessionId),
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

    const contentResult = discoveryApproved
      ? await Promise.allSettled([api.getContentArchitect(sessionId)]).then(([result]) => result)
      : null;
    let contentApproved = false;
    if (contentResult?.status === "fulfilled") {
      inspectCacheReceipt("content_architect", contentResult.value);
      const view = adaptContentArchitect(
        contentResult.value.content_architect,
        discoveryApproved,
        contentResult.value.jobs,
      );
      contentApproved = view.state === "complete";
      dispatch({ type: "content/set", view });
    }

    const studioResult = contentApproved
      ? await Promise.allSettled([api.getStudio(sessionId)]).then(([result]) => result)
      : null;
    if (studioResult?.status === "fulfilled") {
      dispatch({ type: "studio/set", view: adaptStudio(studioResult.value, true) });
    }

    if (!initialNormalizationDone.current) {
      initialNormalizationDone.current = true;
      const requested = initialUrl.stage;
      const resolved = resolveInitialStage(requested, discoveryApproved, contentApproved);
      if (initialUrl.screen) {
        if (window.location.search !== serializeAppUrlState({ screen: initialUrl.screen })) {
          selectScreen(initialUrl.screen, true);
        }
      } else if (resolved.corrected && resolved.stage) {
        selectStage(resolved.stage, true);
        dispatch({
          type: "announce",
          message: requested === null || requested === "discover"
            ? "Continuing from where you left off."
            : "That stage is locked. Showing Explore instead.",
        });
      } else if (!requested && window.location.search) {
        selectStage("discover", true);
      }
    }

    const results = [
      sessionResult,
      discoveryResult,
      ...(contentResult ? [contentResult] : []),
      ...(studioResult ? [studioResult] : []),
    ];
    dispatch({
      type: "connection/set",
      state: results.every((result) => result.status === "fulfilled") ? "confirmed" : "stale",
    });
    const rejected = results.find((result) => result.status === "rejected");
    setConnectionFailure(rejected?.status === "rejected"
      ? captureFailure(rejected.reason, "workspace", "refresh state", "The latest check did not complete.")
      : null);
  }, [api, initialUrl.screen, initialUrl.stage, inspectCacheReceipt, selectScreen, selectStage, state.sessionId]);

  useEffect(() => {
    const poller = new PollCoordinator();
    pollerRef.current = poller;
    const studioPoller = new PollCoordinator({ intervalMs: 2000 });
    studioPollerRef.current = studioPoller;
    const channel = createInvalidationChannel((message) => {
      if (message.sessionId === state.sessionId) void refetchCurrentSession();
    });
    invalidationChannelRef.current = channel;
    return () => {
      poller.teardown();
      studioPoller.teardown();
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
      initialNormalizationDone.current = true;
      const parsed = parseAppUrlState(window.location.search);
      setActiveScreen(parsed.screen);
      if (parsed.screen) return;
      const resolved = resolveInitialStage(parsed.stage, state.discovery?.state === "complete", state.content?.state === "complete");
      const stage = resolved.stage ?? parsed.stage ?? "discover";
      setActiveStage(stage);
      dispatch({ type: "stage/select", stage });
      if (resolved.corrected) {
        window.history.replaceState({}, "", `${window.location.pathname}${serializeAppUrlState({ stage, view: viewForStage(stage) })}`);
      }
    };
    const onOnline = () => void refetchCurrentSession();
    const onOffline = () => {
      dispatch({ type: "connection/set", state: "offline" });
      setConnectionFailure(captureFailure(null, "workspace", "refresh state", "The browser is offline."));
    };
    window.addEventListener("popstate", onPopState);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("popstate", onPopState);
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, [refetchCurrentSession, state.content?.state, state.discovery?.state]);

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
          setConnectionFailure(null);
          if (view.state === "review") {
            dispatch({ type: "announce", message: "Portfolio brief ready for review." });
          }
        } catch (error) {
          dispatch({ type: "connection/set", state: navigator.onLine ? "stale" : "offline" });
          setConnectionFailure(captureFailure(error, "discovery", "poll stage", "Explorer status could not be refreshed."));
          throw error;
        }
      }, false);
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
          setConnectionFailure(null);
          if (view.state === "review") {
            dispatch({ type: "announce", message: "Content plan ready for review." });
          }
        } catch (error) {
          dispatch({ type: "connection/set", state: navigator.onLine ? "stale" : "offline" });
          setConnectionFailure(captureFailure(error, "content_architect", "poll stage", "Content Architect status could not be refreshed."));
          throw error;
        }
      }, false);
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

  useEffect(() => {
    const poller = studioPollerRef.current;
    if (!poller || !state.sessionId) return undefined;
    const sessionId = state.sessionId;
    if (state.studio?.building) {
      poller.subscribe("code_generator", async () => {
        try {
          const result = await api.getStudio(sessionId);
          const view = adaptStudio(result, true);
          dispatch({ type: "studio/set", view });
          dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
          dispatch({ type: "connection/set", state: "confirmed" });
          setConnectionFailure(null);
          if (!view.building) {
            dispatch({
              type: "announce",
              message: view.lastError
                ? "The build did not finish. The details are in the Studio."
                : "Your portfolio is ready.",
            });
          }
        } catch (error) {
          dispatch({ type: "connection/set", state: navigator.onLine ? "stale" : "offline" });
          setConnectionFailure(captureFailure(error, "studio", "poll stage", "Studio status could not be refreshed."));
          throw error;
        }
      }, false);
    } else poller.unsubscribe("code_generator");
    return () => poller.unsubscribe("code_generator");
  }, [api, state.sessionId, state.studio?.building]);

  const contentApprovedForStudio = state.content?.state === "complete";
  const discoveryApproved = state.discovery?.state === "complete";
  const resumeStage: JourneyStageId = contentApprovedForStudio ? "studio" : discoveryApproved ? "content" : "discover";
  const previewReady = Boolean(state.studio?.activeVersionId);

  useEffect(() => {
    const page = activeScreen === "home" ? "Home" : activeScreen === "guide" ? "Guide" : stageDisplayName(activeStage);
    document.title = `${page} · OryxenAI`;
    const description = document.querySelector<HTMLMetaElement>('meta[name="description"]');
    if (description) description.content = activeScreen === "guide"
      ? "How your private portfolio moves through Explorer, Content Architect, and Studio."
      : "Your private OryxenAI portfolio workspace.";
  }, [activeScreen, activeStage]);
  const journey = useMemo<JourneyStageVM[]>(() => {
    const discoveryState = state.discovery?.state ?? "available";
    const discoveryApproved = discoveryState === "complete";
    const contentState = state.content?.state ?? (discoveryApproved ? "available" : "locked");
    const studioState = state.studio?.state ?? (contentState === "complete" ? "available" : "locked");
    return [
      { id: "discover", ordinal: 1, label: "Explore", sublabel: "UNDERSTAND YOUR STORY", state: discoveryState, isSelectable: true },
      { id: "content", ordinal: 2, label: "Content", sublabel: "SHAPE NARRATIVE", state: contentState, isSelectable: contentState !== "locked" },
      { id: "studio", ordinal: 3, label: "Studio", sublabel: "BUILD YOUR PAGE", state: studioState, isSelectable: studioState !== "locked" },
    ];
  }, [state.content, state.discovery, state.studio]);

  const outputEntries = useMemo(() => [
    {
      id: "discover",
      label: "Explorer Agent",
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

  const discoveryHistory = useMemo(() => {
    if (!state.discovery) return [];
    const recordedTurns = state.discovery.questionHistory
      .filter((event) => event.status === "answered" || event.status === "skipped")
      .map((event) => ({
        questionId: event.questionId,
        questionText: event.question,
        answerText: event.answer || (event.status === "skipped" ? "Skipped" : "Answer saved"),
      }));
    return recordedTurns.length > 0 ? recordedTurns : state.discovery.answeredTurns;
  }, [state.discovery]);

  const notifyMutation = (sessionId: string) => invalidationChannelRef.current?.broadcast(sessionId);

  const handleStartPortfolio = async (intakeText: string, attachment?: ExtractedDocument | null) => {
    if (mutatingStage) return;
    recordClientEvent({
      kind: "user_action",
      stage: "discovery",
      action: "start",
      input_characters: intakeText.length + (attachment?.characters ?? 0),
    });
    setMutatingStage("discover");
    try {
      let sessionId = state.sessionId;
      if (!sessionId) {
        const created = await api.createSession("Portfolio workspace");
        sessionId = created.id;
      }
      const action = "discovery-start";
      const result = await api.startDiscovery(
        sessionId,
        {
          source_text: intakeText,
          document_text: attachment?.text ?? "",
          document_name: attachment?.name ?? "",
          goal: "create my portfolio",
        },
        getOrCreateIdempotencyKey(sessionId, action),
      );
      clearIdempotencyKey(sessionId, action);
      inspectCacheReceipt("discovery", result);
      dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
      dispatch({ type: "discovery/set", view: adaptDiscovery(result.discovery, result.jobs) });
      dispatch({ type: "announce", message: "Explorer started." });
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

  const handleContinueWithCurrentInformation = async () => {
    if (!state.sessionId) return;
    const result = await api.putDiscoveryAnswers(state.sessionId, {
      complete: true,
      answers: [],
      continue_with_current_information: true,
    });
    inspectCacheReceipt("discovery", result);
    dispatch({ type: "discovery/set", view: adaptDiscovery(result.discovery, result.jobs) });
    dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
    notifyMutation(state.sessionId);
  };

  const readyBriefKey = readyDiscoveryRunKey(state.sessionId, state.discovery?.raw);
  useEffect(() => {
    if (!readyBriefKey || !state.sessionId || mutatingStage !== null) return;
    if (autoBriefAttempts.current.has(readyBriefKey)) return;
    autoBriefAttempts.current.add(readyBriefKey);
    const sessionId = state.sessionId;
    setMutatingStage("discover");
    void (async () => {
      try {
        const result = await api.putDiscoveryAnswers(sessionId, {
          complete: true,
          answers: [],
          continue_with_current_information: true,
        });
        inspectCacheReceipt("discovery", result);
        dispatch({ type: "discovery/set", view: adaptDiscovery(result.discovery, result.jobs) });
        dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
        notifyMutation(sessionId);
      } catch {
        // A lost response may follow a successful enqueue. Read the server
        // before offering the manual Continue action as a fallback.
        try {
          const result = await api.getDiscovery(sessionId);
          dispatch({ type: "discovery/set", view: adaptDiscovery(result.discovery, result.jobs) });
          dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
          if (isRecord(result.discovery) && result.discovery.status === "questions_ready") {
            dispatch({ type: "announce", message: "The brief could not start automatically. Choose Continue to retry." });
          }
        } catch {
          dispatch({ type: "connection/set", state: "stale" });
        }
      } finally {
        setMutatingStage(null);
      }
    })();
  }, [api, inspectCacheReceipt, mutatingStage, readyBriefKey, state.sessionId]);

  const handleRetryDiscovery = async () => {
    if (!state.sessionId || !state.discovery) return;
    if (state.discovery.job?.status === "queued" || state.discovery.job?.status === "running") {
      await refetchCurrentSession();
      return;
    }
    const rawBrief = typeof state.discovery.raw === "object" && state.discovery.raw !== null &&
      "brief" in state.discovery.raw && typeof state.discovery.raw.brief === "object" && state.discovery.raw.brief !== null
        ? state.discovery.raw.brief as Record<string, unknown> : {};
    const savedRevision = typeof rawBrief.revision_request === "string" ? rawBrief.revision_request.trim() : "";
    if (state.discovery.safeError?.retryOperation === "brief" && savedRevision) {
      const result = await api.reviseDiscovery(state.sessionId, savedRevision);
      inspectCacheReceipt("discovery", result);
      dispatch({ type: "discovery/set", view: adaptDiscovery(result.discovery, result.jobs) });
      dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
      notifyMutation(state.sessionId);
      return;
    }
    const rawQuestions =
      typeof state.discovery.raw === "object" && state.discovery.raw !== null &&
      "operation_a" in state.discovery.raw &&
      typeof state.discovery.raw.operation_a === "object" && state.discovery.raw.operation_a !== null &&
      "items" in state.discovery.raw.operation_a &&
      Array.isArray(state.discovery.raw.operation_a.items)
        ? state.discovery.raw.operation_a.items
        : [];
    const answeredIds = new Set(state.discovery.answeredQuestionIds);
    if (
      state.discovery.safeError?.retryOperation === "questions" &&
      rawQuestions.length > 0 &&
      rawQuestions.every((item: unknown) =>
        typeof item === "object" && item !== null && "id" in item &&
        typeof item.id === "string" && answeredIds.has(item.id),
      )
    ) {
      await handleContinueWithCurrentInformation();
      return;
    }
    if (state.discovery.safeError?.retryOperation !== "questions") {
      await handleContinueWithCurrentInformation();
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
    const retryIntake = {
      goal: typeof rawIntake.goal === "string" ? rawIntake.goal : "",
      ...(typeof rawIntake.source_text === "string"
        ? { source_text: rawIntake.source_text }
        : {
            message: typeof rawIntake.message === "string" ? rawIntake.message : "",
            document_text: typeof rawIntake.document_text === "string" ? rawIntake.document_text : "",
          }),
    };
    const result = await api.startDiscovery(
      sessionId,
      retryIntake,
      getOrCreateIdempotencyKey(sessionId, action),
    );
    clearIdempotencyKey(sessionId, action);
    inspectCacheReceipt("discovery", result);
    dispatch({ type: "discovery/set", view: adaptDiscovery(result.discovery, result.jobs) });
    dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
    dispatch({ type: "announce", message: "Explorer retry started." });
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
      dispatch({ type: "announce", message: "Explorer stopped. Your input is preserved." });
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
      dispatch({ type: "announce", message: "Content Architect stopped. Your approved Explorer brief is preserved." });
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
          "Resolve every deterministic approval error. Preserve valid content. The page must have exactly four pillars, every required field filled with complete visitor-facing copy, and claims bound to page fields only when their publication_status is approved. Safely rewrite or omit pending or blocked exact details instead of changing their publication status.",
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

  const startContentAfterApproval = async () => {
    try {
      setShellFailure(null);
      await runContentMutation("start");
      selectStage("content");
    } catch (error) {
      setShellFailure(captureFailure(error, "content_architect", "start after discovery approval", "Content Architect could not start."));
      dispatch({ type: "announce", message: `Content Architect could not start: ${error instanceof Error ? error.message : "try again."}` });
    }
  };

  // ── Studio (generated portfolio page) ────────────────────────────────
  // A ref lock, not React state: approving content and starting the build run
  // back to back, and the closure above would still see the old busy flag.
  const runStudioMutation = async (
    operation: "start" | "stop" | "message" | "restore",
    argument = "",
    clientMessageId = "",
  ): Promise<void> => {
    if (!state.sessionId || studioLock.current) return;
    const sessionId = state.sessionId;
    studioLock.current = true;
    setStudioBusy(true);
    try {
      const result =
        operation === "start"
          ? await api.startStudio(sessionId)
          : operation === "stop"
            ? await api.stopStudio(sessionId)
            : operation === "message"
              ? await api.sendStudioMessage(sessionId, {
                  message: argument,
                  client_message_id: clientMessageId,
                  base_version_id: state.studio?.activeVersionId ?? null,
                })
              : await api.restoreStudioVersion(sessionId, argument);
      const nextStudio = adaptStudio(result, true);
      if (operation === "start" && !state.studio?.activeVersionId) {
        const versionId = nextStudio.inFlight?.versionId ?? nextStudio.activeVersionId;
        if (versionId) {
          const marker = { startedAt: Date.now(), versionId };
          safeSessionStorage.setItem(presentationKey(sessionId), JSON.stringify(marker));
          setPresentation(marker);
        }
      }
      dispatch({ type: "studio/set", view: nextStudio });
      dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
      dispatch({
        type: "announce",
        message:
          operation === "start"
            ? "Building your portfolio."
            : operation === "stop"
              ? "Build stopped. Your last live page is unchanged."
              : operation === "message"
                ? "Working on your change."
                : "Earlier version restored.",
      });
      notifyMutation(sessionId);
    } catch (error) {
      void refetchCurrentSession();
      throw error;
    } finally {
      studioLock.current = false;
      setStudioBusy(false);
    }
  };

  // Starting is the one Studio request that reports through the stage panel
  // (it has no composer to show an error in), so it records instead of throwing.
  const startStudio = async () => {
    setStudioStartError(null);
    setStudioStartFailure(null);
    try {
      await runStudioMutation("start");
    } catch (error) {
      setStudioStartError(error instanceof Error ? error.message : "The build could not start. Please try again.");
      setStudioStartFailure(captureFailure(error, "studio", "start build", "The build could not start. Please try again."));
    }
  };

  const openStudio = async () => {
    selectStage("studio");
    const status = state.studio?.status;
    if (status === "ready" || status === "build_running") return;
    await startStudio();
  };

  // One explicit click on the approved content: approve, start the build, open the Studio.
  const handleApproveAndGenerate = async () => {
    const completed = await runContentMutation("approve");
    if (completed !== "approve") return; // a safety repair keeps the user on Content
    selectStage("studio");
    await startStudio();
  };

  const handleStopStudio = async () => {
    if (!state.sessionId) return;
    setShellFailure(null);
    recordClientEvent({ kind: "user_action", stage: "studio", action: "stop" });
    studioPollerRef.current?.unsubscribe("code_generator");
    try {
      await runStudioMutation("stop");
    } catch {
      setShellFailure(captureFailure(null, "studio", "stop build", "The build could not be stopped."));
      dispatch({ type: "announce", message: "The build could not be stopped. Refreshing its status." });
    }
  };

  const loadStudioPreview = useCallback(
    (versionId: string) => {
      if (!state.sessionId) return Promise.reject(new Error("There is no active portfolio session."));
      return api.getStudioPreview(state.sessionId, versionId);
    },
    [api, state.sessionId],
  );

  const handleResetPipeline = async () => {
    if (!state.sessionId || resetting || mutatingStage || studioBusy) return;
    const confirmed = window.confirm(
      "Reset your portfolio pipeline? This permanently removes your Explorer material, content plan, generated page, and chat history. You will start again from an empty Explorer screen.",
    );
    if (!confirmed) return;
    const sessionId = state.sessionId;
    setResetting(true);
    setResetError(null);
    setResetFailure(null);
    try {
      const result = await api.resetSession(sessionId);
      safeSessionStorage.removeItem("oryxenai.discovery_intake_draft");
      for (const action of ["discovery-start", "discovery-retry-questions", "content-start"]) {
        clearIdempotencyKey(sessionId, action);
      }
      dispatch({ type: "pipeline/reset", sessionId: result.id, revision: result.revision });
      safeSessionStorage.removeItem(presentationKey(sessionId));
      setPresentation(null);
      notifyMutation(sessionId);
      window.location.replace(
        `${window.location.pathname}${serializeAppUrlState({ stage: "discover", view: "work" })}`,
      );
    } catch (reason) {
      setResetError(reason instanceof Error ? reason.message : "The pipeline could not be reset.");
      setResetFailure(captureFailure(reason, "workspace", "reset pipeline", "The pipeline could not be reset."));
    } finally {
      setResetting(false);
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

          <nav className="workspace-topnav" aria-label="Workspace pages">
            <button type="button" className={activeScreen === "home" ? "is-active" : ""} aria-current={activeScreen === "home" ? "page" : undefined} onClick={() => selectScreen("home")}>Home</button>
            <button type="button" className={activeScreen === "guide" ? "is-active" : ""} aria-current={activeScreen === "guide" ? "page" : undefined} onClick={() => selectScreen("guide")}>Guide</button>
          </nav>
          {!activeScreen && <JourneyRail journey={journey} selectedStageId={activeStage} onSelect={selectStage} />}

          <div className="app-topbar-actions">
            <span className="topbar-motto" aria-hidden="true">A MORE THOUGHTFUL CREATIVE FUTURE</span>
            <span className="topbar-dot" aria-hidden="true">●</span>
            <button
              type="button"
              className="pipeline-reset-button"
              aria-label="Reset pipeline"
              onClick={handleResetPipeline}
              disabled={!state.sessionId || resetting || Boolean(mutatingStage) || studioBusy}
              title={state.sessionId ? "Clear this portfolio and start again" : "Start Explorer to create a pipeline"}
            >
              {resetting ? "Resetting…" : <>Reset <span className="pipeline-reset-word">pipeline</span></>}
            </button>
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

        <ConnectionBanner state={state.connection} failure={connectionFailure} />
        {shellFailure && <div className="pipeline-reset-error" role="alert">{shellFailure.summary} <CopyDiagnosticsButton failure={shellFailure} /></div>}
        {resetError && <div className="pipeline-reset-error" role="alert">{resetError} {resetFailure && <CopyDiagnosticsButton failure={resetFailure} />}</div>}
        <CacheNotice key={cacheNotice?.id ?? "empty"} message={cacheNotice?.message ?? null} />
        {developer ? (
          <ClientTraceNotice traceId={getClientTraceId()} />
        ) : null}

        {/* In-flow Stage Context Strip matching 01-shell-overview.png */}
        {!activeScreen && <StageContextStrip
          stageName={stageDisplayName(activeStage)}
          stagePurpose={stagePurposeText(activeStage)}
          tagline="A STRONG START LEADS FURTHER"
        />}

        <main className="app-work-surface">
          <div className="app-stage-layout">
            <ErrorBoundary fallbackTitle="Unable to display this stage" onReset={refetchCurrentSession}>
              <section id="workspace-stage" className="stage-frame" data-stage={activeScreen ?? activeStage} tabIndex={-1}>
              {activeScreen === "home" ? (
                <WorkspaceHome
                  nextStage={resumeStage}
                  hasSession={Boolean(state.sessionId)}
                  discoveryApproved={discoveryApproved}
                  contentApproved={contentApprovedForStudio}
                  previewReady={previewReady}
                  working={Boolean(state.discovery?.state === "working" || state.content?.state === "working" || state.studio?.building)}
                  onResume={() => selectStage(resumeStage)}
                  onGuide={() => selectScreen("guide")}
                />
              ) : activeScreen === "guide" ? (
                <WorkspaceGuide nextStage={resumeStage} onResume={() => selectStage(resumeStage)} />
              ) : <div key={activeStage} className="stage-transition-layer">
              {!state.sessionId ? (
                <StartSurface
                  onStart={handleStartPortfolio}
                  onExtractDocument={api.extractDocument}
                  disabled={me.can_create_portfolio === false || mutatingStage === "discover"}
                  disabledReason={me.can_create_portfolio === false ? "Your account cannot start another portfolio." : undefined}
                />
              ) : null}

              {state.sessionId && activeStage === "discover" ? (
                <DiscoveryStage
                  view={state.discovery}
                  history={discoveryHistory}
                  canMutate={mutatingStage === null}
                  onStartDiscovery={handleStartPortfolio}
                  onExtractDocument={api.extractDocument}
                  onSubmitAnswer={handleSubmitDiscoveryAnswer}
                  onContinueWithCurrentInformation={handleContinueWithCurrentInformation}
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
                  onApproveAndContinue={handleApproveAndGenerate}
                  approveLabel="Approve & generate my portfolio"
                  onOpenStudio={openStudio}
                  studioInFlight={studioBusy}
                  onRevise={async (request) => { await runContentMutation("revise", request); }}
                  onStop={handleStopContent}
                />
              ) : null}

              {state.sessionId && activeStage === "studio" ? (
                <StudioStage
                  view={state.studio}
                  contentApproved={contentApprovedForStudio}
                  canMutate={mutatingStage === null}
                  inFlight={studioBusy}
                  startError={studioStartError}
                  startFailure={studioStartFailure}
                  loadPreview={loadStudioPreview}
                  onStart={startStudio}
                  onStop={handleStopStudio}
                  onSend={(message, clientMessageId) => runStudioMutation("message", message, clientMessageId)}
                  onRestore={(versionId) => runStudioMutation("restore", versionId)}
                  onBackToContent={() => selectStage("content")}
                  presentationStartMs={presentation?.startedAt}
                  presentationVersionId={presentation?.versionId}
                  onPresentationComplete={() => {
                    if (state.sessionId) safeSessionStorage.removeItem(presentationKey(state.sessionId));
                    setPresentation(null);
                  }}
                />
              ) : null}


              </div>}
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
