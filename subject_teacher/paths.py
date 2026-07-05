"""Path helpers for local app data used by the subject teacher app."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "NeisSubject"


def _bundle_dir() -> Path | None:
    """Directory of files bundled into a PyInstaller EXE, or None in dev."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
    return None


def get_app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Local")

    app_data_dir = Path(base) / APP_DIR_NAME
    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir


def get_token_path() -> Path:
    return get_app_data_dir() / "token.bin"


def get_password_path() -> Path:
    return get_app_data_dir() / "password.bin"


def get_neis_api_key_path() -> Path:
    return get_app_data_dir() / "neis_api_key.bin"


def get_client_secrets_path() -> Path:
    # 1) User-provided override in app data wins, so credentials can be rotated
    #    on an installed machine without shipping a new build.
    override = get_app_data_dir() / "client_secrets.json"
    if override.exists():
        return override
    # 2) Bundled inside the packaged EXE (installed-app OAuth client).
    bundle = _bundle_dir()
    if bundle is not None:
        bundled = bundle / "client_secrets.json"
        if bundled.exists():
            return bundled
    # 3) Dev: repo root.
    project_path = Path(__file__).resolve().parent.parent / "client_secrets.json"
    if project_path.exists():
        return project_path
    # 4) Fallback — also where the "not found" error tells users to drop the file.
    return override


def get_students_path() -> Path:
    return get_app_data_dir() / "students.local.json"


def get_sync_key_path() -> Path:
    return get_app_data_dir() / "sync_key.bin"
