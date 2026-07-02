import "fake-indexeddb/auto";
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { clearSyncKey, loadSyncKey, saveSyncKey } from "./lib/keyStore";

describe("settings security section", () => {
  beforeEach(async () => {
    await clearSyncKey();
  });

  it("shows the protected state and a disconnect button when a key exists", async () => {
    await saveSyncKey(new Uint8Array(32));
    const user = userEvent.setup();
    render(<App initialDate="2026-05-04" />);

    await user.click(screen.getByRole("button", { name: "설정" }));

    expect(await screen.findByText(/암호화로 보호 중/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /기기 연결 해제/ })).toBeInTheDocument();
  });

  it("clears the sync key on disconnect after confirmation", async () => {
    await saveSyncKey(new Uint8Array(32));
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(<App initialDate="2026-05-04" />);

    await user.click(screen.getByRole("button", { name: "설정" }));
    await user.click(await screen.findByRole("button", { name: /기기 연결 해제/ }));

    expect(await loadSyncKey()).toBeNull();
    expect(await screen.findByText(/연결되지 않음/)).toBeInTheDocument();
  });

  it("shows the unpaired state without a key", async () => {
    const user = userEvent.setup();
    render(<App initialDate="2026-05-04" />);

    await user.click(screen.getByRole("button", { name: "설정" }));

    expect(await screen.findByText(/연결되지 않음/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /기기 연결 해제/ })).not.toBeInTheDocument();
  });
});
