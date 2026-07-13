import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Root from "./Root";

vi.mock("./lib/auth", () => ({
  initAuth: vi.fn().mockResolvedValue(undefined),
  isConfigured: vi.fn().mockReturnValue(true),
  requestAccessToken: vi.fn().mockResolvedValue("token"),
  revoke: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("./lib/driveData", () => ({
  loadAll: vi.fn().mockResolvedValue({ attendance: null, students: null, timetable: null }),
  loadMonthlyAttendance: vi.fn().mockResolvedValue(null),
  saveSlotAttendance: vi.fn().mockResolvedValue(undefined),
}));

import { initAuth, requestAccessToken } from "./lib/auth";

describe("Root sign-in", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("never requests a token on page load (no surprise Google window)", async () => {
    render(<Root />);
    expect(await screen.findByRole("button", { name: /Google 계정으로 시작하기/ })).toBeInTheDocument();
    expect(initAuth).not.toHaveBeenCalled();
    expect(requestAccessToken).not.toHaveBeenCalled();
  });

  it("initializes auth and requests a token exactly once when the login button is tapped", async () => {
    render(<Root />);
    await userEvent.click(await screen.findByRole("button", { name: /Google 계정으로 시작하기/ }));
    await waitFor(() => expect(requestAccessToken).toHaveBeenCalledTimes(1));
    expect(initAuth).toHaveBeenCalledTimes(1);
  });
});
