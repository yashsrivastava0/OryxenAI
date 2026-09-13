import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "preact/hooks";
import { AppStoreContext, appReducer, initialAppState } from "./store";
import { createApiClient, type AuthorizedFetch, type CacheReceipt, type MeProjection, type StageEnvelope } from "../data/api-client";
import { adaptDiscovery } from "../data/adapters/discovery";
import { adaptContentArchitect } from "../data/adapters/content";
import { adaptVisualDesignDirector } from "../data/adapters/design";
import { adaptBuildPreparation } from "../data/adapters/preparation";
import { adaptCodeGenerator } from "../data/adapters/generation";
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
import { DesignStage } from "../stages/design/DesignStage";
import { BuildPreparationStage } from "../stages/preparation/BuildPreparationStage";
import { GenerationStage } from "../stages/generation/GenerationStage";
import { DiscoveryStage } from "../stages/discovery/DiscoveryStage";
import { parseAppUrlState, serializeAppUrlState, type JourneyStageId } from "./url-state";
import { safeSessionStorage } from "../data/safe-storage";
import { getClientTraceId, recordClientEvent } from "../data/client-diagnostics";
import { ClientTraceNotice } from "../components/ClientTraceNotice";
import { OutputInspector } from "../components/OutputInspector";

export interface AppShellProps {
  authorizedFetch: AuthorizedFetch;
  me: MeProjection;
  serverSessionId: string | null;
  readOnly: boolean;
  developer?: boolean;
}

function viewForStage(stage: JourneyStageId): "work" | "artifact" {
  return stage === "discover" ? "work" : "artifact";
}

function activeSessionStorageKey(userId: string): string {
  return `oryxenai.active_session_id:${userId}`;
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
  readOnly,
  developer = false,
}: AppShellProps) {
  const initialUrl = useMemo(
    () => parseAppUrlState(typeof window === "undefined" ? "" : window.location.search),
    [],
  );
  const initialStage = initialUrl.stage ?? "discover";
  const [activeStage, setActiveStage] = useState<JourneyStageId>(initialStage);
  const [mutatingStage, setMutatingStage] = useState<JourneyStageId | null>(null);
  const [showResetModal, setShowResetModal] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

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
      const [sessionResult, discoveryResult, contentResult, designResult, preparationResult, generationResult] = await Promise.allSettled([
        api.getSession(sessionId),
        api.getDiscovery(sessionId),
        api.getContentArchitect(sessionId),
        api.getVisualDesignDirector(sessionId),
        api.getBuildPreparation(sessionId),
        api.getCodeGenerator(sessionId),
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

      let designApproved = false;
      if (designResult.status === "fulfilled") {
        inspectCacheReceipt("visual_design_director", designResult.value);
        const view = adaptVisualDesignDirector(
          designResult.value.visual_design_director,
          contentApproved,
          designResult.value.jobs,
        );
        designApproved = view.state === "complete";
        dispatch({
          type: "design/set",
          view,
        });
      }

      let preparationApproved = false;
      if (preparationResult.status === "fulfilled") {
        inspectCacheReceipt("build_preparation", preparationResult.value);
        const view = adaptBuildPreparation(
          preparationResult.value.build_preparation,
          contentApproved,
          designApproved,
          preparationResult.value.jobs,
        );
        preparationApproved = view.state === "complete";
        dispatch({ type: "preparation/set", view });
      }

      if (generationResult.status === "fulfilled") {
        inspectCacheReceipt("code_generator", generationResult.value);
        dispatch({
          type: "generation/set",
          view: adaptCodeGenerator(
            generationResult.value.code_generator,
            preparationApproved,
            generationResult.value.jobs,
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
        if (requested === "prepare" && !designApproved) {
          fallback = contentApproved ? "design" : discoveryApproved ? "content" : "discover";
        }
        if (requested === "generate" && !preparationApproved) {
          fallback = designApproved ? "prepare" : contentApproved ? "design" : discoveryApproved ? "content" : "discover";
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

      const results = [sessionResult, discoveryResult, contentResult, designResult, preparationResult, generationResult];
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

    if (state.preparation?.state === "working") {
      poller.subscribe("build_preparation", async () => {
        try {
          const result = await api.getBuildPreparation(sessionId);
          inspectCacheReceipt("build_preparation", result);
          const view = adaptBuildPreparation(
            result.build_preparation,
            state.content?.state === "complete",
            state.design?.state === "complete",
            result.jobs,
          );
          dispatch({ type: "preparation/set", view });
          dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
          dispatch({ type: "connection/set", state: "confirmed" });
          if (view.state === "complete") {
            dispatch({ type: "announce", message: "Build handoff ready for generation." });
          }
        } catch (error) {
          dispatch({ type: "connection/set", state: navigator.onLine ? "stale" : "offline" });
          throw error;
        }
      });
    } else poller.unsubscribe("build_preparation");

    if (state.generation?.state === "working") {
      poller.subscribe("code_generator", async () => {
        try {
          const result = await api.getCodeGenerator(sessionId);
          inspectCacheReceipt("code_generator", result);
          const view = adaptCodeGenerator(
            result.code_generator,
            state.preparation?.state === "complete",
            result.jobs,
          );
          dispatch({ type: "generation/set", view });
          dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
          dispatch({ type: "connection/set", state: "confirmed" });
          if (view.state === "complete") {
            dispatch({ type: "announce", message: "Portfolio generated and ready to preview." });
          }
        } catch (error) {
          dispatch({ type: "connection/set", state: navigator.onLine ? "stale" : "offline" });
          throw error;
        }
      });
    } else poller.unsubscribe("code_generator");

    return () => {
      poller.unsubscribe("discovery");
      poller.unsubscribe("content_architect");
      poller.unsubscribe("visual_design_director");
      poller.unsubscribe("build_preparation");
      poller.unsubscribe("code_generator");
    };
  }, [
    api,
    inspectCacheReceipt,
    state.content?.state,
    state.design?.state,
    state.discovery?.state,
    state.generation?.state,
    state.preparation?.state,
    state.sessionId,
  ]);

  const journey = useMemo<JourneyStageVM[]>(() => {
    const discoveryState = state.discovery?.state ?? "available";
    const discoveryApproved = discoveryState === "complete";
    const contentState = state.content?.state ?? (discoveryApproved ? "available" : "locked");
    const contentApproved = contentState === "complete";
    const designState = state.design?.state ?? (contentApproved ? "available" : "locked");
    const designApproved = designState === "complete";
    const preparationState = state.preparation?.state ?? (contentApproved && designApproved ? "available" : "locked");
    const preparationApproved = preparationState === "complete";
    const generationState = state.generation?.state ?? (preparationApproved ? "available" : "locked");
    return [
      { id: "discover", ordinal: 1, label: "Discover", sublabel: "UNDERSTAND YOUR STORY", state: discoveryState, isSelectable: true },
      { id: "content", ordinal: 2, label: "Content", sublabel: "SHAPE NARRATIVE", state: contentState, isSelectable: contentState !== "locked" },
      { id: "design", ordinal: 3, label: "Design", sublabel: "CRAFT PRESENTATION", state: designState, isSelectable: designState !== "locked" },
      { id: "prepare", ordinal: 4, label: "Prepare", sublabel: "FINALIZE DETAILS", state: preparationState, isSelectable: preparationState !== "locked" && preparationState !== "unsupported" },
      { id: "generate", ordinal: 5, label: "Generate & Preview", sublabel: "BUILD AND PREVIEW", state: generationState, isSelectable: generationState !== "locked" && generationState !== "unsupported" },
    ];
  }, [state.content, state.design, state.discovery, state.generation, state.preparation]);

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
    {
      id: "design",
      label: "Visual Design Director",
      state: state.design?.state ?? "locked",
      agentOutput: state.design?.agentOutput ?? null,
      available: hasCopyableOutput("design", state.design?.agentOutput),
    },
    {
      id: "prepare",
      label: "Build Preparation Agent",
      state: state.preparation?.state ?? "locked",
      agentOutput: state.preparation?.agentOutput ?? null,
      available: hasCopyableOutput("prepare", state.preparation?.agentOutput),
      stale: state.preparation?.stale ?? false,
    },
    {
      id: "generate",
      label: "Code Generator",
      state: state.generation?.state ?? "locked",
      agentOutput: state.generation?.agentOutput ?? null,
      available: hasCopyableOutput("generate", state.generation?.agentOutput),
      stale: state.generation?.stale ?? false,
    },
  ], [state.content, state.design, state.discovery, state.generation, state.preparation]);

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

  const handleResetPipeline = async () => {
    if (!state.sessionId || isResetting) return;
    setIsResetting(true);
    recordClientEvent({
      kind: "user_action",
      stage: activeStage,
      action: "admin_pipeline_reset",
    });
    try {
      const sessionId = state.sessionId;
      const reset = await api.resetSession(sessionId);
      seenCacheReceipts.current.clear();
      dispatch({ type: "pipeline/reset", sessionId: reset.id, revision: reset.revision });
      selectStage("discover", true);
      notifyMutation(sessionId);
      await refetchCurrentSession();
      dispatch({
        type: "announce",
        message: "Pipeline has been reset to zero. You can now start fresh with a new resume.",
      });
      setShowResetModal(false);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Failed to reset pipeline.";
      dispatch({
        type: "announce",
        message: `Reset failed: ${msg}`,
      });
    } finally {
      setIsResetting(false);
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

  // Approval is committed before the separate "start Visual Design Director"
  // action is offered. If approval silently reroutes into the safety
  // repair path instead (public-scope validation failure), stay on Content
  // so the user can review the corrected plan — never silently advance past
  // an artifact that was not actually approved.
  const handleApproveContentAndContinue = async () => {
    const completedOperation = await runContentMutation("approve");
    if (completedOperation !== "approve") return;
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

  // Approval is committed before the separate "start Build Preparation" action.
  const handleApproveDesignAndContinue = async () => {
    await runDesignMutation("approve");
  };

  const runPreparationMutation = async (operation: "start" | "regenerate") => {
    if (!state.sessionId || mutatingStage) {
      return;
    }
    const sessionId = state.sessionId;
    setMutatingStage("prepare");
    try {
      const action = `build-preparation-${operation}`;
      const idempotencyKey = getOrCreateIdempotencyKey(sessionId, action);
      const result = operation === "start"
        ? await api.startBuildPreparation(sessionId, {}, idempotencyKey)
        : await api.regenerateBuildPreparation(sessionId, {}, idempotencyKey);
      clearIdempotencyKey(sessionId, action);
      inspectCacheReceipt("build_preparation", result);
      dispatch({
        type: "preparation/set",
        view: adaptBuildPreparation(result.build_preparation, true, true, result.jobs),
      });
      dispatch({
        type: "session/set",
        sessionId: result.session_id,
        revision: result.session_revision,
      });
      dispatch({
        type: "announce",
        message: operation === "regenerate"
          ? "Build handoff regeneration started."
          : "Build Preparation started.",
      });
      notifyMutation(sessionId);
      selectStage("prepare");
    } catch (error) {
      void refetchCurrentSession();
      throw error;
    } finally {
      setMutatingStage(null);
    }
  };

  const runGenerationMutation = async (operation: "start" | "regenerate") => {
    if (!state.sessionId || mutatingStage || state.preparation?.state !== "complete") {
      return;
    }
    const sessionId = state.sessionId;
    setMutatingStage("generate");
    try {
      const action = `code-generator-${operation}`;
      const idempotencyKey = getOrCreateIdempotencyKey(sessionId, action);
      const result = operation === "start"
        ? await api.startCodeGenerator(sessionId, idempotencyKey)
        : await api.regenerateCodeGenerator(sessionId, idempotencyKey);
      clearIdempotencyKey(sessionId, action);
      inspectCacheReceipt("code_generator", result);
      dispatch({
        type: "generation/set",
        view: adaptCodeGenerator(result.code_generator, true, result.jobs),
      });
      dispatch({
        type: "session/set",
        sessionId: result.session_id,
        revision: result.session_revision,
      });
      dispatch({
        type: "announce",
        message: operation === "regenerate"
          ? "Portfolio regeneration started."
          : "Portfolio generation started.",
      });
      notifyMutation(sessionId);
      selectStage("generate");
    } catch (error) {
      void refetchCurrentSession();
      throw error;
    } finally {
      setMutatingStage(null);
    }
  };

  const retryGeneration = async () => {
    if (!state.sessionId || mutatingStage || state.preparation?.state !== "complete") return;
    const sessionId = state.sessionId;
    setMutatingStage("generate");
    try {
      const action = "code-generator-retry";
      const idempotencyKey = getOrCreateIdempotencyKey(sessionId, action);
      const result = await api.retryCodeGenerator(sessionId, idempotencyKey);
      clearIdempotencyKey(sessionId, action);
      inspectCacheReceipt("code_generator", result);
      dispatch({
        type: "generation/set",
        view: adaptCodeGenerator(result.code_generator, true, result.jobs),
      });
      dispatch({ type: "session/set", sessionId: result.session_id, revision: result.session_revision });
      dispatch({ type: "announce", message: "Portfolio retry started." });
      notifyMutation(sessionId);
      selectStage("generate");
    } catch (error) {
      void refetchCurrentSession();
      throw error;
    } finally {
      setMutatingStage(null);
    }
  };

  const startContentAfterApproval = async () => {
    try {
      await runContentMutation("start");
      selectStage("content");
    } catch (error) {
      dispatch({ type: "announce", message: `Content Architect could not start: ${error instanceof Error ? error.message : "try again."}` });
    }
  };

  const startDesignAfterApproval = async () => {
    try {
      await runDesignMutation("start");
      selectStage("design");
    } catch (error) {
      dispatch({ type: "announce", message: `Visual Design Director could not start: ${error instanceof Error ? error.message : "try again."}` });
    }
  };

  const startPreparationAfterApproval = async () => {
    try {
      await runPreparationMutation("start");
      selectStage("prepare");
    } catch (error) {
      dispatch({ type: "announce", message: `Build Preparation could not start: ${error instanceof Error ? error.message : "try again."}` });
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
            <span className="header-descriptor">portfolio editorial room</span>
          </a>
          <div className="app-topbar-actions">
            <details className="account-menu">
              <summary aria-label="Open account menu">
                <span className="account-monogram" aria-hidden="true">{(me.username ?? "U").slice(0, 1).toUpperCase()}</span>
                <span className="account-name">{me.username ?? "Account"}</span>
                <span className="account-chevron" aria-hidden="true">▾</span>
              </summary>
              <div className="account-popover">
                <p><strong>{me.username ?? "OryxenAI account"}</strong><span>{me.role === "admin" ? "Administrator" : "Portfolio owner"}</span></p>
                {state.readOnly ? <span className="read-only-tag">Read-only workspace</span> : null}
                {me.role === "admin" ? <a id="app-admin-link" href="/admin">Administration</a> : null}
                {me.role === "admin" && state.sessionId ? (
                  <button
                    id="account-reset-pipeline-btn"
                    type="button"
                    className="account-popover-reset-btn"
                    onClick={() => setShowResetModal(true)}
                    disabled={mutatingStage !== null || isResetting}
                  >
                    Reset pipeline to zero
                  </button>
                ) : null}
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

        <div className="app-work-surface">
          {/* Ambient registration marks and margin tags */}
          <span className="reg-mark reg-tl" aria-hidden="true">+</span>
          <span className="reg-mark reg-tr" aria-hidden="true">+</span>
          <span className="reg-mark reg-bl" aria-hidden="true">+</span>
          <span className="reg-mark reg-br" aria-hidden="true">+</span>

          <span className="editorial-margin-label margin-tl" aria-hidden="true">PRIVATE BY DESIGN.</span>
          <span className="editorial-margin-label margin-tr" aria-hidden="true">IDEAS IN, OPPORTUNITIES OUT.</span>
          <span className="editorial-margin-label margin-bl" aria-hidden="true">FROM EXPERIENCE TO OPPORTUNITY.</span>
          <span className="editorial-margin-label margin-br" aria-hidden="true">A MORE MEANINGFUL NEXT CHAPTER.</span>

          <JourneyRail journey={journey} selectedStageId={activeStage} onSelect={selectStage} />

          <div className="app-stage-layout">
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
                  inFlight={mutatingStage === "discover"}
                  onApproveAndContinue={handleApproveBrief}
                  onStartNextStage={startContentAfterApproval}
                  onReviseBrief={handleReviseBrief}
                />
              ) : null}

              {state.sessionId && activeStage === "content" ? (
                <ContentStage
                  view={state.content}
                  canMutate={!state.readOnly}
                  inFlight={mutatingStage === "content"}
                  onStart={async () => { await runContentMutation("start"); }}
                  onApproveAndContinue={handleApproveContentAndContinue}
                  onStartNextStage={startDesignAfterApproval}
                  onRevise={async (request) => { await runContentMutation("revise", request); }}
                  onStop={handleStopContent}
                />
              ) : null}

                {state.sessionId && activeStage === "design" ? (
                <DesignStage
                  view={state.design}
                  canMutate={!state.readOnly}
                  inFlight={mutatingStage === "design"}
                  onStart={() => runDesignMutation("start")}
                  onApproveAndContinue={handleApproveDesignAndContinue}
                  onStartNextStage={startPreparationAfterApproval}
                  onRevise={(request) => runDesignMutation("revise", request)}
                  onStop={handleStopDesign}
                />
              ) : null}
                {state.sessionId && activeStage === "prepare" ? (
                  <BuildPreparationStage
                    view={state.preparation}
                    canMutate={!state.readOnly && mutatingStage === null}
                    inFlight={mutatingStage === "prepare"}
                    onStart={() => runPreparationMutation("start")}
                    onRegenerate={() => runPreparationMutation("regenerate")}
                    onContinueToGenerate={() => selectStage("generate")}
                  />
                ) : null}
                {state.sessionId && activeStage === "generate" ? (
                  <GenerationStage
                    view={state.generation}
                    canMutate={!state.readOnly && mutatingStage === null}
                    inFlight={mutatingStage === "generate"}
                    onStart={() => runGenerationMutation("start")}
                    onRetry={retryGeneration}
                    onRegenerate={() => runGenerationMutation("regenerate")}
                  />
                ) : null}
              </section>
            </ErrorBoundary>
            <OutputInspector entries={outputEntries} activeStage={activeStage} enabled={Boolean(developer && state.sessionId)} />
          </div>
        </div>
        <footer className="app-footer"><span>Private working space</span><span>Nothing advances without approval</span></footer>
        <StatusAnnouncer message={state.announcement} />

        {showResetModal ? (
          <div
            className="admin-reset-modal-backdrop"
            role="presentation"
            onClick={(e) => {
              if (e.target === e.currentTarget && !isResetting) setShowResetModal(false);
            }}
          >
            <div
              className="admin-reset-modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="reset-modal-title"
            >
              <div className="admin-reset-modal-header">
                <div className="admin-reset-modal-title-row">
                  <span className="admin-reset-badge">ADMIN ACTION</span>
                  <h2 id="reset-modal-title">Reset Pipeline to Zero</h2>
                </div>
                <p className="admin-reset-modal-subtitle">
                  This will permanently clear all Discovery answers, approved brief, content architecture, visual direction, and generated drafts for this portfolio.
                </p>
              </div>
              <div className="admin-reset-modal-body">
                <div className="admin-reset-warning-box">
                  <strong>What will happen:</strong>
                  <ul>
                    <li>The entire agent pipeline restarts from turn 1.</li>
                    <li>The Discovery agent will ask for your resume and goals again.</li>
                    <li>All queued and background agent jobs will be cancelled.</li>
                    <li>You will remain signed in as <strong>{me.username || "admin"}</strong>.</li>
                  </ul>
                </div>
              </div>
              <div className="admin-reset-modal-actions">
                <button
                  type="button"
                  className="admin-reset-cancel-btn"
                  onClick={() => setShowResetModal(false)}
                  disabled={isResetting}
                >
                  Cancel
                </button>
                <button
                  id="confirm-reset-pipeline-btn"
                  type="button"
                  className="admin-reset-confirm-btn"
                  onClick={handleResetPipeline}
                  disabled={isResetting}
                >
                  {isResetting ? "Resetting pipeline…" : "Confirm & Reset Pipeline"}
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </AppStoreContext.Provider>
  );
}
