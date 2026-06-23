# 데스크톱 UI 교사 친화 재설계 (neis_attendance)

- 작성일: 2026-06-23
- 대상: `subject_teacher/neis_attendance` (React + 인라인 CSS 클래스, 토큰은 `neis_attendance/styles.css`)
- 근거: 교사(비개발자) 대상 UI 감사 워크플로(에이전트 7) 결과 + 사용자 결정

## 1. 목표 / 비목표

**목표**: 비개발자 교사가 "보자마자 이해"하도록 군더더기·전문용어·무의미 기능을 걷어내고 일일 흐름(오늘 출결)을 직관화.

**비목표**:
- 자동화(NEIS/Selenium) 백엔드 로직 불변 — UI 한정. **예외 1건**: 인앱 "다시 연결"을 위해 `gui/api.py`에 OAuth 재인증 메서드 1개 추가(§3). 현재 앱엔 인앱 재연결 수단이 없어 교사가 토큰 만료(7일)마다 막히므로 필수.
- 기능의 **완전 삭제 아님** — 잘라낼 항목은 **렌더에서 제외(숨김), 코드·로직은 보존**(복원 용이).

## 2. 확정 결정 (사용자)

| 항목 | 결정 |
|---|---|
| 잘라낼 기능(실행기록·예약실행·Drive/OAuth 별도 탭·tweaks 패널·미동작 검색창) | **숨김** — 렌더 제외, 컴포넌트/로직 파일은 유지 |
| 계정·재연결(OAuth 재인증, 7일마다 필요) | **사이드바 하단 카드**에 "다시 연결" |
| 외관 옵션(테마/액센트/밀도/모서리/글자크기) | **전부 고정**(라이트·기본값), 선택 UI 제거 |
| 미반영 필터(onChange 빈 함수, 동작 안 함) | 제거(죽은 UI) |

## 3. 정보구조(IA) — `app.tsx`

- 사이드바를 **2그룹 4항목**으로:
  - **오늘 출결** (기존 "실행" / `run`)
  - **설정**: 기본 정보 · 시간표 · 학생 명부
- 렌더 제외(숨김): "연결" 그룹(Drive·OAuth 탭), "기타" 그룹(실행기록·예약실행), **검색창**, 하드코딩 배지("대기 3" → 실제 대기 수만)
- 라우트 제외: `drive`, `auth`, `log`, `schedule` 페이지는 NAV에서 제거(컴포넌트 파일 보존). `DriveView`/`AuthView`는 import는 두되 사이드바에서 진입 안 함.
- **사이드바 하단 계정 카드**: 아바타 + 교사명/계정 + "연결됨 · [다시 연결]".
  - ⚠️ **현재 인앱 재연결 수단 없음** — `api.py`엔 `get_drive_user`만 있고 재인증은 터미널 스크립트(`scripts.authorize`)로만 가능(교사 불가). 따라서 **`gui/api.py`에 신규 메서드 `reconnect()` 추가**: `auth.google_oauth.authorize_interactive()`(브라우저 동의 → 토큰 저장) 호출 후 갱신 계정(JSON) 반환. "다시 연결"이 이를 호출하고 성공 시 계정 카드 갱신.
  - 토큰 만료(`reauth_required`) 감지 시 이 카드를 강조(빨강/안내 문구).
- `tweaks` 적용 useEffect: 옵션 제거 후 **고정 기본값**으로 1회 설정(theme=light, density=cozy, accent=#0A84FF, corner=18). `TweaksPanel`은 렌더하지 않음.

## 4. 「오늘 출결」 화면 — `run-view.tsx`

- 제목/메뉴 라벨 **"실행" → "오늘 출결"**.
- 출결 상태 입력: **순환 토글 → 직접 선택 3버튼**(출석 / 결과 / 인정결과). NEIS 기호(`/`,`Ø`) 노출 제거 → **색점 + 한글 라벨**.
- **연결 상태 카드(appDataFolder) 삭제** → 상단은 핵심 카드만(날짜·오늘 수업·대기/완료 요약).
- 중복 칩 통합: "완료 표시 N" + "Drive 저장 완료" → 하나의 상태 표기로.
- 진행 표시는 진행바/상태칩으로만(원시 로그 노출 금지).
- 마감 토글 문구 완결화(예: "처리 후 출결 마감까지 함").
- 수업 목록의 **NEIS 표시명 컬럼 숨김**(교사에겐 내부 라벨), 불필요한 "불러오기" 버튼 숨김.

## 5. 진행 기록(로그) — `app.tsx` / `log-panel.tsx`

- **기본 숨김**: `tweaks.showLog` 기본 false + 하단 도크 기본 접힘.
- 🐞 **버그 수정(핵심결함)**: `appendLog`가 매번 `setLogCollapsed(false)`로 **자동 펼침** → 제거. 로그는 사용자가 명시적으로 열 때만 표시.
- 간소화: 타임스탬프/레벨 태그 숨김(또는 약하게), 레벨 용어 평이화 — **INFO/OK/WARN/ERR → 안내/완료/주의/오류**.
- 라벨 "실행 로그 N lines" → "진행 상황 기록 N줄".

## 6. 용어 평이화 (reword)

| 기존 | 변경 |
|---|---|
| 실행 | 오늘 출결 |
| Drive에 저장 / 저장 완료 | 저장 / 저장됨 |
| 체크 / 체크완료 / 체크대기 | 출결 확인 / 확인함 / 아직 확인 안 함 |
| 교사 인증서 비밀번호 | NEIS 인증서 비밀번호 |
| NEIS 주소 라우팅에 사용 | 우리 지역 NEIS 접속에 사용 |
| CSV/XLSX 가져오기 | 엑셀 파일 가져오기 |
| INFO/OK/WARN/ERR | 안내/완료/주의/오류 |

(개발자 용어 전반: appDataFolder, OAuth, TSV, sync, JSON 등 화면 노출 문구에서 제거/평이화)

## 7. 시각 폴리시 — `styles.css`

- 🐞 **버그**: 미정의 `var(--border)` 사용처 → `var(--sep)`로 교정.
- 대비: `--fg-3`(흐린 회색) 더 진하게 → WCAG AA 확보.
- 본문 기준 15–16px, 제목/본문/보조 **3단 타이포 위계** 정리.
- 상태색 토큰 통일(출석/결과/인정결과/오류), 여백 토큰화.

## 8. 영향 파일
- `neis_attendance/src/app.tsx` (IA/사이드바/계정카드/로그기본값/tweaks 고정)
- `neis_attendance/src/run-view.tsx` (오늘 출결 화면)
- `neis_attendance/src/setup-view.tsx` (Basics 연결상태 섹션 제거, 용어 평이화; Drive/Auth 뷰는 보존하되 미진입)
- `neis_attendance/src/log-panel.tsx` (기본 숨김/문구)
- `neis_attendance/styles.css` (버그·대비·타이포·토큰)
- `subject_teacher/gui/api.py` (신규 `reconnect()` — 인앱 OAuth 재인증)
- (보존) `tweaks-panel.tsx`, `DriveView`/`AuthView` — 렌더 제외, 파일 유지

## 9. 검증
- `cd subject_teacher/neis_attendance && npm run build` 통과(TS 에러 0)
- 기존 컴포넌트 테스트(`components.test.tsx` 등) 통과 유지, 변경 동작에 맞게 갱신
- 데스크톱 실행 후 육안 확인: 사이드바 2그룹, 로그 기본 숨김, 오늘 출결 직접선택 3버튼, 계정 카드 재연결
- mock-api 브라우저 미리보기로 스크린샷 비교(전/후)

## 10. 위험 / 메모
- "다시 연결"은 신규 `api.reconnect()`(= `authorize_interactive`) 필요 — 현재 인앱 재인증 경로가 없어 추가(§3). `authorize_interactive`는 `run_local_server`로 브라우저 동의를 띄움(이번 세션에서 동작 확인됨). 동의가 끝날 때까지 블로킹하므로 UI는 "브라우저에서 로그인하세요" 안내 + 완료 후 갱신.
- 숨김은 렌더 제외이므로 죽은 import 경고가 날 수 있음 → 빌드 경고 확인.
- 백엔드/자동화는 불변(이번 PR과 별개).
