"""Google Drive appDataFolder JSON CRUD helpers."""
from __future__ import annotations

import io
import json
import ssl
from collections.abc import Callable
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload


def _is_transient_error(exc: Exception) -> bool:
    # A long-lived httplib2 keep-alive connection can go bad two ways:
    #  - the OS aborts a stale/idle socket  -> WinError 10053/10054
    #    (ConnectionAbortedError / ConnectionResetError, both ConnectionError),
    #  - a half-read response corrupts SSL record framing
    #    -> ssl.SSLError "wrong version number" / "bad record mac".
    # Both are recoverable by dropping the poisoned connection and retrying.
    if isinstance(exc, ConnectionError):
        return True
    if isinstance(exc, OSError) and getattr(exc, "winerror", None) in (10053, 10054):
        return True
    if isinstance(exc, ssl.SSLError):
        message = str(exc).lower()
        return (
            "wrong_version_number" in message
            or "wrong version number" in message
            or "decryption_failed_or_bad_record_mac" in message
            or "bad record mac" in message
        )
    return False


# Back-compat alias; older call sites / tests referenced the SSL-only name.
_is_transient_ssl_error = _is_transient_error


def _with_transient_retry(
    operation: Callable[[], Any],
    on_retry: Callable[[], None] | None = None,
    attempts: int = 3,
) -> Any:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return operation()
        except Exception as exc:
            if not _is_transient_error(exc):
                raise
            last_error = exc
            # Evict the poisoned connection so the next attempt dials a fresh
            # socket instead of reusing the dead one.
            if on_retry is not None:
                try:
                    on_retry()
                except Exception:
                    pass
    if last_error is not None:
        raise last_error
    return operation()


class DriveAppDataClient:
    """Thin wrapper around Drive v3 appDataFolder operations."""

    def __init__(self, credentials=None, service=None):
        if service is None:
            if credentials is None:
                raise ValueError("either credentials or service must be provided")
            service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        self._service = service

    def _reset_connections(self) -> None:
        """Close and evict cached httplib2 keep-alive connections.

        googleapiclient holds the transport at ``service._http``; when built
        with credentials that is a ``google_auth_httplib2.AuthorizedHttp`` whose
        wrapped ``httplib2.Http`` lives at ``.http`` and caches live sockets in
        ``.connections``. Dropping them forces the next request to redial.
        Best-effort: silently no-op if the shape differs.
        """
        http = getattr(self._service, "_http", None)
        inner = getattr(http, "http", http)
        conns = getattr(inner, "connections", None)
        if not isinstance(conns, dict):
            return
        for conn in list(conns.values()):
            try:
                conn.close()
            except Exception:
                pass
        conns.clear()

    def find_file_id(self, name: str) -> str | None:
        response = _with_transient_retry(
            lambda: self._service.files()
            .list(
                    q=f"name = '{name}' and 'appDataFolder' in parents and trashed = false",
                    spaces="appDataFolder",
                    fields="files(id, name)",
                    pageSize=10,
                )
            .execute(),
            on_retry=self._reset_connections,
        )
        files = response.get("files", [])
        return files[0]["id"] if files else None

    def read_json(self, name: str) -> dict[str, Any] | None:
        file_id = self.find_file_id(name)
        if file_id is None:
            return None

        request = self._service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = _with_transient_retry(
                lambda: downloader.next_chunk(),
                on_retry=self._reset_connections,
            )
        return json.loads(buffer.getvalue().decode("utf-8"))

    def upsert_json(self, name: str, payload: dict[str, Any]) -> str:
        media = MediaIoBaseUpload(
            io.BytesIO(json.dumps(payload, ensure_ascii=False).encode("utf-8")),
            mimetype="application/json",
            resumable=False,
        )
        file_id = self.find_file_id(name)
        if file_id is None:
            response = _with_transient_retry(
                lambda: self._service.files()
                .create(
                        body={"name": name, "parents": ["appDataFolder"]},
                        media_body=media,
                        fields="id",
                    )
                .execute(),
                on_retry=self._reset_connections,
            )
            return response["id"]

        _with_transient_retry(
            lambda: self._service.files().update(fileId=file_id, media_body=media, fields="id").execute(),
            on_retry=self._reset_connections,
        )
        return file_id

    def delete(self, name: str) -> bool:
        file_id = self.find_file_id(name)
        if file_id is None:
            return False
        _with_transient_retry(
            lambda: self._service.files().delete(fileId=file_id).execute(),
            on_retry=self._reset_connections,
        )
        return True

    def list_files(self) -> list[str]:
        response = _with_transient_retry(
            lambda: self._service.files()
            .list(
                    spaces="appDataFolder",
                    fields="files(id, name)",
                    pageSize=100,
                )
            .execute(),
            on_retry=self._reset_connections,
        )
        return [item["name"] for item in response.get("files", [])]
