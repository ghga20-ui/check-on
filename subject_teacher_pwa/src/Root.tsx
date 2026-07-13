import { useEffect, useState } from "react";
import App from "./App";
import BrandMark from "./BrandMark";
import Login from "./Login";
import Pairing from "./Pairing";
import { initAuth, isConfigured, requestAccessToken, revoke } from "./lib/auth";
import { PairingRequiredError } from "./lib/drive";
import {
  loadAll,
  loadMonthlyAttendance,
  saveSlotAttendance,
  type LoadedDriveData,
} from "./lib/driveData";
import { clearDriveCache, loadDriveCache, saveDriveCache } from "./lib/localCache";
import type { StudentEntry, TimetableSlot } from "./lib/schemas";
import "./entry.css";

type Phase = "init" | "signedOut" | "loading" | "ready" | "error" | "pairing";

function toLocalIsoDate(date = new Date()): string {
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, "0");
  const day = date.getDate().toString().padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function toAttendanceByDate(data: LoadedDriveData) {
  return data.attendance?.records ?? {};
}

function toRosters(data: LoadedDriveData): Record<string, StudentEntry[]> {
  return data.students?.classes ?? {};
}

function toSlots(data: LoadedDriveData): TimetableSlot[] {
  return data.timetable?.slots ?? [];
}

export default function Root() {
  const [phase, setPhase] = useState<Phase>("init");
  const [error, setError] = useState("");
  const [data, setData] = useState<LoadedDriveData | null>(null);
  // stale=true means `data` came from the local cache and has not been
  // reconciled with Drive yet (App shows a "refresh" affordance).
  const [stale, setStale] = useState(false);
  const today = toLocalIsoDate();

  useEffect(() => {
    if (!isConfigured()) {
      setPhase("error");
      setError("VITE_GOOGLE_CLIENT_ID 가 설정되지 않았습니다.");
      return;
    }
    // Cache-first, never a Google window on load. GIS token requests always show
    // a visible window even with prompt: "", so on mount we only read the local
    // snapshot. A real refresh happens later from a user gesture (onRefresh).
    let cancelled = false;
    loadDriveCache()
      .then((cached) => {
        if (cancelled) return;
        if (cached) {
          setData(cached.data);
          setStale(true);
          setPhase("ready");
        } else {
          setPhase("signedOut");
        }
      })
      .catch(() => {
        if (!cancelled) setPhase("signedOut");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Fetch fresh Drive data, render it, and refresh the local cache. Assumes a
  // valid access token is already in memory (caller obtained it under a gesture).
  const loadFresh = async () => {
    const month = today.slice(0, 7);
    const loaded = await loadAll(month);
    setData(loaded);
    setStale(false);
    setPhase("ready");
    await saveDriveCache(loaded, month);
  };

  // First sign-in from the login screen: obtain a token, load, cache.
  const signIn = async () => {
    setError("");
    setPhase("loading");
    try {
      await initAuth();
      await requestAccessToken();
      await loadFresh();
    } catch (cause) {
      if (cause instanceof PairingRequiredError) {
        setPhase("pairing");
        return;
      }
      setPhase("signedOut");
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  };

  // Revalidate from Drive while App stays on screen (stale banner button).
  // Runs in the user-gesture context so requestAccessToken may show its window.
  const refresh = async () => {
    setError("");
    try {
      await initAuth();
      await requestAccessToken();
      await loadFresh();
    } catch (cause) {
      if (cause instanceof PairingRequiredError) {
        setPhase("pairing");
        return;
      }
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  };

  const signOut = async () => {
    try {
      await revoke();
    } catch {
      // ignore — clearing local state below is what matters
    }
    await clearDriveCache();
    setData(null);
    setStale(false);
    setError("");
    setPhase("signedOut");
  };

  if (phase === "init") {
    return (
      <div className="splash">
        <div className="splash-mark" aria-hidden="true"><BrandMark size={38} /></div>
        <p className="brand-wordmark splash-wordmark">체크온</p>
        <p>불러오는 중…</p>
      </div>
    );
  }

  if (phase === "error") {
    return <Login onSignIn={signIn} notConfigured={!isConfigured()} error={error} />;
  }

  if (phase === "pairing") {
    return (
      <Pairing
        onPaired={() => {
          setPhase("loading");
          loadFresh().catch((cause) => {
            setPhase("signedOut");
            setError(cause instanceof Error ? cause.message : String(cause));
          });
        }}
      />
    );
  }

  if (phase === "ready" && data) {
    // A↔B contract: App gains optional `stale`/`onRefresh` props in a sibling
    // change. Spread them so this file does not depend on which change lands
    // first (see report — a transient tsc error is expected until then).
    const swrProps = { stale, onRefresh: refresh };
    return (
      <App
        initialDate={today}
        slots={toSlots(data)}
        rosters={toRosters(data)}
        initialAttendance={toAttendanceByDate(data)}
        initialMonth={today.slice(0, 7)}
        onSaveSlot={(date, slotId, payload) =>
          saveSlotAttendance(date.slice(0, 7), date, slotId, payload)
        }
        onLoadMonth={async (month) => (await loadMonthlyAttendance(month))?.records ?? {}}
        onSignOut={signOut}
        {...swrProps}
      />
    );
  }

  return <Login onSignIn={signIn} busy={phase === "loading"} error={error} />;
}
