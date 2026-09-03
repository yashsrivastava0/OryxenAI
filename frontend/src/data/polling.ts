// Visibility-aware poll coordinator. One in-flight request per resource key,
// backoff on failure, cancel scheduled polls when hidden (but never abort a
// response already committing), refetch immediately on return-to-visible.
// See docs/Frontend/05-implementation-blueprint-and-acceptance-matrix.md
// §11.1. Dependencies are injected (documentRef/setTimeoutFn/clearTimeoutFn)
// so this is testable in plain Node, matching the pattern already used by
// src/oryxenai/auth/static/auth-runtime.mjs.

const DEFAULT_INTERVAL_MS = 1500;
const BACKOFF_STEPS_MS = [1500, 3000, 6000, 12000];
const MAX_BACKOFF_MS = 15000;

export type PollFetcher = () => Promise<void>;

interface Subscription {
  fetcher: PollFetcher;
  failureCount: number;
  timer: ReturnType<typeof setTimeout> | null;
  inFlight: boolean;
}

export interface PollCoordinatorOptions {
  intervalMs?: number;
  documentRef?: { visibilityState?: string; addEventListener?: Function; removeEventListener?: Function } | null;
  setTimeoutFn?: typeof setTimeout;
  clearTimeoutFn?: typeof clearTimeout;
}

export class PollCoordinator {
  private readonly intervalMs: number;
  private readonly documentRef: PollCoordinatorOptions["documentRef"];
  private readonly setTimeoutFn: typeof setTimeout;
  private readonly clearTimeoutFn: typeof clearTimeout;
  private readonly subscriptions = new Map<string, Subscription>();
  private readonly visibilityListener = () => this.handleVisibilityChange();

  constructor(options: PollCoordinatorOptions = {}) {
    this.intervalMs = options.intervalMs ?? DEFAULT_INTERVAL_MS;
    this.documentRef = options.documentRef ?? (typeof document !== "undefined" ? document : null);
    const rawSetTimeout = options.setTimeoutFn ?? setTimeout;
    const rawClearTimeout = options.clearTimeoutFn ?? clearTimeout;
    this.setTimeoutFn = ((fn: any, ms?: any, ...args: any[]) => rawSetTimeout(fn, ms, ...args)) as typeof setTimeout;
    this.clearTimeoutFn = ((id?: any) => rawClearTimeout(id)) as typeof clearTimeout;
    this.documentRef?.addEventListener?.("visibilitychange", this.visibilityListener);
  }

  private isVisible(): boolean {
    return this.documentRef?.visibilityState !== "hidden";
  }

  private handleVisibilityChange(): void {
    if (this.isVisible()) {
      // Refetch immediately on return to visibility, then resume the normal
      // cadence from a fresh success.
      for (const [key, sub] of this.subscriptions) {
        if (sub.timer) {
          this.clearTimeoutFn(sub.timer);
          sub.timer = null;
        }
        void this.runOnce(key, sub);
      }
    } else {
      for (const sub of this.subscriptions.values()) {
        if (sub.timer) {
          this.clearTimeoutFn(sub.timer);
          sub.timer = null;
        }
      }
    }
  }

  private scheduleNext(key: string, sub: Subscription, delayMs: number): void {
    if (!this.subscriptions.has(key)) return;
    if (sub.timer) this.clearTimeoutFn(sub.timer);
    sub.timer = this.setTimeoutFn(() => {
      void this.runOnce(key, sub);
    }, delayMs);
  }

  private async runOnce(key: string, sub: Subscription): Promise<void> {
    if (sub.inFlight || !this.subscriptions.has(key)) return;
    if (!this.isVisible()) return;
    sub.inFlight = true;
    try {
      await sub.fetcher();
      sub.failureCount = 0;
      this.scheduleNext(key, sub, this.intervalMs);
    } catch {
      const step = Math.min(sub.failureCount, BACKOFF_STEPS_MS.length - 1);
      const delay = Math.min(BACKOFF_STEPS_MS[step] ?? MAX_BACKOFF_MS, MAX_BACKOFF_MS);
      sub.failureCount += 1;
      this.scheduleNext(key, sub, delay);
    } finally {
      sub.inFlight = false;
    }
  }

  /** Subscribe a resource key to the poll cadence and fetch it immediately. */
  subscribe(key: string, fetcher: PollFetcher): void {
    this.unsubscribe(key);
    const sub: Subscription = { fetcher, failureCount: 0, timer: null, inFlight: false };
    this.subscriptions.set(key, sub);
    void this.runOnce(key, sub);
  }

  unsubscribe(key: string): void {
    const sub = this.subscriptions.get(key);
    if (!sub) return;
    if (sub.timer) this.clearTimeoutFn(sub.timer);
    this.subscriptions.delete(key);
  }

  stopAll(): void {
    for (const key of [...this.subscriptions.keys()]) this.unsubscribe(key);
  }

  teardown(): void {
    this.stopAll();
    this.documentRef?.removeEventListener?.("visibilitychange", this.visibilityListener);
  }
}
