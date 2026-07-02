"""End-to-end encryption for Drive-synced JSON (AES-256-GCM envelopes).

The envelope contract is shared with the PWA (`subject_teacher_pwa/src/lib/crypto.ts`);
`tests/fixtures/e2e_crypto_vector.json` pins cross-language interop. The sync key is
generated on the desktop, shown once as a pairing QR, and never leaves the devices.
"""
from __future__ import annotations

import base64
import json
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

PAIRING_PREFIX = "checkon.sync.v1:"
KEY_SIZE = 32
NONCE_SIZE = 12
ENVELOPE_ALG = "A256GCM"


class EnvelopeError(ValueError):
    """Envelope is malformed, tampered with, or bound to a different file name."""


class SyncKeyMissingError(RuntimeError):
    """An encrypted file was found but no sync key is stored on this device."""


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


def migrate_plaintext_to_encrypted(client) -> int:
    """Re-write every plaintext appDataFolder file through the (key-injected)
    client so it lands encrypted. Envelope files are skipped — idempotent."""
    migrated = 0
    for name in client.list_files():
        raw = client.read_json_raw(name)
        if raw is None or is_envelope(raw):
            continue
        client.upsert_json(name, raw)
        migrated += 1
    return migrated
