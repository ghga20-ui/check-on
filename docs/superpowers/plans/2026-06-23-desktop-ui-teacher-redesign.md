# 데스크톱 UI 교사 친화 재설계 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 비개발자 교사가 보자마자 이해하도록 데스크톱 UI(neis_attendance)를 단순화 — 군더더기/전문용어/무의미 기능 제거(숨김), 「오늘 출결」 직관화, 인앱 재연결 추가.

**Architecture:** React(인라인 CSS 클래스, 토큰=`neis_attendance/styles.css`). 잘라낼 기능은 렌더에서만 제외(코드 보존). 백엔드는 인앱 OAuth 재인증 메서드 1개만 추가.

**Tech Stack:** React 18 + Vite + TypeScript + vitest/testing-library (UI); Python + pytest (백엔드 1건); pywebview 브리지.

## Global Constraints
- 사용자 = **비개발자 교사**. 화면 문구는 평이한 한국어, 개발자 용어(OAuth/appDataFolder/TSV/sync/JSON/DPAPI) 노출 금지.
- 잘라낼 기능은 **삭제가 아니라 렌더 제외(숨김)** — 컴포넌트/로직 파일 보존.
- 외관 옵션(테마/액센트/밀도/모서리/글자크기)은 **고정**(라이트, accent `#0A84FF`, density `cozy`, corner `18`). 선택 UI 없음.
- UI 검증 게이트: `cd subject_teacher/neis_attendance && npm run build` (TS 에러 0) + `npm run test`(기존 vitest) 통과.
- 파이썬 검증: repo 루트에서 `py -m pytest`.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- 작업 브랜치: `feat/desktop-ui-polish` (이미 체크아웃됨).

## 영향 파일
- `subject_teacher/gui/api.py` — 신규 `reconnect()`
- `subject_teacher/neis_attendance/src/app.tsx` — IA/사이드바/계정카드/로그기본값/외관고정
- `subject_teacher/neis_attendance/src/run-view.tsx` — 「오늘 출결」
- `subject_teacher/neis_attendance/src/setup-view.tsx` — BasicsView 연결상태 제거·문구
- `subject_teacher/neis_attendance/src/log-panel.tsx` — 문구·레벨 평이화
- `subject_teacher/neis_attendance/styles.css` — 버그·대비·타이포·상태토큰
- (보존, 미렌더) `tweaks-panel.tsx`, setup-view의 `DriveView`/`AuthView`

---

### Task 1: 백엔드 — 인앱 OAuth 재연결 `api.reconnect()`

**Files:**
- Modify: `subject_teacher/gui/api.py` (`Api` 클래스에 메서드 추가; `get_drive_user`는 api.py:463에 이미 존재)
- Test: `tests/test_gui_api.py`

**Interfaces:**
- Produces: `Api.reconnect() -> str` — `auth.google_oauth.authorize_interactive()`(브라우저 동의→토큰 저장) 실행 후 `get_drive_user()` JSON 반환. 실패 시 `_json_error`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gui_api.py  (append)
def test_reconnect_runs_interactive_auth_then_returns_account(monkeypatch):
    called = {}
    monkeypatch.setattr(
        "subject_teacher.auth.google_oauth.authorize_interactive",
        lambda: called.setdefault("auth", True),
    )
    a = gui_api.Api.__new__(gui_api.Api)
    monkeypatch.setattr(a, "get_drive_user", lambda: json.dumps({"emailAddress": "x@y.com"}), raising=False)

    payload = json.loads(a.reconnect())

    assert called.get("auth") is True
    assert payload["emailAddress"] == "x@y.com"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_gui_api.py -k reconnect -v`
Expected: FAIL (`AttributeError: 'Api' object has no attribute 'reconnect'`)

- [ ] **Step 3: Implement `reconnect`**

```python
# subject_teacher/gui/api.py — add as a method on class Api
    def reconnect(self) -> str:
        """Run the interactive Google consent flow (opens a browser) and return the
        refreshed account info. Used by the in-app '다시 연결' button so teachers
        never need the terminal when the 7-day token expires."""
        try:
            from subject_teacher.auth.google_oauth import authorize_interactive

            authorize_interactive()
            return self.get_drive_user()
        except Exception as exc:
            logger.exception("reconnect failed")
            return _json_error(exc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_gui_api.py -k reconnect -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add subject_teacher/gui/api.py tests/test_gui_api.py
git commit -m "feat(desktop-ui): add api.reconnect() for in-app OAuth re-auth"
```

---

### Task 2: 사이드바/셸 단순화 — `app.tsx`

**Files:**
- Modify: `subject_teacher/neis_attendance/src/app.tsx`

**Interfaces:**
- Consumes: `api.reconnect()` (Task 1) via `window.pywebview.api.reconnect()`.

변경 항목 (파일을 읽고 해당 위치에 적용):

- [ ] **Step 1: NAV를 2그룹으로 교체** (현 17–34행)

```jsx
const NAV = [
  { group: "", items: [
    { key: "run", label: "오늘 출결", icon: "bolt" },
  ]},
  { group: "설정", items: [
    { key: "basics",    label: "기본 정보", icon: "gear" },
    { key: "timetable", label: "시간표",   icon: "board" },
    { key: "roster",    label: "학생 명부", icon: "users" },
  ]},
];
```
(연결·기타 그룹과 하드코딩 배지 제거. `drive`/`auth`/`log`/`schedule` 라우트는 NAV에서 빠짐.)

- [ ] **Step 2: 외관 고정 + tweaks 제거**
  - `useTweaks` 사용 제거하거나 `TWEAK_DEFAULTS`를 고정 상수로만 사용. `tweaks` 적용 useEffect(354–366행)를 **고정값**으로:
```jsx
  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = "light";
    root.dataset.density = "cozy";
    root.dataset.sidebar = sidebarCollapsed ? "collapsed" : "expanded";
    root.style.setProperty("--accent", "#0A84FF");
    root.style.setProperty("--accent-hover", "#0071e3");
    root.style.setProperty("--accent-soft", "#0A84FF22");
    root.style.setProperty("--radius-lg", "18px");
  }, [sidebarCollapsed]);
```
  - 사이드바 접힘은 별도 `const [sidebarCollapsed, setSidebarCollapsed] = useState(false)`로 관리(접기 버튼이 이걸 토글).
  - `<TweaksPanel>...</TweaksPanel>` 블록(475–490행) **렌더 제거**(import는 남겨도 됨).

- [ ] **Step 3: 검색창 제거** — `<div className="sb-search">…</div>`(429–432행) 삭제.

- [ ] **Step 4: 로그 기본 숨김 + 자동펼침 버그 제거**
  - 상태: `const [logOpen, setLogOpen] = useState(false);` 추가. `logCollapsed` 관련 제거.
  - `appendLog`(80–83행)에서 **`setLogCollapsed(false)` 제거**(자동 펼침 버그). 로그는 명시적으로 열 때만.
  - 하단 로그 도크 렌더(471–473행)를 `{logOpen && <LogDock lines={logLines} onClose={() => setLogOpen(false)} clear={clearLog}/>}`로(아래 Task 5의 LogDock 시그니처에 맞춤).
  - 사이드바 하단 또는 계정 카드 옆에 "진행 기록" 토글 버튼 추가: `<button className="sb-loglink" onClick={() => setLogOpen(o => !o)}>진행 기록</button>`.

- [ ] **Step 5: 사이드바 하단 계정 카드 + 다시 연결**
  현 `sb-foot`(451–457행)을 교체:
```jsx
        <div className="sb-foot">
          <div className="avatar">{sidebarInitial}</div>
          <div className="sb-user-wrap">
            <div className="sb-user">{sidebarName}</div>
            <div className="sb-role">{driveUser?.emailAddress ? "연결됨" : "연결 필요"}</div>
          </div>
          <button className="sb-reconnect" disabled={reconnecting} onClick={reconnect}>
            {reconnecting ? "연결 중…" : "다시 연결"}
          </button>
        </div>
```
  그리고 핸들러 추가(App 본문):
```jsx
  const [reconnecting, setReconnecting] = useState<any>(false);
  const reconnect = () => {
    if (!(window.__isPywebview && window.__isPywebview())) {
      appendLog("안내", "브라우저 미리보기에서는 다시 연결을 사용할 수 없습니다");
      return;
    }
    setReconnecting(true);
    appendLog("안내", "브라우저에서 구글 계정으로 로그인해 주세요…");
    window.pywebview!.api.reconnect()
      .then(raw => { const u = parseJsonResult(raw); setDriveUser(u); appendLog("완료", `다시 연결됨 · ${u.emailAddress || "계정"}`); return loadSetupData(); })
      .catch(err => appendLog("오류", `다시 연결 실패: ${formatApiError(err)}`))
      .finally(() => setReconnecting(false));
  };
```

- [ ] **Step 6: 라우트 정리** — `<main>`의 페이지 분기(460–469행)에서 `drive`/`auth`/`log`/`schedule` 분기 제거(컴포넌트 import는 보존). 남길 분기: `run`, `basics`, `timetable`, `roster`.

- [ ] **Step 7: appendLog 레벨 인자 평이화 정합** — 전 파일에서 `appendLog("INFO"/"OK"/"WARN"/"ERR", …)` 호출을 `안내/완료/주의/오류`로 통일(Task 5의 LogDock가 이 라벨을 그대로 표시).

- [ ] **Step 8: 빌드 검증 + 커밋**

Run: `cd subject_teacher/neis_attendance && npm run build`
Expected: 빌드 성공(TS 에러 0).
```bash
git add subject_teacher/neis_attendance/src/app.tsx
git commit -m "feat(desktop-ui): 2-group sidebar, account card with reconnect, log hidden by default, fixed appearance"
```

---

### Task 3: 「오늘 출결」 화면 — `run-view.tsx`

**Files:**
- Modify: `subject_teacher/neis_attendance/src/run-view.tsx`

- [ ] **Step 1: 제목/문구 변경** — topbar(195–198행) `"실행"` → `"오늘 출결"`, 부제 평이화: `"· 선택한 날짜의 수업을 확인하고 NEIS에 반영합니다"` 유지 가능. page-hero subtitle(227행)의 개발자 표현 제거: `"Drive에서 확인한 출결을 NEIS 과목별 출결관리에 그대로 반영합니다."` → `"확인한 출결을 NEIS에 그대로 반영합니다."`

- [ ] **Step 2: 인증서 비번 라벨**(238행) `"교사 인증서 비밀번호"` → `"NEIS 인증서 비밀번호"`.

- [ ] **Step 3: 연결 상태 카드 삭제** — `stat-grid`(275–296행)에서 **첫 카드(연결 상태/appDataFolder, 276–280행) 삭제**, 나머지 3카드 유지. note의 "체크 완료/체크 대기"(284행) → "출결 확인 N / 아직 확인 안 함 N".

- [ ] **Step 4: 동작 안 하는 필터 제거** — section-head-actions의 `<Segmented value="all" onChange={()=>{}} .../>`(304–310행) 삭제(빈 onChange 죽은 UI).

- [ ] **Step 5: 수업 목록 NEIS 표시명 숨김 + 칩 정리**
  - list-header(314–322행)와 list-row(330–354행)의 그리드에서 "과목 · NEIS 표시명" 컬럼의 `NEIS: {s.neisLabel}` 부분(337행) 제거 → `{s.room} · {s.time}`만.
  - "체크" 컬럼(341–348행): `Chip kind="ok"`의 `완료 · 표시 {s.absences}` → `확인함 · {s.absences}명`, `체크 대기` → `아직 확인 안 함`.
  - status-stack(349–352행): 중복 `Drive 저장 완료` 칩 제거(StatusChip만 유지).

- [ ] **Step 6: ClassSheet 직접 선택 3버튼** — 학생 행 순환 토글(`toggle`, 72–77행, 148행 onClick)을 **직접 선택**으로:
  - 각 학생 행에 3버튼(출석/결과/인정결과)을 두고 해당 상태로 바로 설정: `setMarks(m => ({...m, [n]: value}))`. 색점+한글 라벨, 현재 선택 강조.
  - 기호 표기(`∅`, `결과(/)`, `출석인정(∅)`) → 한글 라벨("출석"/"결과"/"인정결과"). mark-legend(120–131행)도 동일 라벨로.
  - 하단 안내문(160행) "출석 → 결과(/) → 출석인정(∅) 순서로 변경" → "각 학생의 출석/결과/인정결과를 눌러 정하세요."

- [ ] **Step 7: 저장 문구 평이화** — ClassSheet 저장 버튼(164–166행) `"Drive에 저장"/"Drive 저장 중..."` → `"저장"/"저장 중…"`. `appendLog` 문구(84행) `"… Drive 저장 완료 …"` → `"… 저장됨 …"`. 마감 체크박스(212행) `"출결마감까지"` → `"처리 후 출결 마감까지 함"`.

- [ ] **Step 8: 빌드 검증 + 커밋**

Run: `cd subject_teacher/neis_attendance && npm run build`
Expected: 성공.
```bash
git add subject_teacher/neis_attendance/src/run-view.tsx
git commit -m "feat(desktop-ui): 오늘 출결 — direct-select marks, drop connection card/dead filter, plain wording"
```

---

### Task 4: 기본 정보 — `setup-view.tsx` BasicsView

**Files:**
- Modify: `subject_teacher/neis_attendance/src/setup-view.tsx` (BasicsView, 20–116행)

- [ ] **Step 1: 연결 상태 섹션 삭제** — `<div className="section">…연결 상태…</div>`(91–112행) **통째 삭제**(Drive/OAuth/DPAPI 카드 = 교사에게 불명확).

- [ ] **Step 2: 문구 평이화**
  - 27행 `"Drive에서 불러오기"` → `"불러오기"`.
  - 43행 `"NEIS 공개 API 시간표 가져오기에 사용됩니다."` → `"시간표를 자동으로 가져올 때 사용해요."`
  - 55행 `"NEIS 주소 라우팅에 사용됩니다."` → `"우리 지역 NEIS에 접속할 때 사용해요."`
  - 84행 `"실행 탭의 기본값으로 사용돼요."` → `"오늘 출결 화면의 기본값이 돼요."`
  - 37행 subtitle `"학교·학기 정보와 실행 기본값을 정리합니다."` → `"학교·학기 정보와 기본값을 정리합니다."`

- [ ] **Step 3: 빌드 검증 + 커밋**

Run: `cd subject_teacher/neis_attendance && npm run build`
Expected: 성공.
```bash
git add subject_teacher/neis_attendance/src/setup-view.tsx
git commit -m "feat(desktop-ui): drop confusing connection-status section, plain wording in basics"
```

---

### Task 5: 진행 기록(로그) — `log-panel.tsx`

**Files:**
- Modify: `subject_teacher/neis_attendance/src/log-panel.tsx`

- [ ] **Step 1: 시그니처/문구 변경** — LogDock를 항상 펼친 단순 패널로(닫기=숨김):
```jsx
export const LogDock = ({ lines, onClose, clear }) => {
  const bodyRef = useRef(null);
  useEffect(() => { if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight; }, [lines]);
  return (
    <div className="log-dock" data-collapsed="false">
      <div className="log-head">
        <span className="dot"/>
        진행 상황 기록
        <span className="meta">· {lines.length}줄</span>
        <span className="sp"/>
        <button className="action" onClick={clear}>지우기</button>
        <button className="action" onClick={onClose}>숨기기</button>
      </div>
      <div className="log-body" ref={bodyRef}>
        {lines.map((l, i) => (
          <div className="line" key={i}><span className={`lv ${l.lv}`}>{l.lv}</span><span className="msg">{l.msg}</span></div>
        ))}
      </div>
    </div>
  );
};
```
  - 타임스탬프(`ts`) 표시 제거(노이즈). 레벨 라벨은 app.tsx가 이미 `안내/완료/주의/오류`로 넘김(Task 2 Step 7).
  - styles.css의 `.lv.안내/.완료/.주의/.오류` 색은 Task 6에서 정의(기존 `.lv.INFO` 등 대체).

- [ ] **Step 2: 빌드 검증 + 커밋**

Run: `cd subject_teacher/neis_attendance && npm run build`
Expected: 성공.
```bash
git add subject_teacher/neis_attendance/src/log-panel.tsx
git commit -m "feat(desktop-ui): simpler log panel (plain labels, no timestamps, hide on demand)"
```

---

### Task 6: 시각 폴리시 + 버그 — `styles.css`

**Files:**
- Modify: `subject_teacher/neis_attendance/styles.css`

- [ ] **Step 1: 미정의 변수 버그 수정** — `var(--border)` 사용처를 `var(--sep)`로 교정.

Run(위치 확인): `grep -n "var(--border)" subject_teacher/neis_attendance/styles.css`
모든 매치를 `var(--sep)`로 치환.

- [ ] **Step 2: 대비 개선** — `--fg-3`(흐린 보조 텍스트)을 한 단계 진하게(예: 라이트 테마에서 `#8A8A8E` → `#6B6B70` 수준, WCAG AA 본문 대비 확보). 다크 테마 변수도 동일 기조로.

- [ ] **Step 3: 로그 레벨 색 토큰** — 기존 `.lv.INFO/.OK/.WARN/.ERR` 규칙을 `.lv.안내/.완료/.주의/.오류`로 추가/대체(각각 파랑/초록/주황/빨강 계열, accent/green/orange/red 토큰 사용).

- [ ] **Step 4: 타이포 위계** — 본문 기준 15–16px 확인, `h1/h2`와 본문/보조(`desc`,`sub2`)의 크기·굵기 위계가 3단으로 분명한지 점검·정리(과도한 letter-spacing 음수 완화).

- [ ] **Step 5: 빌드 검증 + 커밋**

Run: `cd subject_teacher/neis_attendance && npm run build`
Expected: 성공.
```bash
git add subject_teacher/neis_attendance/styles.css
git commit -m "fix(desktop-ui): styles — undefined var bug, AA contrast, log level tokens, typography"
```

---

### Task 7: 잔여 용어 스윕 + 테스트/빌드 최종 검증

**Files:**
- Modify: 위 파일들 중 잔여 jargon 발견 시
- Test: `subject_teacher/neis_attendance/src/components.test.tsx` 등 기존 테스트

- [ ] **Step 1: jargon 스윕** — 화면 노출 문구에서 잔여 개발자 용어 검색·평이화:

Run: `cd subject_teacher/neis_attendance && grep -rnE "appDataFolder|OAuth|DPAPI|TSV|JSON|sync|Drive에" src styles.css`
사용자 노출 문구면 평이화(내부 변수/주석은 제외).

- [ ] **Step 2: 기존 컴포넌트 테스트 갱신/통과** — `components.test.tsx`가 `Segmented`/`Checkbox`/`StatusChip` 등을 테스트. 시그니처 변경(LogDock 등)으로 깨지면 새 동작에 맞게 갱신.

Run: `cd subject_teacher/neis_attendance && npm run test`
Expected: 통과.

- [ ] **Step 3: 전체 빌드 + 파이썬 테스트**

Run: `cd subject_teacher/neis_attendance && npm run build` → 성공
Run: `py -m pytest tests/test_gui_api.py -q` (repo 루트) → 통과

- [ ] **Step 4: 커밋**

```bash
git add -A
git commit -m "chore(desktop-ui): jargon sweep + tests/build green"
```

---

## Self-Review (작성자 체크)
- **Spec 커버리지**: §3 IA→Task2, §4 오늘출결→Task3, §5 로그→Task2(기본숨김/버그)+Task5(패널), §6 용어→Task2-5+Task7, §7 시각→Task6, §2-3 reconnect→Task1. 전 항목 매핑.
- **플레이스홀더**: 코드 확정 부분(api.reconnect, NAV, 계정카드, LogDock, reconnect 핸들러)은 실제 코드. UI 구조 편집은 "파일 읽고 해당 행 적용 + 정확한 신규 문구" 제공(추상 TODO 아님). styles는 grep로 위치 특정.
- **타입/시그니처 일관성**: `LogDock({lines,onClose,clear})` (Task5) ↔ app.tsx 렌더(Task2 Step4) 일치. `api.reconnect()`(Task1) ↔ `window.pywebview.api.reconnect()`(Task2 Step5) 일치. appendLog 레벨 `안내/완료/주의/오류`(Task2 Step7) ↔ log 색 토큰(Task6 Step3) ↔ LogDock 표시(Task5) 일치.
- **순서/의존**: Task1(백엔드)→Task2(reconnect 호출). Task2(레벨 라벨)↔Task5/Task6(표시/색)는 함께. Task3/4는 독립. Task6은 Task5 라벨 의존. Task7 최종.
