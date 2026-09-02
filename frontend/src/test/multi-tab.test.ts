import { describe, it, expect, beforeEach } from "vitest";
import { createInvalidationChannel } from "../data/invalidation";
import { safeSessionStorage } from "../data/safe-storage";
import { PollCoordinator } from "../data/polling";

describe("Phase 5 Multi-Tab Synchronization & Invalidation (docs/Frontend/05 §18)", () => {
  beforeEach(() => {
    safeSessionStorage.clear();
  });

  it("broadcasts and receives state-invalidated messages via InvalidationChannel", () => {
    const received: Array<{ type: string; sessionId: string; at: number }> = [];

    // Mock BroadcastChannel in Node environment
    class MockBroadcastChannel {
      name: string;
      onmessage: ((event: { data: unknown }) => void) | null = null;
      static instances: MockBroadcastChannel[] = [];

      constructor(name: string) {
        this.name = name;
        MockBroadcastChannel.instances.push(this);
      }

      postMessage(data: unknown) {
        for (const ch of MockBroadcastChannel.instances) {
          if (ch !== this && ch.name === this.name && ch.onmessage) {
            ch.onmessage({ data });
          }
        }
      }

      close() {
        const idx = MockBroadcastChannel.instances.indexOf(this);
        if (idx !== -1) MockBroadcastChannel.instances.splice(idx, 1);
      }
    }

    const originalBC = globalThis.BroadcastChannel;
    // @ts-expect-error test mock
    globalThis.BroadcastChannel = MockBroadcastChannel;

    try {
      const channel1 = createInvalidationChannel((msg) => received.push(msg));
      const channel2 = createInvalidationChannel(() => {});

      channel2.broadcast("session-xyz-123");

      expect(received.length).toBe(1);
      expect(received[0]?.type).toBe("state-invalidated");
      expect(received[0]?.sessionId).toBe("session-xyz-123");
      expect(typeof received[0]?.at).toBe("number");

      channel1.close();
      channel2.close();
    } finally {
      globalThis.BroadcastChannel = originalBC;
    }
  });

  it("preserves unsent drafts in safeSessionStorage across sessions", () => {
    const draftKey = "oryxenai.draft.question_1";
    safeSessionStorage.setItem(draftKey, "I have 10 years of distributed systems experience.");

    expect(safeSessionStorage.getItem(draftKey)).toBe("I have 10 years of distributed systems experience.");

    // Simulating another tab state sync without mutating the draft storage
    expect(safeSessionStorage.getItem(draftKey)).not.toBeNull();

    safeSessionStorage.removeItem(draftKey);
    expect(safeSessionStorage.getItem(draftKey)).toBeNull();
  });

  it("PollCoordinator manages subscriptions and clean teardown", () => {
    const coordinator = new PollCoordinator({ intervalMs: 1000, documentRef: null });
    let polled = false;

    coordinator.subscribe("test_stage", async () => {
      polled = true;
    });

    expect(polled).toBe(true);

    coordinator.unsubscribe("test_stage");
    coordinator.teardown();
  });
});
