import "fake-indexeddb/auto";
import { beforeEach, describe, expect, it } from "vitest";
import { clearSyncKey, loadSyncKey, saveSyncKey } from "./keyStore";
import { loadQueue, persistQueue } from "./db";

describe("keyStore", () => {
  beforeEach(async () => {
    await clearSyncKey();
  });

  it("returns null when no key is stored", async () => {
    expect(await loadSyncKey()).toBeNull();
  });

  it("round-trips 32 key bytes", async () => {
    const key = new Uint8Array(Array.from({ length: 32 }, (_, i) => i));
    await saveSyncKey(key);
    expect(await loadSyncKey()).toEqual(key);
  });

  it("clearSyncKey removes the key", async () => {
    await saveSyncKey(new Uint8Array(32));
    await clearSyncKey();
    expect(await loadSyncKey()).toBeNull();
  });

  it("coexists with the save queue store (v2 upgrade keeps both)", async () => {
    await persistQueue([{ id: "q1" } as never]);
    await saveSyncKey(new Uint8Array(32));
    expect((await loadQueue()).length).toBe(1);
    expect(await loadSyncKey()).not.toBeNull();
  });
});
