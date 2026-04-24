"""DPAPI-backed token storage helpers for the current Windows user."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import win32crypt


class TokenNotFoundError(FileNotFoundError):
    """Raised when the requested token file does not exist."""


def save_token(path: Path, payload: dict[str, Any]) -> None:
    """Serialize a token payload to JSON and encrypt it with DPAPI."""
    path.parent.mkdir(parents=True, exist_ok=True)
    plaintext = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ciphertext = win32crypt.CryptProtectData(plaintext)
    path.write_bytes(ciphertext)


def load_token(path: Path) -> dict[str, Any]:
    """Load a token payload from a DPAPI-encrypted JSON file."""
    if not path.exists():
        raise TokenNotFoundError(str(path))

    ciphertext = path.read_bytes()
    _, plaintext = win32crypt.CryptUnprotectData(ciphertext)
    return json.loads(plaintext.decode("utf-8"))


def delete_token(path: Path) -> None:
    """Delete a stored token file if it exists."""
    try:
        path.unlink()
    except FileNotFoundError:
        pass
