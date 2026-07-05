import json
from unittest.mock import MagicMock

import pytest

from subject_teacher.drive import crypto
from subject_teacher.gui.api import Api


@pytest.fixture
def key_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(crypto, "get_sync_key_path", lambda: tmp_path / "sync_key.bin")
    return tmp_path


def test_status_disabled_without_key(key_dir):
    api = Api()
    assert json.loads(api.get_sync_encryption_status()) == {"enabled": False}


def test_enable_creates_key_and_migrates(key_dir, monkeypatch):
    api = Api()
    fake_store = MagicMock()
    monkeypatch.setattr(api, "_store", lambda: fake_store)
    monkeypatch.setattr(crypto, "migrate_plaintext_to_encrypted", lambda client: (3, 0))

    result = json.loads(api.enable_sync_encryption())

    assert result["created"] is True
    assert result["migrated"] == 3
    assert result["payload"].startswith(crypto.PAIRING_PREFIX)
    assert crypto.load_sync_key() is not None
    assert json.loads(api.get_sync_encryption_status()) == {"enabled": True}


def test_enable_is_idempotent_for_existing_key(key_dir, monkeypatch):
    key = crypto.generate_sync_key()
    crypto.save_sync_key(key)
    api = Api()
    monkeypatch.setattr(api, "_store", lambda: MagicMock())
    monkeypatch.setattr(crypto, "migrate_plaintext_to_encrypted", lambda client: (0, 0))

    result = json.loads(api.enable_sync_encryption())

    assert result["created"] is False
    assert result["payload"] == crypto.pairing_payload(key)


def test_pairing_payload_null_without_key(key_dir):
    api = Api()
    assert json.loads(api.get_pairing_payload()) == {"payload": None}


def test_enable_reports_failed_count(key_dir, monkeypatch):
    api = Api()
    monkeypatch.setattr(api, "_store", lambda: MagicMock())
    monkeypatch.setattr(crypto, "migrate_plaintext_to_encrypted", lambda client: (4, 3))

    result = json.loads(api.enable_sync_encryption())

    assert result["migrated"] == 4
    assert result["failed"] == 3


def test_sync_encryption_methods_are_serialized():
    # Migration shares the app's single httplib2 connection; running it
    # concurrently with other bridge calls corrupts SSL state (2026-07-02 crash).
    from subject_teacher.gui.api import SERIALIZED_API_METHODS

    assert {
        "enable_sync_encryption",
        "get_sync_encryption_status",
        "get_pairing_payload",
        "get_recovery_code",
        "restore_from_recovery_code",
        "reissue_sync_key",
    } <= SERIALIZED_API_METHODS


def _store_with_files(files: dict):
    store = MagicMock()
    store.client.list_files.return_value = list(files.keys())
    store.client.read_json_raw.side_effect = lambda name: files[name]
    return store


def test_get_recovery_code_null_without_key(key_dir):
    api = Api()
    assert json.loads(api.get_recovery_code()) == {"code": None}


def test_get_recovery_code_roundtrips_to_stored_key(key_dir):
    key = crypto.generate_sync_key()
    crypto.save_sync_key(key)
    api = Api()

    code = json.loads(api.get_recovery_code())["code"]

    assert crypto.parse_recovery_code(code) == key


def test_restore_rejects_malformed_code(key_dir):
    api = Api()
    result = json.loads(api.restore_from_recovery_code("not-a-code"))
    assert result["ok"] is False
    assert "error" in result
    assert crypto.load_sync_key() is None


def test_restore_accepts_when_no_encrypted_data(key_dir, monkeypatch):
    key = crypto.generate_sync_key()
    code = crypto.recovery_code(key)
    api = Api()
    monkeypatch.setattr(api, "_store", lambda: _store_with_files({}))

    result = json.loads(api.restore_from_recovery_code(code))

    assert result == {"ok": True, "decryptsExisting": False}
    assert crypto.load_sync_key() == key


def test_restore_verifies_against_existing_envelope(key_dir, monkeypatch):
    key = crypto.generate_sync_key()
    code = crypto.recovery_code(key)
    envelope = crypto.encrypt_envelope("settings.json", {"schemaVersion": 1}, key)
    api = Api()
    monkeypatch.setattr(api, "_store", lambda: _store_with_files({"settings.json": envelope}))

    result = json.loads(api.restore_from_recovery_code(code))

    assert result == {"ok": True, "decryptsExisting": True}
    assert crypto.load_sync_key() == key


def test_restore_rejects_code_that_cannot_open_data(key_dir, monkeypatch):
    real_key = crypto.generate_sync_key()
    other_key = crypto.generate_sync_key()
    envelope = crypto.encrypt_envelope("settings.json", {"schemaVersion": 1}, real_key)
    api = Api()
    monkeypatch.setattr(api, "_store", lambda: _store_with_files({"settings.json": envelope}))

    result = json.loads(api.restore_from_recovery_code(crypto.recovery_code(other_key)))

    assert result["ok"] is False
    assert crypto.load_sync_key() is None  # wrong key must not be stored


def test_reissue_requires_existing_key(key_dir):
    api = Api()
    result = json.loads(api.reissue_sync_key())
    assert result["ok"] is False


def test_reissue_generates_new_key_and_reencrypts(key_dir, monkeypatch):
    old_key = crypto.generate_sync_key()
    crypto.save_sync_key(old_key)
    api = Api()
    monkeypatch.setattr(api, "_store", lambda: MagicMock())
    monkeypatch.setattr(crypto, "reencrypt_from_old_key", lambda client, old: (5, 0))

    result = json.loads(api.reissue_sync_key())

    assert result["ok"] is True
    assert result["reencrypted"] == 5
    new_key = crypto.load_sync_key()
    assert new_key != old_key
    assert result["payload"] == crypto.pairing_payload(new_key)
    assert crypto.parse_recovery_code(result["recoveryCode"]) == new_key
