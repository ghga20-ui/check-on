// One-time pairing screen: receives the E2E sync key from the desktop app
// via QR scan (BarcodeDetector, falling back to jsQR) or manual code entry.
// The key goes straight into IndexedDB and is never sent anywhere.

import { useEffect, useRef, useState } from "react";
import jsQR from "jsqr";
import { parsePairingPayload } from "./lib/crypto";
import { saveSyncKey } from "./lib/keyStore";
import { resetSyncKeyCache } from "./lib/drive";

interface QrDetector {
  detect(video: HTMLVideoElement): Promise<Array<{ rawValue: string }>>;
}

function makeBarcodeDetector(): QrDetector | null {
  const ctor = (window as unknown as {
    BarcodeDetector?: new (options: { formats: string[] }) => QrDetector;
  }).BarcodeDetector;
  return ctor ? new ctor({ formats: ["qr_code"] }) : null;
}

export default function Pairing({ onPaired }: { onPaired: () => void }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [scanning, setScanning] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const stopRef = useRef<() => void>(() => {});

  const accept = async (text: string) => {
    try {
      const key = parsePairingPayload(text);
      await saveSyncKey(key);
      resetSyncKeyCache();
      stopRef.current();
      onPaired();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "연결 코드 형식이 올바르지 않습니다.");
    }
  };

  const startScan = async () => {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      // The <video> stays mounted (hidden while idle), so the ref is always
      // available here — attaching after a state-triggered re-render is racy.
      const video = videoRef.current;
      if (!video) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      setScanning(true);
      video.srcObject = stream;
      await video.play();
      const canvas = document.createElement("canvas");
      let active = true;
      stopRef.current = () => {
        active = false;
        stream.getTracks().forEach((track) => track.stop());
        setScanning(false);
      };
      const detector = makeBarcodeDetector();
      const tick = async () => {
        if (!active) return;
        let text: string | null = null;
        if (detector) {
          const found = await detector.detect(video).catch(() => []);
          text = found[0]?.rawValue ?? null;
        } else if (video.videoWidth > 0) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const ctx = canvas.getContext("2d");
          if (ctx) {
            ctx.drawImage(video, 0, 0);
            const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
            text = jsQR(image.data, image.width, image.height)?.data ?? null;
          }
        }
        if (text) {
          await accept(text);
          return;
        }
        requestAnimationFrame(() => void tick());
      };
      void tick();
    } catch {
      setScanning(false);
      setError("카메라를 열 수 없습니다. 아래에 연결 코드를 직접 입력해 주세요.");
    }
  };

  useEffect(() => () => stopRef.current(), []);

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-mark" aria-hidden="true">🔒</div>
        <h1>데스크톱과 연결</h1>
        <p className="login-tagline">
          선생님의 출결 데이터는 <b>암호화</b>되어 있어, 구글을 포함한 누구도 내용을 볼 수
          없습니다. 이 휴대폰에서 읽으려면 데스크톱과 한 번 연결해 열쇠를 받아야 해요.
        </p>
        <p className="login-note" style={{ marginTop: 4 }}>
          ✓ <b>처음 한 번만</b> 하면 됩니다 — 이후에는 자동으로 연결됩니다.
        </p>

        <ol style={{ textAlign: "left", margin: "12px 0", paddingLeft: 20, lineHeight: 1.7 }}>
          <li>PC에서 <b>체크온 데스크톱 앱</b>을 엽니다</li>
          <li><b>설정 → 기본 정보</b> 맨 아래 <b>모바일 연결 암호화</b>로 이동</li>
          <li><b>[암호화 켜기]</b> 또는 <b>[휴대폰 연결 QR 보기]</b>를 눌러 QR코드를 띄웁니다</li>
          <li>아래 <b>[QR코드 스캔]</b>으로 촬영하면 끝!</li>
        </ol>

        <video
          ref={videoRef}
          playsInline
          muted
          style={{
            width: "100%",
            borderRadius: 12,
            display: scanning ? "block" : "none",
          }}
        />
        {!scanning && (
          <button className="login-btn" type="button" onClick={() => void startScan()}>
            QR코드 스캔
          </button>
        )}

        <label htmlFor="pairing-code" style={{ display: "block", marginTop: 16 }}>
          연결 코드 (카메라를 쓸 수 없을 때)
        </label>
        <input
          id="pairing-code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="checkon.sync.v1:..."
          autoComplete="off"
          spellCheck={false}
          style={{ width: "100%", marginTop: 4 }}
        />
        <button
          className="login-btn"
          type="button"
          style={{ marginTop: 8 }}
          onClick={() => void accept(code)}
        >
          연결
        </button>

        {error && (
          <p className="login-error" role="alert">
            {error}
          </p>
        )}
        <p className="login-note">
          연결 코드는 비밀번호와 같습니다. 다른 사람에게 보여 주거나 메신저로 전송하지
          마세요.
        </p>
      </div>
    </div>
  );
}
