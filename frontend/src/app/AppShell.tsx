import { useEffect, useMemo, useReducer, useRef, useState, useCallback } from "preact/hooks";
import { AppStoreContext, appReducer, initialAppState } from "./store";
import { createApiClient, type AuthorizedFetch, type MeProjection } from "../data/api-client";
import { adaptDiscovery } from "../data/adapters/discovery";
import { adaptContentArchitect } from "../data/adapters/content";
import { adaptVisualDesignDirector } from "../data/adapters/design";
import { adaptBuildPreparation } from "../data/adapters/preparation";
import { adaptCodeGenerator } from "../data/adapters/generation";
import { getOrCreateIdempotencyKey, clearIdempotencyKey } from "../data/idempotency";
import { PollCoordinator } from "../data/polling";
import { createInvalidationChannel, type InvalidationChannel } from "../data/invalidation";
import { JourneyRail, type JourneyStageVM } from "../components/JourneyRail";
import { ConnectionBanner } from "../components/ConnectionBanner";
import { StatusAnnouncer } from "../components/StatusAnnouncer";
import { LivingDraftMark } from "../components/LivingDraftMark";
import { StartSurface } from "../components/StartSurface";
import { DiscoveryStage } from "../stages/discovery/DiscoveryStage";
import { ContentStage } from "../stages/content/ContentStage";
import { DesignStage } from "../stages/design/DesignStage";
import { PreparationStage } from "../stages/preparation/PreparationStage";
import { GenerationStage } from "../stages/generation/GenerationStage";
import { ConnectedPreviewSurface } from "../stages/preview/PreviewSurface";
import { adaptPreview } from "../data/adapters/preview";
import { parseAppUrlState, serializeAppUrlState, type JourneyStageId } from "./url-state";
import type { AnsweredTurn } from "../components/ConversationSurface";

export interface AppShellProps {
  authorizedFetch: AuthorizedFetch;
  me: MeProjection;
  serverSessionId: string | null;
  readOnly: boolean;
}

export function AppShell({ authorizedFetch, me, serverSessionId, readOnly }: AppShellProps) {
  const initialUrl = parseAppUrlState(typeof window !== "undefined" ? window.location.search : "");
  const [activeStage, setActiveStage] = useState<JourneyStageId>(initialUrl.stage ?? "discover");
  const [discoveryHistory, setDiscoveryHistory] = useState<AnsweredTurn[]>([]);

  const [state, dispatch] = useReducer(appReducer, {
    ...initialAppState,
    me,
    readOnly,
    sessionId: serverSessionId,
    activeStage: initialUrl.stage ?? "discover",
  });

  const api = useMemo(() => createApiClient(authorizedFetch), [authorizedFetch]);
  const pollerRef = useRef<PollCoordinator | null>(null);
  const invalidationChannelRef = useRef<InvalidationChannel | null>(null);

  // Setup PollCoordinator and Invalidation Channel
  useEffect(() => {
    const poller = new PollCoordinator();
    pollerRef.current = poller;

    const channel = createInvalidationChannel((msg) => {
      if (state.sessionId && msg.sessionId === state.sessionId) {
        // Tab synchronization: another tab invalidated the session state
        refetchCurrentSession();
      }
    });
    invalidationChannelRef.current = channel;

    return () => {
      poller.teardown();
      channel.close();
    };
  }, [state.sessionId]);

  // Handle browser back/forward (popstate)
  useEffect(() => {
    const onPopState = () => {
      const url = parseAppUrlState(window.location.search);
      if (url.stage) {
        setActiveStage(url.stage);
        dispatch({ type: "stage/select", stage: url.stage });
      }
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  // Fetch / restore session projections
  const refetchCurrentSession = useCallback(async () => {
    if (!state.sessionId) return;
    dispatch({ type: "connection/set", state: "checking" });
    try {
      // Coarse session projection
      const sessionData = await api.getSession(state.sessionId);
      dispatch({ type: "session/set", sessionId: sessionData.id, revision: sessionData.revision });

      // Fetch Discovery state
      const discoveryData = await api.getDiscovery(state.sessionId);
      const discoveryView = adaptDiscovery(discoveryData.discovery);
      dispatch({ type: "discovery/set", view: discoveryView });

      const isDiscoveryApproved = discoveryView.state === "complete";

      // Fetch Content Architect state
      const contentData = await api.getContentArchitect(state.sessionId);
      const contentView = adaptContentArchitect(contentData.content_architect, isDiscoveryApproved);
      dispatch({ type: "content/set", view: contentView });

      const isContentApproved = contentView.state === "complete";

      // Fetch Visual Design Director state
      const designData = await api.getVisualDesignDirector(state.sessionId);
      const designView = adaptVisualDesignDirector(designData.visual_design_director, isContentApproved);
      dispatch({ type: "design/set", view: designView });

      const isDesignApproved = designView.state === "complete";

      // Fetch Build Preparation state
      const prepData = await api.getBuildPreparation(state.sessionId);
      const prepView = adaptBuildPreparation(prepData.build_preparation, isDesignApproved);
      dispatch({ type: "preparation/set", view: prepView });

      const isPrepComplete = prepView.state === "complete";

      // Fetch Code Generator state
      const genData = await api.getCodeGenerator(state.sessionId);
      const genView = adaptCodeGenerator(genData.code_generator, isPrepComplete, Boolean(state.readOnly));
      dispatch({ type: "generation/set", view: genView });
      const previewV = adaptPreview(genView);
      dispatch({ type: "preview/set", view: previewV });

      if (!initialUrl.stage) {
        if (state.readOnly && genView.hasUsablePreview) {
          setActiveStage("preview");
          dispatch({ type: "stage/select", stage: "preview" });
        } else if (genView.hasUsablePreview && genView.state === "complete" && isPrepComplete) {
          setActiveStage("preview");
          dispatch({ type: "stage/select", stage: "preview" });
        }
      }

      dispatch({ type: "connection/set", state: "confirmed" });
    } catch {
      dispatch({ type: "connection/set", state: "stale" });
    }
  }, [api, state.sessionId, state.readOnly, initialUrl.stage]);

  // Initial load on session change
  useEffect(() => {
    if (state.sessionId) {
      refetchCurrentSession();
    } else {
      dispatch({ type: "connection/set", state: "confirmed" });
    }
  }, [state.sessionId, refetchCurrentSession]);

  // Tab visibility: refetch when returning from background
  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible" && state.sessionId) {
        refetchCurrentSession();
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => document.removeEventListener("visibilitychange", onVisibilityChange);
  }, [state.sessionId, refetchCurrentSession]);

  // Polling management: subscribe only when active stage is in working state
  useEffect(() => {
    const poller = pollerRef.current;
    if (!poller || !state.sessionId) return;
    const sessionId = state.sessionId;

    // Discovery Polling
    if (state.discovery?.state === "working") {
      poller.subscribe("discovery", async () => {
        try {
          const res = await api.getDiscovery(sessionId);
          const view = adaptDiscovery(res.discovery);
          dispatch({ type: "discovery/set", view });
          dispatch({ type: "session/set", sessionId: res.session_id, revision: res.session_revision });
          if (view.state === "review") {
            dispatch({ type: "announce", message: "Portfolio brief is ready for review." });
          }
        } catch {
          dispatch({ type: "connection/set", state: "stale" });
        }
      });
    } else {
      poller.unsubscribe("discovery");
    }

    // Content Architect Polling
    if (state.content?.state === "working") {
      poller.subscribe("content_architect", async () => {
        try {
          const res = await api.getContentArchitect(sessionId);
          const view = adaptContentArchitect(res.content_architect, state.discovery?.state === "complete");
          dispatch({ type: "content/set", view });
          dispatch({ type: "session/set", sessionId: res.session_id, revision: res.session_revision });
          if (view.state === "review") {
            dispatch({ type: "announce", message: "Content plan is ready for review." });
          }
        } catch {
          dispatch({ type: "connection/set", state: "stale" });
        }
      });
    } else {
      poller.unsubscribe("content_architect");
    }

    // Visual Design Director Polling
    if (state.design?.state === "working") {
      poller.subscribe("visual_design_director", async () => {
        try {
          const res = await api.getVisualDesignDirector(sessionId);
          const view = adaptVisualDesignDirector(res.visual_design_director, state.content?.state === "complete");
          dispatch({ type: "design/set", view });
          dispatch({ type: "session/set", sessionId: res.session_id, revision: res.session_revision });
          if (view.state === "review") {
            dispatch({ type: "announce", message: "Visual direction is ready for review." });
          }
        } catch {
          dispatch({ type: "connection/set", state: "stale" });
        }
      });
    } else {
      poller.unsubscribe("visual_design_director");
    }

    // Build Preparation Polling
    if (state.preparation?.state === "working") {
      poller.subscribe("build_preparation", async () => {
        try {
          const res = await api.getBuildPreparation(sessionId);
          const view = adaptBuildPreparation(res.build_preparation, state.design?.state === "complete");
          dispatch({ type: "preparation/set", view });
          dispatch({ type: "session/set", sessionId: res.session_id, revision: res.session_revision });
          if (view.state === "complete") {
            dispatch({ type: "announce", message: "Build handoff package verified and ready for generation." });
          } else if (view.state === "attention") {
            dispatch({ type: "announce", message: "Build preparation needs attention." });
          }
        } catch {
          dispatch({ type: "connection/set", state: "stale" });
        }
      });
    } else {
      poller.unsubscribe("build_preparation");
    }

    // Code Generator Polling
    if (state.generation?.state === "working") {
      poller.subscribe("code_generator", async () => {
        try {
          const res = await api.getCodeGenerator(sessionId);
          const view = adaptCodeGenerator(res.code_generator, state.preparation?.state === "complete", Boolean(state.readOnly));
          dispatch({ type: "generation/set", view });
          const previewV = adaptPreview(view);
          dispatch({ type: "preview/set", view: previewV });
          dispatch({ type: "session/set", sessionId: res.session_id, revision: res.session_revision });
          if (view.state === "complete") {
            dispatch({ type: "announce", message: "Portfolio generation complete. Verified Preview ready." });
          } else if (view.state === "attention") {
            dispatch({ type: "announce", message: "Generation needs attention." });
          }
        } catch {
          dispatch({ type: "connection/set", state: "stale" });
        }
      });
    } else {
      poller.unsubscribe("code_generator");
    }

    return () => {
      poller.unsubscribe("discovery");
      poller.unsubscribe("content_architect");
      poller.unsubscribe("visual_design_director");
      poller.unsubscribe("build_preparation");
      poller.unsubscribe("code_generator");
    };
  }, [
    state.sessionId,
    state.discovery?.state,
    state.content?.state,
    state.design?.state,
    state.preparation?.state,
    state.generation?.state,
    state.readOnly,
    api,
  ]);

  // Compute 6-stage journey status
  const journey = useMemo<JourneyStageVM[]>(() => {
    const discoveryState = state.discovery?.state ?? "available";
    const isDiscoveryApproved = state.discovery?.state === "complete";
    const contentState = state.content?.state ?? (isDiscoveryApproved ? "available" : "locked");
    const isContentApproved = state.content?.state === "complete";
    const designState = state.design?.state ?? (isContentApproved ? "available" : "locked");
    const isDesignApproved = state.design?.state === "complete";
    const isPrepComplete = state.preparation?.state === "complete";
    const prepState = state.preparation?.state ?? (isDesignApproved ? "available" : "locked");
    const genState = state.generation?.state ?? (isPrepComplete ? "available" : "locked");
    const hasPreview = Boolean(state.generation?.hasUsablePreview);

    return [
      {
        id: "discover",
        ordinal: 1,
        label: "Discover",
        state: state.sessionId ? discoveryState : "available",
        isSelectable: Boolean(state.sessionId),
      },
      {
        id: "content",
        ordinal: 2,
        label: "Content",
        state: contentState,
        isSelectable: contentState !== "locked",
      },
      {
        id: "design",
        ordinal: 3,
        label: "Design",
        state: designState,
        isSelectable: designState !== "locked",
      },
      {
        id: "prepare",
        ordinal: 4,
        label: "Prepare",
        state: prepState,
        isSelectable: prepState !== "locked",
      },
      {
        id: "generate",
        ordinal: 5,
        label: "Generate",
        state: genState,
        isSelectable: genState !== "locked",
      },
      {
        id: "preview",
        ordinal: 6,
        label: "Preview",
        state: hasPreview ? "complete" : "locked",
        isSelectable: hasPreview,
      },
    ];
  }, [state.sessionId, state.discovery, state.content, state.design, state.preparation, state.generation]);

  // Navigate to stage and synchronize address bar
  const handleSelectStage = (stage: JourneyStageId) => {
    setActiveStage(stage);
    dispatch({ type: "stage/select", stage });
    const query = serializeAppUrlState({
      stage,
      view: stage === "discover" ? "work" : stage === "preview" ? "preview" : "artifact",
    });
    window.history.pushState({}, "", `${window.location.pathname}${query}`);
  };

  // ── Mutation Actions ─────────────────────────────────────────────────────────

  const notifyMutation = (sessionId: string) => {
    invalidationChannelRef.current?.broadcast(sessionId);
  };

  // Start initial portfolio
  const handleStartPortfolio = async (intakeText: string) => {
    let session = state.sessionId ? { id: state.sessionId } : null;
    if (!session) {
      const created = await api.createSession("Portfolio Studio");
      session = { id: created.id };
      dispatch({ type: "session/set", sessionId: created.id, revision: created.revision });
    }

    const res = await api.startDiscovery(session.id, {
      message: intakeText,
      goal: "create my portfolio",
    });
    const view = adaptDiscovery(res.discovery);
    dispatch({ type: "discovery/set", view });
    dispatch({ type: "announce", message: "Discovery started." });
    notifyMutation(session.id);
  };

  // Submit Discovery answer
  const handleSubmitDiscoveryAnswer = async (
    questionId: string,
    mode: string,
    value: unknown,
    isComplete: boolean,
  ) => {
    if (!state.sessionId) return;
    const currentQ = state.discovery?.currentQuestions.find((q) => q.id === questionId);
    if (currentQ) {
      const answerLabel =
        Array.isArray(value)
          ? value.join(", ")
          : typeof value === "string"
            ? value
            : JSON.stringify(value);

      setDiscoveryHistory((prev) => [
        ...prev,
        { questionId, questionText: currentQ.text, answerText: answerLabel },
      ]);
    }

    const res = await api.putDiscoveryAnswers(state.sessionId, {
      complete: isComplete,
      answers: [{ question_id: questionId, mode, value }],
    });
    const view = adaptDiscovery(res.discovery);
    dispatch({ type: "discovery/set", view });
    dispatch({ type: "session/set", sessionId: res.session_id, revision: res.session_revision });
    notifyMutation(state.sessionId);
  };

  // Generate brief now
  const handleGenerateBriefNow = async () => {
    if (!state.sessionId) return;
    const res = await api.putDiscoveryAnswers(state.sessionId, {
      complete: true,
      answers: [],
    });
    const view = adaptDiscovery(res.discovery);
    dispatch({ type: "discovery/set", view });
    notifyMutation(state.sessionId);
  };

  // Revise Brief
  const handleReviseBrief = async (revisionRequest: string) => {
    if (!state.sessionId) return;
    const res = await api.reviseDiscovery(state.sessionId, revisionRequest);
    const view = adaptDiscovery(res.discovery);
    dispatch({ type: "discovery/set", view });
    dispatch({ type: "announce", message: "Brief revision requested." });
    notifyMutation(state.sessionId);
  };

  // Approve Brief
  const handleApproveBrief = async () => {
    if (!state.sessionId) return;
    const res = await api.approveDiscovery(state.sessionId);
    const view = adaptDiscovery(res.discovery);
    dispatch({ type: "discovery/set", view });
    dispatch({ type: "announce", message: "Portfolio brief approved." });
    notifyMutation(state.sessionId);
    refetchCurrentSession();
  };

  // Start Content Architect
  const handleStartContent = async () => {
    if (!state.sessionId) return;
    const res = await api.startContentArchitect(state.sessionId, { preferences: {} });
    const view = adaptContentArchitect(res.content_architect, true);
    dispatch({ type: "content/set", view });
    dispatch({ type: "announce", message: "Content Architect started." });
    notifyMutation(state.sessionId);
  };

  // Revise Content
  const handleReviseContent = async (revisionRequest: string) => {
    if (!state.sessionId) return;
    const res = await api.reviseContentArchitect(state.sessionId, revisionRequest);
    const view = adaptContentArchitect(res.content_architect, true);
    dispatch({ type: "content/set", view });
    dispatch({ type: "announce", message: "Content revision requested." });
    notifyMutation(state.sessionId);
  };

  // Approve Content
  const handleApproveContent = async () => {
    if (!state.sessionId) return;
    const res = await api.approveContentArchitect(state.sessionId);
    const view = adaptContentArchitect(res.content_architect, true);
    dispatch({ type: "content/set", view });
    dispatch({ type: "announce", message: "Content plan approved." });
    notifyMutation(state.sessionId);
    refetchCurrentSession();
  };

  // Start Visual Design Director
  const handleStartDesign = async () => {
    if (!state.sessionId) return;
    const res = await api.startVisualDesignDirector(state.sessionId, { preferences: {} });
    const view = adaptVisualDesignDirector(res.visual_design_director, true);
    dispatch({ type: "design/set", view });
    dispatch({ type: "announce", message: "Visual Design Director started." });
    notifyMutation(state.sessionId);
  };

  // Revise Design
  const handleReviseDesign = async (revisionRequest: string) => {
    if (!state.sessionId) return;
    const res = await api.reviseVisualDesignDirector(state.sessionId, revisionRequest);
    const view = adaptVisualDesignDirector(res.visual_design_director, true);
    dispatch({ type: "design/set", view });
    dispatch({ type: "announce", message: "Visual direction revision requested." });
    notifyMutation(state.sessionId);
  };

  // Approve Design
  const handleApproveDesign = async () => {
    if (!state.sessionId) return;
    const res = await api.approveVisualDesignDirector(state.sessionId);
    const view = adaptVisualDesignDirector(res.visual_design_director, true);
    dispatch({ type: "design/set", view });
    dispatch({ type: "announce", message: "Visual direction approved." });
    notifyMutation(state.sessionId);
    refetchCurrentSession();
  };

  // Start Build Preparation
  const handleStartPreparation = async () => {
    if (!state.sessionId) return;
    const res = await api.startBuildPreparation(state.sessionId);
    const view = adaptBuildPreparation(res.build_preparation, true);
    dispatch({ type: "preparation/set", view });
    dispatch({ type: "announce", message: "Build preparation started." });
    notifyMutation(state.sessionId);
  };

  // Regenerate Build Preparation
  const handleRegeneratePreparation = async () => {
    if (!state.sessionId) return;
    const res = await api.regenerateBuildPreparation(state.sessionId);
    const view = adaptBuildPreparation(res.build_preparation, true);
    dispatch({ type: "preparation/set", view });
    dispatch({ type: "announce", message: "Build preparation restarted." });
    notifyMutation(state.sessionId);
  };

  // Start Code Generator
  const handleStartGeneration = async () => {
    if (!state.sessionId) return;
    const key = getOrCreateIdempotencyKey(state.sessionId, "start");
    try {
      const res = await api.startCodeGenerator(state.sessionId, key);
      clearIdempotencyKey(state.sessionId, "start");
      const view = adaptCodeGenerator(res.code_generator, true, state.readOnly);
      dispatch({ type: "generation/set", view });
      dispatch({ type: "announce", message: "Portfolio generation started." });
      notifyMutation(state.sessionId);
    } catch (err) {
      refetchCurrentSession();
      throw err;
    }
  };

  // Retry Code Generator
  const handleRetryGeneration = async () => {
    if (!state.sessionId) return;
    const key = getOrCreateIdempotencyKey(state.sessionId, "retry");
    try {
      const res = await api.retryCodeGenerator(state.sessionId, key);
      clearIdempotencyKey(state.sessionId, "retry");
      const view = adaptCodeGenerator(res.code_generator, true, state.readOnly);
      dispatch({ type: "generation/set", view });
      dispatch({ type: "announce", message: "Generation retry started." });
      notifyMutation(state.sessionId);
    } catch (err) {
      refetchCurrentSession();
      throw err;
    }
  };

  return (
    <AppStoreContext.Provider value={{ state, dispatch }}>
      <div className="app-shell">
        <header className="app-topbar">
          <div className="app-brand">
            <LivingDraftMark active={state.connection === "checking"} />
            <span>OryxenAI</span>
          </div>
          <div className="app-account-menu">
            <span>{me.username ?? "there"}</span>
            {state.readOnly && <span className="read-only-tag">Read-only</span>}
            {me.role === "admin" ? <a href="/admin">Admin</a> : null}
          </div>
        </header>

        <ConnectionBanner state={state.connection} />

        <main className="app-work-surface">
          {/* Journey Rail is visible once a portfolio exists */}
          {state.sessionId ? (
            <JourneyRail
              journey={journey}
              selectedStageId={activeStage}
              onSelect={handleSelectStage}
            />
          ) : null}

          {/* First-time visitor without a session */}
          {!state.sessionId ? (
            <StartSurface onStart={handleStartPortfolio} disabled={state.readOnly} />
          ) : null}

          {/* Active Stage Render */}
          {state.sessionId && activeStage === "discover" ? (
            <DiscoveryStage
              view={state.discovery}
              history={discoveryHistory}
              canMutate={!state.readOnly}
              onStartDiscovery={handleStartPortfolio}
              onSubmitAnswer={handleSubmitDiscoveryAnswer}
              onGenerateBriefNow={handleGenerateBriefNow}
              onApproveBrief={handleApproveBrief}
              onReviseBrief={handleReviseBrief}
              onContinueToContent={() => handleSelectStage("content")}
            />
          ) : null}

          {state.sessionId && activeStage === "content" ? (
            <ContentStage
              view={state.content}
              canMutate={!state.readOnly}
              onStart={handleStartContent}
              onApprove={handleApproveContent}
              onRevise={handleReviseContent}
              onContinueToDesign={() => handleSelectStage("design")}
            />
          ) : null}

          {state.sessionId && activeStage === "design" ? (
            <DesignStage
              view={state.design}
              canMutate={!state.readOnly}
              onStart={handleStartDesign}
              onApprove={handleApproveDesign}
              onRevise={handleReviseDesign}
              onContinueToPrepare={() => handleSelectStage("prepare")}
            />
          ) : null}

          {state.sessionId && activeStage === "prepare" ? (
            <PreparationStage
              view={state.preparation}
              canMutate={!state.readOnly}
              onStart={handleStartPreparation}
              onRegenerate={handleRegeneratePreparation}
              onContinueToGeneration={() => handleSelectStage("generate")}
            />
          ) : null}

          {state.sessionId && activeStage === "generate" ? (
            <GenerationStage
              view={state.generation}
              canMutate={!state.readOnly}
              readOnly={state.readOnly}
              onStart={handleStartGeneration}
              onRetry={handleRetryGeneration}
              onOpenPreview={() => handleSelectStage("preview")}
            />
          ) : null}

          {state.sessionId && activeStage === "preview" ? (
            <div className="preview-stage-container">
              <ConnectedPreviewSurface
                view={state.preview ?? adaptPreview(state.generation)}
                readOnly={state.readOnly}
                onNavigateStage={handleSelectStage}
                initialViewport={initialUrl.viewport ?? undefined}
                initialRoute={initialUrl.route ?? undefined}
                onRouteSelected={(route) => {
                  const query = serializeAppUrlState({ stage: "preview", view: "preview", route });
                  window.history.replaceState({}, "", `${window.location.pathname}${query}`);
                }}
                onViewportChanged={(viewport) => {
                  const query = serializeAppUrlState({ stage: "preview", view: "preview", viewport });
                  window.history.replaceState({}, "", `${window.location.pathname}${query}`);
                }}
              />
            </div>
          ) : null}
        </main>

        <StatusAnnouncer message={state.announcement} />
      </div>
    </AppStoreContext.Provider>
  );
}
