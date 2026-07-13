import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import {
  slotAttendanceToMarks,
  marksToSlotAttendance,
  type MarksByStudent,
  type StudentMark,
} from "./lib/attendance";
import { loadQueue, persistQueue } from "./lib/db";
import { resetSyncKeyCache } from "./lib/drive";
import { clearSyncKey, loadSyncKey } from "./lib/keyStore";
import {
  computeLessonDisplayStatus,
  getLessonsForDate,
  selectedDateLabel,
} from "./lib/lessonStatus";
import {
  enqueueSave,
  failedItems,
  markStatusByTarget,
  pendingItems,
  type SaveQueueItem,
} from "./lib/offlineQueue";
import type { SlotAttendance, StudentEntry, TimetableSlot } from "./lib/schemas";
import { sampleRosters, sampleSlots } from "./sampleData";
import { PrivacyPolicy } from "./PrivacyPolicy";
import Pairing from "./Pairing";

type AttendanceByDate = Record<string, Record<string, SlotAttendance>>;
type RostersByClass = Record<string, StudentEntry[]>;

/** Persists one slot's attendance (e.g. to Drive). Resolves on success. */
export type SaveSlotHandler = (
  date: string,
  slotId: string,
  payload: SlotAttendance,
) => Promise<void>;

interface AppProps {
  initialDate?: string;
  /** Timetable slots. Defaults to bundled sample data for tests/offline demo. */
  slots?: TimetableSlot[];
  /** Rosters keyed by `grade-classNo`. Defaults to sample data. */
  rosters?: RostersByClass;
  /** Attendance already on Drive, keyed by date then slot id. */
  initialAttendance?: AttendanceByDate;
  /** Month (YYYY-MM) already in initialAttendance, so it is not refetched. */
  initialMonth?: string;
  /** Called after each local save to persist to Drive. Omit for demo mode. */
  onSaveSlot?: SaveSlotHandler;
  /** Loads another month's attendance when the user navigates across months. */
  onLoadMonth?: (month: string) => Promise<AttendanceByDate>;
  /** Signs the teacher out (revoke token) — wired from Root. */
  onSignOut?: () => void;
  /** True when rendering from a cached copy (Drive not yet re-fetched). */
  stale?: boolean;
  /** Re-fetch from Drive. Surfaced by the stale badge and after pairing. */
  onRefresh?: () => void;
}

function toLocalIsoDate(date = new Date()): string {
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, "0");
  const day = date.getDate().toString().padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function classKey(slot: TimetableSlot): string {
  return `${slot.grade}-${slot.classNo}`;
}

function dateAtLocalMidnight(isoDate: string): Date {
  return new Date(`${isoDate}T00:00:00`);
}

function addDays(isoDate: string, days: number): string {
  const date = dateAtLocalMidnight(isoDate);
  date.setDate(date.getDate() + days);
  return toLocalIsoDate(date);
}

function addMonths(month: string, delta: number): string {
  const [year, mon] = month.split("-").map(Number);
  const date = new Date(year, mon - 1 + delta, 1);
  return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, "0")}`;
}

function monthTitle(month: string): string {
  const [year, mon] = month.split("-").map(Number);
  return `${year}년 ${mon}월`;
}

/** 42-cell (6×7) grid of ISO dates for a month, leading/trailing nulls. */
function buildMonthGrid(month: string): (string | null)[] {
  const [year, mon] = month.split("-").map(Number);
  const startWeekday = new Date(year, mon - 1, 1).getDay();
  const days = new Date(year, mon, 0).getDate();
  const cells: (string | null)[] = [];
  for (let i = 0; i < startWeekday; i++) cells.push(null);
  for (let d = 1; d <= days; d++) {
    cells.push(`${year}-${mon.toString().padStart(2, "0")}-${d.toString().padStart(2, "0")}`);
  }
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

/** Rough bell schedule so the current lesson can be focused ("지금"). */
function currentPeriodNow(now = new Date()): number | null {
  const minutes = now.getHours() * 60 + now.getMinutes();
  const schedule: Array<[number, number, number]> = [
    [1, 530, 590],
    [2, 600, 650],
    [3, 660, 710],
    [4, 720, 770],
    [5, 830, 890],
    [6, 900, 950],
    [7, 960, 1010],
  ];
  for (const [period, start, end] of schedule) {
    if (minutes >= start - 10 && minutes < end) return period;
  }
  return null;
}

function markLabel(mark: StudentMark): string {
  if (mark === "absent") return "결과";
  if (mark === "excused") return "인정결과";
  return "출석";
}

function marksEqual(a: MarksByStudent, b: MarksByStudent): boolean {
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  for (const key of keys) {
    const na = Number(key);
    if ((a[na] ?? "present") !== (b[na] ?? "present")) return false;
  }
  return true;
}

function exceptionSummaryFromMarks(marks: MarksByStudent): string {
  const parts = Object.entries(marks)
    .filter(([, mark]) => mark !== "present")
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([number, mark]) => `${number}번 ${mark === "excused" ? "인정결과" : "결과"}`);
  return parts.length ? parts.join(", ") : "저장하면 전원 출석";
}

function formatSavedAt(isoDate: string): string {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return "마지막 저장 알 수 없음";
  return `마지막 저장 ${date.getHours().toString().padStart(2, "0")}:${date.getMinutes().toString().padStart(2, "0")}`;
}

const PRIVACY_ACK_KEY = "privacyNoticeAck";
const LONG_PRESS_MS = 500;

function GearIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="3.2" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M12 2.5v2.2M12 19.3v2.2M21.5 12h-2.2M4.7 12H2.5M18.7 5.3l-1.6 1.6M6.9 17.1l-1.6 1.6M18.7 18.7l-1.6-1.6M6.9 6.9 5.3 5.3"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function App({
  initialDate = toLocalIsoDate(),
  slots = sampleSlots,
  rosters = sampleRosters,
  initialAttendance,
  initialMonth,
  onSaveSlot,
  onLoadMonth,
  onSignOut,
  stale,
  onRefresh,
}: AppProps = {}) {
  const [tab, setTab] = useState<"today" | "record">("today");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [pairingOpen, setPairingOpen] = useState(false);
  const [privacyAcked, setPrivacyAcked] = useState<boolean>(
    () => localStorage.getItem(PRIVACY_ACK_KEY) === "1",
  );
  const [selectedDate, setSelectedDate] = useState(initialDate);
  const [dateInputValue, setDateInputValue] = useState(initialDate);
  const [dateSheetOpen, setDateSheetOpen] = useState(false);
  const [calendarMonth, setCalendarMonth] = useState(() => selectedDate.slice(0, 7));
  const [selectedSlotId, setSelectedSlotId] = useState<string | null>(null);
  const [attendanceByDate, setAttendanceByDate] = useState<AttendanceByDate>(initialAttendance ?? {});
  const [drafts, setDrafts] = useState<Record<string, MarksByStudent>>({});
  const [queue, setQueue] = useState<SaveQueueItem[]>([]);
  const [isOnline, setIsOnline] = useState<boolean>(
    () => (typeof navigator === "undefined" ? true : navigator.onLine),
  );
  const [toast, setToast] = useState<string | null>(null);
  const [showPrivacy, setShowPrivacy] = useState(false);
  // E2E pairing state for the 설정 보안 section (null = still loading).
  const [paired, setPaired] = useState<boolean | null>(null);
  useEffect(() => {
    let cancelled = false;
    loadSyncKey()
      .then((key) => {
        if (!cancelled) setPaired(key !== null);
      })
      .catch(() => {
        if (!cancelled) setPaired(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);
  const disconnectPairing = async () => {
    const ok = window.confirm(
      "이 기기의 암호화 연결(열쇠)을 삭제할까요?\n다시 사용하려면 데스크톱 QR로 다시 연결해야 합니다.",
    );
    if (!ok) return;
    await clearSyncKey();
    resetSyncKeyCache();
    setPaired(false);
  };

  // Toast is a state machine: a save shows a sticky "반영 중…" that later
  // transitions to success/failure. A monotonic token guards against a newer
  // toast being clobbered by a stale Drive result.
  const toastTimer = useRef<number | null>(null);
  const toastSeq = useRef(0);
  const showToast = useCallback((message: string, sticky = false) => {
    const id = ++toastSeq.current;
    setToast(message);
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    if (!sticky) {
      toastTimer.current = window.setTimeout(() => {
        if (toastSeq.current === id) setToast(null);
      }, 2600);
    }
    return id;
  }, []);
  const resolveToast = useCallback((id: number, message: string) => {
    if (toastSeq.current !== id) return; // a newer toast has taken over
    setToast(message);
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => {
      if (toastSeq.current === id) setToast(null);
    }, 2600);
  }, []);

  const realTodayValue = toLocalIsoDate();
  const visibleSlots = getLessonsForDate(slots, selectedDate);
  const selectedSlot = slots.find((slot) => slot.id === selectedSlotId) ?? null;
  const selectedRoster = selectedSlot ? rosters[classKey(selectedSlot)] ?? [] : [];
  const selectedDraftKey = selectedSlot ? `${selectedDate}:${selectedSlot.id}` : "";
  const selectedBaseline = selectedSlot
    ? slotAttendanceToMarks(selectedRoster, attendanceByDate[selectedDate]?.[selectedSlot.id])
    : {};
  const selectedDraft = selectedSlot ? drafts[selectedDraftKey] ?? selectedBaseline : {};
  const draftSummary = selectedSlot ? exceptionSummaryFromMarks(selectedDraft) : "";
  const attendanceForDate = attendanceByDate[selectedDate] ?? {};

  const counts = useMemo(() => {
    const visibleSlotIds = new Set(visibleSlots.map((slot) => slot.id));
    const checked = Object.keys(attendanceForDate).filter((slotId) => visibleSlotIds.has(slotId)).length;
    const pending = pendingItems(queue).length;
    const failed = failedItems(queue).length;
    const unchecked = Math.max(visibleSlots.length - checked, 0);
    return { checked, failed, pending, unchecked };
  }, [attendanceForDate, queue, visibleSlots]);
  const lastSyncedAt = useMemo(() => {
    const times = queue
      .filter((item) => item.status === "synced" && item.syncedAt)
      .map((item) => item.syncedAt as string);
    return times.length ? times.sort().at(-1) ?? null : null;
  }, [queue]);

  const nowPeriod = selectedDate === realTodayValue ? currentPeriodNow() : null;
  const nowCardRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const card = nowCardRef.current;
    if (tab === "today" && card && typeof card.scrollIntoView === "function") {
      card.scrollIntoView({ block: "center", behavior: "auto" });
    }
    // Only re-run on view changes, not on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, selectedDate]);

  const openLesson = (slot: TimetableSlot) => {
    const roster = rosters[classKey(slot)] ?? [];
    const draftKey = `${selectedDate}:${slot.id}`;
    // Seed from the synced record (not all-present) so marks checked on the
    // desktop show up here — and saving doesn't wipe them back to present.
    const record = attendanceByDate[selectedDate]?.[slot.id];
    setDrafts((current) => ({
      ...current,
      [draftKey]: current[draftKey] ?? slotAttendanceToMarks(roster, record),
    }));
    setSelectedSlotId(slot.id);
  };

  const setMark = (studentNumber: number, next: StudentMark) => {
    if (!selectedSlot) return;
    setDrafts((current) => {
      const draft = current[selectedDraftKey] ?? selectedBaseline;
      return {
        ...current,
        [selectedDraftKey]: { ...draft, [studentNumber]: next },
      };
    });
  };
  // Single tap toggles 출석 ↔ 결과; long-press toggles 인정결과.
  const tapStudent = (studentNumber: number) => {
    const mark = selectedDraft[studentNumber] ?? "present";
    setMark(studentNumber, mark === "absent" ? "present" : "absent");
  };
  const longPressStudent = (studentNumber: number) => {
    const mark = selectedDraft[studentNumber] ?? "present";
    setMark(studentNumber, mark === "excused" ? "present" : "excused");
  };
  const pressTimer = useRef<number | null>(null);
  const longPressFired = useRef(false);
  const startPress = (studentNumber: number) => {
    longPressFired.current = false;
    if (pressTimer.current) window.clearTimeout(pressTimer.current);
    pressTimer.current = window.setTimeout(() => {
      longPressFired.current = true;
      longPressStudent(studentNumber);
    }, LONG_PRESS_MS);
  };
  const endPress = () => {
    if (pressTimer.current) window.clearTimeout(pressTimer.current);
  };
  const clickStudent = (studentNumber: number) => {
    if (longPressFired.current) {
      longPressFired.current = false;
      return; // the long-press already applied 인정결과
    }
    tapStudent(studentNumber);
  };

  // Mirror the latest queue so flush callbacks read fresh data without being
  // re-created (and re-triggering effects) on every queue change.
  const queueRef = useRef(queue);
  useEffect(() => {
    queueRef.current = queue;
  }, [queue]);
  const hydratedRef = useRef(false);
  const flushingRef = useRef(false);

  // Upload one enqueued save to Drive and resolve its queue status. Identified
  // by date+slot rather than id because enqueueSave dedupes pending items.
  const flushSave = async (date: string, slotId: string, payload: SlotAttendance) => {
    if (!onSaveSlot) return;
    try {
      await onSaveSlot(date, slotId, payload);
      setQueue((current) => markStatusByTarget(current, date, slotId, "synced"));
    } catch {
      setQueue((current) => markStatusByTarget(current, date, slotId, "failed"));
    }
  };

  // Re-upload every not-yet-synced item. Used on startup, on reconnect, and by
  // the manual retry button. Guarded so overlapping triggers don't double-run;
  // saves are idempotent so a rare duplicate upload is harmless.
  const flushAll = useCallback(async () => {
    if (!onSaveSlot || flushingRef.current) return;
    flushingRef.current = true;
    try {
      for (const item of queueRef.current.filter((entry) => entry.status !== "synced")) {
        try {
          await onSaveSlot(item.date, item.slotId, item.payload);
          setQueue((current) => markStatusByTarget(current, item.date, item.slotId, "synced"));
        } catch {
          setQueue((current) => markStatusByTarget(current, item.date, item.slotId, "failed"));
        }
      }
    } finally {
      flushingRef.current = false;
    }
  }, [onSaveSlot]);

  const flushAllRef = useRef(flushAll);
  useEffect(() => {
    flushAllRef.current = flushAll;
  }, [flushAll]);

  // Restore the persisted queue on startup, overlay its payloads onto the view,
  // then retry anything left unsynced from a previous session.
  useEffect(() => {
    let cancelled = false;
    loadQueue()
      .then((items) => {
        if (cancelled) return;
        if (items.length) {
          setQueue(items);
          setAttendanceByDate((current) => {
            const next = { ...current };
            for (const item of items) {
              next[item.date] = { ...(next[item.date] ?? {}), [item.slotId]: item.payload };
            }
            return next;
          });
        }
        hydratedRef.current = true;
        void flushAllRef.current();
      })
      .catch(() => {
        hydratedRef.current = true;
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Persist the queue after every change (once hydration has run, so the empty
  // initial state never clobbers a stored queue).
  useEffect(() => {
    if (!hydratedRef.current) return;
    void persistQueue(queue);
  }, [queue]);

  // Track connectivity for the offline banner, and auto-retry uploads when the
  // device comes back online.
  useEffect(() => {
    const goOnline = () => {
      setIsOnline(true);
      void flushAllRef.current();
    };
    const goOffline = () => setIsOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  // Drive splits attendance into monthly files; we preload only the current
  // month. Fetch a month once, on demand, and merge it in (local entries win so
  // an in-flight save isn't lost).
  const loadedMonthsRef = useRef(new Set<string>(initialMonth ? [initialMonth] : []));
  const ensureMonthLoaded = useCallback(
    (month: string) => {
      if (!onLoadMonth) return;
      if (loadedMonthsRef.current.has(month)) return;
      loadedMonthsRef.current.add(month);
      onLoadMonth(month)
        .then((records) => {
          setAttendanceByDate((current) => {
            const next = { ...current };
            for (const [date, daySlots] of Object.entries(records)) {
              next[date] = { ...daySlots, ...(next[date] ?? {}) };
            }
            return next;
          });
        })
        .catch(() => {
          loadedMonthsRef.current.delete(month);
        });
    },
    [onLoadMonth],
  );
  useEffect(() => {
    ensureMonthLoaded(selectedDate.slice(0, 7));
  }, [selectedDate, ensureMonthLoaded]);
  useEffect(() => {
    if (tab === "record") ensureMonthLoaded(calendarMonth);
  }, [tab, calendarMonth, ensureMonthLoaded]);

  // Persist locally, enqueue, and reconcile the toast to the real Drive result.
  const commitSlot = (date: string, slotId: string, saved: SlotAttendance) => {
    setAttendanceByDate((current) => ({
      ...current,
      [date]: { ...(current[date] ?? {}), [slotId]: saved },
    }));
    setQueue((current) => enqueueSave(current, { date, slotId, payload: saved }));

    if (onSaveSlot && isOnline) {
      const id = showToast("기기에 저장됨 · Drive 반영 중…", true);
      onSaveSlot(date, slotId, saved)
        .then(() => {
          setQueue((current) => markStatusByTarget(current, date, slotId, "synced"));
          resolveToast(id, "저장 완료");
        })
        .catch(() => {
          setQueue((current) => markStatusByTarget(current, date, slotId, "failed"));
          resolveToast(id, "저장 실패 — 아래에서 다시 시도");
        });
    } else if (onSaveSlot && !isOnline) {
      showToast("기기에 저장됨 · 연결되면 자동 반영");
      void flushSave(date, slotId, saved);
    } else {
      showToast("기기에 저장됨");
    }
  };

  const saveLesson = () => {
    if (!selectedSlot) return;
    const date = selectedDate;
    const slotId = selectedSlot.id;
    const saved = marksToSlotAttendance(selectedDraft, new Date().toISOString());
    commitSlot(date, slotId, saved);
    setDrafts((current) => {
      const next = { ...current };
      delete next[`${date}:${slotId}`];
      return next;
    });
    setSelectedSlotId(null);
  };

  const saveAllPresent = (slot: TimetableSlot) => {
    const roster = rosters[classKey(slot)] ?? [];
    const marks: MarksByStudent = Object.fromEntries(
      roster.map((student) => [student.number, "present" as StudentMark]),
    );
    const saved = marksToSlotAttendance(marks, new Date().toISOString());
    commitSlot(selectedDate, slot.id, saved);
  };

  // Cancel = discard: drop the draft and close. Confirm once if there are
  // unsaved changes. Backdrop tap uses the same path.
  const closeLesson = () => {
    if (!selectedSlot) {
      setSelectedSlotId(null);
      return;
    }
    const draft = drafts[selectedDraftKey];
    const dirty = draft && !marksEqual(draft, selectedBaseline);
    if (dirty && !window.confirm("변경 내용을 버릴까요?")) return;
    setDrafts((current) => {
      const next = { ...current };
      delete next[selectedDraftKey];
      return next;
    });
    setSelectedSlotId(null);
  };

  const retryFailed = () => {
    void flushAll();
  };

  const ackPrivacy = () => {
    localStorage.setItem(PRIVACY_ACK_KEY, "1");
    setPrivacyAcked(true);
  };

  const dayStatus = (date: string): "done" | "unchecked" | "failed" | null => {
    const lessons = getLessonsForDate(slots, date);
    if (!lessons.length) return null;
    const records = attendanceByDate[date] ?? {};
    if (queue.some((item) => item.date === date && item.status === "failed")) return "failed";
    const checked = lessons.filter((lesson) => records[lesson.id]).length;
    if (checked === lessons.length) return "done";
    // Future lessons are not "missed" yet — flag 미확인 only up to today.
    return date > realTodayValue ? null : "unchecked";
  };

  const renderLessonList = (date: string, showNow: boolean) => {
    const lessons = getLessonsForDate(slots, date);
    const records = attendanceByDate[date] ?? {};
    if (lessons.length === 0) {
      return <div className="empty-card">선택한 날짜에 표시할 수업이 없습니다.</div>;
    }
    return (
      <div className="lesson-list">
        {lessons.map((slot) => {
          const saved = records[slot.id];
          const summary = computeLessonDisplayStatus(saved);
          const queued = queue.find((item) => item.date === date && item.slotId === slot.id);
          const driveStatus =
            queued?.status === "failed"
              ? { className: "failed", label: "Drive 실패" }
              : queued?.status === "pending"
                ? { className: "pending", label: "Drive 대기" }
                : { className: "synced", label: "Drive 완료" };
          const neisLabel = saved?.syncedToNeis
            ? saved.closedOnNeis
              ? "NEIS 마감됨"
              : "NEIS 반영됨"
            : "NEIS 미반영";
          const isNow = showNow && date === realTodayValue && slot.period === nowPeriod;
          return (
            <div
              className={`lesson-card ${summary.checked ? "checked" : ""} ${isNow ? "now" : ""}`}
              key={slot.id}
              ref={isNow ? nowCardRef : undefined}
            >
              <button
                className="lesson-open"
                type="button"
                onClick={() => openLesson(slot)}
                aria-label={`${slot.grade}-${slot.classNo} ${slot.subjectName} ${slot.period}교시 열기`}
              >
                <span className="period">{slot.period}교시</span>
                <span className="lesson-main">
                  <strong>
                    {slot.grade}-{slot.classNo} {slot.subjectName}
                    {isNow && <span className="now-badge">지금</span>}
                  </strong>
                  {/* Unchecked cards already say 미확인 in the status chip — skip the duplicate detail line. */}
                  {summary.checked && <small>{summary.compactLabel}</small>}
                  {saved && <small className="saved-at">{formatSavedAt(saved.checkedAt)}</small>}
                  {saved && (
                    <span className="meta-row">
                      <span className={`mini-status ${driveStatus.className}`}>{driveStatus.label}</span>
                      <span className="mini-status">{neisLabel}</span>
                    </span>
                  )}
                </span>
                <span className={summary.checked ? "status done" : "status"}>
                  {summary.checked ? "확인함" : "미확인"}
                </span>
              </button>
              {!summary.checked && (
                <button
                  className="lesson-allpresent"
                  type="button"
                  onClick={() => saveAllPresent(slot)}
                >
                  전원 출석으로 저장
                </button>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="mobile-app">
      {!privacyAcked && (
        <div className="privacy-banner" role="alert">
          <span>이 앱은 학생 학번·출결만 처리합니다. 학생 이름은 외부로 전송·저장되지 않습니다.</span>
          <button type="button" className="privacy-banner-btn" onClick={ackPrivacy}>확인</button>
        </div>
      )}

      {tab === "today" && (
        <>
          <header className="top">
            <div>
              <p className="muted">교과 출결</p>
              <h1>{selectedDate === initialDate ? "오늘 수업" : "선택 날짜"}</h1>
            </div>
            <div className="top-actions">
              {stale && <span className="stale-badge">저장된 사본</span>}
              {stale && onRefresh && (
                <button className="round-btn" type="button" onClick={onRefresh} aria-label="새로 불러오기">↻</button>
              )}
              {counts.pending > 0 && (
                <div className="sync-pill" aria-label={`동기화 대기 ${counts.pending}건`}>
                  동기화 대기 {counts.pending}건
                </div>
              )}
              <button className="round-btn" type="button" aria-label="설정" onClick={() => setSettingsOpen(true)}>
                <GearIcon />
              </button>
            </div>
          </header>

          <button
            className="date-card"
            type="button"
            aria-label="날짜 선택"
            onClick={() => {
              setDateInputValue(selectedDate);
              setDateSheetOpen(true);
            }}
          >
            <div>
              <strong>{selectedDateLabel(selectedDate)}</strong>
              <span>{onSaveSlot ? "Google Drive 연동 · 모바일 입력" : "샘플 데이터 · 데모"}</span>
            </div>
            <div
              className={`ring ${counts.checked === visibleSlots.length && visibleSlots.length > 0 ? "complete" : ""}`}
              style={{
                "--ring-pct": `${visibleSlots.length ? Math.round((counts.checked / visibleSlots.length) * 100) : 0}%`,
              } as CSSProperties}
            >
              {counts.checked}/{visibleSlots.length}
            </div>
          </button>

          {!isOnline && (
            <div className="status-banner offline" role="status">
              인터넷에 연결되어 있지 않아요. 저장은 기기에 보관되고, 연결되면 자동으로 반영됩니다.
            </div>
          )}
          {onSaveSlot && counts.failed > 0 && (
            <div className="status-banner failed" role="alert">
              <span>저장 실패 {counts.failed}건이 있어요.</span>
              <button type="button" onClick={retryFailed}>다시 시도</button>
            </div>
          )}

          <main>{renderLessonList(selectedDate, true)}</main>
        </>
      )}

      {tab === "record" && (
        <>
          <header className="top">
            <div>
              <p className="muted">교과 출결</p>
              <h1>기록</h1>
            </div>
            <button className="round-btn" type="button" aria-label="설정" onClick={() => setSettingsOpen(true)}>
              <GearIcon />
            </button>
          </header>

          <section className="calendar-card">
            <div className="calendar-head">
              <button type="button" className="round-btn" aria-label="이전 달" onClick={() => setCalendarMonth((m) => addMonths(m, -1))}>‹</button>
              <strong>{monthTitle(calendarMonth)}</strong>
              <button type="button" className="round-btn" aria-label="다음 달" onClick={() => setCalendarMonth((m) => addMonths(m, 1))}>›</button>
            </div>
            <div className="calendar-weekdays">
              {["일", "월", "화", "수", "목", "금", "토"].map((w) => (
                <span key={w}>{w}</span>
              ))}
            </div>
            <div className="calendar-grid">
              {buildMonthGrid(calendarMonth).map((date, index) => {
                if (!date) return <span key={`e-${index}`} className="cal-cell empty" />;
                const status = dayStatus(date);
                const day = Number(date.slice(8));
                return (
                  <button
                    key={date}
                    type="button"
                    className={`cal-cell ${date === selectedDate ? "sel" : ""}`}
                    aria-label={`${date} ${status === "done" ? "완료" : status === "failed" ? "저장 실패" : status === "unchecked" ? "미확인" : ""}`}
                    onClick={() => setSelectedDate(date)}
                  >
                    <span className="cal-day">{day}</span>
                    {status && <span className={`cal-dot ${status}`} />}
                  </button>
                );
              })}
            </div>
            <div className="calendar-legend">
              <span><i className="cal-dot done" />완료</span>
              <span><i className="cal-dot unchecked" />미확인</span>
              <span><i className="cal-dot failed" />실패</span>
            </div>
          </section>

          <section className="record-day">
            <h2 className="record-day-title">{selectedDateLabel(selectedDate)}</h2>
            <main>{renderLessonList(selectedDate, false)}</main>
          </section>
        </>
      )}

      <nav className="bottom-nav" aria-label="모바일 메뉴">
        <button className={tab === "today" ? "on" : ""} type="button" onClick={() => setTab("today")}>오늘</button>
        <button className={tab === "record" ? "on" : ""} type="button" onClick={() => setTab("record")}>기록</button>
      </nav>

      {settingsOpen && (
        <div className="settings-screen" role="dialog" aria-modal="true" aria-label="설정">
          <header className="settings-head">
            <h1>설정</h1>
            <button className="icon-btn" type="button" aria-label="설정 닫기" onClick={() => setSettingsOpen(false)}>×</button>
          </header>
          <div className="settings-body">
            <section className="info-card">
              <strong>보안</strong>
              {paired === true && (
                <>
                  <p><b>암호화로 보호 중</b> — 출결 데이터가 암호화되어 저장되며, 이
                    기기와 데스크톱만 읽을 수 있습니다. QR 연결은 기기마다 처음 한 번만
                    필요합니다.</p>
                  <button className="secondary danger" type="button" onClick={() => void disconnectPairing()}>
                    기기 연결 해제
                  </button>
                </>
              )}
              {paired === false && (
                <>
                  <p>암호화 기기 연결되지 않음 — 데스크톱 앱의 <b>설정 → 모바일 연결
                    암호화</b>에서 QR을 띄운 뒤, 아래 버튼으로 연결하세요.</p>
                  <button className="primary wide" type="button" onClick={() => setPairingOpen(true)}>
                    지금 연결하기
                  </button>
                </>
              )}
            </section>
            <section className="info-card">
              <strong>개인정보</strong>
              <p>학생 이름은 저장하지 않습니다. 학번·출결만 본인 Google Drive에 저장되며,
                암호화를 켜면 구글도 내용을 읽을 수 없습니다.</p>
              <button className="policy-link" type="button" onClick={() => setShowPrivacy(true)}>개인정보처리방침 전문 보기</button>
            </section>
            <section className="info-card">
              <strong>시간표</strong>
              <p className="page-note">편집은 PC(데스크톱 앱)에서 합니다.</p>
              {slots.map((slot) => (
                <p key={slot.id}>{slot.period}교시 · {slot.grade}-{slot.classNo} {slot.subjectName}</p>
              ))}
            </section>
            <section className="info-card">
              <strong>학생 명부</strong>
              {Object.entries(rosters).map(([key, roster]) => (
                <p key={key}>{key} · {roster.length}명</p>
              ))}
            </section>
            <section className="info-card">
              <strong>계정</strong>
              <p>Google 계정에 연결되어 출결이 내 Drive에 저장됩니다.</p>
              {lastSyncedAt && <p>마지막 동기화: {formatSavedAt(lastSyncedAt)}</p>}
              {onSignOut && (
                <button className="secondary danger" type="button" onClick={onSignOut}>로그아웃 (연결 해제)</button>
              )}
            </section>
          </div>
        </div>
      )}

      {dateSheetOpen && (
        <div className="sheet" role="presentation" onClick={() => setDateSheetOpen(false)}>
          <div
            className="sheet-panel compact-sheet"
            role="dialog"
            aria-modal="true"
            aria-label="날짜 선택"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="grabber" />
            <div className="sheet-head">
              <div>
                <p className="muted">수업 날짜</p>
                <h2>날짜 선택</h2>
              </div>
              <button className="icon-btn" type="button" onClick={() => setDateSheetOpen(false)} aria-label="닫기">×</button>
            </div>
            <div className="quick-dates">
              <button type="button" onClick={() => { const nextDate = addDays(selectedDate, -1); setSelectedDate(nextDate); setDateInputValue(nextDate); setDateSheetOpen(false); }}>어제</button>
              <button type="button" onClick={() => { const nextDate = toLocalIsoDate(); setSelectedDate(nextDate); setDateInputValue(nextDate); setDateSheetOpen(false); }}>오늘</button>
              <button type="button" onClick={() => { const nextDate = addDays(selectedDate, 1); setSelectedDate(nextDate); setDateInputValue(nextDate); setDateSheetOpen(false); }}>내일</button>
            </div>
            <input
              className="date-input"
              type="date"
              aria-label="직접 날짜 선택"
              value={dateInputValue}
              onChange={(event) => {
                const nextDate = event.target.value;
                setDateInputValue(nextDate);
                if (/^\d{4}-\d{2}-\d{2}$/.test(nextDate)) {
                  setSelectedDate(nextDate);
                }
              }}
            />
          </div>
        </div>
      )}

      {selectedSlot && (
        <div className="sheet" role="presentation" onClick={() => closeLesson()}>
          <div
            className="sheet-panel"
            role="dialog"
            aria-modal="true"
            aria-label={`${selectedSlot.grade}-${selectedSlot.classNo} ${selectedSlot.subjectName} 출결 입력`}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="grabber" />
            <div className="sheet-head">
              <div>
                <p className="muted">{selectedSlot.period}교시 · {classKey(selectedSlot)}</p>
                <h2>{selectedSlot.grade}-{selectedSlot.classNo} {selectedSlot.subjectName}</h2>
              </div>
              <button className="icon-btn" type="button" onClick={() => closeLesson()} aria-label="닫기">×</button>
            </div>

            <div className="legend">
              <span><i className="dot present" />출석</span>
              <span><i className="dot absent" />결과</span>
              <span><i className="dot excused" />인정결과</span>
              <span className="legend-hint">한 번 눌러 결과 · 길게 눌러 인정결과</span>
            </div>

            <div className="chip-grid">
              {selectedRoster.map((student) => {
                const mark = selectedDraft[student.number] ?? "present";
                return (
                  <button
                    key={student.number}
                    className="chip"
                    data-mark={mark}
                    type="button"
                    aria-pressed={mark !== "present"}
                    aria-label={`${student.number}번 ${student.name ? `${student.name} ` : ""}${markLabel(mark)}`}
                    onPointerDown={() => startPress(student.number)}
                    onPointerUp={endPress}
                    onPointerLeave={endPress}
                    onPointerCancel={endPress}
                    onContextMenu={(event) => event.preventDefault()}
                    onClick={() => clickStudent(student.number)}
                  >
                    <span className="chip-no">{student.number}</span>
                    {student.name && <span className="chip-name">{student.name}</span>}
                  </button>
                );
              })}
            </div>

            <div className="draft-summary">
              <strong>저장 전 요약</strong>
              <span>{draftSummary}</span>
            </div>

            <div className="sheet-actions">
              <button className="secondary" type="button" onClick={() => closeLesson()}>취소</button>
              <button className="primary" type="button" onClick={saveLesson}>저장</button>
            </div>
          </div>
        </div>
      )}

      {pairingOpen && (
        <div className="fs-overlay">
          <Pairing
            onPaired={() => {
              setPairingOpen(false);
              setPaired(true);
              onRefresh?.();
            }}
          />
        </div>
      )}

      {showPrivacy && <PrivacyPolicy onClose={() => setShowPrivacy(false)} />}
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}
