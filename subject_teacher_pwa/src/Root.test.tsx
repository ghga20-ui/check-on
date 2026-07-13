import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Root from "./Root";

vi.mock("./lib/auth", () => ({
  initAuth: vi.fn().mockResolvedValue(undefined),
  isConfigured: vi.fn().mockReturnValue(true),
  hasSignedInBefore: vi.fn().mockReturnValue(false),
  requestAccessToken: vi.fn().mockResolvedValue("token"),
  revoke: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("./lib/driveData", () => ({
  loadAll: vi.fn().mockResolvedValue({ attendance: null, students: null, timetable: null }),
  loadMonthlyAttendance: vi.fn().mockResolvedValue(null),
  saveSlotAttendance: vi.fn().mockResolvedValue(undefined),
}));

import { hasSignedInBefore, initAuth, requestAccessToken } from "./lib/auth";

describe("Root auto sign-in gating", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("never requests a token on load for a first-time visitor (no surprise Google window)", async () => {
    vi.mocked(hasSignedInBefore).mockReturnValue(false);
    render(<Root />);
    expect(await screen.findByRole("button", { name: /Google 계정으로 시작하기/ })).toBeInTheDocument();
    expect(requestAccessToken).not.toHaveBeenCalled();
  });

  it("attempts the auto sign-in for a returning visitor", async () => {
    vi.mocked(hasSignedInBefore).mockReturnValue(true);
    render(<Root />);
    await waitFor(() => expect(requestAccessToken).toHaveBeenCalledTimes(1));
  });

  it("initializes auth and requests a token exactly once when the login button is tapped", async () => {
    vi.mocked(hasSignedInBefore).mockReturnValue(false);
    render(<Root />);
    await userEvent.click(await screen.findByRole("button", { name: /Google 계정으로 시작하기/ }));
    await waitFor(() => expect(requestAccessToken).toHaveBeenCalledTimes(1));
    expect(initAuth).toHaveBeenCalled();
  });
});
