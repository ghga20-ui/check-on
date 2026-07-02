import base64
import json
from pathlib import Path

import pytest

from subject_teacher.drive import crypto

VECTOR = json.loads(
    (Path(__file__).parent / "fixtures" / "e2e_crypto_vector.json").read_text("utf-8")
)
KEY = base64.b64decode(VECTOR["keyB64"])
NONCE = base64.b64decode(VECTOR["nonceB64"])


def test_encrypt_matches_cross_language_vector():
    payload = json.loads(VECTOR["plaintextJson"])
    envelope = crypto.encrypt_envelope(VECTOR["aad"], payload, KEY, nonce=NONCE)
    assert envelope["checkonEnc"] == 1
    assert envelope["alg"] == "A256GCM"
    assert envelope["nonce"] == VECTOR["nonceB64"]
    assert envelope["ct"] == VECTOR["ciphertextB64"]


def test_decrypt_matches_cross_language_vector():
    envelope = {
        "checkonEnc": 1,
        "alg": "A256GCM",
        "nonce": VECTOR["nonceB64"],
        "ct": VECTOR["ciphertextB64"],
    }
    assert crypto.decrypt_envelope(VECTOR["aad"], envelope, KEY) == json.loads(
        VECTOR["plaintextJson"]
    )


def test_roundtrip_with_random_nonce():
    payload = {"month": "2026-07", "records": {"2026-07-01": {}}}
    envelope = crypto.encrypt_envelope("attendance-2026-07.json", payload, KEY)
    assert crypto.is_envelope(envelope)
    assert crypto.decrypt_envelope("attendance-2026-07.json", envelope, KEY) == payload


def test_tampered_ciphertext_rejected():
    envelope = crypto.encrypt_envelope("settings.json", {"a": 1}, KEY)
    ct = bytearray(base64.b64decode(envelope["ct"]))
    ct[0] ^= 0xFF
    envelope["ct"] = base64.b64encode(bytes(ct)).decode()
    with pytest.raises(crypto.EnvelopeError):
        crypto.decrypt_envelope("settings.json", envelope, KEY)


def test_wrong_file_name_rejected():
    envelope = crypto.encrypt_envelope("settings.json", {"a": 1}, KEY)
    with pytest.raises(crypto.EnvelopeError):
        crypto.decrypt_envelope("timetable.json", envelope, KEY)


def test_is_envelope_rejects_plain_documents():
    assert not crypto.is_envelope({"schemaVersion": 1, "month": "2026-07"})
    assert not crypto.is_envelope(None)
    assert not crypto.is_envelope([])


def test_pairing_payload_format():
    payload = crypto.pairing_payload(KEY)
    assert payload.startswith(crypto.PAIRING_PREFIX)
    encoded = payload[len(crypto.PAIRING_PREFIX):]
    assert "=" not in encoded
    padded = encoded + "=" * (-len(encoded) % 4)
    assert base64.urlsafe_b64decode(padded) == KEY


def test_sync_key_save_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(crypto, "get_sync_key_path", lambda: tmp_path / "sync_key.bin")
    assert crypto.load_sync_key() is None
    key = crypto.generate_sync_key()
    assert len(key) == 32
    crypto.save_sync_key(key)
    assert crypto.load_sync_key() == key
    crypto.clear_sync_key()
    assert crypto.load_sync_key() is None
