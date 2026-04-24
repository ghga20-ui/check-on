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
