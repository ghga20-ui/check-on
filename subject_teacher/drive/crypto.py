"""End-to-end encryption for Drive-synced JSON (AES-256-GCM envelopes).

The envelope contract is shared with the PWA (`subject_teacher_pwa/src/lib/crypto.ts`);
`tests/fixtures/e2e_crypto_vector.json` pins cross-language interop. The sync key is
generated on the desktop, shown once as a pairing QR, and never leaves the devices.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from subject_teacher.auth.token_store import (
    TokenNotFoundError,
    delete_token,
    load_token,
    save_token,
)
from subject_teacher.paths import get_sync_key_path

logger = logging.getLogger(__name__)

PAIRING_PREFIX = "checkon.sync.v1:"
KEY_SIZE = 32
NONCE_SIZE = 12
ENVELOPE_ALG = "A256GCM"


class EnvelopeError(ValueError):
    """Envelope is malformed, tampered with, or bound to a different file name."""


class SyncKeyMissingError(RuntimeError):
    """An encrypted file was found but no sync key is stored on this device."""


class RecoveryCodeError(ValueError):
    """A recovery code is the wrong length, has bad characters, or fails its checksum."""


# Crockford Base32: uppercase, excludes I L O U to avoid transcription ambiguity.
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_CROCKFORD_INDEX = {c: i for i, c in enumerate(_CROCKFORD)}
# Human aliases so a hand-copied code still decodes.
_CROCKFORD_INDEX.update({"O": 0, "I": 1, "L": 1})
_RECOVERY_CHECKSUM_SIZE = 3  # bytes of SHA-256(key) appended for typo detection


def _crockford_encode(data: bytes) -> str:
    bits = 0
    nbits = 0
    out: list[str] = []
    for byte in data:
        bits = (bits << 8) | byte
        nbits += 8
        while nbits >= 5:
            nbits -= 5
            out.append(_CROCKFORD[(bits >> nbits) & 0x1F])
    if nbits:
        out.append(_CROCKFORD[(bits << (5 - nbits)) & 0x1F])
    return "".join(out)


def _crockford_decode(text: str) -> bytes:
    bits = 0
    nbits = 0
    out = bytearray()
    for ch in text:
        try:
            val = _CROCKFORD_INDEX[ch]
        except KeyError as exc:
            raise RecoveryCodeError("복구 코드에 사용할 수 없는 문자가 있습니다.") from exc
        bits = (bits << 5) | val
        nbits += 5
        if nbits >= 8:
            nbits -= 8
            out.append((bits >> nbits) & 0xFF)
    return bytes(out)


def recovery_code(key: bytes) -> str:
    """A transcription-friendly backup of the sync key: 14 hyphen-separated groups."""
    if len(key) != KEY_SIZE:
        raise ValueError("key must be 32 bytes")
    payload = key + hashlib.sha256(key).digest()[:_RECOVERY_CHECKSUM_SIZE]
    code = _crockford_encode(payload)  # 35 bytes -> 56 chars
    return "-".join(code[i : i + 4] for i in range(0, len(code), 4))


def parse_recovery_code(text: str) -> bytes:
    """Decode a recovery code back to the 32-byte key, verifying the checksum.

    Tolerant of case, hyphens/spaces, and 0/O · 1/I/L transcription slips.
    """
    normalized = "".join(text.upper().split()).replace("-", "")
    expected_len = ((KEY_SIZE + _RECOVERY_CHECKSUM_SIZE) * 8 + 4) // 5  # 56
    if len(normalized) != expected_len:
        raise RecoveryCodeError("복구 코드 길이가 올바르지 않습니다. 하이픈을 빼고 56자인지 확인해 주세요.")
    raw = _crockford_decode(normalized)
    key, checksum = raw[:KEY_SIZE], raw[KEY_SIZE : KEY_SIZE + _RECOVERY_CHECKSUM_SIZE]
    if hashlib.sha256(key).digest()[:_RECOVERY_CHECKSUM_SIZE] != checksum:
        raise RecoveryCodeError("복구 코드가 올바르지 않습니다. 입력을 다시 확인해 주세요.")
    return key


def is_envelope(raw: Any) -> bool:
    return isinstance(raw, dict) and raw.get("checkonEnc") == 1


def encrypt_envelope(
    name: str, payload: dict[str, Any], key: bytes, *, nonce: bytes | None = None
) -> dict[str, Any]:
    if nonce is None:
        nonce = secrets.token_bytes(NONCE_SIZE)
    plaintext = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    # AAD = file name, so a ciphertext moved to another file fails authentication.
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, name.encode("utf-8"))
    return {
        "checkonEnc": 1,
        "alg": ENVELOPE_ALG,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ct": base64.b64encode(ciphertext).decode("ascii"),
    }


def decrypt_envelope(name: str, envelope: dict[str, Any], key: bytes) -> dict[str, Any]:
    if envelope.get("alg") != ENVELOPE_ALG:
        raise EnvelopeError(f"unsupported envelope alg: {envelope.get('alg')!r}")
    try:
        nonce = base64.b64decode(envelope["nonce"])
        ciphertext = base64.b64decode(envelope["ct"])
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, name.encode("utf-8"))
    except (InvalidTag, KeyError, ValueError) as exc:
        raise EnvelopeError(f"cannot decrypt {name}") from exc
    return json.loads(plaintext.decode("utf-8"))


def generate_sync_key() -> bytes:
    return secrets.token_bytes(KEY_SIZE)


def save_sync_key(key: bytes) -> None:
    save_token(get_sync_key_path(), {"key": base64.b64encode(key).decode("ascii")})


def load_sync_key() -> bytes | None:
    try:
        payload = load_token(get_sync_key_path())
    except TokenNotFoundError:
        return None
    return base64.b64decode(payload["key"])


def clear_sync_key() -> None:
    delete_token(get_sync_key_path())


def pairing_payload(key: bytes) -> str:
    encoded = base64.urlsafe_b64encode(key).rstrip(b"=").decode("ascii")
    return PAIRING_PREFIX + encoded


def migrate_plaintext_to_encrypted(client) -> tuple[int, int]:
    """Re-write every plaintext appDataFolder file through the (key-injected)
    client so it lands encrypted. Envelope files are skipped — idempotent.

    Best-effort per file: one failure must not strand the rest in plaintext.
    Returns (migrated, failed); callers surface failed > 0 so the teacher can
    simply run it again.
    """
    migrated = 0
    failed = 0
    for name in client.list_files():
        try:
            raw = client.read_json_raw(name)
            if raw is None or is_envelope(raw):
                continue
            client.upsert_json(name, raw)
            migrated += 1
        except Exception:
            logger.warning("migration failed for %s; will retry on next run", name, exc_info=True)
            failed += 1
    return migrated, failed


def reencrypt_from_old_key(client, old_key: bytes) -> tuple[int, int]:
    """Re-key every file: decrypt with ``old_key`` and re-write through the client,
    which must already be writing with the NEW key. Plaintext files are just
    re-written (and thus newly encrypted).

    Used by key re-issue after a suspected leak: the old key becomes useless once
    every file is re-encrypted. Best-effort per file, returning (reencrypted, failed)
    so a partial failure can be retried without stranding files on mixed keys.
    """
    reencrypted = 0
    failed = 0
    for name in client.list_files():
        try:
            raw = client.read_json_raw(name)
            if raw is None:
                continue
            data = decrypt_envelope(name, raw, old_key) if is_envelope(raw) else raw
            client.upsert_json(name, data)
            reencrypted += 1
        except Exception:
            logger.warning("re-encrypt failed for %s; will retry on next run", name, exc_info=True)
            failed += 1
    return reencrypted, failed
