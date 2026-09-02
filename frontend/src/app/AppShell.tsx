import { useEffect, useMemo, useReducer, useRef, useState, useCallback } from "preact/hooks";
import { AppStoreContext, appReducer, initialAppState } from "./store";
import { createApiClient, type AuthorizedFetch, type MeProjection } from "../data/api-client";
import { adaptDiscovery } from "../data/adapters/discovery";
import { adaptContentArchitect } from "../data/adapters/content";
import { adaptVisualDesignDirector } from "../data/adapters/design";
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
import { PreviewFrameShell } from "../preview/PreviewFrameShell";
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

      dispatch({ type: "connection/set", state: "confirmed" });
    } catch {
      dispatch({ type: "connection/set", state: "stale" });
    }
  }, [api, state.sessionId]);

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

    return () => {
      poller.unsubscribe("discovery");
      poller.unsubscribe("content_architect");
      poller.unsubscribe("visual_design_director");
    };
  }, [state.sessionId, state.discovery?.state, state.content?.state, state.design?.state, api]);

  // Compute 6-stage journey status
  const journey = useMemo<JourneyStageVM[]>(() => {
    const discoveryState = state.discovery?.state ?? "available";
    const isDiscoveryApproved = state.discovery?.state === "complete";
    const contentState = state.content?.state ?? (isDiscoveryApproved ? "available" : "locked");
    const isContentApproved = state.content?.state === "complete";
    const designState = state.design?.state ?? (isContentApproved ? "available" : "locked");
    const isDesignApproved = state.design?.state === "complete";

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
        state: isDesignApproved ? "available" : "locked",
        isSelectable: isDesignApproved,
      },
      {
        id: "generate",
        ordinal: 5,
        label: "Generate",
        state: "locked",
        isSelectable: false,
      },
      {
        id: "preview",
        ordinal: 6,
        label: "Preview",
        state: "locked",
        isSelectable: false,
      },
    ];
  }, [state.sessionId, state.discovery, state.content, state.design]);

  // Navigate to stage and synchronize address bar
  const handleSelectStage = (stage: JourneyStageId) => {
    setActiveStage(stage);
    dispatch({ type: "stage/select", stage });
    const query = serializeAppUrlState({ stage, view: stage === "discover" ? "work" : "artifact" });
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
            <div className="phase-future-panel">
              <p className="eyebrow">Stage 04 / Build Preparation</p>
              <h2>Build Preparation Hand-off Ready</h2>
              <p className="stage-desc">
                Content Plan and Visual Direction are both approved. Build Preparation will assemble verified packages in Phase 3.
              </p>
            </div>
          ) : null}

          {state.sessionId && (activeStage === "generate" || activeStage === "preview") ? (
            <div className="phase-future-panel">
              <p className="eyebrow">Stage 05 & 06 / Generation & Preview</p>
              <h2>Verified Code Generation & Isolated Preview</h2>
              <p className="stage-desc">
                Generation and verified isolated preview frame arrive in Phases 3 and 4.
              </p>
              <PreviewFrameShell />
            </div>
          ) : null}
        </main>

        <StatusAnnouncer message={state.announcement} />
      </div>
    </AppStoreContext.Provider>
  );
}
