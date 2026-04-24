from unittest.mock import MagicMock

from subject_teacher.auth import google_oauth


def test_credentials_to_payload_roundtrip():
    credentials = MagicMock()
    credentials.token = "ya29.xxx"
    credentials.refresh_token = "1//xyz"
    credentials.token_uri = "https://oauth2.googleapis.com/token"
    credentials.client_id = "abc.apps.googleusercontent.com"
    credentials.client_secret = "GOCSPX-secret"
    credentials.scopes = ["https://www.googleapis.com/auth/drive.appdata"]

    payload = google_oauth._credentials_to_payload(credentials)

    assert payload["refresh_token"] == "1//xyz"
    assert payload["scopes"] == ["https://www.googleapis.com/auth/drive.appdata"]


def test_payload_to_credentials_roundtrip():
    payload = {
        "token": "ya29.xxx",
        "refresh_token": "1//xyz",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "abc.apps.googleusercontent.com",
        "client_secret": "GOCSPX-secret",
        "scopes": ["https://www.googleapis.com/auth/drive.appdata"],
    }

    credentials = google_oauth._payload_to_credentials(payload)

    assert credentials.refresh_token == "1//xyz"
    assert "drive.appdata" in credentials.scopes[0]


def test_load_credentials_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert google_oauth.load_credentials() is None
