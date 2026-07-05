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
const PAYLOAD2 = "checkon.sync.v1:Zm5ld2tleW5ld2tleW5ld2tleW5ld2tleW5ld2tleXk";
const RECOVERY = "0000-1111-2222-3333-4444-5555-6666-7777-8888-9999-AAAA-BBBB-CCCC-DDDD";
const RECOVERY2 = "ZZZZ-YYYY-XXXX-WWWW-VVVV-TTTT-SSSS-RRRR-QQQQ-PPPP-NNNN-MMMM-KKKK-JJJJ";

function makeApi(enabled: boolean) {
  return {
    get_sync_encryption_status: vi.fn().mockResolvedValue(JSON.stringify({ enabled })),
    enable_sync_encryption: vi
      .fn()
      .mockResolvedValue(
        JSON.stringify({ payload: PAYLOAD, migrated: 2, failed: 0, created: true }),
      ),
    get_pairing_payload: vi.fn().mockResolvedValue(JSON.stringify({ payload: PAYLOAD })),
    get_recovery_code: vi.fn().mockResolvedValue(JSON.stringify({ code: RECOVERY })),
    restore_from_recovery_code: vi
      .fn()
      .mockResolvedValue(JSON.stringify({ ok: true, decryptsExisting: true })),
    reissue_sync_key: vi.fn().mockResolvedValue(
      JSON.stringify({ ok: true, payload: PAYLOAD2, recoveryCode: RECOVERY2, reencrypted: 3, failed: 0 }),
    ),
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

  it("surfaces a partial-migration failure with a retry button", async () => {
    const api = makeApi(false);
    api.enable_sync_encryption = vi
      .fn()
      .mockResolvedValue(
        JSON.stringify({ payload: PAYLOAD, migrated: 4, failed: 3, created: true }),
      );
    render(<SyncEncryptionCard api={api as never} />);

    await userEvent.click(await screen.findByRole("button", { name: /암호화 켜기/ }));

    expect(await screen.findByText(/3건은 일시적인 오류/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /다시 시도/ })).toBeInTheDocument();
  });

  it("shows the QR on demand when already enabled", async () => {
    const api = makeApi(true);
    render(<SyncEncryptionCard api={api as never} />);

    await userEvent.click(await screen.findByRole("button", { name: /연결 QR 보기/ }));

    expect(api.get_pairing_payload).toHaveBeenCalled();
    expect(await screen.findByAltText(/휴대폰 연결 QR/)).toBeInTheDocument();
    expect(api.enable_sync_encryption).not.toHaveBeenCalled();
  });

  it("reveals the recovery code to back up when enabled", async () => {
    const api = makeApi(true);
    render(<SyncEncryptionCard api={api as never} />);

    await userEvent.click(await screen.findByRole("button", { name: /복구 코드 저장/ }));

    expect(api.get_recovery_code).toHaveBeenCalled();
    expect(await screen.findByText(RECOVERY)).toBeInTheDocument();
    expect(screen.getByText(/종이에 적어/)).toBeInTheDocument();
  });

  it("restores encryption from a recovery code", async () => {
    const api = makeApi(false);
    render(<SyncEncryptionCard api={api as never} />);

    await userEvent.click(await screen.findByRole("button", { name: /복구 코드로 복원/ }));
    await userEvent.type(screen.getByPlaceholderText(/XXXX/), RECOVERY);
    await userEvent.click(screen.getByRole("button", { name: /^복원$/ }));

    expect(api.restore_from_recovery_code).toHaveBeenCalledWith(RECOVERY);
    expect(await screen.findByText(/복원했습니다/)).toBeInTheDocument();
  });

  it("surfaces a recovery code that cannot open the account's data", async () => {
    const api = makeApi(false);
    api.restore_from_recovery_code = vi.fn().mockResolvedValue(
      JSON.stringify({ ok: false, error: "이 복구 코드로는 이 계정의 기존 데이터를 열 수 없습니다. 코드를 다시 확인해 주세요." }),
    );
    render(<SyncEncryptionCard api={api as never} />);

    await userEvent.click(await screen.findByRole("button", { name: /복구 코드로 복원/ }));
    await userEvent.type(screen.getByPlaceholderText(/XXXX/), "BADCODE");
    await userEvent.click(screen.getByRole("button", { name: /^복원$/ }));

    expect(await screen.findByText(/열 수 없습니다/)).toBeInTheDocument();
  });

  it("reissues the key and prompts re-pairing with a new recovery code", async () => {
    const api = makeApi(true);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<SyncEncryptionCard api={api as never} />);

    await userEvent.click(await screen.findByRole("button", { name: /열쇠 재발급/ }));

    expect(api.reissue_sync_key).toHaveBeenCalled();
    expect(await screen.findByText(/새로 발급/)).toBeInTheDocument();
    expect(await screen.findByAltText(/휴대폰 연결 QR/)).toBeInTheDocument();
    expect(screen.getByText(RECOVERY2)).toBeInTheDocument();
  });
});
