# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

**체크온(CheckOn)**: 교과담당(과목) 교사가 매 수업 직후 휴대폰으로 출결을 체크하고, PC에서 그 결과를 NEIS(교육행정정보시스템)에 자동 입력하는 출결 도구.

세 개의 표면(surface)으로 구성됩니다.

1. **모바일 PWA** (`subject_teacher_pwa/`): 교사가 수업 직후 즉시 출결 체크. Vite + React + TypeScript, Vercel 배포.
2. **데스크톱 앱** (`subject_teacher/`): PC에서 출결 현황을 검토하고 NEIS 동기화를 실행. pywebview + Vite/React 프런트엔드(`subject_teacher/neis_attendance/`) + Python 백엔드.
3. **공유 백엔드**: Google Drive `appDataFolder`. 모바일과 데스크톱이 `settings.json`, `timetable.json`, `students.json`, `attendance-YYYY-MM.json`을 공유. 클라우드에 올라가는 출결 데이터는 **종단간(E2E) 암호화**되어 구글도 내용을 읽을 수 없음.

> 제품명은 항상 **체크온/CheckOn**. 사용자에게 보이는 이름에 NEIS/나이스를 넣지 않음(상표법 §34①3). 코드가 NEIS를 자동화한다는 기술적 서술은 무방.

## 실행 및 빌드 명령

레포 루트(`neis-attendance/`)에서 실행합니다. 이 환경의 Python은 `py -3.14` 입니다(PATH의 `python`은 무관한 별도 venv).

```bash
# 데스크톱 앱 실행
py -3.14 -m subject_teacher.main

# Python 의존성 설치
pip install -r requirements.txt

# Python 테스트
py -3.14 -m pytest tests/ -q

# 데스크톱 UI (Vite/React) — subject_teacher/neis_attendance/ 에서
npm install && npm run build   # 앱에 반영하려면 빌드 후 앱 재시작
npm test                       # vitest

# 모바일 PWA — subject_teacher_pwa/ 에서
npm install && npm run dev
npm test                       # vitest

# 데스크톱 EXE 빌드 (PyInstaller)
pyinstaller NEIS_Subject_Teacher.spec
```

## 아키텍처

### 디렉터리 구조

| 경로 | 역할 |
|---|---|
| `subject_teacher/` | 데스크톱 앱 Python 백엔드 (앱 서비스, Drive 저장소, NEIS 자동화, GUI 브리지). |
| `subject_teacher/main.py` | 데스크톱 진입점. `gui/webview_app.py`로 pywebview 앱 기동. |
| `subject_teacher/gui/api.py` | 프런트엔드(React)↔Python 브리지. Drive I/O 메서드는 직렬화됨(httplib2 비-thread-safe). |
| `subject_teacher/neis_attendance/` | 데스크톱 UI (Vite + React + TS). 빌드 산출물(`dist/`)만 EXE에 포함. |
| `subject_teacher/app_service.py` | 실행 오케스트레이션, Selenium 드라이버 생성, Drive→NEIS 준비, sync 플래그 갱신. |
| `subject_teacher/neis/` | NEIS 과목별 출결 자동화. `runner.py`(일일 오케스트레이션), `subject_commands.py`(셀렉터/클릭). |
| `subject_teacher/drive/` | `appDataFolder` 클라이언트, 스키마(Pydantic), 마이그레이션, E2E 암호화(`crypto.py`). |
| `subject_teacher/auth/` | Google OAuth + DPAPI 토큰 저장. |
| `subject_teacher_pwa/` | 모바일 PWA (별도 Vercel 배포 단위). |
| `tests/` | Python 테스트 (pytest). |
| `config.py`, `regions.py`, `utils.py`, `logger_config.py` | **공유 루트 모듈** — 원래 별도 앱에서 왔으나 현재 `subject_teacher`가 재사용. 함부로 옮기거나 지우지 말 것. |

### 핵심 데이터 흐름

1. **모바일 PWA** → 수업 직후 출결 체크 → Drive `attendance-YYYY-MM.json`에 `source="mobile"`로 저장(암호화).
2. **데스크톱 앱** → Drive에서 현황을 읽어 검토(복호화) → 교사가 NEIS 동기화 실행.
3. **NEIS 자동화** (`neis/`) → Selenium이 과목별 출결관리 화면에서 교시·학년·반·과목을 매칭해 셀을 클릭, 저장, `결과: n명` 카운트 검증.
4. Drive의 sync 플래그(`syncedToNeis`, `closedOnNeis`) 갱신.

### E2E 암호화 (개인정보 핵심)

- Drive에는 암호문 봉투만 저장: `{"checkonEnc":1,"alg":"A256GCM","nonce":...,"ct":...}` (AES-256-GCM, AAD=파일명).
- 키는 데스크톱에서 생성(32B), DPAPI로 PC 로컬(`%LOCALAPPDATA%/NeisSubject/sync_key.bin`)에만 저장. **Drive에 절대 안 올라감.**
- 휴대폰은 QR 페어링(`checkon.sync.v1:` + base64url 키)으로 키를 받아 IndexedDB에 보관.
- 파이썬(`drive/crypto.py`)과 TS(`subject_teacher_pwa/src/lib/crypto.ts`) 구현은 `tests/fixtures/e2e_crypto_vector.json` 벡터로 동일 암호문을 내는지 상호검증.
- 읽기는 이중 경로(봉투→복호화 / 평문→그대로), 쓰기는 키가 있을 때만 암호화(opt-in).

### 스레딩 / Drive I/O

- 데스크톱의 장시간 작업(Drive·NEIS)은 백그라운드 스레드에서 실행해 GUI 블로킹 방지.
- **httplib2는 thread-safe가 아님**: Drive에 닿는 브리지 메서드는 `gui/api.py`의 `SERIALIZED_API_METHODS`에 넣어 `API_IO_LOCK`으로 직렬화. 위반 시 SSL 오류/세그폴트 발생.

### PyInstaller 빌드 시 경로 처리

`sys.frozen` 플래그로 개발/EXE 환경을 구분:
```python
if getattr(sys, 'frozen', False):
    APPLICATION_PATH = os.path.dirname(sys.executable)
else:
    APPLICATION_PATH = os.path.dirname(os.path.abspath(__file__))
```

## 주요 의존성

- **pywebview** + **pythonnet**: 데스크톱 셸(WebView2).
- **Vite / React / TypeScript**: 데스크톱 UI 및 모바일 PWA.
- **Selenium** + **webdriver-manager**: NEIS 브라우저 자동화(공유 `utils.py` 경유).
- **google-auth-oauthlib** / **google-api-python-client**: Google OAuth + Drive `appDataFolder`.
- **pydantic**: Drive JSON 스키마.
- **pytest** / **playwright**: 테스트.
- **PyInstaller**: 데스크톱 EXE 빌드.

## 보안 규칙 (필수)

- 학생 **이름은 절대 클라우드에 올리지 않음**. Drive 로스터는 학번만(numbers-only). 이름은 데스크톱 로컬 DPAPI 저장소에만.
- NEIS 인증서 비밀번호와 Google 토큰을 Drive JSON에 저장하지 않음. 로컬 비밀은 `paths.py`/`auth/token_store.py`를 통해 `%LOCALAPPDATA%/NeisSubject`에만.
- 페어링 키/QR payload는 로그·커밋·클라우드에 남기지 않음.
- `client_secrets.json`, `token.bin`, `password.bin`, `tmp_*.json` 등 진단 덤프는 커밋 금지.
- 개인정보처리방침류 문서는 참고용 초안이며 배포 전 변호사 검토 권장.

## 참고

- 서브패키지 상세 규칙: `subject_teacher/AGENTS.md`
- 설계/계획 문서: `docs/superpowers/specs/`, `docs/superpowers/plans/`
