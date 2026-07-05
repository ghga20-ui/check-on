# ✅ 체크온 (CheckOn)

**수업 직후, 휴대폰으로 출결 체크 한 번. PC에서 NEIS 입력은 자동으로.**

체크온은 교과담당(과목) 선생님을 위한 출결 도구입니다. 매 수업이 끝나면 휴대폰에서 결석·지각을 바로 체크하고, PC에서는 그 결과를 NEIS(교육행정정보시스템) 과목별 출결관리에 자동으로 입력합니다.

---

## 🧩 구성

체크온은 세 부분이 함께 동작합니다.

| 부분 | 무엇인가 | 어디서 쓰나 |
| :-- | :-- | :-- |
| 📱 **모바일 앱(PWA)** | 수업 직후 즉시 출결 체크 | 휴대폰 |
| 🖥️ **데스크톱 앱** | 출결 현황 검토 + NEIS 자동 입력 | 학교 PC(Windows) |
| ☁️ **동기화** | 두 기기가 같은 출결을 공유 | Google Drive(내 계정) |

## 🔒 개인정보 보호 — 종단간(E2E) 암호화

출결 데이터는 내 구글 드라이브를 **통로**로 오가지만, 내용은 **암호화**되어 저장됩니다.

- 드라이브에는 잠긴 상자(암호문)만 올라갑니다. **구글도 내용을 읽을 수 없습니다.**
- 열쇠는 데스크톱에서 만들어 PC에만 안전하게 보관되고, 휴대폰에는 **QR 코드로 한 번만** 전달됩니다(인터넷을 거치지 않음).
- 학생 **이름은 애초에 클라우드에 올라가지 않습니다.** 드라이브에는 학번만, 이름은 PC 안에만 있습니다.

> 자세한 암호화 설계는 `docs/superpowers/specs/2026-07-02-e2e-sync-encryption-design.md` 를 참고하세요.

---

## 🚀 개발 환경 실행 (개발자용)

레포 루트에서 실행합니다.

```bash
# Python 의존성 설치
pip install -r requirements.txt

# 데스크톱 앱 실행 (Windows)
py -3.14 -m subject_teacher.main

# 데스크톱 UI(React) 빌드 — subject_teacher/neis_attendance/ 에서
npm install && npm run build

# 모바일 PWA 개발 서버 — subject_teacher_pwa/ 에서
npm install && npm run dev

# 데스크톱 EXE 빌드
pyinstaller NEIS_Subject_Teacher.spec
```

## 🧪 테스트

```bash
# Python
py -3.14 -m pytest tests/ -q

# 데스크톱 UI / PWA (각 폴더에서)
npm test
```

## 📁 폴더 구조

```
neis-attendance/
├─ subject_teacher/            # 데스크톱 앱 (Python 백엔드)
│  └─ neis_attendance/         #   └ 데스크톱 UI (Vite/React)
├─ subject_teacher_pwa/        # 모바일 앱 (PWA, Vercel 배포)
├─ tests/                      # Python 테스트
├─ docs/                       # 설계·계획·법무 문서
├─ config.py / regions.py /    # 공유 모듈 (데스크톱이 재사용)
│  utils.py / logger_config.py
└─ NEIS_Subject_Teacher.spec   # PyInstaller 빌드 설정
```

개발 가이드는 `CLAUDE.md`(및 `subject_teacher/AGENTS.md`)를 참고하세요.

---

*선생님의 소중한 업무 시간을 아껴 드리기 위해 만들었습니다.*
