/* Data: today's timetable, full timetable, rosters */
const TODAY_SLOTS = [
  { id: "s1", period: 1, time: "08:50–09:40", subject: "통합사회",    neisLabel: "통합사회1", grade: 2, classNo: "3", room: "2-3", roster: "2-3",
    checked: true,  synced: true,  absences: 1, note: "김도현 결석" },
  { id: "s2", period: 2, time: "09:50–10:40", subject: "한국지리",    neisLabel: "한국지리", grade: 2, classNo: "1", room: "2-1", roster: "2-1",
    checked: true,  synced: true,  absences: 0, note: "전원 출석" },
  { id: "s3", period: 3, time: "10:50–11:40", subject: "세계사",      neisLabel: "세계사",   grade: 3, classNo: "4", room: "3-4", roster: "3-4",
    checked: true,  synced: false, absences: 2, note: "이수민 지각, 박지후 결석" },
  { id: "s4", period: 4, time: "11:50–12:40", subject: "동아시아사",  neisLabel: "동아시아사", grade: 3, classNo: "2", room: "3-2", roster: "3-2",
    checked: false, synced: false, absences: 0, note: "" },
  { id: "s5", period: 6, time: "14:00–14:50", subject: "통합사회",    neisLabel: "통합사회1", grade: 2, classNo: "5", room: "2-5", roster: "2-5",
    checked: false, synced: false, absences: 0, note: "" },
  { id: "s6", period: 7, time: "15:00–15:50", subject: "한국지리",    neisLabel: "한국지리", grade: 2, classNo: "2", room: "2-2", roster: "2-2",
    checked: false, synced: false, absences: 0, note: "" },
];

const TIMETABLE = [
  { day: "월", period: 1, grade: 2, classNo: "3", subject: "통합사회",   neis: "통합사회1" },
  { day: "월", period: 2, grade: 2, classNo: "1", subject: "한국지리",   neis: "한국지리" },
  { day: "월", period: 3, grade: 3, classNo: "4", subject: "세계사",     neis: "세계사" },
  { day: "월", period: 4, grade: 3, classNo: "2", subject: "동아시아사", neis: "동아시아사" },
  { day: "월", period: 6, grade: 2, classNo: "5", subject: "통합사회",   neis: "통합사회1" },
  { day: "월", period: 7, grade: 2, classNo: "2", subject: "한국지리",   neis: "한국지리" },
  { day: "화", period: 1, grade: 3, classNo: "1", subject: "세계사",     neis: "세계사" },
  { day: "화", period: 2, grade: 3, classNo: "3", subject: "동아시아사", neis: "동아시아사" },
  { day: "화", period: 4, grade: 2, classNo: "4", subject: "통합사회",   neis: "통합사회1" },
  { day: "화", period: 5, grade: 2, classNo: "6", subject: "한국지리",   neis: "한국지리" },
  { day: "수", period: 2, grade: 2, classNo: "3", subject: "한국지리",   neis: "한국지리" },
  { day: "수", period: 3, grade: 3, classNo: "2", subject: "세계사",     neis: "세계사" },
  { day: "수", period: 5, grade: 3, classNo: "4", subject: "동아시아사", neis: "동아시아사" },
  { day: "목", period: 1, grade: 2, classNo: "1", subject: "통합사회",   neis: "통합사회1" },
  { day: "목", period: 3, grade: 2, classNo: "5", subject: "한국지리",   neis: "한국지리" },
  { day: "목", period: 6, grade: 3, classNo: "3", subject: "세계사",     neis: "세계사" },
  { day: "금", period: 2, grade: 3, classNo: "1", subject: "동아시아사", neis: "동아시아사" },
  { day: "금", period: 4, grade: 2, classNo: "2", subject: "통합사회",   neis: "통합사회1" },
];

const NAMES_A = ["김도윤","김민서","김서준","김시우","김예린","김지호","김하린","남지안","문유빈","박건우","박서연","박지후","배채원","백민준","서지우","손예준","송하윤","신재희","안유나","양도현","오수아","유지민","윤태림","이도현","이서윤","이수민","이지아","임채원","장시윤","정수빈","조유진","최다은","한주원","홍시현","황예원"];
const NAMES_B = ["강민재","권서윤","김규리","김도연","김서우","김세아","김준호","남다영","문채린","박다윤","박주원","백지호","서민준","성유찬","송예서","신하윤","오지후","유다은","윤서율","이건희","이나윤","이주은","임도현","전유빈","정지훈","조민지","최시온","한태민","허지안","홍서준"];
const roster = (names) => names.map((n, i) => ({ n: i+1, name: n }));

const ROSTERS = {
  "2-1": roster(NAMES_A.slice(0, 28)),
  "2-2": roster(NAMES_B.slice(0, 26)),
  "2-3": roster(NAMES_A.slice(2, 30)),
  "2-4": roster(NAMES_B.slice(1, 27)),
  "2-5": roster(NAMES_A.slice(5, 30)),
  "2-6": roster(NAMES_B.slice(3, 28)),
  "3-1": roster(NAMES_A.slice(0, 25)),
  "3-2": roster(NAMES_B.slice(0, 25)),
  "3-3": roster(NAMES_A.slice(4, 28)),
  "3-4": roster(NAMES_B.slice(2, 26)),
};

Object.assign(window, { TODAY_SLOTS, TIMETABLE, ROSTERS });
