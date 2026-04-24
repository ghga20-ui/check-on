# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## 프로젝트 개요

**나이스 출결관리 프로 - 담임용**: 담임 교사가 NEIS(교육행정정보시스템)에서 출결 서류를 자동으로 다운로드하고 엑셀로 정리하는 Windows 데스크톱 앱.

## 실행 및 빌드 명령

```bash
# 개발 환경에서 실행
python interface_teacher.py

# 의존성 설치
pip install -r requirements.txt

# EXE 빌드 (PyInstaller)
pyinstaller NEIS_Teacher_20251230.spec
```

## 아키텍처

### 모듈 구조

| 파일 | 역할 |
|---|---|
| `interface_teacher.py` | 메인 GUI (CustomTkinter `App` 클래스). 모든 사용자 인터랙션 처리. |
| `btn_commands.py` | Selenium 기반 NEIS 자동화 함수들. 브라우저 조작 및 파일 다운로드. |
| `utils.py` | Selenium 헬퍼: `login()`, `neis_go_menu()`, `neis_click_btn()`, `retry_on_error` 데코레이터. |
| `config.py` | 전역 런타임 상태 (`user_password`, `class_number`, `class_count`, `selected_region`, `last_download_folder`). |
| `regions.py` | 17개 시도교육청 코드 → NEIS URL 매핑. |
| `logger_config.py` | 파일(`logs/YYYY-MM-DD.log`) + 콘솔 동시 출력 로거 설정. |
| `neis_menu_teacher.json` | 사용자 설정 영속화: 교육청, 메뉴 경로(1~4차), 담당 반. |
| `password.bin` | 인증서 비밀번호 암호화 저장 파일. |
| `Attendance Result.xlsm` | VBA 매크로 포함 엑셀 파일. `Module1.Run_All_Processes(folder)` 진입점. |

### 핵심 데이터 흐름

1. **GUI (`interface_teacher.py`)** → 설정 수집 (교육청, 비밀번호, 반, 기간, 메뉴 경로)
2. **btn_commands.py** → `open_neis()` (Selenium Chrome 드라이버 시작, NEIS 로그인)
3. **btn_commands.py** → `neis_attendace_v2()` / `download_tardiness_report_v2()` / `download_monthly_attendance()` (메뉴 탐색 후 파일 다운로드)
4. **interface_teacher.py** → `run_excel_macro_direct()` → `win32com.client`로 Excel VBA 매크로 실행
5. 결과 파일이 사용자 지정 폴더에 저장됨

### 설정 영속화

- `neis_menu_teacher.json`: 메뉴 경로 4단계, 교육청, 반 번호 저장 (앱 종료 시 `save_menus()` 호출)
- `password.bin`: 비밀번호 입력 즉시 DPAPI로 암호화 저장 (`on_password_change` 콜백)
- `password.txt`: 과거 평문 저장 방식의 레거시 마이그레이션 대상. 배포본에 포함하면 안 됨
- `config.py` 전역 변수: 런타임 중 GUI와 btn_commands 사이 상태 공유용

### 스레딩

모든 자동화 작업은 `run_worker()` 를 통해 **별도 데몬 스레드**에서 실행됨. GUI 블로킹 방지. `queue.Queue` + `after(100, check_log_queue)` 패턴으로 스레드에서 GUI 상태바 업데이트.

### PyInstaller 빌드 시 경로 처리

`sys.frozen` 플래그로 개발/EXE 환경을 구분함:
```python
if getattr(sys, 'frozen', False):
    APPLICATION_PATH = os.path.dirname(sys.executable)
else:
    APPLICATION_PATH = os.path.dirname(os.path.abspath(__file__))
```
`logger_config.py`와 `interface_teacher.py` 모두 이 패턴 사용.

## 주요 의존성

- **CustomTkinter** / **CTkMessagebox**: 모던 Tkinter GUI
- **Selenium** + **webdriver-manager**: Chrome 브라우저 자동화
- **pywin32** (`win32com.client`): Excel VBA 매크로 실행 (Windows 전용)
- **pandas** / **openpyxl**: 엑셀 파일 처리
- **PyInstaller**: EXE 단일 파일 빌드

## NEIS 메뉴 구조

NEIS 메뉴는 학교마다 1~4차 명칭이 다를 수 있음. `neis_menu_teacher.json`에 저장되는 기본값:

- **결석 신고서**: 학급담임 → 교육활동신청관리 → 출결관리 → 결석신고서관리
- **지각·조퇴 신고서**: 학급담임 → 교육활동신청관리 → 출결관리 → 지각·조퇴·결과신고서관리
- **월별 출결현황**: 학급담임 → 학적 → 출결현황및통계 → 출결현황및통계
