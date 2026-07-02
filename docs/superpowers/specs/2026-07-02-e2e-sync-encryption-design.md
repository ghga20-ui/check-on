# 동기화 데이터 종단간 암호화(E2E) 설계 — 클라우드는 암호문만 본다

- 작성일: 2026-07-02
- 대상: `subject_teacher/` (데스크톱), `subject_teacher_pwa/` (모바일 PWA)
- 선행 설계: `2026-06-21-caseC-privacy-design.md` (이름 로컬화 — 완료됨)

## 1. 배경 / 문제

Case C 전환으로 클라우드(Google Drive appDataFolder)에는 학번 기반 가명정보만
남았지만, 여전히 **구글(해외 제3자)이 학번·출결 내용을 평문으로 읽을 수 있는
상태**다. LAN 직결·WebRTC·블루투스 등 "클라우드 무경유" 방안은 학교망 분리
(업무망/무선망)와 PWA 브라우저 제약으로 성립하지 않음이 검토됐다(2026-07-02 보고).

결정: **전송 채널은 Drive를 유지하되, 내용을 기기에서만 복호화 가능한 암호문으로
만든다.** 복호화 키는 선생님의 데스크톱·폰에만 존재하며 어떤 경로로도 클라우드에
올라가지 않는다. 구글은 "내용을 알 수 없는 우편배달부"가 된다.

## 2. 목표 / 비목표

**목표**
- Drive에 저장되는 모든 JSON(`settings.json`, `timetable.json`, `students.json`,
  `attendance-*.json`)을 AES-256-GCM 암호문으로 전환.
- 키 페어링: 데스크톱에서 생성한 키를 QR코드(+수동 입력 코드)로 폰에 1회 전달.
  키는 기기 간 직접 전달만 존재 — 네트워크·클라우드 미경유.
- 기존 평문 파일의 1회성 암호화 마이그레이션 (데스크톱이 수행).
- 처리방침 갱신 근거 확보: "클라우드에는 암호화된 데이터만 저장되며 복호화 키는
  이용자 기기에만 존재합니다."

**비목표 (의도적으로 안 함)**
- 키 회전(rotation)·다중 키 — v1은 단일 대칭키. 유출 의심 시 "동기화 초기화"로 대체.
- 파일명 은닉 — `attendance-2026-07.json` 같은 이름은 월(月) 이상을 드러내지 않아 유지.
- 클라우드 키 백업 — 목적 자체와 모순. 복구는 복구 코드(인쇄/보관)로 해결.
- Drive 외 전송 채널 변경 — 채널은 그대로, 내용만 암호화.

## 3. 핵심 결정

| 항목 | 결정 |
|---|---|
| 암호 알고리즘 | AES-256-GCM, 파일 단위 암호화, 쓰기마다 96-bit 랜덤 nonce |
| AAD | 파일명 문자열(UTF-8) — 암호문을 다른 파일로 바꿔치기하는 조작 차단 |
| 봉투(envelope) 형식 | 평문 JSON 대신 `{"checkonEnc": 1, "alg": "A256GCM", "nonce": "<b64>", "ct": "<b64>"}` 저장 |
| 키 생성 주체 | **데스크톱** (32바이트 CSPRNG). 폰은 항상 수신자 |
| 키 전달 | 데스크톱 화면 QR `checkon.sync.v1:<base64url(key)>` + 동일 문자열 수동 입력 폴백 |
| 키 보관 (데스크톱) | `%LOCALAPPDATA%\NeisSubject\sync_key.bin`, DPAPI (`token_store` 재사용) |
| 키 보관 (폰) | IndexedDB `neis-subject` DB에 raw 키 바이트 저장 (VERSION 1→2, `keys` 스토어 추가) |
| 하위 호환 읽기 | `checkonEnc` 필드 있으면 복호화, 없으면 레거시 평문으로 수용 (마이그레이션 유예기) |
| 쓰기 | 키가 있으면 항상 암호문. 키가 없으면(페어링 전) 기존 평문 동작 그대로 — 기능은 옵트인 |
| 마이그레이션 | 데스크톱 페어링 완료 직후 1회: `list_files()` → 평문 파일만 읽어 암호문으로 재기록 |
| 복구 | 페어링 화면에서 "복구 코드 인쇄/저장" 안내. 양쪽 키 소실 시 "동기화 초기화"(클라우드 파일 삭제 후 재생성) |

폰 키 저장을 non-extractable `CryptoKey`가 아닌 raw 바이트로 하는 이유: 테스트
환경(jsdom/fake-indexeddb) 호환과 코드 단순성. 위협 모델상 IndexedDB 접근이
가능한 공격자(기기 탈취·XSS)는 어차피 복호화된 화면 데이터에 접근 가능하므로
non-extractable이 주는 실익이 작다. PWA는 서드파티 스크립트가 GIS 하나뿐이다.

## 4. 데이터 흐름 (변경 후)

```
[데스크톱]                            [Google Drive]                 [모바일 PWA]
 sync_key.bin (DPAPI) ──QR 1회──────────────────────────────────►  IndexedDB keys
        │                                                               │
        ▼                                                               ▼
 암호화 ──────────►  {"checkonEnc":1, nonce, ct}  ◄────────────── 암호화
 복호화 ◄──────────  (구글은 내용 판독 불가)      ──────────────►  복호화
```

키는 QR 스캔 순간에만 화면↔카메라로 이동한다. 이후 모든 동기화는 암호문.

## 5. 암호 봉투 상세 (양측 공통 계약)

```json
{
  "checkonEnc": 1,
  "alg": "A256GCM",
  "nonce": "<base64, 12바이트>",
  "ct": "<base64, ciphertext||tag>"
}
```

- 평문 = 기존 파일 JSON의 UTF-8 직렬화. 봉투 바깥은 여전히 `application/json`이라
  Drive 계층·mimetype·파일명 로직은 무변경.
- AAD = 파일명 (예: `attendance-2026-07.json`). 파일명이 바뀌면 복호화 실패해야 정상.
- GCM 태그(16바이트)는 `ct` 끝에 이어붙임 — WebCrypto 기본 출력과 동일, Python
  `cryptography.AESGCM`도 같은 형식.
- **교차 언어 테스트 벡터를 저장소에 커밋**한다
  (`tests/fixtures/e2e_crypto_vector.json`: key/nonce/aad/평문/기대 암호문).
  Python·TS 양쪽 테스트가 같은 벡터로 암·복호화를 단언해 상호운용을 보증.

## 6. 코드 변경

### 6.1 데스크톱 (`subject_teacher/`)

- `paths.py`: `get_sync_key_path()` → `get_app_data_dir() / "sync_key.bin"`
- 신규 `drive/crypto.py`:
  - `generate_sync_key() -> bytes` (32바이트, `secrets.token_bytes`)
  - `save_sync_key(key)` / `load_sync_key() -> bytes | None` (token_store DPAPI 재사용)
  - `encrypt_envelope(name, payload: dict, key) -> dict` / `decrypt_envelope(name, envelope, key) -> dict`
  - `is_envelope(raw: dict) -> bool` (`checkonEnc` 검사)
  - 의존성: `cryptography` (requirements + PyInstaller spec hiddenimports 확인)
- `drive/client.py`: `read_json` 반환 직전 — 봉투면 복호화, 평문이면 그대로.
  `upsert_json` 진입 직후 — 키가 로드돼 있으면 봉투로 감싸 저장.
  키는 클라이언트 생성 시 1회 로드(`DriveAppDataClient(..., sync_key=...)`) —
  `build_store()`에서 주입. 상위(`store.py`, `api.py`)는 무변경.
- `gui/api.py` 신규 메서드:
  - `get_sync_encryption_status()` → `{enabled, migratedAt}`
  - `enable_sync_encryption()` → 키 생성·저장 + 마이그레이션 실행 + QR 페이로드 반환
  - `get_pairing_payload()` → `checkon.sync.v1:<base64url>` 문자열 (로그 금지)
- 마이그레이션(`drive/crypto.py` 또는 `state.py`): `list_files()` → 각 파일
  `read_json`(평문 수용) → `upsert_json`(암호문). 멱등: 이미 봉투인 파일은 건너뜀.
- 데스크톱 UI(`neis_attendance/` React): 설정에 "모바일 연결 암호화" 카드 —
  활성화 버튼 → QR 표시(`qrcode` npm, 로컬 렌더) + 수동 코드 + "복구 코드 인쇄"
  안내. QR 표시 중 화면공유 주의 문구 1줄.

### 6.2 모바일 PWA (`subject_teacher_pwa/`)

- 신규 `lib/crypto.ts`: WebCrypto AES-GCM — `encryptEnvelope` / `decryptEnvelope`
  / `isEnvelope` (봉투 계약은 §5와 동일)
- 신규 `lib/keyStore.ts`: `db.ts`의 DB VERSION 1→2, `keys` 오브젝트 스토어 추가.
  `saveSyncKey(bytes)` / `loadSyncKey()` / `clearSyncKey()`
- `lib/drive.ts`: `readJson` — 봉투면 복호화(키 없으면 `PairingRequiredError` throw),
  평문이면 그대로. `writeJson` — 키가 있으면 암호화. 상위(`driveData.ts`) 무변경.
- 페어링 화면 `Pairing.tsx`:
  - 카메라 스캔: `BarcodeDetector` 지원 시 사용, 미지원(iOS Safari)이면 `jsQR` +
    `getUserMedia` 폴백
  - 수동 입력: `checkon.sync.v1:...` 문자열 붙여넣기/타이핑 — 카메라 권한 없이도 성립
  - 검증: 접두사·키 길이(32바이트) 확인 후 저장, 즉시 `loadAll` 재시도
- 라우팅(`Root.tsx`/`App.tsx`): `PairingRequiredError` 감지 시 페어링 화면으로 유도.
  설정 탭에 "연결 해제(키 삭제)" 추가.

### 6.3 배포 순서 (호환성 게이트)

1. **PWA 먼저 배포**: 이중 읽기(평문+봉투) + 페어링 화면. 이 시점엔 클라우드가
   전부 평문이라 기존 사용자 무영향.
2. **데스크톱 릴리즈**: 암호화 활성화 UI + 마이그레이션. 사용자가 활성화한
   순간부터 그 계정의 클라우드는 암호문 — 이미 배포된 PWA가 읽을 수 있음.
3. 유예기 이후(전 사용자 전환 확인) 평문 쓰기 경로 제거는 후속 결정.

순서를 지키지 않으면: 구 PWA가 봉투 JSON을 zod 스키마로 파싱하다 실패한다.
(치명 아님 — 에러 화면 후 새 버전 새로고침으로 해결되지만, 순서 준수가 깔끔.)

## 7. 테스트 (TDD)

- **교차 벡터**: `tests/fixtures/e2e_crypto_vector.json` — Python·TS 양쪽에서
  같은 key/nonce/aad로 같은 암호문 생성·복호화 단언 (상호운용의 핵심 증명)
- Python `tests/test_drive_crypto.py`: 라운드트립, 변조 감지(ct 1바이트 플립 →
  예외), AAD 불일치(파일명 변경 → 예외), `is_envelope` 판별, 키 저장 라운드트립
- Python `tests/test_drive_client.py` 추가: 키 주입 시 upsert가 봉투 저장,
  read가 봉투 복호화 + 레거시 평문 통과, 마이그레이션 멱등(봉투 파일 스킵)
- TS `crypto.test.ts` / `keyStore.test.ts`: 라운드트립, 벡터 일치, VERSION 2
  업그레이드 후 기존 saveQueue 보존
- TS `drive.test.ts`: 키 없음 + 봉투 → `PairingRequiredError`, 키 있음 → 투명 복호화
- 페어링 페이로드: 접두사/길이 검증, 잘못된 문자열 거부

## 8. 위험 / 캐비엇

- **키 소실**: DPAPI는 Windows 프로필 종속, 폰은 브라우저 데이터 삭제에 취약.
  양쪽 동시 소실 시 클라우드 데이터 복구 불가 → "동기화 초기화"로 재시작.
  출결 원본은 NEIS가 진실원본이므로 손실 범위는 앱 내 기록뿐. 복구 코드 인쇄
  안내로 확률을 낮춘다.
- **QR 노출**: QR에는 키 원문이 들어간다. 표시 중 화면공유·촬영 주의 문구 필수,
  페이로드는 로그·상태 저장 금지, 표시 종료 시 즉시 폐기.
- **nonce 재사용**: 랜덤 96-bit는 이 쓰기 빈도(하루 수십 회)에서 충돌 확률 무시 가능.
- **iOS 카메라**: PWA 홈화면 설치 모드에서 getUserMedia 제약 사례 있음 — 수동
  입력 폴백이 있어 페어링 자체는 항상 성립.
- 법적 효과는 "구글이 내용을 알 수 없음"이지 개인정보 처리 자체의 소멸이 아님 —
  처리방침·고지 문서는 유지하되 안전조치 항목을 강화 서술 (변호사 검토 권장 유지).

## 9. 구현 순서

1. **공통 계약**: 교차 테스트 벡터 픽스처 생성 → Python `drive/crypto.py` (TDD)
   → TS `lib/crypto.ts` (TDD, 벡터 일치 확인)
2. **PWA 트랙**: `keyStore.ts` → `drive.ts` 이중 읽기 → `Pairing.tsx` → 배포
3. **데스크톱 트랙**: `paths.py`/키 저장 → `client.py` 봉투 통합 → 마이그레이션
   → `gui/api.py` + 설정 UI QR
4. **문서**: 처리방침 "암호화 저장" 문구 갱신 (데스크톱 사이드바 + PWA 설정)
