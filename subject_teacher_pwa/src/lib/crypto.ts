// AES-256-GCM envelope crypto shared with the desktop app
// (`subject_teacher/drive/crypto.py`). The contract is pinned by the
// cross-language vector in tests/fixtures/e2e_crypto_vector.json (repo root):
// AAD = file name, nonce 12 bytes, GCM tag appended to the ciphertext.

export const PAIRING_PREFIX = "checkon.sync.v1:";
const NONCE_SIZE = 12;
const KEY_SIZE = 32;

export interface Envelope {
  checkonEnc: 1;
  alg: "A256GCM";
  nonce: string;
  ct: string;
}

export function isEnvelope(raw: unknown): raw is Envelope {
  return (
    typeof raw === "object" &&
    raw !== null &&
    !Array.isArray(raw) &&
    (raw as { checkonEnc?: unknown }).checkonEnc === 1
  );
}

function b64encode(bytes: Uint8Array): string {
  let binary = "";
  bytes.forEach((b) => (binary += String.fromCharCode(b)));
  return btoa(binary);
}

function b64decode(text: string): Uint8Array {
  return Uint8Array.from(atob(text), (c) => c.charCodeAt(0));
}

export function importSyncKey(bytes: Uint8Array): Promise<CryptoKey> {
  return crypto.subtle.importKey("raw", bytes as BufferSource, "AES-GCM", false, [
    "encrypt",
    "decrypt",
  ]);
}

export async function encryptEnvelope(
  name: string,
  data: unknown,
  key: CryptoKey,
  nonceOverride?: Uint8Array,
): Promise<Envelope> {
  const nonce = nonceOverride ?? crypto.getRandomValues(new Uint8Array(NONCE_SIZE));
  const plaintext = new TextEncoder().encode(JSON.stringify(data));
  const ct = await crypto.subtle.encrypt(
    {
      name: "AES-GCM",
      iv: nonce as BufferSource,
      additionalData: new TextEncoder().encode(name),
    },
    key,
    plaintext,
  );
  return {
    checkonEnc: 1,
    alg: "A256GCM",
    nonce: b64encode(nonce),
    ct: b64encode(new Uint8Array(ct)),
  };
}

export async function decryptEnvelope(
  name: string,
  envelope: Envelope,
  key: CryptoKey,
): Promise<unknown> {
  if (envelope.alg !== "A256GCM") {
    throw new Error(`지원하지 않는 암호화 형식입니다: ${envelope.alg}`);
  }
  const plaintext = await crypto.subtle.decrypt(
    {
      name: "AES-GCM",
      iv: b64decode(envelope.nonce) as BufferSource,
      additionalData: new TextEncoder().encode(name),
    },
    key,
    b64decode(envelope.ct) as BufferSource,
  );
  return JSON.parse(new TextDecoder().decode(plaintext));
}

/** Parse `checkon.sync.v1:<base64url>` into the 32-byte key. Throws on malformed input. */
export function parsePairingPayload(text: string): Uint8Array {
  const trimmed = text.trim();
  if (!trimmed.startsWith(PAIRING_PREFIX)) {
    throw new Error("연결 코드 형식이 올바르지 않습니다.");
  }
  const b64 = trimmed.slice(PAIRING_PREFIX.length).replace(/-/g, "+").replace(/_/g, "/");
  const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
  let bytes: Uint8Array;
  try {
    bytes = b64decode(padded);
  } catch {
    throw new Error("연결 코드 형식이 올바르지 않습니다.");
  }
  if (bytes.length !== KEY_SIZE) {
    throw new Error("연결 코드 길이가 올바르지 않습니다.");
  }
  return bytes;
}
