import "fake-indexeddb/auto";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { encryptEnvelope, importSyncKey, isEnvelope } from "./crypto";
import { clearSyncKey, saveSyncKey } from "./keyStore";
import { PairingRequiredError, readJson, resetSyncKeyCache, writeJson } from "./drive";

vi.mock("./auth", () => ({ getValidAccessToken: () => Promise.resolve("tok") }));

const KEY_BYTES = new Uint8Array(Array.from({ length: 32 }, (_, i) => i));

function mockFetchSequence(responses: Array<{ json: unknown }>) {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  let i = 0;
  vi.stubGlobal("fetch", (url: string, init?: RequestInit) => {
    calls.push({ url, init });
    const body = JSON.stringify(responses[Math.min(i++, responses.length - 1)].json);
    return Promise.resolve(new Response(body, { status: 200 }));
  });
  return calls;
}

describe("drive gateway encryption", () => {
  beforeEach(async () => {
    await clearSyncKey();
    resetSyncKeyCache();
  });
  afterEach(() => vi.unstubAllGlobals());

  it("readJson transparently decrypts an envelope when the key exists", async () => {
    await saveSyncKey(KEY_BYTES);
    resetSyncKeyCache();
    const envelope = await encryptEnvelope(
      "settings.json",
      { schemaVersion: 1 },
      await importSyncKey(KEY_BYTES),
    );
    mockFetchSequence([{ json: { files: [{ id: "f1" }] } }, { json: envelope }]);
    const file = await readJson("settings.json");
    expect(file?.data).toEqual({ schemaVersion: 1 });
  });

  it("readJson throws PairingRequiredError on envelope without key", async () => {
    const envelope = await encryptEnvelope(
      "settings.json",
      { schemaVersion: 1 },
      await importSyncKey(KEY_BYTES),
    );
    mockFetchSequence([{ json: { files: [{ id: "f1" }] } }, { json: envelope }]);
    await expect(readJson("settings.json")).rejects.toBeInstanceOf(PairingRequiredError);
  });

  it("readJson passes legacy plaintext through", async () => {
    mockFetchSequence([{ json: { files: [{ id: "f1" }] } }, { json: { schemaVersion: 1 } }]);
    const file = await readJson("settings.json");
    expect(file?.data).toEqual({ schemaVersion: 1 });
  });

  it("writeJson uploads an envelope when the key exists", async () => {
    await saveSyncKey(KEY_BYTES);
    resetSyncKeyCache();
    const calls = mockFetchSequence([{ json: { id: "f1" } }]);
    await writeJson("settings.json", { schemaVersion: 1 }, "f1");
    const uploaded = JSON.parse(calls[0].init?.body as string);
    expect(isEnvelope(uploaded)).toBe(true);
  });

  it("writeJson uploads plaintext without a key", async () => {
    const calls = mockFetchSequence([{ json: { id: "f1" } }]);
    await writeJson("settings.json", { schemaVersion: 1 }, "f1");
    expect(JSON.parse(calls[0].init?.body as string)).toEqual({ schemaVersion: 1 });
  });
});
