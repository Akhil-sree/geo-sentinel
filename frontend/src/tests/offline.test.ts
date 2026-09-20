import { describe, expect, it } from "vitest";
import { enqueueReport, flushQueue, queueSize, describeSync } from "../lib/offline";

describe("offline queue", () => {
  it("keeps failed reports for retry and counts synced", async () => {
    const rep = { id: "t1", payload: {}, queuedAt: new Date().toISOString(), attempts: 0 };
    await enqueueReport(rep); await enqueueReport({ ...rep, id: "t2" });
    expect(await queueSize()).toBe(2);
    let n = 0;
    const synced = await flushQueue(async (r) => {
      if (r.id === "t1") throw new Error("network down");
      n++;
    });
    expect(synced).toBe(1);
    expect(await queueSize()).toBe(1);   // failed one stays, attempts incremented
  });

  it("reports OFFLINE / SYNCING / SYNCED / FAILED sync states", () => {
    expect(describeSync(false, 2, false)).toBe("OFFLINE");
    expect(describeSync(true, 2, false)).toBe("SYNCING");
    expect(describeSync(true, 2, true)).toBe("FAILED");
    expect(describeSync(true, 0, false)).toBe("SYNCED");
  });
});
