import { useEffect, useMemo, useReducer, useRef } from "preact/hooks";
import { AppStoreContext, appReducer, initialAppState } from "./store";
import { createApiClient, type AuthorizedFetch, type MeProjection } from "../data/api-client";
import { adaptDiscovery } from "../data/adapters/discovery";
import { PollCoordinator } from "../data/polling";
import { JourneyRail, type JourneyStageVM } from "../components/JourneyRail";
import { ConnectionBanner } from "../components/ConnectionBanner";
import { StatusAnnouncer } from "../components/StatusAnnouncer";
import { LivingDraftMark } from "../components/LivingDraftMark";
import { ArtifactSpecimen } from "../components/ArtifactSpecimen";
import { ProgressSpecimen } from "../components/ProgressSpecimen";
import { PreviewFrameShell } from "../preview/PreviewFrameShell";
import { serializeAppUrlState, type JourneyStageId } from "./url-state";

export interface AppShellProps {
  authorizedFetch: AuthorizedFetch;
  me: MeProjection;
  serverSessionId: string | null;
  readOnly: boolean;
}

/**
 * Phase 1 foundation shell (docs/Frontend/05 §19 Phase 1): real auth-resolved
 * chrome, journey rail, connection state, and — where a portfolio session
 * already exists — a real, polled Discovery status proving the full stack
 * (api-client -> adapter -> store -> component) end to end. The
 * conversational/artifact stage surfaces themselves are Phase 2 scope; below
 * the live status line this renders labeled visual specimens instead of
 * pretending Discovery is fully ported yet.
 */
export function AppShell({ authorizedFetch, me, serverSessionId, readOnly }: AppShellProps) {
  const [state, dispatch] = useReducer(appReducer, {
    ...initialAppState,
    me,
    readOnly,
    sessionId: serverSessionId,
  });
  const api = useMemo(() => createApiClient(authorizedFetch), [authorizedFetch]);
  const pollerRef = useRef<PollCoordinator | null>(null);

  useEffect(() => {
    const poller = new PollCoordinator();
    pollerRef.current = poller;
    return () => poller.teardown();
  }, []);

  useEffect(() => {
    if (!state.sessionId) {
      dispatch({ type: "connection/set", state: "confirmed" });
      return;
    }
    const poller = pollerRef.current;
    if (!poller) return;
    const sessionId = state.sessionId;
    poller.subscribe("discovery", async () => {
      dispatch({ type: "connection/set", state: "checking" });
      const response = await api.getDiscovery(sessionId);
      const view = adaptDiscovery(response.discovery);
      dispatch({ type: "discovery/set", view });
      dispatch({ type: "session/set", sessionId: response.session_id, revision: response.session_revision });
      dispatch({ type: "connection/set", state: "confirmed" });
    });
    return () => poller.unsubscribe("discovery");
  }, [state.sessionId, api]);

  const journey = useMemo<JourneyStageVM[]>(() => {
    const discoveryState = state.discovery?.state ?? "available";
    return [
      { id: "discover", ordinal: 1, label: "Discover", state: state.sessionId ? discoveryState : "available", isSelectable: true },
      { id: "content", ordinal: 2, label: "Content", state: "locked", isSelectable: false },
      { id: "design", ordinal: 3, label: "Design", state: "locked", isSelectable: false },
      { id: "prepare", ordinal: 4, label: "Prepare", state: "locked", isSelectable: false },
      { id: "generate", ordinal: 5, label: "Generate", state: "locked", isSelectable: false },
      { id: "preview", ordinal: 6, label: "Preview", state: "locked", isSelectable: false },
    ];
  }, [state.discovery, state.sessionId]);

  const handleSelectStage = (stage: JourneyStageId) => {
    const query = serializeAppUrlState({ stage });
    window.history.pushState({}, "", `${window.location.pathname}${query}`);
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
            {me.role === "admin" ? <a href="/admin">Admin</a> : null}
          </div>
        </header>
        <ConnectionBanner state={state.connection} />
        <main className="app-work-surface">
          <JourneyRail journey={journey} onSelect={handleSelectStage} />
          {state.sessionId && state.discovery ? (
            <p className="eyebrow">Live Discovery status: {state.discovery.statusText}</p>
          ) : (
            <p className="eyebrow">Starting a portfolio arrives with the Discovery conversation surface in Phase 2.</p>
          )}
          <ArtifactSpecimen />
          <ProgressSpecimen />
          <PreviewFrameShell />
        </main>
        <StatusAnnouncer message={state.announcement} />
      </div>
    </AppStoreContext.Provider>
  );
}
