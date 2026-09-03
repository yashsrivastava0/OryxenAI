import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PollCoordinator } from "./polling";

describe("PollCoordinator", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("fetches immediately on subscribe, then again after the interval", async () => {
    const coordinator = new PollCoordinator({ intervalMs: 1000, documentRef: null });
    let calls = 0;
    coordinator.subscribe("resource", async () => {
      calls += 1;
    });
    await vi.advanceTimersByTimeAsync(0);
    expect(calls).toBe(1);
    await vi.advanceTimersByTimeAsync(1000);
    expect(calls).toBe(2);
    coordinator.teardown();
  });

  it("never runs a second fetch for the same key while one is in flight", async () => {
    const coordinator = new PollCoordinator({ intervalMs: 1000, documentRef: null });
    let concurrent = 0;
    let maxConcurrent = 0;
    coordinator.subscribe("resource", async () => {
      concurrent += 1;
      maxConcurrent = Math.max(maxConcurrent, concurrent);
      await new Promise((resolve) => setTimeout(resolve, 5000));
      concurrent -= 1;
    });
    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(1000);
    await vi.advanceTimersByTimeAsync(1000);
    expect(maxConcurrent).toBe(1);
    coordinator.teardown();
  });

  it("backs off after a failure and resets cadence on the next success", async () => {
    const coordinator = new PollCoordinator({ intervalMs: 1000, documentRef: null });
    let attempt = 0;
    const timestamps: number[] = [];
    coordinator.subscribe("resource", async () => {
      timestamps.push(Date.now());
      attempt += 1;
      if (attempt <= 2) throw new Error("fail");
    });
    await vi.advanceTimersByTimeAsync(0); // attempt 1, fails
    await vi.advanceTimersByTimeAsync(1500); // backoff step 1 -> attempt 2, fails
    await vi.advanceTimersByTimeAsync(3000); // backoff step 2 -> attempt 3, succeeds
    await vi.advanceTimersByTimeAsync(1000); // back to normal cadence -> attempt 4
    expect(attempt).toBe(4);
    coordinator.teardown();
  });

  it("stops scheduling while hidden and does not fetch until visible again", async () => {
    let visibilityState = "visible";
    const listeners: Array<() => void> = [];
    const documentRef = {
      get visibilityState() {
        return visibilityState;
      },
      addEventListener: (_event: string, listener: () => void) => listeners.push(listener),
      removeEventListener: () => {},
    };
    const coordinator = new PollCoordinator({ intervalMs: 1000, documentRef });
    let calls = 0;
    coordinator.subscribe("resource", async () => {
      calls += 1;
    });
    await vi.advanceTimersByTimeAsync(0);
    expect(calls).toBe(1);

    visibilityState = "hidden";
    listeners.forEach((fn) => fn());
    await vi.advanceTimersByTimeAsync(5000);
    expect(calls).toBe(1); // no scheduled poll fires while hidden

    visibilityState = "visible";
    listeners.forEach((fn) => fn());
    await vi.advanceTimersByTimeAsync(0);
    expect(calls).toBe(2); // immediate refetch on return to visible
    coordinator.teardown();
  });

  it("unsubscribe stops further polling for that key", async () => {
    const coordinator = new PollCoordinator({ intervalMs: 1000, documentRef: null });
    let calls = 0;
    coordinator.subscribe("resource", async () => {
      calls += 1;
    });
    await vi.advanceTimersByTimeAsync(0);
    coordinator.unsubscribe("resource");
    await vi.advanceTimersByTimeAsync(5000);
    expect(calls).toBe(1);
  });

  it("does not throw Illegal invocation when setTimeout requires specific this context", async () => {
    const strictWindow = {};
    function strictSetTimeout(this: any, fn: any, ms?: any) {
      if (this !== strictWindow && this !== undefined && this !== globalThis) {
        throw new TypeError("Illegal invocation");
      }
      return setTimeout(fn, ms);
    }
    const coordinator = new PollCoordinator({
      intervalMs: 1000,
      documentRef: null,
      setTimeoutFn: strictSetTimeout as any,
    });
    let calls = 0;
    expect(() => {
      coordinator.subscribe("resource", async () => {
        calls += 1;
      });
    }).not.toThrow();
    await vi.advanceTimersByTimeAsync(0);
    expect(calls).toBe(1);
    coordinator.teardown();
  });
});
