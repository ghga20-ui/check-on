import { describe, expect, it } from "vitest";
import vector from "../../../tests/fixtures/e2e_crypto_vector.json";
import {
  decryptEnvelope,
  encryptEnvelope,
  importSyncKey,
  isEnvelope,
  parsePairingPayload,
  PAIRING_PREFIX,
} from "./crypto";

const b64decode = (text: string) => Uint8Array.from(atob(text), (c) => c.charCodeAt(0));

describe("crypto envelope (cross-language contract)", () => {
  it("encrypts to the exact Python-generated vector", async () => {
    const key = await importSyncKey(b64decode(vector.keyB64));
    const envelope = await encryptEnvelope(
      vector.aad,
      JSON.parse(vector.plaintextJson),
      key,
      b64decode(vector.nonceB64),
    );
    expect(envelope.checkonEnc).toBe(1);
    expect(envelope.alg).toBe("A256GCM");
    expect(envelope.nonce).toBe(vector.nonceB64);
    expect(envelope.ct).toBe(vector.ciphertextB64);
  });

  it("decrypts the Python-generated vector", async () => {
    const key = await importSyncKey(b64decode(vector.keyB64));
    const data = await decryptEnvelope(
      vector.aad,
      { checkonEnc: 1, alg: "A256GCM", nonce: vector.nonceB64, ct: vector.ciphertextB64 },
      key,
    );
    expect(data).toEqual(JSON.parse(vector.plaintextJson));
  });

  it("round-trips with a random nonce", async () => {
    const key = await importSyncKey(b64decode(vector.keyB64));
    const envelope = await encryptEnvelope("settings.json", { a: 1 }, key);
    expect(isEnvelope(envelope)).toBe(true);
    expect(await decryptEnvelope("settings.json", envelope, key)).toEqual({ a: 1 });
  });

  it("rejects a wrong file name (AAD mismatch)", async () => {
    const key = await importSyncKey(b64decode(vector.keyB64));
    const envelope = await encryptEnvelope("settings.json", { a: 1 }, key);
    await expect(decryptEnvelope("timetable.json", envelope, key)).rejects.toThrow();
  });

  it("isEnvelope rejects plain documents", () => {
    expect(isEnvelope({ schemaVersion: 1 })).toBe(false);
    expect(isEnvelope(null)).toBe(false);
    expect(isEnvelope([])).toBe(false);
  });
});

describe("parsePairingPayload", () => {
  it("decodes the desktop payload back to the key bytes", () => {
    const keyBytes = b64decode(vector.keyB64);
    const b64url = vector.keyB64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    expect(parsePairingPayload(`${PAIRING_PREFIX}${b64url}`)).toEqual(keyBytes);
  });

  it("tolerates surrounding whitespace", () => {
    const b64url = vector.keyB64.replace(/=+$/, "");
    expect(parsePairingPayload(`  ${PAIRING_PREFIX}${b64url}\n`)).toHaveLength(32);
  });

  it("rejects wrong prefix and wrong key length", () => {
    expect(() => parsePairingPayload("nope:abc")).toThrow();
    expect(() => parsePairingPayload(`${PAIRING_PREFIX}QUJD`)).toThrow();
  });
});
