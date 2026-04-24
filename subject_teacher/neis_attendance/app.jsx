/* global React, ReactDOM, Icon, LogDock, RunView, BasicsView, TimetableView, RosterView, DriveView, AuthView, PlaceholderView, TODAY_SLOTS, TIMETABLE, ROSTERS, TweaksPanel, useTweaks, TweakSection, TweakRadio, TweakToggle, TweakSlider, TweakColor, TweakSelect */
const { useState, useEffect, useMemo } = React;

const NAV = [
  { group: "작업",  items: [
    { key: "run",      label: "실행",         icon: "bolt",    badge: "대기 3" },
  ]},
  { group: "설정",  items: [
    { key: "basics",   label: "기본 정보",    icon: "gear" },
    { key: "timetable",label: "시간표",       icon: "board" },
    { key: "roster",   label: "학생 명부",    icon: "users" },
  ]},
  { group: "연결",  items: [
    { key: "drive",    label: "Google Drive", icon: "cloud" },
    { key: "auth",     label: "OAuth 인증",   icon: "key" },
  ]},
  { group: "기타",  items: [
    { key: "log",      label: "실행 기록",    icon: "list" },
    { key: "schedule", label: "예약 실행",    icon: "calendar" },
  ]},
];

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "#0A84FF",
  "theme": "light",
  "density": "cozy",
  "sidebarMode": "expanded",
  "showLog": true,
  "corner": 18
}/*EDITMODE-END*/;

const now = () => {
  const d = new Date();
  return `${d.getHours().toString().padStart(2,"0")}:${d.getMinutes().toString().padStart(2,"0")}:${d.getSeconds().toString().padStart(2,"0")}`;
};

function App() {
  const [tweaks, setTweaks] = useTweaks(TWEAK_DEFAULTS);
  const [page, setPage] = useState("run");
  const [slots, setSlots] = useState(TODAY_SLOTS);
  const [timetable, setTimetable] = useState(TIMETABLE);
  const [rosters, setRosters] = useState(ROSTERS);
  const [date, setDate] = useState("2026-04-20 (월)");
  const [password, setPassword] = useState("");
  const [closeAfter, setCloseAfter] = useState(true);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0, current: "", state: "idle" });
  const [logCollapsed, setLogCollapsed] = useState(true);
  const [logLines, setLogLines] = useState([
    { ts: "09:02:14", lv: "INFO", msg: "앱 실행 — subject_teacher v0.4.1" },
    { ts: "09:02:14", lv: "OK",   msg: "Drive appDataFolder 연결 · 3개 파일 감지" },
    { ts: "09:02:15", lv: "INFO", msg: "settings.json, timetable.json, students.json 동기화 완료" },
    { ts: "09:02:15", lv: "OK",   msg: "오늘 수업 6건 로드 — 3건 반영됨, 3건 대기" },
  ]);
  const [settings, setSettings] = useState({
    region: "서울", year: "2026", term: "1", effectiveFrom: "2026-03-02", closeByDefault: true
  });

  const appendLog = (lv, msg) => setLogLines(l => [...l, { ts: now(), lv, msg }]);
  const clearLog = () => setLogLines([]);

  /* Apply theme / accent globally */
  useEffect(() => {
    document.documentElement.dataset.theme = tweaks.theme;
    document.documentElement.dataset.density = tweaks.density;
    document.documentElement.dataset.sidebar = tweaks.sidebarMode;
    document.documentElement.style.setProperty("--accent", tweaks.accent);
    document.documentElement.style.setProperty("--accent-hover", tweaks.accent);
    document.documentElement.style.setProperty("--accent-soft",
      tweaks.accent.startsWith("#")
        ? `${tweaks.accent}22`
        : tweaks.accent);
    document.documentElement.style.setProperty("--radius-lg", tweaks.corner + "px");
  }, [tweaks]);

  const startRun = () => {
    const pending = slots.filter(s => !s.synced);
    if (!pending.length) { appendLog("INFO", "모든 수업이 이미 반영됨"); return; }
    setRunning(true);
    setProgress({ done: 0, total: pending.length, current: pending[0] ? `${pending[0].grade}-${pending[0].classNo} ${pending[0].subject}` : "", state: "running" });
    appendLog("INFO", `NEIS 반영 실행 — 대상 ${pending.length}건`);
    let i = 0;
    const tick = () => {
      if (i >= pending.length) {
        setRunning(false);
        setProgress(p => ({ ...p, current: "", state: "done" }));
        appendLog("OK", `실행 완료 — ${pending.length}건 반영${closeAfter ? ", 출결마감" : ""}`);
        return;
      }
      const cur = pending[i];
      setProgress({ done: i, total: pending.length, current: `${cur.grade}-${cur.classNo} ${cur.subject}`, state: "running" });
      appendLog("INFO", `→ ${cur.grade}-${cur.classNo} ${cur.subject} (${cur.period}교시) 작성 중`);
      setTimeout(() => {
        setSlots(sl => sl.map(s => s.id === cur.id ? { ...s, synced: true } : s));
        appendLog("OK", `✓ ${cur.grade}-${cur.classNo} ${cur.subject} 반영됨`);
        i += 1;
        setProgress(p => ({ ...p, done: i }));
        setTimeout(tick, 260);
      }, 520);
    };
    setTimeout(tick, 300);
  };

  const pendingCount = slots.filter(s => !s.synced).length;
  const navWithBadges = NAV.map(g => ({
    ...g, items: g.items.map(it => it.key === "run" ? { ...it, badge: pendingCount ? `${pendingCount}` : null } : it)
  }));

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sb-head">
          <div className="sb-logo"><Icon name="school" size={22}/></div>
          <div className="sb-name-wrap">
            <div className="sb-name">출결 자동화</div>
            <div className="sb-sub">교과교사용</div>
          </div>
          <button className="sb-collapse" onClick={() => setTweaks({ sidebarMode: tweaks.sidebarMode === "collapsed" ? "expanded" : "collapsed" })} title="사이드바 접기">
            <Icon name={tweaks.sidebarMode === "collapsed" ? "chev-r" : "chev-l"} size={16}/>
          </button>
        </div>

        <div className="sb-search">
          <Icon name="search" size={14}/>
          <input placeholder="검색"/>
        </div>

        {navWithBadges.map(group => (
          <div key={group.group}>
            <div className="sb-section">{group.group}</div>
            <div className="sb-list">
              {group.items.map(it => (
                <button key={it.key}
                  className={`sb-item ${page === it.key ? "active" : ""}`}
                  onClick={() => setPage(it.key)}>
                  <span className="sb-ic"><Icon name={it.icon} size={17}/></span>
                  <span>{it.label}</span>
                  {it.badge && <span className="count">{it.badge}</span>}
                </button>
              ))}
            </div>
          </div>
        ))}

        <div className="sb-foot">
          <div className="avatar">박</div>
          <div className="sb-user-wrap">
            <div className="sb-user">박민영</div>
            <div className="sb-role">사회과 · 2년차</div>
          </div>
        </div>
      </aside>

      <main className="main">
        {page === "run"       && <RunView {...{date,setDate,password,setPassword,closeAfter,setCloseAfter,slots,setSlots,running,progress,runLog:logLines,startRun,appendLog}}/>}
        {page === "basics"    && <BasicsView settings={settings} setSettings={setSettings} appendLog={appendLog}/>}
        {page === "timetable" && <TimetableView rows={timetable} setRows={setTimetable} appendLog={appendLog}/>}
        {page === "roster"    && <RosterView rosters={rosters} setRosters={setRosters} appendLog={appendLog}/>}
        {page === "drive"     && <DriveView appendLog={appendLog}/>}
        {page === "auth"      && <AuthView appendLog={appendLog}/>}
        {page === "log"       && <PlaceholderView title="실행 기록" icon="list" body="이전 실행의 성공·실패와 변경 내역을 한 번에 확인합니다."/>}
        {page === "schedule"  && <PlaceholderView title="예약 실행" icon="calendar" body="매일 지정된 시각에 자동으로 실행하도록 예약합니다."/>}
      </main>

      {tweaks.showLog && (
        <LogDock lines={logLines} collapsed={logCollapsed} setCollapsed={setLogCollapsed} clear={clearLog}/>
      )}

      <TweaksPanel>
        <TweakSection title="외관">
          <TweakRadio label="테마" value={tweaks.theme} onChange={v=>setTweaks({theme:v})}
            options={[{value:"light",label:"라이트"},{value:"dark",label:"다크"}]}/>
          <TweakColor label="액센트" value={tweaks.accent} onChange={v=>setTweaks({accent:v})}
            presets={["#0A84FF","#5E5CE6","#FF9F0A","#30D158","#BF5AF2","#FF375F"]}/>
          <TweakSlider label="모서리 둥글기" value={tweaks.corner} onChange={v=>setTweaks({corner:v})} min={6} max={28} step={1}/>
        </TweakSection>
        <TweakSection title="레이아웃">
          <TweakRadio label="사이드바" value={tweaks.sidebarMode} onChange={v=>setTweaks({sidebarMode:v})}
            options={[{value:"expanded",label:"펼침"},{value:"collapsed",label:"접힘"}]}/>
          <TweakRadio label="밀도" value={tweaks.density} onChange={v=>setTweaks({density:v})}
            options={[{value:"compact",label:"조밀"},{value:"cozy",label:"기본"},{value:"roomy",label:"넓게"}]}/>
          <TweakToggle label="하단 로그 도크" value={tweaks.showLog} onChange={v=>setTweaks({showLog:v})}/>
        </TweakSection>
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
