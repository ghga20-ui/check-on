import "fake-indexeddb/auto";
import { beforeEach, describe, expect, it } from "vitest";
import { clearDriveCache, loadDriveCache, saveDriveCache } from "./localCache";
import type { LoadedDriveData } from "./driveData";

const SNAPSHOT: LoadedDriveData = {
  settings: null,
  timetable: { schemaVersion: 1, effectiveFrom: "2026-07-01", slots: [] },
  students: { schemaVersion: 1, classes: {} },
  attendance: { schemaVersion: 1, month: "2026-07", records: {} },
};

describe("localCache", () => {
  beforeEach(async () => {
    await clearDriveCache();
  });

  it("returns null when nothing is cached", async () => {
    expect(await loadDriveCache()).toBeNull();
  });

  it("round-trips a snapshot with its month and a timestamp", async () => {
    const before = Date.now();
    await saveDriveCache(SNAPSHOT, "2026-07");
    const cached = await loadDriveCache();

    expect(cached).not.toBeNull();
    expect(cached?.month).toBe("2026-07");
    expect(cached?.data).toEqual(SNAPSHOT);
    expect(cached?.savedAt).toBeGreaterThanOrEqual(before);
  });

  it("overwrites the previous snapshot rather than appending", async () => {
    await saveDriveCache(SNAPSHOT, "2026-06");
    await saveDriveCache(SNAPSHOT, "2026-07");
    expect((await loadDriveCache())?.month).toBe("2026-07");
  });

  it("clears the cached snapshot", async () => {
    await saveDriveCache(SNAPSHOT, "2026-07");
    await clearDriveCache();
    expect(await loadDriveCache()).toBeNull();
  });
});
