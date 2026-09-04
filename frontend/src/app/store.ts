// Small reducer + context store (docs/Frontend/05 §7 "App store" — no
// signals/state-management package). Server state (identity, session,
// approved artifacts, job state, revisions) is the authority; this store
// only holds normalized projections of what the server already said.
import { createContext } from "preact";
import { useContext } from "preact/hooks";
import type { MeProjection } from "../data/api-client";
import type { DiscoveryViewModel } from "../data/adapters/discovery";
import type { ContentViewModel } from "../data/adapters/content";
import type { DesignViewModel } from "../data/adapters/design";
import type { JourneyStageId } from "./url-state";

export type ConnectionState = "confirmed" | "checking" | "stale" | "offline";

export interface AppState {
  me: MeProjection | null;
  sessionId: string | null;
  sessionRevision: number | null;
  readOnly: boolean;
  activeStage: JourneyStageId;
  discovery: DiscoveryViewModel | null;
  content: ContentViewModel | null;
  design: DesignViewModel | null;
  connection: ConnectionState;
  announcement: string | null;
}

export type AppAction =
  | { type: "me/set"; me: MeProjection }
  | { type: "session/set"; sessionId: string; revision: number }
  | { type: "stage/select"; stage: JourneyStageId }
  | { type: "discovery/set"; view: DiscoveryViewModel }
  | { type: "content/set"; view: ContentViewModel }
  | { type: "design/set"; view: DesignViewModel }
  | { type: "connection/set"; state: ConnectionState }
  | { type: "announce"; message: string };

export const initialAppState: AppState = {
  me: null,
  sessionId: null,
  sessionRevision: null,
  readOnly: false,
  activeStage: "discover",
  discovery: null,
  content: null,
  design: null,
  connection: "checking",
  announcement: null,
};

export function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "me/set":
      return { ...state, me: action.me, readOnly: Boolean(action.me.read_only) };
    case "session/set":
      return { ...state, sessionId: action.sessionId, sessionRevision: action.revision };
    case "stage/select":
      return { ...state, activeStage: action.stage };
    case "discovery/set":
      return { ...state, discovery: action.view };
    case "content/set":
      return { ...state, content: action.view };
    case "design/set":
      return { ...state, design: action.view };
    case "connection/set":
      return { ...state, connection: action.state };
    case "announce":
      return { ...state, announcement: action.message };
    default:
      return state;
  }
}

export interface AppStoreContextValue {
  state: AppState;
  dispatch: (action: AppAction) => void;
}

export const AppStoreContext = createContext<AppStoreContextValue | null>(null);

export function useAppStore(): AppStoreContextValue {
  const ctx = useContext(AppStoreContext);
  if (!ctx) throw new Error("useAppStore must be used within AppStoreContext.Provider");
  return ctx;
}
