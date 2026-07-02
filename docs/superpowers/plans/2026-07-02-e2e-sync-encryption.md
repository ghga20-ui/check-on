# E2E 동기화 암호화 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drive appDataFolder에 저장되는 모든 동기화 JSON을 AES-256-GCM 암호문 봉투로 전환하고, 복호화 키를 QR 페어링으로 데스크톱→폰에 1회 전달한다 (스펙: `docs/superpowers/specs/2026-07-02-e2e-sync-encryption-design.md`).

**Architecture:** 암·복호화는 양측의 Drive 관문(`drive/client.py`의 `read_json`/`upsert_json`, PWA `lib/drive.ts`의 `readJson`/`writeJson`)에서만 수행 — 상위 코드는 무변경. 봉투 `{"checkonEnc":1,"alg":"A256GCM","nonce":b64,"ct":b64}`, AAD=파일명. 키는 데스크톱 DPAPI(`sync_key.bin`) / 폰 IndexedDB. 기능은 옵트인(키 없으면 기존 평문 동작).

**Tech Stack:** Python `cryptography`(AESGCM, 46.0.5 확인됨), WebCrypto(`crypto.subtle`), fake-indexeddb(테스트), `qrcode`(데스크톱 UI QR 생성), `jsqr`(PWA 카메라 스캔 폴백).

## Global Constraints

- Python 실행은 반드시 `py -3.14`, 저장소 루트(`C:\Users\admin\Desktop\2026_project\neis-attendance`)에서. PATH의 `python`은 다른 venv라 금지.
- Python 테스트: `py -3.14 -m pytest tests/ -q` (기준선 140 passed). PWA 테스트: `cd subject_teacher_pwa && npm test`. 데스크톱 UI 테스트: `cd subject_teacher/neis_attendance && npm test`.
- 페어링 페이로드 접두사는 정확히 `checkon.sync.v1:` + base64url(패딩 제거) 32바이트 키.
- 봉투 필드명은 정확히 `checkonEnc`(=1), `alg`(="A256GCM"), `nonce`, `ct` — 양 언어 공통 계약.
- 키·페어링 페이로드는 절대 로그·커밋·클라우드에 남기지 않는다.
- 학생 이름은 어떤 경로로도 클라우드로 가지 않는다(기존 Case C 불변식 유지).
- 커밋 메시지 푸터: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: Python 암호 봉투 모듈 + 교차 테스트 벡터

**Files:**
- Create: `tests/fixtures/e2e_crypto_vector.json`
- Create: `subject_teacher/drive/crypto.py`
- Create: `tests/test_drive_crypto.py`
- Modify: `subject_teacher/paths.py` (`get_sync_key_path` 추가)

**Interfaces:**
- Produces: `is_envelope(raw) -> bool`, `encrypt_envelope(name: str, payload: dict, key: bytes, *, nonce: bytes | None = None) -> dict`, `decrypt_envelope(name: str, envelope: dict, key: bytes) -> dict`, `EnvelopeError(ValueError)`, `SyncKeyMissingError(RuntimeError)`, `generate_sync_key() -> bytes`, `save_sync_key(key)`, `load_sync_key() -> bytes | None`, `clear_sync_key()`, `pairing_payload(key: bytes) -> str`, 상수 `PAIRING_PREFIX = "checkon.sync.v1:"`

- [ ] **Step 1: 벡터 픽스처 생성** — `tests/fixtures/e2e_crypto_vector.json`:

```json
{
  "keyB64": "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=",
  "nonceB64": "AAECAwQFBgcICQoL",
  "aad": "attendance-2026-07.json",
  "plaintextJson": "{\"schemaVersion\":1,\"month\":\"2026-07\",\"records\":{}}",
  "ciphertextB64": "PCCleK2Ar3rbJOX42IYWT7nnqxadFDEIUEXfpy9ZMoQsIJneg+Ng/RfLDYn7pRJDkyRWIxN95DSXyeKMo64rNcL5"
}
```

(검증된 값 — `cryptography.AESGCM`으로 사전 생성함. ct 끝 16바이트가 GCM 태그.)

- [ ] **Step 2: 실패하는 테스트 작성** — `tests/test_drive_crypto.py`:

```python
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


def test_sync_key_save_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(crypto, "get_sync_key_path", lambda: tmp_path / "sync_key.bin")
    assert crypto.load_sync_key() is None
    key = crypto.generate_sync_key()
    assert len(key) == 32
    crypto.save_sync_key(key)
    assert crypto.load_sync_key() == key
    crypto.clear_sync_key()
    assert crypto.load_sync_key() is None
```

- [ ] **Step 3: 실패 확인** — `py -3.14 -m pytest tests/test_drive_crypto.py -q` → `ModuleNotFoundError` 또는 collection error 예상

- [ ] **Step 4: 구현** — `subject_teacher/paths.py`에 추가:

```python
def get_sync_key_path() -> Path:
    return get_app_data_dir() / "sync_key.bin"
```

`subject_teacher/drive/crypto.py` 생성:

```python
"""End-to-end encryption for Drive-synced JSON (AES-256-GCM envelopes).

The envelope contract is shared with the PWA (`subject_teacher_pwa/src/lib/crypto.ts`);
`tests/fixtures/e2e_crypto_vector.json` pins cross-language interop.
"""
from __future__ import annotations

import base64
import json
import secrets
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from subject_teacher.auth.token_store import TokenNotFoundError, delete_token, load_token, save_token
from subject_teacher.paths import get_sync_key_path

PAIRING_PREFIX = "checkon.sync.v1:"
KEY_SIZE = 32
NONCE_SIZE = 12
ENVELOPE_ALG = "A256GCM"


class EnvelopeError(ValueError):
    """Envelope is malformed, tampered with, or bound to a different file name."""


class SyncKeyMissingError(RuntimeError):
    """An encrypted file was found but no sync key is stored on this device."""


def is_envelope(raw: Any) -> bool:
    return isinstance(raw, dict) and raw.get("checkonEnc") == 1


def encrypt_envelope(
    name: str, payload: dict[str, Any], key: bytes, *, nonce: bytes | None = None
) -> dict[str, Any]:
    if nonce is None:
        nonce = secrets.token_bytes(NONCE_SIZE)
    plaintext = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, name.encode("utf-8"))
    return {
        "checkonEnc": 1,
        "alg": ENVELOPE_ALG,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ct": base64.b64encode(ciphertext).decode("ascii"),
    }


def decrypt_envelope(name: str, envelope: dict[str, Any], key: bytes) -> dict[str, Any]:
    if envelope.get("alg") != ENVELOPE_ALG:
        raise EnvelopeError(f"unsupported envelope alg: {envelope.get('alg')!r}")
    try:
        nonce = base64.b64decode(envelope["nonce"])
        ciphertext = base64.b64decode(envelope["ct"])
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, name.encode("utf-8"))
    except (InvalidTag, KeyError, ValueError) as exc:
        raise EnvelopeError(f"cannot decrypt {name}") from exc
    return json.loads(plaintext.decode("utf-8"))


def generate_sync_key() -> bytes:
    return secrets.token_bytes(KEY_SIZE)


def save_sync_key(key: bytes) -> None:
    save_token(get_sync_key_path(), {"key": base64.b64encode(key).decode("ascii")})


def load_sync_key() -> bytes | None:
    try:
        payload = load_token(get_sync_key_path())
    except TokenNotFoundError:
        return None
    return base64.b64decode(payload["key"])


def clear_sync_key() -> None:
    delete_token(get_sync_key_path())


def pairing_payload(key: bytes) -> str:
    encoded = base64.urlsafe_b64encode(key).rstrip(b"=").decode("ascii")
    return PAIRING_PREFIX + encoded
```

(주의: `crypto.get_sync_key_path`를 모듈 네임스페이스로 import해야 monkeypatch가 동작 — `from subject_teacher.paths import get_sync_key_path` 그대로 두고 함수 내부에서 `get_sync_key_path()` 호출하면 됨. 테스트는 `crypto.get_sync_key_path`를 패치하므로 모듈 attribute 참조가 유지된다.)

- [ ] **Step 5: 통과 확인** — `py -3.14 -m pytest tests/test_drive_crypto.py -q` → 8 passed
- [ ] **Step 6: 커밋** — `git add subject_teacher/drive/crypto.py subject_teacher/paths.py tests/test_drive_crypto.py tests/fixtures/e2e_crypto_vector.json && git commit -m "feat(e2e): AES-256-GCM envelope crypto + cross-language vector"`

### Task 2: DriveAppDataClient 봉투 통합

**Files:**
- Modify: `subject_teacher/drive/client.py`
- Test: `tests/test_drive_client.py` (추가)

**Interfaces:**
- Consumes: Task 1의 `is_envelope`/`encrypt_envelope`/`decrypt_envelope`/`SyncKeyMissingError`
- Produces: `DriveAppDataClient(credentials=None, service=None, sync_key: bytes | None = None)`, `read_json_raw(name) -> dict | None` (복호화 없이 원문), `read_json`은 봉투면 복호화·평문이면 그대로, `upsert_json`은 키 있으면 암호화 저장

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_drive_client.py`에 추가:

```python
import base64
import json as json_module

from subject_teacher.drive import crypto as drive_crypto

E2E_KEY = bytes(range(32))


def _service_returning(files_result, media_bytes=None):
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {"files": files_result}
    return service


def test_upsert_json_encrypts_when_key_present():
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {"files": []}
    service.files.return_value.create.return_value.execute.return_value = {"id": "new123"}

    client = DriveAppDataClient(service=service, sync_key=E2E_KEY)
    client.upsert_json("settings.json", {"schemaVersion": 1})

    media = service.files.return_value.create.call_args.kwargs["media_body"]
    stored = json_module.loads(media._fd.getvalue().decode("utf-8"))
    assert drive_crypto.is_envelope(stored)
    assert drive_crypto.decrypt_envelope("settings.json", stored, E2E_KEY) == {"schemaVersion": 1}


def test_upsert_json_stays_plaintext_without_key():
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {"files": []}
    service.files.return_value.create.return_value.execute.return_value = {"id": "new123"}

    client = DriveAppDataClient(service=service)
    client.upsert_json("settings.json", {"schemaVersion": 1})

    media = service.files.return_value.create.call_args.kwargs["media_body"]
    stored = json_module.loads(media._fd.getvalue().decode("utf-8"))
    assert stored == {"schemaVersion": 1}
```

`read_json` 계열은 `MediaIoBaseDownload` 목킹이 번거로우므로 `read_json_raw`를 목킹해 검증:

```python
def test_read_json_decrypts_envelope(monkeypatch):
    envelope = drive_crypto.encrypt_envelope("settings.json", {"schemaVersion": 1}, E2E_KEY)
    client = DriveAppDataClient(service=MagicMock(), sync_key=E2E_KEY)
    monkeypatch.setattr(client, "read_json_raw", lambda name: envelope)
    assert client.read_json("settings.json") == {"schemaVersion": 1}


def test_read_json_passes_legacy_plaintext(monkeypatch):
    client = DriveAppDataClient(service=MagicMock(), sync_key=E2E_KEY)
    monkeypatch.setattr(client, "read_json_raw", lambda name: {"schemaVersion": 1})
    assert client.read_json("settings.json") == {"schemaVersion": 1}


def test_read_json_envelope_without_key_raises(monkeypatch):
    envelope = drive_crypto.encrypt_envelope("settings.json", {"schemaVersion": 1}, E2E_KEY)
    client = DriveAppDataClient(service=MagicMock())
    monkeypatch.setattr(client, "read_json_raw", lambda name: envelope)
    import pytest
    with pytest.raises(drive_crypto.SyncKeyMissingError):
        client.read_json("settings.json")
```

- [ ] **Step 2: 실패 확인** — `py -3.14 -m pytest tests/test_drive_client.py -q` → 신규 5건 FAIL (`sync_key` 미지원 / `read_json_raw` 없음)
- [ ] **Step 3: 구현** — `client.py`: 생성자에 `sync_key: bytes | None = None` 저장. 기존 `read_json` 본문을 `read_json_raw`로 개명하고 새 `read_json` 작성:

```python
def read_json(self, name: str) -> dict[str, Any] | None:
    raw = self.read_json_raw(name)
    if raw is None or not crypto.is_envelope(raw):
        return raw
    if self._sync_key is None:
        raise crypto.SyncKeyMissingError(name)
    return crypto.decrypt_envelope(name, raw, self._sync_key)
```

`upsert_json` 첫 줄에:

```python
if self._sync_key is not None:
    payload = crypto.encrypt_envelope(name, payload, self._sync_key)
```

import는 `from subject_teacher.drive import crypto` (별칭 순환 없음).

- [ ] **Step 4: 통과 확인** — `py -3.14 -m pytest tests/test_drive_client.py -q` → 전체 passed
- [ ] **Step 5: 커밋** — `git commit -m "feat(e2e): DriveAppDataClient transparent envelope encrypt/decrypt"`

### Task 3: 평문→암호문 마이그레이션

**Files:**
- Modify: `subject_teacher/drive/crypto.py` (함수 추가)
- Modify: `subject_teacher/drive/store.py` (`client` property)
- Test: `tests/test_drive_crypto.py` (추가)

**Interfaces:**
- Produces: `migrate_plaintext_to_encrypted(client) -> int` (암호화로 재기록한 파일 수, 봉투는 스킵 — 멱등), `DriveStore.client` property

- [ ] **Step 1: 실패하는 테스트 작성**:

```python
def test_migration_rewrites_plaintext_and_skips_envelopes():
    from unittest.mock import MagicMock

    plain = {"schemaVersion": 1, "month": "2026-07", "records": {}}
    already = crypto.encrypt_envelope("settings.json", {"schemaVersion": 1}, KEY)
    client = MagicMock()
    client.list_files.return_value = ["attendance-2026-07.json", "settings.json"]
    client.read_json_raw.side_effect = lambda name: (
        plain if name == "attendance-2026-07.json" else already
    )

    migrated = crypto.migrate_plaintext_to_encrypted(client)

    assert migrated == 1
    client.upsert_json.assert_called_once_with("attendance-2026-07.json", plain)


def test_migration_noop_on_empty_folder():
    from unittest.mock import MagicMock

    client = MagicMock()
    client.list_files.return_value = []
    assert crypto.migrate_plaintext_to_encrypted(client) == 0
    client.upsert_json.assert_not_called()
```

- [ ] **Step 2: 실패 확인** → `AttributeError: migrate_plaintext_to_encrypted`
- [ ] **Step 3: 구현** — `crypto.py`에 추가 (upsert_json이 키 주입된 클라이언트에서 자동 암호화하는 점을 이용):

```python
def migrate_plaintext_to_encrypted(client) -> int:
    """Re-write every plaintext appDataFolder file through the (key-injected)
    client so it lands encrypted. Envelope files are skipped — idempotent."""
    migrated = 0
    for name in client.list_files():
        raw = client.read_json_raw(name)
        if raw is None or is_envelope(raw):
            continue
        client.upsert_json(name, raw)
        migrated += 1
    return migrated
```

`store.py`에 property 추가:

```python
@property
def client(self) -> DriveAppDataClient:
    return self._client
```

- [ ] **Step 4: 통과 확인** — `py -3.14 -m pytest tests/test_drive_crypto.py -q`
- [ ] **Step 5: 커밋** — `git commit -m "feat(e2e): idempotent plaintext-to-encrypted migration"`

### Task 4: build_store 키 주입 + GUI API 3종

**Files:**
- Modify: `subject_teacher/state.py:67-79` (`build_store`)
- Modify: `subject_teacher/gui/api.py` (메서드 3개, `Api` 클래스 끝부분에 추가)
- Test: `tests/test_sync_encryption_api.py` (신규)

**Interfaces:**
- Consumes: Task 1~3 전부
- Produces: pywebview 브리지 메서드 `get_sync_encryption_status() -> str(JSON {"enabled": bool})`, `enable_sync_encryption() -> str(JSON {"payload": str, "migrated": int, "created": bool})`, `get_pairing_payload() -> str(JSON {"payload": str} | {"payload": null})` — 모두 JSON 문자열 반환(기존 브리지 관례)

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_sync_encryption_api.py`:

```python
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
```

주의: `Api()` 생성자가 무거우면(윈도우/스레드 등) 테스트에서 `Api.__new__(Api)` + 필요한 속성 수동 세팅으로 대체 — 구현 시 생성자를 먼저 읽고 판단. `enable_sync_encryption`은 DPAPI를 실제로 호출하므로 Windows 로컬 테스트에서만 유효(현 개발 환경은 Windows — OK). `crypto.migrate_plaintext_to_encrypted`는 api 모듈이 `crypto.migrate_plaintext_to_encrypted(...)`로 참조해야 monkeypatch가 적용됨.

- [ ] **Step 2: 실패 확인** — `py -3.14 -m pytest tests/test_sync_encryption_api.py -q`
- [ ] **Step 3: 구현** — `state.py`:

```python
def build_store() -> DriveStore:
    global _students_migrated
    credentials = get_credentials()
    from subject_teacher.drive.crypto import load_sync_key

    client = DriveAppDataClient(credentials=credentials, sync_key=load_sync_key())
    ...  # 이하 기존 마이그레이션 로직 그대로
```

`gui/api.py` — `Api` 클래스에 추가 (모듈 상단에 `from subject_teacher.drive import crypto` import):

```python
def get_sync_encryption_status(self) -> str:
    return json.dumps({"enabled": crypto.load_sync_key() is not None})

def get_pairing_payload(self) -> str:
    key = crypto.load_sync_key()
    payload = crypto.pairing_payload(key) if key is not None else None
    return json.dumps({"payload": payload})

def enable_sync_encryption(self) -> str:
    key = crypto.load_sync_key()
    created = key is None
    if created:
        key = crypto.generate_sync_key()
        crypto.save_sync_key(key)
    self._store_cache = None  # 키 주입된 새 클라이언트로 재구성
    store = self._store()
    migrated = crypto.migrate_plaintext_to_encrypted(store.client)
    return json.dumps({
        "payload": crypto.pairing_payload(key),
        "migrated": migrated,
        "created": created,
    })
```

`_store_cache` 속성명·캐시 무효화 방식은 구현 시 `api.py`의 실제 `_store()` 코드(368행 부근)에 맞춘다. `enable_sync_encryption`/`get_pairing_payload` 반환값은 절대 로그로 출력하지 않는다.

- [ ] **Step 4: 통과 + 전체 회귀** — `py -3.14 -m pytest tests/ -q` → 기존 140 + 신규 전부 passed
- [ ] **Step 5: 커밋** — `git commit -m "feat(e2e): sync-key injection in build_store + pairing bridge API"`

### Task 5: PWA 암호 모듈 (`crypto.ts`) — 교차 벡터 검증

**Files:**
- Create: `subject_teacher_pwa/src/lib/crypto.ts`
- Test: `subject_teacher_pwa/src/lib/crypto.test.ts`

**Interfaces:**
- Produces: `interface Envelope { checkonEnc: 1; alg: "A256GCM"; nonce: string; ct: string }`, `isEnvelope(raw: unknown): raw is Envelope`, `importSyncKey(bytes: Uint8Array): Promise<CryptoKey>`, `encryptEnvelope(name: string, data: unknown, key: CryptoKey, nonceOverride?: Uint8Array): Promise<Envelope>`, `decryptEnvelope(name: string, env: Envelope, key: CryptoKey): Promise<unknown>`, `parsePairingPayload(text: string): Uint8Array`, `PAIRING_PREFIX`

- [ ] **Step 1: 실패하는 테스트 작성** — `crypto.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import vector from "../../../tests/fixtures/e2e_crypto_vector.json";
import {
  decryptEnvelope,
  encryptEnvelope,
  importSyncKey,
  isEnvelope,
  parsePairingPayload,
  PAIRING_PREFIX,
} from "./crypto";

const b64decode = (text: string) => Uint8Array.from(atob(text), (c) => c.charCodeAt(0));

describe("crypto envelope (cross-language contract)", () => {
  it("encrypts to the exact Python-generated vector", async () => {
    const key = await importSyncKey(b64decode(vector.keyB64));
    const envelope = await encryptEnvelope(
      vector.aad,
      JSON.parse(vector.plaintextJson),
      key,
      b64decode(vector.nonceB64),
    );
    expect(envelope.checkonEnc).toBe(1);
    expect(envelope.alg).toBe("A256GCM");
    expect(envelope.nonce).toBe(vector.nonceB64);
    expect(envelope.ct).toBe(vector.ciphertextB64);
  });

  it("decrypts the Python-generated vector", async () => {
    const key = await importSyncKey(b64decode(vector.keyB64));
    const data = await decryptEnvelope(
      vector.aad,
      { checkonEnc: 1, alg: "A256GCM", nonce: vector.nonceB64, ct: vector.ciphertextB64 },
      key,
    );
    expect(data).toEqual(JSON.parse(vector.plaintextJson));
  });

  it("round-trips with a random nonce", async () => {
    const key = await importSyncKey(b64decode(vector.keyB64));
    const envelope = await encryptEnvelope("settings.json", { a: 1 }, key);
    expect(isEnvelope(envelope)).toBe(true);
    expect(await decryptEnvelope("settings.json", envelope, key)).toEqual({ a: 1 });
  });

  it("rejects a wrong file name (AAD mismatch)", async () => {
    const key = await importSyncKey(b64decode(vector.keyB64));
    const envelope = await encryptEnvelope("settings.json", { a: 1 }, key);
    await expect(decryptEnvelope("timetable.json", envelope, key)).rejects.toThrow();
  });

  it("isEnvelope rejects plain documents", () => {
    expect(isEnvelope({ schemaVersion: 1 })).toBe(false);
    expect(isEnvelope(null)).toBe(false);
  });
});

describe("parsePairingPayload", () => {
  it("decodes the desktop payload back to the key bytes", () => {
    const keyBytes = b64decode(vector.keyB64);
    const b64url = vector.keyB64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    expect(parsePairingPayload(`${PAIRING_PREFIX}${b64url}`)).toEqual(keyBytes);
  });

  it("rejects wrong prefix and wrong key length", () => {
    expect(() => parsePairingPayload("nope:abc")).toThrow();
    expect(() => parsePairingPayload(`${PAIRING_PREFIX}QUJD`)).toThrow();
  });
});
```

- [ ] **Step 2: 실패 확인** — `cd subject_teacher_pwa && npm test` → crypto.test 실패 (모듈 없음)
- [ ] **Step 3: 구현** — `crypto.ts`:

```typescript
// AES-256-GCM envelope crypto shared with the desktop app.
// Contract pinned by tests/fixtures/e2e_crypto_vector.json (repo root).

export const PAIRING_PREFIX = "checkon.sync.v1:";
const NONCE_SIZE = 12;
const KEY_SIZE = 32;

export interface Envelope {
  checkonEnc: 1;
  alg: "A256GCM";
  nonce: string;
  ct: string;
}

export function isEnvelope(raw: unknown): raw is Envelope {
  return (
    typeof raw === "object" &&
    raw !== null &&
    !Array.isArray(raw) &&
    (raw as { checkonEnc?: unknown }).checkonEnc === 1
  );
}

function b64encode(bytes: Uint8Array): string {
  let binary = "";
  bytes.forEach((b) => (binary += String.fromCharCode(b)));
  return btoa(binary);
}

function b64decode(text: string): Uint8Array {
  return Uint8Array.from(atob(text), (c) => c.charCodeAt(0));
}

export function importSyncKey(bytes: Uint8Array): Promise<CryptoKey> {
  return crypto.subtle.importKey("raw", bytes as BufferSource, "AES-GCM", false, [
    "encrypt",
    "decrypt",
  ]);
}

export async function encryptEnvelope(
  name: string,
  data: unknown,
  key: CryptoKey,
  nonceOverride?: Uint8Array,
): Promise<Envelope> {
  const nonce = nonceOverride ?? crypto.getRandomValues(new Uint8Array(NONCE_SIZE));
  const plaintext = new TextEncoder().encode(JSON.stringify(data));
  const ct = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: nonce as BufferSource, additionalData: new TextEncoder().encode(name) },
    key,
    plaintext,
  );
  return { checkonEnc: 1, alg: "A256GCM", nonce: b64encode(nonce), ct: b64encode(new Uint8Array(ct)) };
}

export async function decryptEnvelope(
  name: string,
  envelope: Envelope,
  key: CryptoKey,
): Promise<unknown> {
  if (envelope.alg !== "A256GCM") {
    throw new Error(`지원하지 않는 암호화 형식입니다: ${envelope.alg}`);
  }
  const plaintext = await crypto.subtle.decrypt(
    {
      name: "AES-GCM",
      iv: b64decode(envelope.nonce) as BufferSource,
      additionalData: new TextEncoder().encode(name),
    },
    key,
    b64decode(envelope.ct) as BufferSource,
  );
  return JSON.parse(new TextDecoder().decode(plaintext));
}

/** Parse `checkon.sync.v1:<base64url>` into the 32-byte key. Throws on malformed input. */
export function parsePairingPayload(text: string): Uint8Array {
  const trimmed = text.trim();
  if (!trimmed.startsWith(PAIRING_PREFIX)) {
    throw new Error("연결 코드 형식이 올바르지 않습니다.");
  }
  const b64 = trimmed.slice(PAIRING_PREFIX.length).replace(/-/g, "+").replace(/_/g, "/");
  const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
  const bytes = b64decode(padded);
  if (bytes.length !== KEY_SIZE) {
    throw new Error("연결 코드 길이가 올바르지 않습니다.");
  }
  return bytes;
}
```

tsconfig에 `resolveJsonModule`이 없으면 추가. JSON import 경로(`../../../tests/fixtures/...`)가 vite root 밖 문제를 일으키면 vitest 설정의 `server.fs.allow` 또는 픽스처를 `src/lib/__fixtures__/`로 복사(원본과 동일 내용 유지 주석 필수) — 구현 시 판단.

- [ ] **Step 4: 통과 확인** — `npm test`
- [ ] **Step 5: 커밋** — `git commit -m "feat(pwa): WebCrypto AES-GCM envelope matching desktop vector"`

### Task 6: PWA 키 저장소 (`keyStore.ts`, IndexedDB v2)

**Files:**
- Modify: `subject_teacher_pwa/src/lib/db.ts` (VERSION 1→2, `keys` 스토어, `openDb` export)
- Create: `subject_teacher_pwa/src/lib/keyStore.ts`
- Test: `subject_teacher_pwa/src/lib/keyStore.test.ts`

**Interfaces:**
- Produces: `saveSyncKey(bytes: Uint8Array): Promise<void>`, `loadSyncKey(): Promise<Uint8Array | null>`, `clearSyncKey(): Promise<void>`

- [ ] **Step 1: 실패하는 테스트 작성** — `keyStore.test.ts` (기존 `db.test.ts`의 fake-indexeddb 셋업 패턴을 그대로 따를 것):

```typescript
import "fake-indexeddb/auto";
import { beforeEach, describe, expect, it } from "vitest";
import { clearSyncKey, loadSyncKey, saveSyncKey } from "./keyStore";
import { loadQueue, persistQueue } from "./db";

describe("keyStore", () => {
  beforeEach(async () => {
    await clearSyncKey();
  });

  it("returns null when no key is stored", async () => {
    expect(await loadSyncKey()).toBeNull();
  });

  it("round-trips 32 key bytes", async () => {
    const key = new Uint8Array(Array.from({ length: 32 }, (_, i) => i));
    await saveSyncKey(key);
    expect(await loadSyncKey()).toEqual(key);
  });

  it("clearSyncKey removes the key", async () => {
    await saveSyncKey(new Uint8Array(32));
    await clearSyncKey();
    expect(await loadSyncKey()).toBeNull();
  });

  it("coexists with the save queue store (v2 upgrade keeps both)", async () => {
    await persistQueue([{ id: "q1" } as never]);
    await saveSyncKey(new Uint8Array(32));
    expect((await loadQueue()).length).toBe(1);
    expect(await loadSyncKey()).not.toBeNull();
  });
});
```

- [ ] **Step 2: 실패 확인** — `npm test`
- [ ] **Step 3: 구현** — `db.ts`: `VERSION`을 2로, `onupgradeneeded`에서 두 스토어 모두 보장:

```typescript
const VERSION = 2;
const KEYS_STORE = "keys";

request.onupgradeneeded = () => {
  const db = request.result;
  if (!db.objectStoreNames.contains(STORE)) {
    db.createObjectStore(STORE, { keyPath: "id" });
  }
  if (!db.objectStoreNames.contains(KEYS_STORE)) {
    db.createObjectStore(KEYS_STORE);
  }
};
```

`openDb`·`hasIndexedDB`·`KEYS_STORE`를 export. `keyStore.ts`:

```typescript
// IndexedDB persistence for the E2E sync key (never leaves the device).
import { hasIndexedDB, KEYS_STORE, openDb } from "./db";

const KEY_ID = "syncKey";

export async function saveSyncKey(bytes: Uint8Array): Promise<void> {
  if (!hasIndexedDB()) return;
  const db = await openDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(KEYS_STORE, "readwrite");
      tx.objectStore(KEYS_STORE).put(bytes, KEY_ID);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}

export async function loadSyncKey(): Promise<Uint8Array | null> {
  if (!hasIndexedDB()) return null;
  const db = await openDb();
  try {
    return await new Promise((resolve, reject) => {
      const request = db.transaction(KEYS_STORE, "readonly").objectStore(KEYS_STORE).get(KEY_ID);
      request.onsuccess = () => resolve(request.result ? new Uint8Array(request.result) : null);
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}

export async function clearSyncKey(): Promise<void> {
  if (!hasIndexedDB()) return;
  const db = await openDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(KEYS_STORE, "readwrite");
      tx.objectStore(KEYS_STORE).delete(KEY_ID);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
```

- [ ] **Step 4: 통과 확인** — `npm test` (기존 db.test.ts 회귀 포함)
- [ ] **Step 5: 커밋** — `git commit -m "feat(pwa): IndexedDB v2 sync-key store"`

### Task 7: PWA Drive 관문 통합 (`drive.ts`)

**Files:**
- Modify: `subject_teacher_pwa/src/lib/drive.ts`
- Test: `subject_teacher_pwa/src/lib/drive.crypto.test.ts` (신규)

**Interfaces:**
- Consumes: Task 5 `crypto.ts`, Task 6 `keyStore.ts`
- Produces: `class PairingRequiredError extends Error`, `resetSyncKeyCache(): void`; `readJson`/`writeJson` 시그니처 무변경(투명 암·복호화)

- [ ] **Step 1: 실패하는 테스트 작성** — `drive.crypto.test.ts` (fetch·auth 목킹):

```typescript
import "fake-indexeddb/auto";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { encryptEnvelope, importSyncKey, isEnvelope } from "./crypto";
import { clearSyncKey, saveSyncKey } from "./keyStore";
import { PairingRequiredError, readJson, resetSyncKeyCache, writeJson } from "./drive";

vi.mock("./auth", () => ({ getValidAccessToken: () => Promise.resolve("tok") }));

const KEY_BYTES = new Uint8Array(Array.from({ length: 32 }, (_, i) => i));

function mockFetchSequence(responses: Array<{ json: unknown }>) {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  let i = 0;
  vi.stubGlobal("fetch", (url: string, init?: RequestInit) => {
    calls.push({ url, init });
    const body = JSON.stringify(responses[Math.min(i++, responses.length - 1)].json);
    return Promise.resolve(new Response(body, { status: 200 }));
  });
  return calls;
}

describe("drive gateway encryption", () => {
  beforeEach(async () => {
    await clearSyncKey();
    resetSyncKeyCache();
  });
  afterEach(() => vi.unstubAllGlobals());

  it("readJson transparently decrypts an envelope when the key exists", async () => {
    await saveSyncKey(KEY_BYTES);
    resetSyncKeyCache();
    const envelope = await encryptEnvelope(
      "settings.json",
      { schemaVersion: 1 },
      await importSyncKey(KEY_BYTES),
    );
    mockFetchSequence([{ json: { files: [{ id: "f1" }] } }, { json: envelope }]);
    const file = await readJson("settings.json");
    expect(file?.data).toEqual({ schemaVersion: 1 });
  });

  it("readJson throws PairingRequiredError on envelope without key", async () => {
    const envelope = await encryptEnvelope(
      "settings.json",
      { schemaVersion: 1 },
      await importSyncKey(KEY_BYTES),
    );
    mockFetchSequence([{ json: { files: [{ id: "f1" }] } }, { json: envelope }]);
    await expect(readJson("settings.json")).rejects.toBeInstanceOf(PairingRequiredError);
  });

  it("readJson passes legacy plaintext through", async () => {
    mockFetchSequence([{ json: { files: [{ id: "f1" }] } }, { json: { schemaVersion: 1 } }]);
    const file = await readJson("settings.json");
    expect(file?.data).toEqual({ schemaVersion: 1 });
  });

  it("writeJson uploads an envelope when the key exists", async () => {
    await saveSyncKey(KEY_BYTES);
    resetSyncKeyCache();
    const calls = mockFetchSequence([{ json: { id: "f1" } }]);
    await writeJson("settings.json", { schemaVersion: 1 }, "f1");
    const uploaded = JSON.parse(calls[0].init?.body as string);
    expect(isEnvelope(uploaded)).toBe(true);
  });

  it("writeJson uploads plaintext without a key", async () => {
    const calls = mockFetchSequence([{ json: { id: "f1" } }]);
    await writeJson("settings.json", { schemaVersion: 1 }, "f1");
    expect(JSON.parse(calls[0].init?.body as string)).toEqual({ schemaVersion: 1 });
  });
});
```

- [ ] **Step 2: 실패 확인** — `npm test`
- [ ] **Step 3: 구현** — `drive.ts`에 추가:

```typescript
import { decryptEnvelope, encryptEnvelope, importSyncKey, isEnvelope } from "./crypto";
import { loadSyncKey } from "./keyStore";

export class PairingRequiredError extends Error {
  constructor() {
    super("데스크톱과 연결(페어링)이 필요합니다.");
    this.name = "PairingRequiredError";
  }
}

let cachedKey: CryptoKey | null = null;
let cachedKeyLoaded = false;

async function getSyncKey(): Promise<CryptoKey | null> {
  if (!cachedKeyLoaded) {
    const bytes = await loadSyncKey();
    cachedKey = bytes ? await importSyncKey(bytes) : null;
    cachedKeyLoaded = true;
  }
  return cachedKey;
}

/** Call after pairing or 연결 해제 so the next request re-reads the stored key. */
export function resetSyncKeyCache(): void {
  cachedKey = null;
  cachedKeyLoaded = false;
}
```

`readJson`: `alt=media` 응답 파싱 후,

```typescript
let data = (await response.json()) as unknown;
if (isEnvelope(data)) {
  const key = await getSyncKey();
  if (!key) throw new PairingRequiredError();
  data = await decryptEnvelope(name, data, key);
}
return { id, data: data as T };
```

`writeJson` 첫머리:

```typescript
const key = await getSyncKey();
const payload = key ? await encryptEnvelope(name, data, key) : data;
const body = JSON.stringify(payload);
```

- [ ] **Step 4: 통과 + PWA 전체 회귀** — `npm test`
- [ ] **Step 5: 커밋** — `git commit -m "feat(pwa): transparent envelope encryption at the Drive gateway"`

### Task 8: PWA 페어링 화면 + Root 게이팅

**Files:**
- Create: `subject_teacher_pwa/src/Pairing.tsx`
- Modify: `subject_teacher_pwa/src/Root.tsx` (phase `"pairing"` 추가)
- Modify: `subject_teacher_pwa/package.json` (`jsqr` 의존성)
- Test: `subject_teacher_pwa/src/Pairing.test.tsx`

**Interfaces:**
- Consumes: `parsePairingPayload`(Task 5), `saveSyncKey`(Task 6), `resetSyncKeyCache`·`PairingRequiredError`(Task 7)
- Produces: `<Pairing onPaired={() => void} />` — 수동 입력 + (지원 시) 카메라 QR 스캔

- [ ] **Step 1: `npm install jsqr`** (subject_teacher_pwa에서)
- [ ] **Step 2: 실패하는 테스트 작성** — `Pairing.test.tsx` (수동 입력 경로만 — 카메라는 jsdom 불가):

```tsx
import "fake-indexeddb/auto";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Pairing from "./Pairing";
import { loadSyncKey, clearSyncKey } from "./lib/keyStore";
import { PAIRING_PREFIX } from "./lib/crypto";

const VALID = `${PAIRING_PREFIX}AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8`;

describe("Pairing", () => {
  beforeEach(async () => {
    await clearSyncKey();
  });

  it("saves the key and calls onPaired for a valid code", async () => {
    const onPaired = vi.fn();
    render(<Pairing onPaired={onPaired} />);
    await userEvent.type(screen.getByLabelText(/연결 코드/), VALID);
    await userEvent.click(screen.getByRole("button", { name: /연결/ }));
    expect(onPaired).toHaveBeenCalled();
    expect(await loadSyncKey()).not.toBeNull();
  });

  it("shows an error for a malformed code and keeps the key empty", async () => {
    const onPaired = vi.fn();
    render(<Pairing onPaired={onPaired} />);
    await userEvent.type(screen.getByLabelText(/연결 코드/), "checkon.sync.v1:짧음");
    await userEvent.click(screen.getByRole("button", { name: /연결/ }));
    expect(await screen.findByText(/올바르지 않습니다/)).toBeInTheDocument();
    expect(onPaired).not.toHaveBeenCalled();
    expect(await loadSyncKey()).toBeNull();
  });
});
```

- [ ] **Step 3: 실패 확인** — `npm test`
- [ ] **Step 4: 구현** — `Pairing.tsx` (수동 입력 우선, 카메라는 `BarcodeDetector` → jsQR 폴백; 지원·권한 실패 시 조용히 수동 입력만 노출):

```tsx
import { useEffect, useRef, useState } from "react";
import jsQR from "jsqr";
import { parsePairingPayload } from "./lib/crypto";
import { saveSyncKey } from "./lib/keyStore";
import { resetSyncKeyCache } from "./lib/drive";

export default function Pairing({ onPaired }: { onPaired: () => void }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [scanning, setScanning] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const stopRef = useRef<() => void>(() => {});

  const accept = async (text: string) => {
    try {
      const key = parsePairingPayload(text);
      await saveSyncKey(key);
      resetSyncKeyCache();
      stopRef.current();
      onPaired();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "연결 코드 형식이 올바르지 않습니다.");
    }
  };

  const startScan = async () => {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      setScanning(true);
      const video = videoRef.current!;
      video.srcObject = stream;
      await video.play();
      const canvas = document.createElement("canvas");
      let active = true;
      stopRef.current = () => {
        active = false;
        stream.getTracks().forEach((track) => track.stop());
        setScanning(false);
      };
      const detector = "BarcodeDetector" in window
        ? new (window as never as { BarcodeDetector: new (o: { formats: string[] }) => { detect(v: HTMLVideoElement): Promise<Array<{ rawValue: string }>> } }).BarcodeDetector({ formats: ["qr_code"] })
        : null;
      const tick = async () => {
        if (!active) return;
        let text: string | null = null;
        if (detector) {
          const found = await detector.detect(video).catch(() => []);
          text = found[0]?.rawValue ?? null;
        } else if (video.videoWidth > 0) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const ctx = canvas.getContext("2d")!;
          ctx.drawImage(video, 0, 0);
          const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
          text = jsQR(image.data, image.width, image.height)?.data ?? null;
        }
        if (text) {
          await accept(text);
          return;
        }
        requestAnimationFrame(() => void tick());
      };
      void tick();
    } catch {
      setScanning(false);
      setError("카메라를 열 수 없습니다. 아래에 연결 코드를 직접 입력해 주세요.");
    }
  };

  useEffect(() => () => stopRef.current(), []);

  return (
    <div className="pairing">
      <h1>데스크톱과 연결</h1>
      <p>
        데이터가 암호화되어 안전하게 보호됩니다. 데스크톱 앱의 <b>설정 → 모바일 연결 암호화</b>에
        표시된 QR코드를 스캔하거나, 연결 코드를 입력해 주세요.
      </p>
      {scanning ? (
        <video ref={videoRef} playsInline muted style={{ width: "100%", borderRadius: 12 }} />
      ) : (
        <button type="button" onClick={() => void startScan()}>QR코드 스캔</button>
      )}
      <label htmlFor="pairing-code">연결 코드</label>
      <input
        id="pairing-code"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="checkon.sync.v1:..."
        autoComplete="off"
      />
      <button type="button" onClick={() => void accept(code)}>연결</button>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
```

`Root.tsx`: `Phase`에 `"pairing"` 추가. 초기 로드·`signIn`의 `loadAll` 실패 catch에서:

```typescript
if (cause instanceof PairingRequiredError) { setPhase("pairing"); return; }
```

렌더 분기 추가:

```tsx
if (phase === "pairing") {
  return (
    <Pairing
      onPaired={() => {
        setPhase("loading");
        loadAll(today.slice(0, 7))
          .then((loaded) => { setData(loaded); setPhase("ready"); })
          .catch((cause) => { setPhase("signedOut"); setError(String(cause)); });
      }}
    />
  );
}
```

주의: 초기 silent 로그인 catch가 현재 모든 실패를 `signedOut`으로 보내므로, `PairingRequiredError`를 구분해 `pairing`으로 보내도록 catch 로직 수정. 스타일은 기존 `styles.css` 클래스 재사용(구현 시 확인).

- [ ] **Step 5: 통과 + 전체 회귀** — `npm test`, `npm run build` (tsc 포함)
- [ ] **Step 6: 커밋** — `git commit -m "feat(pwa): pairing screen (QR scan + manual code) and gating"`

### Task 9: 데스크톱 UI — 암호화 활성화 카드 + QR 표시

**Files:**
- Modify: `subject_teacher/neis_attendance/package.json` (`qrcode`, `@types/qrcode`)
- Modify: `subject_teacher/neis_attendance/src/bridge.ts` (`DesktopApi`에 3개 메서드)
- Modify: `subject_teacher/neis_attendance/src/mock-api.ts` (모의 구현)
- Modify: `subject_teacher/neis_attendance/src/setup-view.tsx` (BasicsView에 카드 추가)
- Test: `subject_teacher/neis_attendance/src/components.test.tsx` 또는 신규 `sync-card.test.tsx`

**Interfaces:**
- Consumes: Task 4의 브리지 메서드 3종 (JSON 문자열 반환)
- Produces: `SyncEncryptionCard({ api })` — 상태 조회 → 활성화 버튼 → QR(dataURL `<img>`) + 복구 코드 안내

- [ ] **Step 1: `npm install qrcode && npm install -D @types/qrcode`** (subject_teacher/neis_attendance에서)
- [ ] **Step 2: 실패하는 테스트 작성** — 목 API로 카드 렌더·활성화 흐름:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SyncEncryptionCard } from "./setup-view";

const api = {
  get_sync_encryption_status: vi.fn().mockResolvedValue(JSON.stringify({ enabled: false })),
  enable_sync_encryption: vi.fn().mockResolvedValue(
    JSON.stringify({ payload: "checkon.sync.v1:AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8", migrated: 2, created: true }),
  ),
  get_pairing_payload: vi.fn().mockResolvedValue(
    JSON.stringify({ payload: "checkon.sync.v1:AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8" }),
  ),
};

describe("SyncEncryptionCard", () => {
  it("enables encryption and shows the QR + recovery code", async () => {
    render(<SyncEncryptionCard api={api as never} />);
    await userEvent.click(await screen.findByRole("button", { name: /암호화 켜기/ }));
    expect(api.enable_sync_encryption).toHaveBeenCalled();
    expect(await screen.findByAltText(/연결 QR/)).toBeInTheDocument();
    expect(screen.getByText(/화면 공유/)).toBeInTheDocument();
  });
});
```

(테스트 파일 위치·셋업은 기존 `components.test.tsx` 패턴을 따른다. jsdom에서 `qrcode`의 `toDataURL`은 동작함 — canvas 미지원 시 `toDataURL(text)` 문자열 API 사용.)

- [ ] **Step 3: 실패 확인** — `cd subject_teacher/neis_attendance && npm test`
- [ ] **Step 4: 구현** — `bridge.ts` `DesktopApi`에:

```typescript
get_sync_encryption_status(): Promise<string>;
enable_sync_encryption(): Promise<string>;
get_pairing_payload(): Promise<string>;
```

`mock-api.ts`에 모의 3종(상태 토글 시뮬레이션). `setup-view.tsx`에 `SyncEncryptionCard` export 추가 후 `BasicsView` 하단에 배치:

```tsx
import QRCode from "qrcode";

export const SyncEncryptionCard = ({ api }: { api: DesktopApi }) => {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [payload, setPayload] = useState("");
  const [qrUrl, setQrUrl] = useState("");
  const [migrated, setMigrated] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get_sync_encryption_status().then((raw) => setEnabled(JSON.parse(raw).enabled));
  }, [api]);

  useEffect(() => {
    if (!payload) return;
    QRCode.toDataURL(payload, { margin: 1, width: 220 }).then(setQrUrl);
    return () => setQrUrl("");
  }, [payload]);

  const enable = async () => {
    setBusy(true);
    try {
      const result = JSON.parse(await api.enable_sync_encryption());
      setPayload(result.payload);
      setMigrated(result.migrated);
      setEnabled(true);
    } finally {
      setBusy(false);
    }
  };

  const showQr = async () => {
    const result = JSON.parse(await api.get_pairing_payload());
    if (result.payload) setPayload(result.payload);
  };

  return (
    <div className="card">
      <div className="section-head">모바일 연결 암호화</div>
      <p>켜면 클라우드에 저장되는 출결 데이터가 암호화되어, 이 QR로 연결한 내 기기에서만 읽을 수 있습니다.</p>
      {enabled === false && (
        <button className="tb-btn primary" disabled={busy} onClick={enable}>암호화 켜기</button>
      )}
      {enabled === true && !payload && (
        <button className="tb-btn" onClick={showQr}>휴대폰 연결 QR 보기</button>
      )}
      {payload && (
        <div>
          {qrUrl && <img src={qrUrl} alt="휴대폰 연결 QR코드" width={220} height={220} />}
          <p>휴대폰 앱에서 <b>QR코드 스캔</b>을 눌러 촬영하세요. 카메라가 안 되면 아래 연결 코드를 입력해도 됩니다.</p>
          <code style={{ wordBreak: "break-all" }}>{payload}</code>
          <p>⚠ 이 QR·코드는 비밀번호와 같습니다. 화면 공유 중에는 열지 말고, 인쇄해 안전한 곳에 보관하면 복구 코드로 쓸 수 있습니다.</p>
          {migrated !== null && <p>기존 데이터 {migrated}건을 암호화했습니다.</p>}
          <button className="tb-btn" onClick={() => { setPayload(""); setQrUrl(""); }}>닫기</button>
        </div>
      )}
    </div>
  );
};
```

wiring: `app.tsx`가 BasicsView에 내려주는 방식대로 `api`(브리지 객체)를 전달 — 구현 시 `app.tsx`의 기존 prop 패턴을 읽고 동일하게 연결. 페이로드는 컴포넌트 state 외 어디에도 저장·로그하지 않는다.

- [ ] **Step 5: 통과 + 빌드** — `npm test && npm run build` (dist가 데스크톱에 번들되므로 빌드 필수)
- [ ] **Step 6: 커밋** — `git commit -m "feat(desktop): sync-encryption card with pairing QR"`

### Task 10: 처리방침 문구 갱신 + 전체 회귀

**Files:**
- Modify: `subject_teacher_pwa/src/PrivacyPolicy.tsx`
- Modify: `subject_teacher/neis_attendance/src/privacy-policy.tsx`

- [ ] **Step 1:** 두 처리방침의 클라우드 저장 항목에 문구 추가 (기존 문체에 맞춰 배치, 참고용 초안·변호사 검토 권장 표기는 유지):

> 암호화 기능을 켜면 클라우드(Google Drive)에는 AES-256으로 암호화된 데이터만 저장되며, 복호화 키는 이용자의 기기(데스크톱·휴대폰)에만 보관되어 Google을 포함한 제3자는 내용을 열람할 수 없습니다.

- [ ] **Step 2: 3개 스위트 전체 회귀** —
  - `py -3.14 -m pytest tests/ -q` → all passed
  - `cd subject_teacher_pwa && npm test && npm run build`
  - `cd subject_teacher/neis_attendance && npm test && npm run build`
- [ ] **Step 3: 커밋** — `git commit -m "docs(privacy): E2E encryption clause in both privacy policies"`
- [ ] **Step 4: 배포 순서 리마인드** — 푸시하면 Vercel이 PWA(이중 읽기)를 먼저 배포하므로 스펙 §6.3 순서 자동 충족. 데스크톱은 사용자가 "암호화 켜기"를 누른 뒤부터 암호문 기록.

## Self-Review 결과

- 스펙 커버리지: §5 봉투 계약→Task 1/5, §6.1→Task 1~4, §6.2→Task 5~8, 데스크톱 UI→Task 9, §6.3 배포 순서→Task 10 Step 4, 처리방침→Task 10. 키 회전·평문 쓰기 제거는 스펙상 비목표/후속 결정 — 계획 제외 확인.
- 타입 일치: `read_json_raw`(Py)/`resetSyncKeyCache`(TS)/`PAIRING_PREFIX` 등 태스크 간 참조 명칭 대조 완료.
- 플레이스홀더: "구현 시 판단/확인" 표기는 기존 파일의 실측이 필요한 wiring 지점 3곳(JSON import 경로, Api 생성자, app.tsx prop 패턴)에 한정 — 대체 코드 경로 명시함.
