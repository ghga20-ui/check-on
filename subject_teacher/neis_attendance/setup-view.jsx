/* global React, Icon, Toggle, Segmented, PillTabs, Banner, EmptyState, Chip, Checkbox, TIMETABLE, ROSTERS */
const { useState, useMemo } = React;

const DAYS = ["월","화","수","목","금"];

const BasicsView = ({ settings, setSettings, appendLog }) => {
  return (
    <>
      <div className="topbar">
        <Icon name="gear" size={16}/>
        <span className="title">기본 정보</span>
        <div className="topbar-actions">
          <button className="tb-btn"><Icon name="cloud" size={14}/> Drive에서 불러오기</button>
          <button className="tb-btn primary" onClick={() => appendLog("OK", "settings.json 저장 완료")}>
            <Icon name="check" size={14}/> 저장
          </button>
        </div>
      </div>
      <div className="content">
        <div className="page-hero">
          <div>
            <h1>기본 정보</h1>
            <div className="subtitle">학교·학기 정보와 실행 기본값을 정리합니다.</div>
          </div>
        </div>

        <div className="list-group form-list">
          <div className="form-row">
            <div><div className="rlabel">교육청</div><div className="rhint">NEIS 주소 라우팅에 사용됩니다.</div></div>
            <div className="rctrl">
              <select className="select" value={settings.region} onChange={e => setSettings({...settings, region: e.target.value})}>
                {["서울","부산","대구","인천","광주","대전","울산","세종","경기","강원","충북","충남","전북","전남","경북","경남","제주"].map(r=>
                  <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div/>
          </div>
          <div className="form-row">
            <div><div className="rlabel">학년도</div></div>
            <div className="rctrl">
              <input className="input" style={{width:140}} value={settings.year} onChange={e => setSettings({...settings, year: e.target.value})}/>
            </div><div/>
          </div>
          <div className="form-row">
            <div><div className="rlabel">학기</div></div>
            <div className="rctrl">
              <Segmented value={settings.term} onChange={v => setSettings({...settings, term: v})}
                options={[{value:"1",label:"1학기"},{value:"2",label:"2학기"}]}/>
            </div><div/>
          </div>
          <div className="form-row">
            <div><div className="rlabel">적용 시작일</div><div className="rhint">이 날짜부터 시간표가 적용됩니다.</div></div>
            <div className="rctrl">
              <input className="input" style={{width:180}} value={settings.effectiveFrom} onChange={e=>setSettings({...settings, effectiveFrom: e.target.value})}/>
            </div><div/>
          </div>
          <div className="form-row">
            <div><div className="rlabel">출결마감 자동 실행</div><div className="rhint">실행 탭의 기본값으로 사용돼요.</div></div>
            <div className="rctrl">
              <Toggle on={settings.closeByDefault} onChange={v => setSettings({...settings, closeByDefault: v})}/>
            </div><div/>
          </div>
        </div>

        <div className="section">
          <div className="section-head">
            <div><h2>연결 상태</h2><div className="desc">Google Drive와 인증서의 상태를 확인합니다.</div></div>
          </div>
          <div className="stat-grid" style={{gridTemplateColumns:"repeat(3, minmax(0,1fr))"}}>
            <div className="stat-card success">
              <div className="label"><span className="dot" style={{background:"var(--green)"}}/>Drive</div>
              <div className="value" style={{fontSize:22}}>연결됨</div>
              <div className="note ok">appDataFolder · 3개 파일</div>
            </div>
            <div className="stat-card accent">
              <div className="label"><span className="dot"/>OAuth</div>
              <div className="value" style={{fontSize:22}}>유효</div>
              <div className="note">만료까지 · 43일</div>
            </div>
            <div className="stat-card">
              <div className="label"><span className="dot" style={{background:"var(--orange)"}}/>DPAPI 토큰</div>
              <div className="value" style={{fontSize:22}}>저장됨</div>
              <div className="note">마지막 갱신 2026.04.18</div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

const TimetableView = ({ rows, setRows, appendLog }) => {
  const [selected, setSelected] = useState(new Set());
  const [day, setDay] = useState("전체");

  const filtered = rows.map((r, i) => ({...r, _i: i})).filter(r => day === "전체" || r.day === day);

  const addRow = () => {
    setRows([...rows, {day:"월", period:1, grade:2, classNo:1, subject:"", neis:""}]);
  };
  const removeSelected = () => {
    const keep = rows.filter((_, i) => !selected.has(i));
    setRows(keep); setSelected(new Set());
    appendLog("OK", "선택된 행 삭제됨");
  };
  const updateRow = (i, patch) => {
    setRows(rows.map((r, idx) => idx === i ? {...r, ...patch} : r));
  };
  const toggle = (i) => {
    const n = new Set(selected);
    n.has(i) ? n.delete(i) : n.add(i);
    setSelected(n);
  };

  return (
    <>
      <div className="topbar">
        <Icon name="board" size={16}/>
        <span className="title">시간표</span>
        <span className="sub">· {rows.length}개 수업</span>
        <div className="topbar-actions">
          <button className="tb-btn" onClick={addRow}><Icon name="plus" size={14}/> 행 추가</button>
          {selected.size > 0 && (
            <button className="tb-btn" onClick={removeSelected}><Icon name="trash" size={14}/> 선택 삭제 ({selected.size})</button>
          )}
          <button className="tb-btn primary" onClick={() => appendLog("OK", "timetable.json 저장 완료")}>
            <Icon name="check" size={14}/> 시간표 저장
          </button>
        </div>
      </div>
      <div className="content">
        <div className="page-hero">
          <div>
            <h1>시간표</h1>
            <div className="subtitle">수업 슬롯을 요일별로 정리하고 NEIS 표시명을 맞춥니다.</div>
          </div>
          <PillTabs value={day} onChange={setDay}
            options={[{value:"전체",label:"전체"}, ...DAYS.map(d=>({value:d,label:d+"요일"}))]}/>
        </div>

        <div className="list-group" style={{overflow:"hidden"}}>
          <div className="tt-grid head">
            <div/>
            <div>요일</div>
            <div>교시</div>
            <div>학년</div>
            <div>반</div>
            <div>과목명</div>
            <div>NEIS 표시명</div>
            <div/>
          </div>
          {filtered.length === 0 ? (
            <EmptyState icon="board" title="이 요일에는 수업이 없어요" body="위의 행 추가 버튼으로 수업 슬롯을 추가하세요."/>
          ) : filtered.map(r => (
            <div key={r._i} className="tt-grid">
              <Checkbox checked={selected.has(r._i)} onChange={() => toggle(r._i)}/>
              <div className="cell-input">
                <select className="select" value={r.day} onChange={e => updateRow(r._i, {day: e.target.value})}>
                  {DAYS.map(d => <option key={d}>{d}</option>)}
                </select>
              </div>
              <div className="cell-input">
                <select className="select" value={r.period} onChange={e => updateRow(r._i, {period: +e.target.value})}>
                  {[1,2,3,4,5,6,7].map(n => <option key={n}>{n}</option>)}
                </select>
              </div>
              <div className="cell-input">
                <select className="select" value={r.grade} onChange={e => updateRow(r._i, {grade: +e.target.value})}>
                  {[1,2,3].map(n => <option key={n}>{n}</option>)}
                </select>
              </div>
              <div className="cell-input">
                <input className="input" value={r.classNo} onChange={e => updateRow(r._i, {classNo: e.target.value})}/>
              </div>
              <div className="cell-input">
                <input className="input" value={r.subject} placeholder="과목명" onChange={e => updateRow(r._i, {subject: e.target.value})}/>
              </div>
              <div className="cell-input">
                <input className="input" value={r.neis} placeholder="NEIS 표시명" onChange={e => updateRow(r._i, {neis: e.target.value})}/>
              </div>
              <button className="tb-iconbtn" title="행 삭제" onClick={() => { setRows(rows.filter((_, idx) => idx !== r._i)); appendLog("WARN", "시간표 행 1개 삭제"); }}>
                <Icon name="trash" size={15}/>
              </button>
            </div>
          ))}
        </div>
      </div>
    </>
  );
};

const RosterView = ({ rosters, setRosters, appendLog }) => {
  const keys = Object.keys(rosters);
  const [klass, setKlass] = useState(keys[0]);
  const [paste, setPaste] = useState("");
  const list = rosters[klass] || [];

  const addStudent = () => setRosters({...rosters, [klass]: [...list, {n: list.length + 1, name: ""}]});
  const update = (i, patch) => setRosters({...rosters, [klass]: list.map((s, idx) => idx === i ? {...s, ...patch} : s)});
  const remove = (i) => setRosters({...rosters, [klass]: list.filter((_, idx) => idx !== i)});

  const importPaste = () => {
    const rows = paste.split("\n").map(l => l.trim()).filter(Boolean).map(l => {
      const [n, ...rest] = l.split(/\s+/);
      return { n: parseInt(n, 10), name: rest.join(" ") };
    }).filter(r => !isNaN(r.n) && r.name);
    setRosters({...rosters, [klass]: rows});
    setPaste("");
    appendLog("OK", `${klass} 명부 ${rows.length}명 가져옴`);
  };

  const addKlass = () => {
    const k = prompt("학급 키를 입력하세요 (예: 2-2)");
    if (!k) return;
    setRosters({...rosters, [k]: []});
    setKlass(k);
  };

  return (
    <>
      <div className="topbar">
        <Icon name="users" size={16}/>
        <span className="title">학생 명부</span>
        <span className="sub">· {keys.length}개 학급 · 선택 학급 {list.length}명</span>
        <div className="topbar-actions">
          <button className="tb-btn" onClick={addKlass}><Icon name="plus" size={14}/> 학급 추가</button>
          <button className="tb-btn primary" onClick={() => appendLog("OK", "students.json 저장 완료")}>
            <Icon name="check" size={14}/> 명부 저장
          </button>
        </div>
      </div>
      <div className="content">
        <div className="page-hero">
          <div>
            <h1>학생 명부</h1>
            <div className="subtitle">학급별로 학생을 관리하고 붙여넣기로 빠르게 채우세요.</div>
          </div>
          <PillTabs value={klass} onChange={setKlass} options={keys.map(k => ({value:k, label:k}))}/>
        </div>

        <div className="card card-pad" style={{marginBottom:16}}>
          <div style={{display:"flex",gap:14,alignItems:"flex-start"}}>
            <div style={{flex:1}}>
              <div style={{fontSize:14,fontWeight:600,marginBottom:6,display:"flex",alignItems:"center",gap:8}}>
                <Icon name="paste" size={16}/> 붙여넣기로 빠르게 채우기
              </div>
              <div style={{fontSize:12,color:"var(--fg-3)",marginBottom:10}}>
                각 줄을 <span className="kbd">번호 이름</span> 형식으로 입력하세요. 예: <span className="kbd">18 정수빈</span>
              </div>
              <textarea className="textarea" rows={4} value={paste} onChange={e=>setPaste(e.target.value)}
                placeholder="1 김도윤&#10;2 김민서&#10;3 김서준…"/>
            </div>
            <div style={{display:"flex",flexDirection:"column",gap:8,paddingTop:24}}>
              <button className="tb-btn primary" onClick={importPaste} disabled={!paste.trim()}>
                <Icon name="check" size={14}/> 반영
              </button>
              <button className="tb-btn" onClick={() => setPaste("")}>
                <Icon name="x" size={14}/> 지우기
              </button>
            </div>
          </div>
        </div>

        <div className="list-group">
          <div className="sr-grid head">
            <div/><div>번호</div><div>이름</div><div/>
          </div>
          {list.length === 0 ? (
            <EmptyState icon="users" title="아직 학생이 없어요" body="붙여넣기를 사용하거나 아래에서 행을 추가하세요."/>
          ) : list.map((s, i) => (
            <div key={i} className="sr-grid">
              <div/>
              <div className="num">
                <input className="input" style={{padding:"6px 10px"}} value={s.n} onChange={e=>update(i, {n: +e.target.value})}/>
              </div>
              <div>
                <input className="input" style={{padding:"6px 10px"}} value={s.name} onChange={e=>update(i, {name: e.target.value})}/>
              </div>
              <button className="tb-iconbtn" onClick={() => remove(i)} title="삭제"><Icon name="trash" size={15}/></button>
            </div>
          ))}
          <div style={{padding:10,borderTop:"1px solid var(--sep)"}}>
            <button className="tb-btn ghost" onClick={addStudent}><Icon name="plus" size={14}/> 학생 추가</button>
          </div>
        </div>
      </div>
    </>
  );
};

const DriveView = ({ appendLog }) => (
  <>
    <div className="topbar">
      <Icon name="cloud" size={16}/>
      <span className="title">Google Drive</span>
      <div className="topbar-actions">
        <button className="tb-btn"><Icon name="refresh" size={14}/> 연결 확인</button>
      </div>
    </div>
    <div className="content">
      <div className="page-hero">
        <div><h1>Google Drive</h1><div className="subtitle">appDataFolder에 저장된 설정·시간표·학생 명부 파일을 관리합니다.</div></div>
      </div>
      <Banner kind="info" icon="info" title="appDataFolder는 이 앱만 접근할 수 있는 비공개 영역입니다">
        Drive 앱 사용자 화면에는 보이지 않아요.
      </Banner>
      <div className="list-group" style={{marginTop:16}}>
        {[
          {name:"settings.json", size:"412 B", ts:"2026.04.18 09:12", icon:"gear"},
          {name:"timetable.json", size:"2.1 KB", ts:"2026.04.18 09:12", icon:"board"},
          {name:"students.json",  size:"5.3 KB", ts:"2026.04.18 09:12", icon:"users"},
        ].map(f => (
          <div key={f.name} className="list-row" style={{gridTemplateColumns:"auto 1fr auto auto auto"}}>
            <div className="period"><span className="p-num" style={{background:"var(--accent-soft)",color:"var(--accent)"}}><Icon name={f.icon} size={14}/></span></div>
            <div className="subject">{f.name}<div className="sub2">appDataFolder · JSON</div></div>
            <div className="klass">{f.size}</div>
            <div className="klass">{f.ts}</div>
            <button className="tb-btn ghost" onClick={() => appendLog("INFO", `${f.name} 다운로드`)}>다운로드</button>
          </div>
        ))}
      </div>
    </div>
  </>
);

const AuthView = ({ appendLog }) => (
  <>
    <div className="topbar">
      <Icon name="key" size={16}/>
      <span className="title">OAuth 인증</span>
    </div>
    <div className="content">
      <div className="page-hero"><div><h1>OAuth 인증</h1><div className="subtitle">Drive 읽기·쓰기 권한을 관리합니다.</div></div></div>
      <div className="card card-pad">
        <div style={{display:"flex",alignItems:"center",gap:14}}>
          <div style={{width:44,height:44,borderRadius:12,background:"var(--accent-soft)",display:"grid",placeItems:"center",color:"var(--accent)"}}>
            <Icon name="lock" size={22}/>
          </div>
          <div style={{flex:1}}>
            <div style={{fontWeight:600}}>박민영 · park.myung@school.go.kr</div>
            <div style={{fontSize:13,color:"var(--fg-3)"}}>Drive appDataFolder 권한 · 만료까지 43일</div>
          </div>
          <button className="tb-btn primary" onClick={() => appendLog("INFO", "OAuth 재인증 시작")}>
            <Icon name="refresh" size={14}/> 재인증
          </button>
        </div>
      </div>
    </div>
  </>
);

const PlaceholderView = ({ title, icon, body }) => (
  <>
    <div className="topbar"><Icon name={icon} size={16}/><span className="title">{title}</span></div>
    <div className="content">
      <div className="page-hero"><div><h1>{title}</h1><div className="subtitle">{body}</div></div></div>
      <EmptyState icon={icon} title="준비 중" body="이 화면은 빠르게 열람하기 위한 자리입니다."/>
    </div>
  </>
);

Object.assign(window, { BasicsView, TimetableView, RosterView, DriveView, AuthView, PlaceholderView });
