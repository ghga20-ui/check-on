/* global React, Icon, Chip, StatusChip, Checkbox, Ring, Bar, Banner, EmptyState, Toggle, Segmented, TODAY_SLOTS, ROSTERS */
const { useState, useEffect, useMemo } = React;

/* Student-check sheet (modal) */
const ClassSheet = ({ slot, onClose, onSaveMarks, currentMarks, appendLog }) => {
  const students = ROSTERS[slot.roster] || [];
  const [marks, setMarks] = useState(() => ({ ...currentMarks }));
  const [filter, setFilter] = useState("all");

  const counts = useMemo(() => {
    const c = { present: 0, absent: 0, late: 0, sick: 0, unset: 0 };
    students.forEach(s => {
      const m = marks[s.n] || "present";
      c[m] = (c[m] || 0) + 1;
    });
    return c;
  }, [marks, students]);

  const setAll = (m) => {
    const next = {};
    students.forEach(s => next[s.n] = m);
    setMarks(next);
  };

  const toggle = (n) => {
    const cur = marks[n] || "present";
    const order = ["present", "absent", "late", "sick"];
    const next = order[(order.indexOf(cur) + 1) % order.length];
    setMarks(m => ({ ...m, [n]: next }));
  };

  const filtered = filter === "all" ? students : students.filter(s => (marks[s.n] || "present") === filter);

  return (
    <div className="sheet-scrim" onClick={onClose}>
      <div className="sheet" onClick={e => e.stopPropagation()}>
        <div className="sheet-grabber" />
        <div className="sheet-head">
          <div>
            <div className="st-t">{slot.period}교시 · {slot.subject}</div>
            <div className="st-s">{slot.grade}학년 {slot.classNo}반 · {slot.room} · {slot.time}</div>
          </div>
          <button className="tb-iconbtn" onClick={onClose}><Icon name="x" /></button>
        </div>
        <div className="sheet-body">
          <div style={{display:"flex",gap:10,alignItems:"center",marginBottom:14,flexWrap:"wrap"}}>
            <Chip kind="info">총 {students.length}명</Chip>
            <Chip kind="ok">출석 {counts.present}</Chip>
            <Chip kind="bad">결석 {counts.absent}</Chip>
            <Chip kind="warn">지각 {counts.late}</Chip>
            <Chip kind="gray" dot={false}>조퇴·병결 {counts.sick}</Chip>
            <div style={{flex:1}}/>
            <button className="tb-btn ghost" onClick={() => setAll("present")}>
              <Icon name="check" size={14}/> 전원 출석
            </button>
          </div>

          <div className="mark-legend">
            {[
              ["all", "전체", "var(--fg-3)"],
              ["present", "출석", "var(--green)"],
              ["absent", "결석", "var(--red)"],
              ["late", "지각", "var(--orange)"],
              ["sick", "조퇴·병결", "var(--purple)"],
            ].map(([v, l, c]) => (
              <button key={v} className={filter === v ? "on" : ""} onClick={() => setFilter(v)}>
                <span className="dot" style={{background: c}}/>{l}
              </button>
            ))}
          </div>

          <div className="stu-grid">
            {filtered.map(s => {
              const m = marks[s.n] || "present";
              return (
                <div key={s.n} className="stu-row" data-mark={m} onClick={() => toggle(s.n)}>
                  <span className="n">{s.n}</span>
                  <span className="nm">{s.name}</span>
                  <span className="state">
                    {m === "present" && <Icon name="check" size={12}/>}
                    {m === "absent"  && <Icon name="x" size={12}/>}
                    {m === "late"    && "지"}
                    {m === "sick"    && "병"}
                  </span>
                </div>
              );
            })}
          </div>
          <p style={{fontSize:12,color:"var(--fg-3)",marginTop:14}}>학생 행을 눌러 출석 → 결석 → 지각 → 조퇴·병결 순서로 변경할 수 있어요.</p>
        </div>
        <div className="sheet-foot">
          <button className="tb-btn" onClick={onClose}>취소</button>
          <button className="tb-btn primary" onClick={() => { onSaveMarks(slot.id, marks); appendLog("OK", `${slot.grade}-${slot.classNo} ${slot.subject} 체크 저장 (결석 ${counts.absent}, 지각 ${counts.late})`); onClose(); }}>
            <Icon name="check" size={14}/> 저장
          </button>
        </div>
      </div>
    </div>
  );
};

const RunView = ({ date, setDate, password, setPassword, closeAfter, setCloseAfter,
                   slots, setSlots, running, progress, runLog, startRun, appendLog }) => {
  const [openSlot, setOpenSlot] = useState(null);
  const [marksById, setMarksById] = useState({});

  const total = slots.length;
  const checked = slots.filter(s => s.checked).length;
  const synced = slots.filter(s => s.synced).length;
  const pending = total - synced;
  const absent = slots.reduce((a, s) => a + (s.absences || 0), 0);

  const onSaveMarks = (id, marks) => {
    setMarksById(m => ({ ...m, [id]: marks }));
    const absCount = Object.values(marks).filter(v => v && v !== "present").length;
    setSlots(prev => prev.map(s => s.id === id ? { ...s, checked: true, absences: absCount, note: absCount ? `결석·지각 ${absCount}명` : "전원 출석" } : s));
  };

  return (
    <>
      <div className="topbar">
        <Icon name="bolt" size={16}/>
        <span className="title">실행</span>
        <span className="sub">· 오늘의 수업을 확인하고 NEIS에 반영합니다</span>
        <div className="topbar-actions">
          <button className="tb-btn"><Icon name="refresh" size={14}/> 새로고침</button>
          <span className="divider"/>
          <Checkbox checked={closeAfter} onChange={setCloseAfter} label="출결마감까지"/>
          <button className="run-cta" onClick={startRun} disabled={running || pending === 0}>
            {running
              ? <><Icon name="clock" size={16}/> 반영 중… {progress.done}/{progress.total}</>
              : pending === 0
                ? <><Icon name="check" size={14}/> 모두 반영됨</>
                : <><Icon name="play" size={14}/> NEIS 반영 실행 · {pending}건</>}
          </button>
        </div>
      </div>

      <div className="content">
        <div className="page-hero">
          <div>
            <h1>오늘, 월요일</h1>
            <div className="subtitle">{date} · Drive에서 확인한 출결을 NEIS 과목별 출결관리에 그대로 반영합니다.</div>
          </div>
          <div className="hero-actions">
            <div className="field" style={{width:160}}>
              <label>날짜</label>
              <input className="input" value={date} onChange={e => setDate(e.target.value)} />
            </div>
            <div className="field" style={{width:200}}>
              <label>교사 인증서 비밀번호</label>
              <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••"/>
            </div>
          </div>
        </div>

        {(running || progress.state === "done") && (
          <div className="inline-progress">
            <div className="ip-row">
              <strong>
                {running ? "NEIS 반영 중" : "마지막 실행 완료"}
              </strong>
              {progress.current && <span className="ip-cur">· {progress.current}</span>}
              <span className="ip-count">{progress.done}/{progress.total} ({Math.round(progress.done/Math.max(progress.total,1)*100)}%)</span>
            </div>
            <Bar pct={progress.total ? progress.done/progress.total*100 : 0} ok={progress.state==="done"}/>
          </div>
        )}

        {pending > 0 && !running && (
          <Banner kind="info" icon="info" title={`${pending}건의 수업이 아직 NEIS에 반영되지 않았습니다`}>
            하단의 NEIS 반영 실행 버튼으로 한 번에 처리할 수 있어요.
          </Banner>
        )}

        <div className="stat-grid" style={{marginTop:16}}>
          <div className="stat-card success">
            <div className="label"><span className="dot" style={{background:"var(--green)"}}/>연결 상태</div>
            <div className="value">연결됨</div>
            <div className="note ok">Google Drive · appDataFolder</div>
          </div>
          <div className="stat-card accent">
            <div className="label"><span className="dot"/>오늘 수업</div>
            <div className="value">{total}<span className="unit">건</span></div>
            <div className="note">체크 완료 {checked} / 체크 대기 {total - checked}</div>
          </div>
          <div className="stat-card">
            <div className="label"><span className="dot" style={{background:"var(--orange)"}}/>NEIS 반영</div>
            <div className="value">{synced}<span className="unit">/ {total}</span></div>
            <div className="note warn">{pending > 0 ? `미반영 ${pending}건` : "모두 반영됨"}</div>
          </div>
          <div className="stat-card">
            <div className="label"><span className="dot" style={{background:"var(--red)"}}/>결석·지각</div>
            <div className="value">{absent}<span className="unit">명</span></div>
            <div className="note">오늘 기준 누계</div>
          </div>
        </div>

        <div className="section">
          <div className="section-head">
            <div>
              <h2>오늘 수업</h2>
              <div className="desc">카드를 누르면 학생별 출결을 확인하고 바로 수정할 수 있어요.</div>
            </div>
            <div className="section-head-actions">
              <Segmented value="all" onChange={()=>{}} options={[
                {value:"all", label:"전체"},
                {value:"pending", label:`미반영 ${pending}`},
                {value:"done", label:"반영됨"},
              ]}/>
            </div>
          </div>

          <div className="list-group">
            <div className="list-header" style={{gridTemplateColumns:"80px 1.6fr 80px 80px 130px 1fr auto"}}>
              <div>교시</div>
              <div>과목 · NEIS 표시명</div>
              <div>학년</div>
              <div>반</div>
              <div>체크</div>
              <div>상태</div>
              <div></div>
            </div>
            {slots.length === 0 ? (
              <EmptyState icon="calendar" title="오늘 수업이 없어요"
                title="오늘 수업이 없어요"
                body="시간표에 오늘 요일의 수업 슬롯을 추가하면 여기서 보여드려요." />
            ) : slots.map(s => (
              <div key={s.id} className="list-row" style={{gridTemplateColumns:"80px 1.6fr 80px 80px 130px 1fr auto"}}
                   onClick={() => setOpenSlot(s)}>
                <div className="period">
                  <span className="p-num">{s.period}</span>
                </div>
                <div className="subject">
                  {s.subject}
                  <div className="sub2">NEIS: {s.neisLabel} · {s.room} · {s.time}</div>
                </div>
                <div className="klass">{s.grade}</div>
                <div className="klass">{s.classNo}</div>
                <div>
                  {s.checked
                    ? <Chip kind="ok"><Icon name="check" size={11}/> 완료 · 결석 {s.absences}</Chip>
                    : <Chip kind="gray">체크 대기</Chip>}
                </div>
                <div><StatusChip item={s}/></div>
                <div className="chev"><Icon name="chev-r" size={16}/></div>
              </div>
            ))}
          </div>

        </div>
      </div>

      {openSlot && (
        <ClassSheet
          slot={openSlot}
          onClose={() => setOpenSlot(null)}
          currentMarks={marksById[openSlot.id] || {}}
          onSaveMarks={onSaveMarks}
          appendLog={appendLog}
        />
      )}
    </>
  );
};

window.RunView = RunView;
