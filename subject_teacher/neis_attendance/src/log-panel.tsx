import React from "react";
const { useEffect, useRef } = React;

export const LogDock = ({ lines, onClose, clear }) => {
  const bodyRef = useRef<any>(null);
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
