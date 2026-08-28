import { afterEach, describe, expect, it, vi } from "vitest";
import {
  clearOutbox,
  enqueue,
  flushOutbox,
  pendingCount,
  pendingEntries,
} from "./outbox";

afterEach(() => {
  clearOutbox();
  vi.restoreAllMocks();
});

describe("outbox", () => {
  it("persists entries and reports the pending count", () => {
    expect(pendingCount()).toBe(0);
    enqueue("sale.completed", { total_cents: 1000 });
    enqueue("op.b", { ok: true });
    expect(pendingCount()).toBe(2);
    expect(pendingEntries()[0].operation).toBe("sale.completed");
  });

  it("flushes entries in order and survives restarts", async () => {
    enqueue("sale.completed", { id: "a" });
    enqueue("sale.completed", { id: "b" });
    const sent: string[] = [];
    const flushed = await flushOutbox(async (entry) => {
      sent.push((entry.payload as { id: string }).id);
    });
    expect(flushed).toBe(2);
    expect(sent).toEqual(["a", "b"]);
    expect(pendingCount()).toBe(0);
  });

  it("stops at the first failure and keeps the remaining queue", async () => {
    enqueue("a", {});
    enqueue("b", {});
    let calls = 0;
    const flushed = await flushOutbox(async () => {
      calls += 1;
      if (calls === 1) throw new Error("offline");
    });
    expect(flushed).toBe(0);
    expect(pendingCount()).toBe(2);
  });

  it("retries successfully once the failure clears", async () => {
    enqueue("a", {});
    let fail = true;
    const send = vi.fn(async () => {
      if (fail) throw new Error("offline");
    });
    await flushOutbox(send);
    expect(pendingCount()).toBe(1);
    fail = false;
    const flushed = await flushOutbox(send);
    expect(flushed).toBe(1);
    expect(pendingCount()).toBe(0);
  });
});
