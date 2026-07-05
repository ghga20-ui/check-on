import sys
from pathlib import Path

from subject_teacher.paths import get_app_data_dir, get_client_secrets_path, get_password_path, get_token_path


def test_app_data_dir_uses_localappdata(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    app_data_dir = get_app_data_dir()

    assert app_data_dir == tmp_path / "NeisSubject"


def test_app_data_dir_is_created(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    app_data_dir = get_app_data_dir()

    assert app_data_dir.exists()
    assert app_data_dir.is_dir()


def test_token_and_password_paths(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert get_token_path().name == "token.bin"
    assert get_password_path().name == "password.bin"
    assert get_token_path().parent == tmp_path / "NeisSubject"


def test_client_secrets_prefers_project_root(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    client_secrets_path = get_client_secrets_path()

    assert client_secrets_path.name == "client_secrets.json"


def test_client_secrets_uses_appdata_override(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    override = tmp_path / "NeisSubject" / "client_secrets.json"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text("{}", encoding="utf-8")

    assert get_client_secrets_path() == override


def test_client_secrets_uses_bundled_when_frozen(monkeypatch, tmp_path: Path):
    # App data has no override; a frozen build must find the bundled secret.
    app_data = tmp_path / "appdata"
    bundle = tmp_path / "bundle"
    bundle.mkdir(parents=True, exist_ok=True)
    bundled = bundle / "client_secrets.json"
    bundled.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(app_data))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)

    assert get_client_secrets_path() == bundled
