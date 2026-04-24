from pathlib import Path

import pytest

from subject_teacher.auth.token_store import (
    TokenNotFoundError,
    delete_token,
    load_token,
    save_token,
)


def test_save_and_load_roundtrip(tmp_path: Path):
    path = tmp_path / "token.bin"
    payload = {"access_token": "ya29.abc", "refresh_token": "1//xyz"}

    save_token(path, payload)

    loaded = load_token(path)
    assert loaded == payload


def test_load_missing_raises(tmp_path: Path):
    path = tmp_path / "nonexistent.bin"

    with pytest.raises(TokenNotFoundError):
        load_token(path)


def test_delete_token(tmp_path: Path):
    path = tmp_path / "token.bin"

    save_token(path, {"refresh_token": "x"})
    assert path.exists()

    delete_token(path)

    assert not path.exists()


def test_delete_missing_is_idempotent(tmp_path: Path):
    path = tmp_path / "nonexistent.bin"

    delete_token(path)


def test_saved_file_is_not_plaintext(tmp_path: Path):
    path = tmp_path / "token.bin"

    save_token(path, {"refresh_token": "SECRET_MARKER_ZZZ"})

    raw = path.read_bytes()
    assert b"SECRET_MARKER_ZZZ" not in raw
