import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SyncEncryptionCard } from "./setup-view";

// jsdom has no canvas; the QR image is rendered from a mocked data URL.
vi.mock("qrcode", () => ({
  default: { toDataURL: vi.fn().mockResolvedValue("data:image/png;base64,QR") },
}));

const PAYLOAD = "checkon.sync.v1:AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8";

function makeApi(enabled: boolean) {
  return {
    get_sync_encryption_status: vi.fn().mockResolvedValue(JSON.stringify({ enabled })),
    enable_sync_encryption: vi
      .fn()
      .mockResolvedValue(JSON.stringify({ payload: PAYLOAD, migrated: 2, created: true })),
    get_pairing_payload: vi.fn().mockResolvedValue(JSON.stringify({ payload: PAYLOAD })),
  };
}

describe("SyncEncryptionCard", () => {
  it("enables encryption and shows the QR + recovery guidance", async () => {
    const api = makeApi(false);
    render(<SyncEncryptionCard api={api as never} />);

    await userEvent.click(await screen.findByRole("button", { name: /암호화 켜기/ }));

    expect(api.enable_sync_encryption).toHaveBeenCalled();
    expect(await screen.findByAltText(/휴대폰 연결 QR/)).toBeInTheDocument();
    expect(screen.getByText(/화면 공유/)).toBeInTheDocument();
    expect(screen.getByText(PAYLOAD)).toBeInTheDocument();
    expect(screen.getByText(/2건을 암호화/)).toBeInTheDocument();
  });

  it("shows the QR on demand when already enabled", async () => {
    const api = makeApi(true);
    render(<SyncEncryptionCard api={api as never} />);

    await userEvent.click(await screen.findByRole("button", { name: /연결 QR 보기/ }));

    expect(api.get_pairing_payload).toHaveBeenCalled();
    expect(await screen.findByAltText(/휴대폰 연결 QR/)).toBeInTheDocument();
    expect(api.enable_sync_encryption).not.toHaveBeenCalled();
  });
});
