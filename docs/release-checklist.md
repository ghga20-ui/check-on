# 체크온(CheckOn) 배포 체크리스트

체크온은 **모바일 PWA + 데스크톱 앱 + 구글 OAuth 백엔드** 세 부분을 함께 배포합니다.
각 릴리스마다 아래를 순서대로 확인하세요.

---

## 0. 사전 조건 (한 번만)

- [ ] Google Cloud OAuth 동의 화면이 **프로덕션으로 게시**됨 (테스트 모드면 토큰이 7일마다 만료).
- [ ] 개인정보처리방침이 **공개 URL**로 접근 가능 (PWA `/privacy`), OAuth 동의 화면에 연결됨.
- [ ] 데스크톱용 **설치형(Installed) OAuth 클라이언트**와 PWA용 **웹(Web) OAuth 클라이언트**가 같은 프로젝트에 존재.
- [ ] 웹 클라이언트의 **승인된 자바스크립트 원본**에 Vercel 배포 URL 등록.
- [ ] (검토 권장) 학교·교육청 규정상 개인 구글 계정에 학번 출결 저장 가능 여부 확인.

## 1. 공통 검증 (배포 전)

- [ ] Python 테스트 통과: 레포 루트에서 `py -3.14 -m pytest tests/ -q`
- [ ] 데스크톱 UI 테스트: `subject_teacher/neis_attendance/`에서 `npm test`
- [ ] PWA 테스트: `subject_teacher_pwa/`에서 `npm test`
- [ ] 종단간 암호화 상호검증 벡터 통과 (`tests/test_drive_crypto.py`, PWA `crypto.test.ts`).

## 2. 데스크톱 앱 빌드

- [ ] React UI 빌드: `subject_teacher/neis_attendance/`에서 `npm install && npm run build`
- [ ] `client_secrets.json`(설치형 클라이언트)이 레포 루트에 있는지 확인 (gitignore됨 → 커밋 금지, 빌드 시 EXE에 번들됨).
- [ ] EXE 빌드: 루트에서 `py -3.14 -m PyInstaller NEIS_Subject_Teacher.spec --noconfirm --distpath dist/checkon_build`
- [ ] 스모크 테스트: `dist/checkon_build/NEIS_Subject_Teacher.exe` 실행 → 창이 뜨고 UI가 렌더되는지, Google 로그인이 되는지 1회 확인.
- [ ] 인스톨러 생성 (Inno Setup 6 필요): `ISCC.exe /DAppVersion=<버전> installer\checkon.iss`
      → `dist/installer/CheckOn-Setup-<버전>.exe`
- [ ] 인스톨러를 **다른 PC(관리자 권한 없는 환경 포함)**에서 설치·실행 테스트. WebView2 런타임 없는 PC에서 안내 메시지가 뜨는지 확인.
- [ ] (선택) 코드 서명 — 미서명 시 Windows SmartScreen "알 수 없는 게시자" 경고가 뜨므로 사용자 안내 필요.

## 3. 모바일 PWA 배포

- [ ] `subject_teacher_pwa/`가 Vercel에 자동 배포됨 (푸시 시). 커밋 계정이 연결된 GitHub 사용자여야 배포 통과.
- [ ] Vercel 환경변수 `VITE_GOOGLE_CLIENT_ID`에 **프로덕션 웹 클라이언트 ID** 설정.
- [ ] 휴대폰에서 PWA "홈 화면에 추가" 후 실행 → Google 로그인 → 데스크톱과 QR 페어링 → 출결 동기화 1회 확인.

## 4. 종단간 암호화 / 개인정보 최종 확인

- [ ] 암호화를 켠 뒤 구글 드라이브 파일이 **암호문 봉투**(`checkonEnc`) 형태인지 확인.
- [ ] 클라우드 로스터에 **학생 이름이 없는지**(학번만) 확인.
- [ ] 페어링 키/QR payload가 로그·커밋·클라우드에 남지 않는지 확인.
- [ ] **열쇠 복구/재발급 흐름**이 동작하는지 확인 (PC 교체·초기화 시 데이터 복구 가능 여부).

## 5. NEIS 자동화 실기기 검증

- [ ] 실제 NEIS "과목별출결관리" 화면에서: 날짜 선택 → 교시·과목 선택 → 출결 셀 체크 → 저장 → `결과: n명` 카운트 일치 확인.
- [ ] 같은 과목 다른 반(예: `2학년 1(문학)` / `2학년 2(문학)`)이 혼동되지 않는지 확인.
- [ ] (활성화 시) `출결마감` 동작을 소수 케이스에서 먼저 라이브 검증.

## 6. 민감 파일 제외

배포 산출물(EXE·설치본·zip)과 커밋에 아래가 섞이지 않도록 확인:

- [ ] `client_secrets.json`, `token.bin`, `password.bin`, `sync_key.bin`
- [ ] `tmp_*.json`(NEIS 진단 덤프), `logs/`, `__pycache__/`, `.pytest_cache/`
- [ ] 학생 **이름**이 담긴 로컬 파일(`students.local.json`)

## 배포 보류 기준

아래 중 하나라도 실패하면 재빌드 후 다시 확인:

- EXE 실행 불가 / 창이 안 뜸
- Google 로그인 실패 (OAuth 게시·client_secrets 확인)
- 드라이브 파일이 평문으로 올라감 (암호화 미적용)
- 클라우드에 학생 이름 노출
- NEIS 저장 후 `결과` 카운트 불일치
- 민감 파일 포함
