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


def test_migration_rewrites_plaintext_and_skips_envelopes():
    from unittest.mock import MagicMock

    plain = {"schemaVersion": 1, "month": "2026-07", "records": {}}
    already = crypto.encrypt_envelope("settings.json", {"schemaVersion": 1}, KEY)
    client = MagicMock()
    client.list_files.return_value = ["attendance-2026-07.json", "settings.json"]
    client.read_json_raw.side_effect = lambda name: (
        plain if name == "attendance-2026-07.json" else already
    )

    migrated, failed = crypto.migrate_plaintext_to_encrypted(client)

    assert (migrated, failed) == (1, 0)
    client.upsert_json.assert_called_once_with("attendance-2026-07.json", plain)


def test_migration_noop_on_empty_folder():
    from unittest.mock import MagicMock

    client = MagicMock()
    client.list_files.return_value = []
    assert crypto.migrate_plaintext_to_encrypted(client) == (0, 0)
    client.upsert_json.assert_not_called()


def test_migration_continues_past_a_failing_file():
    # A partial migration must not abort the loop: the crash on 2026-07-02 left
    # 3 of 7 files plaintext because one SSL error stopped everything.
    from unittest.mock import MagicMock

    plain = {"schemaVersion": 1}
    client = MagicMock()
    client.list_files.return_value = ["a.json", "b.json", "c.json"]
    client.read_json_raw.return_value = plain
    client.upsert_json.side_effect = [ConnectionResetError(10054, "reset"), "id-b", "id-c"]

    migrated, failed = crypto.migrate_plaintext_to_encrypted(client)

    assert (migrated, failed) == (2, 1)
    assert client.upsert_json.call_count == 3


def test_recovery_code_roundtrip():
    code = crypto.recovery_code(KEY)
    groups = code.split("-")
    assert len(groups) == 14
    assert all(len(g) == 4 for g in groups)
    assert code == code.upper()
    assert crypto.parse_recovery_code(code) == KEY


def test_recovery_code_tolerates_case_and_separators():
    code = crypto.recovery_code(KEY)
    messy = " " + code.lower().replace("-", "  ") + " \n"
    assert crypto.parse_recovery_code(messy) == KEY


def test_recovery_code_maps_ambiguous_characters():
    # A teacher may transcribe 0/O and 1/I/L interchangeably.
    code = crypto.recovery_code(KEY)
    swapped = code.replace("0", "O").replace("1", "I")
    assert crypto.parse_recovery_code(swapped) == KEY


def test_recovery_code_detects_single_character_typo():
    code = crypto.recovery_code(KEY)
    # Change the first data character to a different valid Crockford symbol.
    first = code[0]
    replacement = "Z" if first != "Z" else "2"
    typo = replacement + code[1:]
    with pytest.raises(crypto.RecoveryCodeError):
        crypto.parse_recovery_code(typo)


def test_recovery_code_rejects_wrong_length():
    with pytest.raises(crypto.RecoveryCodeError):
        crypto.parse_recovery_code("ABCD-1234")


def test_recovery_code_rejects_invalid_character():
    code = crypto.recovery_code(KEY)
    # 'U' is excluded from the Crockford alphabet and is not a mapped alias.
    bad = "U" + code[1:]
    with pytest.raises(crypto.RecoveryCodeError):
        crypto.parse_recovery_code(bad)


def test_reencrypt_decrypts_with_old_key_and_rewrites():
    from unittest.mock import MagicMock

    old_key = KEY
    doc = {"schemaVersion": 1, "records": {"2026-07-01": {"3": "absent"}}}
    envelope = crypto.encrypt_envelope("attendance-2026-07.json", doc, old_key)
    plaintext_file = {"schemaVersion": 1, "slots": []}
    client = MagicMock()
    client.list_files.return_value = ["attendance-2026-07.json", "timetable.json"]
    client.read_json_raw.side_effect = lambda name: (
        envelope if name == "attendance-2026-07.json" else plaintext_file
    )

    reencrypted, failed = crypto.reencrypt_from_old_key(client, old_key)

    assert (reencrypted, failed) == (2, 0)
    # The envelope is decrypted with the OLD key; upsert re-encrypts with the new key.
    client.upsert_json.assert_any_call("attendance-2026-07.json", doc)
    client.upsert_json.assert_any_call("timetable.json", plaintext_file)


def test_reencrypt_continues_past_a_failing_file():
    from unittest.mock import MagicMock

    doc = {"schemaVersion": 1}
    client = MagicMock()
    client.list_files.return_value = ["a.json", "b.json"]
    # Each file carries an envelope bound to its own name (AAD).
    client.read_json_raw.side_effect = lambda name: crypto.encrypt_envelope(name, doc, KEY)
    client.upsert_json.side_effect = [ConnectionResetError(10054, "reset"), "id-b"]

    reencrypted, failed = crypto.reencrypt_from_old_key(client, KEY)

    assert (reencrypted, failed) == (1, 1)


def test_sync_key_save_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(crypto, "get_sync_key_path", lambda: tmp_path / "sync_key.bin")
    assert crypto.load_sync_key() is None
    key = crypto.generate_sync_key()
    assert len(key) == 32
    crypto.save_sync_key(key)
    assert crypto.load_sync_key() == key
    crypto.clear_sync_key()
    assert crypto.load_sync_key() is None
