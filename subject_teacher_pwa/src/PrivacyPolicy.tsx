/** 개인정보처리방침 — 전문(요지) 화면. 설정 탭에서 진입한다.
 *  정본: docs/legal/privacy-policy.md */
export function PrivacyPolicy({ onClose }: { onClose: () => void }) {
  return (
    <div className="sheet" role="dialog" aria-modal="true" aria-label="개인정보처리방침">
      <div className="sheet-panel policy-panel">
        <div className="grabber" />
        <div className="sheet-head">
          <div>
            <p className="muted">체크온 · 시행일 2026-06-24</p>
            <h2>개인정보처리방침</h2>
          </div>
          <button className="icon-btn" type="button" onClick={onClose} aria-label="닫기">×</button>
        </div>
        <div className="policy-body">
          <p>체크온은 교사가 학생 출결을 NEIS에 자동 반영·정리하도록 돕는 개인 제작 도구입니다.
            별도의 운영 서버 없이, 데이터는 교사 본인 Google Drive와 기기에만 저장됩니다.</p>

          <h3>1. 처리하는 항목과 목적</h3>
          <ul>
            <li>목적: 학생 출결의 NEIS 자동 반영·정리</li>
            <li>클라우드(교사 Google Drive 숨김 폴더): 학생 <b>학번</b>·출결 기록 — <b>이름은 저장하지 않음(가명)</b></li>
            <li>기기 로컬에만: 학생 이름·NEIS 인증서 비밀번호·설정 (암호화 저장)</li>
            <li>Google 로그인 토큰: 임시 사용(영구 저장하지 않음)</li>
          </ul>

          <h3>2. 보유 및 파기</h3>
          <p>출결·설정 데이터는 교사 본인 Drive에 보관되며, 삭제하거나 ‘로그아웃(연결 해제)’ 시 파기됩니다.
            운영자는 별도 서버에 개인정보를 보관하지 않습니다.</p>

          <h3>3. 처리위탁 및 국외 이전</h3>
          <p>저장 인프라는 Google LLC(Google Drive)이며, 데이터는 교사 본인 Google 계정(미국 등 국외 서버 포함)에
            보관될 수 있습니다. 앱은 Drive 숨김 폴더(drive.appdata) 권한 1개만 사용합니다. NEIS 입력은 교사가
            직접 로그인하여 수행합니다.</p>

          <h3>4. 안전성 확보 조치</h3>
          <p>최소수집·가명처리(이름 미저장), 기기 로컬의 이름·비밀번호 DPAPI 암호화, 권한 최소화, HTTPS 통신.</p>

          <h3>5. 정보주체의 권리 · 만 14세 미만</h3>
          <p>정보주체 또는 법정대리인은 열람·정정·삭제·처리정지를 요구할 수 있습니다. 만 14세 미만 학생의
            개인정보 보호와 법정대리인 동의 등의 관리 책임은 소속 학교에 있으며, 본 앱은 클라우드에 학번만(가명)
            처리합니다.</p>

          <h3>6. 문의</h3>
          <p>운영: 개인 개발자 · 문의(열람·정정·삭제): <b>ghga20@gmail.com</b></p>

          <p className="policy-note">※ 본 방침은 참고용 초안이며 법률 자문이 아닙니다. 변경 시 앱 내에서 고지합니다.</p>
        </div>
      </div>
    </div>
  );
}
