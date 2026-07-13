import type { MarkType, SlotAttendance, StudentEntry } from "./schemas";

export type StudentMark = "present" | MarkType;
export type MarksByStudent = Record<number, StudentMark>;

export function createEmptyMarks(students: StudentEntry[]): MarksByStudent {
  return Object.fromEntries(students.map((student) => [student.number, "present"]));
}

export function cycleMark(mark: StudentMark): StudentMark {
  if (mark === "present") return "absent";
  if (mark === "absent") return "excused";
  return "present";
}

/**
 * Rebuild the per-student draft from a synced record so absences checked on
 * another device (or in a previous session) show up in the roster view.
 * Falls back to all-present when there is no record yet.
 */
export function slotAttendanceToMarks(
  students: StudentEntry[],
  slot?: SlotAttendance,
): MarksByStudent {
  const marks = createEmptyMarks(students);
  for (const absence of slot?.absences ?? []) {
    if (absence.studentNumber in marks) {
      marks[absence.studentNumber] = absence.markType;
    }
  }
  return marks;
}

export function marksToSlotAttendance(marks: MarksByStudent, checkedAt: string): SlotAttendance {
  const absences = Object.entries(marks)
    .filter(([, mark]) => mark !== "present")
    .map(([studentNumber, mark]) => ({
      studentNumber: Number(studentNumber),
      markType: mark as MarkType,
      note: "",
    }))
    .sort((a, b) => a.studentNumber - b.studentNumber);

  return {
    absences,
    checkedAt,
    source: "mobile",
    syncedToNeis: false,
    closedOnNeis: false,
  };
}

export function summarizeLesson(slot?: SlotAttendance): {
  checked: boolean;
  label: string;
  absenceCount: number;
} {
  if (!slot) {
    return { checked: false, label: "미확인", absenceCount: 0 };
  }

  const absenceCount = slot.absences.length;
  return {
    checked: true,
    label: absenceCount ? `결과·인정결과 ${absenceCount}명` : "전원 출석",
    absenceCount,
  };
}
