# 체크온(CheckOn) 디자인 랭귀지

두 표면(**데스크톱** `subject_teacher/neis_attendance`, **모바일 PWA** `subject_teacher_pwa`)이
공유하는 단일 기준 사전이다. 색·상태 잉크·radius 토큰, 용어, 브랜드 허용 구역 규율을 정의한다.
데스크톱 `styles.css`가 이 문서의 기준값을 구현한다. 모바일도 같은 사전을 따른다.

> 원칙: 색·마크·워드마크는 이미 공유된다. 이 문서는 **상태 잉크·radius·용어**의 흔들림을
> 없애기 위한 것이다. 값이 바뀌면 이 문서를 먼저 고치고, 그다음 두 표면을 맞춘다.

---

## 1. 토큰

### 1.1 상태 잉크 (status ink)

중립/연한 틴트 배경 위에 얹는 **전경 상태색**. 칩 텍스트, 로그 레벨, 연결 상태 글리프,
파괴적 동작 텍스트에 쓴다. 라이트는 진하게(가독), 다크는 밝게 조정한다.

| 토큰 | 의미 | 라이트 | 다크 |
|---|---|---|---|
| `--ok-ink`   | 성공 · 반영됨 · 확인함 | `#248A3D` | `#30D158` |
| `--warn-ink` | 주의 · 미반영 · 대기 | `#C77A00` | `#FF9F0A` |
| `--bad-ink`  | 오류 · 결과 · 파괴적 동작 | `#D70015` | `#FF453A` |

**틴트 배경**은 브랜드 팔레트(`--green`/`--orange`/`--red`)의 알파로 만든다:
`rgba(48,209,88,.14)` (ok), `rgba(255,159,10,.16)` (warn), `rgba(255,69,58,.14)` (bad).

> **솔리드 채움 예외.** 흰 글씨를 얹는 솔리드 상태 채움(토스트 `.app-toast.ok/.err`,
> 온보딩 완료 배지 `.ob-step.done .ob-num`)은 고정된 진한 녹/적(`#1B7A33` / `#C42017`)을
> 두 테마에서 그대로 쓴다. 이들은 항상-어두운 표면 위 흰 글씨라, 잉크 토큰처럼 다크에서
> 밝아지면 흰 글씨 대비가 깨진다. 잉크 토큰은 **전경 텍스트**에만, 솔리드 채움은 별개로 취급한다.

### 1.2 컬러 팔레트

| 토큰 | 역할 | 라이트 | 다크 |
|---|---|---|---|
| `--accent` | 브랜드 파랑(주 액션) | `#0A84FF` | `#0A84FF` |
| `--accent-hover` | 액션 hover | `#0071E3` | `#0071E3` |
| `--accent-soft` | 액센트 틴트 | `rgba(10,132,255,.12)` | `rgba(10,132,255,.22)` |
| `--green` / `--orange` / `--red` | 상태 원색(도트·틴트 원료) | `#30D158` / `#FF9F0A` / `#FF453A` | 동일 |
| `--purple` / `--yellow` | 보조 | `#BF5AF2` / `#FFD60A` | 동일 |
| `--bg` | 앱 배경 | `#F2F2F7` | `#000000` |
| `--bg-2` | 서브 배경(칩·필드) | `#E5E5EA` | `#111113` |
| `--panel` | 카드·시트 면 | `#FFFFFF` | `#1C1C1E` |
| `--panel-alt` | 헤더·강조 면 | `#FBFBFD` | `#2C2C2E` |
| `--fg` | 본문 | `#111114` | `#F5F5F7` |
| `--fg-2` | 보조 텍스트 | `#3A3A3C` | `#D1D1D6` |
| `--fg-3` | 설명·캡션(AA) | `#6B6B70` | `#8E8E93` |
| `--fg-4` | 비활성 | `#AEAEB2` | `#636366` |
| `--sep` / `--sep-strong` | 구분선 | `rgba(60,60,67,.14)` / `.24` | `rgba(255,255,255,.09)` / `.18` |

### 1.3 Radius

`8 / 12 / 18 / 22` 4단계. 정규 이름은 `--radius-s/m/l/xl`. 기존 이름은 별칭으로 남겨
대량 리네이밍 위험 없이 한 방향으로 읽히게 했다.

| 토큰 | 값 | 별칭 | 대표 사용처 |
|---|---|---|---|
| `--radius-s`  | `8px`  | `--radius-sm` | 사이드바 항목, 작은 버튼 |
| `--radius-m`  | `12px` | `--radius`    | 배너, 인라인 프로그레스, run CTA |
| `--radius-l`  | `18px` | `--radius-lg` | 카드(`.card`/`.stat-card`), 리스트 그룹 |
| `--radius-xl` | `22px` | —             | 시트(`.sheet`, 넓은 뷰포트) |

> **남은 부채.** 버튼·입력(`10px`), 브랜드 로고 컨테이너(`10–11px`), 아이콘 배지(`14/16px`),
> 바텀시트 상단 모서리(`20px`)는 4단계 밖의 값이라 그대로 뒀다. 시각 변화 위험이 있어
> 전수 치환하지 않았다. 다음 라운드에서 스케일 편입 여부를 결정한다.

---

## 2. 용어 사전 (기준)

코드 식별자·테스트 픽스처 키는 유지하고, **사용자 눈에 보이는 문자열**만 이 표를 따른다.

### 2.1 확인 단계 (교사의 출결 확인 여부)

| 상태 | 표기 |
|---|---|
| 확인 완료 | **확인함** |
| 미확인 | **미확인** |

- 금지: "아직 확인 안 함" → **미확인**으로 축약 통일.

### 2.2 NEIS 반영 단계

| 상태 | 표기 |
|---|---|
| 반영 완료 | **NEIS 반영됨** (집계 문구는 "모두 반영됨") |
| 미반영 | **미반영** |
| 마감 완료 | **마감됨** |
| 진행 중 | **반영 중…** (말줄임표 포함) |

- 금지: "NEIS 반영 중"(진행 헤더) → **반영 중…**. 어미 변형 금지.
- "출결마감"·"출결 마감까지"는 **동작(액션) 레이블**이므로 상태 표기와 별개로 유지한다.

### 2.3 출결 마크

| 마크 | 표기 |
|---|---|
| 출석 | **출석** |
| 결과(결석 처리) | **결과** |
| 인정결과 | **인정결과** |

- 다른 표기 변형 금지. (모바일이 쓰는 "출석인정"은 이 사전 기준으로 **인정결과**로 수렴한다.)

### 2.4 Drive 확인 상태(모바일 기록)

데스크톱에서 모바일이 남긴 Drive 확인 기록을 표시할 때도 **확인함 / 미확인** 동일 용어를 쓴다.

---

## 3. 브랜드 허용 구역 (C안 규율)

브랜드 자산 = **종 마크(BrandMark)·"체크온CheckOn" 워드마크·파랑 그라데이션**
(`linear-gradient(145deg, var(--accent), #5856D6)`).

브랜드는 **분위기를 여는 곳**에만 등장한다. 핵심 작업 화면은 상태에만 집중한다.
두 표면(데스크톱/모바일) 공통 기준이다.

### 브랜드 허용 (brand-allowed)
- **진입 화면** — 로그인 / 페어링 / 온보딩(첫 진입).
- **사이드바 헤더 / 상단 앱 헤더** — 로고 + 워드마크.
- **완료 순간** — 온보딩 스텝 완료, 실행 성공 토스트 등 "축하/마무리" 모먼트.

### 브랜드 금지 → 상태색만 (state-only)
- **출결 시트**(`.sheet` / 학생 마킹) — 중립 + `--ok/warn/bad-ink` 3종만.
- **실행 화면**(run-view 본문 · 카드 · 리스트) — 그라데이션·종 마크 없이 상태색·중립만.
- 액션 버튼의 파랑(`--accent`)은 브랜드가 아니라 **주 액션 시그널**로 허용한다.

> 요약: **그라데이션·종 마크·워드마크는 "여는 화면 / 헤더 / 완료 모먼트"에서만.**
> 사용자가 실제로 손을 움직이는 화면은 상태 3색 + 중립으로 조용하게.

---

## 4. 아이콘 세트 (모바일 재사용용 스니펫)

데스크톱 `src/components.tsx`의 `Icon`에서 발췌. 공통 규격:
`viewBox="0 0 20 20"`, `fill="none"`, `stroke="currentColor"`,
`stroke-width≈1.6`, `stroke-linecap/linejoin="round"`. 색은 `currentColor`이므로
상태 잉크 토큰과 그대로 합쳐진다 (`color: var(--ok-ink)` 등).

```svg
<!-- check · 확인함 / 반영됨 -->
<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 10.5l4 4 8-9"/>
</svg>

<!-- warn · 경고(삼각형) -->
<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M10 3.2 L17.5 16 H2.5 Z"/>
  <path d="M10 8.5v3.5"/>
  <circle cx="10" cy="14" r=".7" fill="currentColor"/>
</svg>

<!-- info · 안내(원형, 배너·모바일 공용) -->
<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="10" cy="10" r="7.5"/>
  <path d="M10 9v4.5"/>
  <circle cx="10" cy="6.6" r=".7" fill="currentColor"/>
</svg>

<!-- refresh · 새로고침 -->
<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M16 10a6 6 0 01-10.3 4.2M4 10a6 6 0 0110.3-4.2"/>
  <path d="M14.3 2.8v3h-3M5.7 17.2v-3h3"/>
</svg>

<!-- gear · 설정 -->
<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="10" cy="10" r="2.2"/>
  <path d="M10 1.8v2M10 16.2v2M1.8 10h2M16.2 10h2M4.2 4.2l1.4 1.4M14.4 14.4l1.4 1.4M4.2 15.8l1.4-1.4M14.4 5.6l1.4-1.4"/>
</svg>

<!-- calendar · 날짜 -->
<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="4.5" width="14" height="12" rx="2"/>
  <path d="M3 8.5h14M7 3v3M13 3v3"/>
</svg>

<!-- cloud · 연결 (Drive/동기화) -->
<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M5.6 14.5a3.3 3.3 0 01-.2-6.5 4.5 4.5 0 018.8-.4 3 3 0 01.8 5.9"/>
  <path d="M5 14.5h9.5"/>
</svg>
```

---

## 5. 유지보수

- 토큰 값 변경 시: `styles.css`(:root / :root[data-theme="dark"]) → 이 문서 → 모바일 순으로 맞춘다.
- 새 상태 문자열 추가 시: §2 사전에 먼저 등재하고 두 표면에 반영한다.
- 아이콘 추가 시: `components.tsx`에 넣고 §4에 스니펫을 복사해 모바일이 이식할 수 있게 한다.
