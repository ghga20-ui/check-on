# AGENTS.md

This file provides guidance to Codex and other coding agents working in this repository.
For the subject-teacher backend, also read the tighter rules in `subject_teacher/AGENTS.md`.

## 프로젝트 개요

**체크온(CheckOn)**: 교과담당(과목) 교사가 매 수업 직후 휴대폰으로 출결을 체크하고, PC에서 NEIS에 자동 입력하는 출결 도구.

세 표면으로 구성됩니다.

1. **모바일 PWA** (`subject_teacher_pwa/`) — 수업 직후 출결 체크. Vite + React + TS, Vercel 배포.
2. **데스크톱 앱** (`subject_teacher/`) — 출결 검토 + NEIS 동기화 실행. pywebview + Vite/React(`subject_teacher/neis_attendance/`) + Python.
3. **공유 백엔드** — Google Drive `appDataFolder`. 클라우드 출결 데이터는 종단간(E2E) 암호화.

제품명은 항상 **체크온/CheckOn**. 사용자에게 보이는 이름에 NEIS/나이스를 넣지 않음.

## 실행 및 빌드 명령

레포 루트에서 실행. 이 환경의 Python은 `py -3.14`.

```bash
py -3.14 -m subject_teacher.main          # 데스크톱 앱 실행
pip install -r requirements.txt           # Python 의존성
py -3.14 -m pytest tests/ -q              # Python 테스트
pyinstaller NEIS_Subject_Teacher.spec     # 데스크톱 EXE 빌드
```

프런트엔드는 각 폴더에서 `npm install` 후 `npm test`(vitest):
`subject_teacher/neis_attendance/`(데스크톱 UI), `subject_teacher_pwa/`(PWA).

## 디렉터리 구조

| 경로 | 역할 |
|---|---|
| `subject_teacher/` | 데스크톱 Python 백엔드 (앱 서비스·Drive 저장소·NEIS 자동화·GUI 브리지). |
| `subject_teacher/neis_attendance/` | 데스크톱 UI (Vite/React). 빌드된 `dist/`만 EXE에 포함. |
| `subject_teacher_pwa/` | 모바일 PWA (별도 Vercel 배포). |
| `subject_teacher/drive/crypto.py` | E2E 암호화(AES-256-GCM). TS 대응은 `subject_teacher_pwa/src/lib/crypto.ts`. |
| `tests/` | Python 테스트. |
| `config.py`, `regions.py`, `utils.py`, `logger_config.py` | **공유 루트 모듈** — `subject_teacher`가 재사용. 옮기거나 지우지 말 것. |

## 변경 가이드

- `subject_teacher/*`를 먼저 수정. 공유 루트 모듈은 정말 필요할 때만 손댐.
- Drive에 닿는 GUI 브리지 메서드는 `gui/api.py`의 `SERIALIZED_API_METHODS`에 넣어 직렬화(httplib2 비-thread-safe).
- 장시간 Drive/NEIS 작업은 백그라운드 스레드에서 실행해 GUI 블로킹 방지.
- Selenium 셀렉터/클릭 흐름을 바꿀 때는 실패 진단(폴백·덤프)을 유지. NEIS 마크업은 취약함.
- Drive 스키마 형태가 바뀌면 `drive/migrations.py`와 `tests/test_drive_*`를 함께 갱신.

## 보안 규칙 (필수)

- 학생 **이름은 절대 클라우드에 올리지 않음**. Drive 로스터는 학번만.
- NEIS 비밀번호·Google 토큰을 Drive JSON에 저장 금지. 로컬 비밀은 `%LOCALAPPDATA%/NeisSubject`에만.
- 페어링 키/QR payload는 로그·커밋·클라우드에 남기지 않음.
- `client_secrets.json`, `token.bin`, `password.bin`, `tmp_*.json` 커밋 금지.

## 검증

가장 관련 있는 테스트부터 좁게 실행하고, 경계를 넘는 변경일 때만 넓힘.

- 상태/서비스: `pytest tests/test_subject_teacher_state.py tests/test_app_service.py tests/test_neis_runner.py`
- 셀렉터: `pytest tests/test_subject_commands_selectors.py`
- Drive/암호화/인증: `pytest tests/test_drive_client.py tests/test_drive_crypto.py tests/test_drive_store.py tests/test_drive_schemas.py tests/test_drive_migrations.py tests/test_sync_encryption_api.py tests/test_google_oauth.py tests/test_token_store.py`
