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
    monkeypatch.setattr(crypto, "migrate_plaintext_to_encrypted", lambda client: 3)

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
    monkeypatch.setattr(crypto, "migrate_plaintext_to_encrypted", lambda client: 0)

    result = json.loads(api.enable_sync_encryption())

    assert result["created"] is False
    assert result["payload"] == crypto.pairing_payload(key)


def test_pairing_payload_null_without_key(key_dir):
    api = Api()
    assert json.loads(api.get_pairing_payload()) == {"payload": None}
