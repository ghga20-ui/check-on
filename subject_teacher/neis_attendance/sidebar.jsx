/* global React, Icon, TODAY_SLOTS */
const Sidebar = ({ route, setRoute, connection }) => {
  const pending = TODAY_SLOTS.filter(s => !s.synced).length;
  const unchecked = TODAY_SLOTS.filter(s => !s.checked).length;
  return (
    <aside className="sidebar">
      <div className="sb-brand">
        <div className="sb-brand-mark">나</div>
        <div className="sb-brand-text">
          <div className="t1">출결관리</div>
          <div className="t2">교과교사용 · v2.0</div>
        </div>
      </div>

      <div className="sb-search">
        <Icon name="search" size={14} />
        <input placeholder="검색" />
        <span className="kbd">⌘F</span>
      </div>

      <div className="sb-section-label">오늘</div>
      <div className="sb-list">
        <button className="sb-item" aria-selected={route === "run"} onClick={() => setRoute("run")}>
          <span className="sb-icon"><Icon name="bolt" size={17} /></span>
          <span className="sb-label">실행</span>
          {unchecked > 0 && <span className="sb-count">{unchecked}</span>}
        </button>
        <button className="sb-item" aria-selected={route === "today"} onClick={() => setRoute("today")}>
          <span className="sb-icon"><Icon name="calendar" size={17} /></span>
          <span className="sb-label">오늘 수업</span>
          <span className="sb-count">{TODAY_SLOTS.length}</span>
        </button>
        <button className="sb-item" aria-selected={route === "pending"} onClick={() => setRoute("pending")}>
          <span className="sb-icon"><Icon name="clock" size={17} /></span>
          <span className="sb-label">반영 대기</span>
          {pending > 0 && <span className="sb-count">{pending}</span>}
        </button>
      </div>

      <div className="sb-divider" />
      <div className="sb-section-label">설정</div>
      <div className="sb-list">
        <button className="sb-item" aria-selected={route === "basics"} onClick={() => setRoute("basics")}>
          <span className="sb-icon"><Icon name="gear" size={17} /></span>
          <span className="sb-label">기본 정보</span>
        </button>
        <button className="sb-item" aria-selected={route === "timetable"} onClick={() => setRoute("timetable")}>
          <span className="sb-icon"><Icon name="board" size={17} /></span>
          <span className="sb-label">시간표</span>
          <span className="sb-count">13</span>
        </button>
        <button className="sb-item" aria-selected={route === "roster"} onClick={() => setRoute("roster")}>
          <span className="sb-icon"><Icon name="users" size={17} /></span>
          <span className="sb-label">학생 명부</span>
          <span className="sb-count">3</span>
        </button>
      </div>

      <div className="sb-divider" />
      <div className="sb-section-label">시스템</div>
      <div className="sb-list">
        <button className="sb-item" aria-selected={route === "drive"} onClick={() => setRoute("drive")}>
          <span className="sb-icon"><Icon name="cloud" size={17} /></span>
          <span className="sb-label">Google Drive</span>
        </button>
        <button className="sb-item" aria-selected={route === "auth"} onClick={() => setRoute("auth")}>
          <span className="sb-icon"><Icon name="key" size={17} /></span>
          <span className="sb-label">OAuth 인증</span>
        </button>
      </div>

      <div className="sb-footer">
        <div className="sb-avatar">박</div>
        <div className="sb-foot-text">
          <div className="t1">박민영 선생님</div>
          <div className="t2">사회과 · 2학년 부장</div>
        </div>
        <div className="sb-conn-dot" data-state={connection} title={connection === "ok" ? "Drive 연결됨" : connection === "error" ? "연결 오류" : "연결 확인 전"}/>
      </div>
    </aside>
  );
};
window.Sidebar = Sidebar;
