import "fake-indexeddb/auto";
import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Pairing from "./Pairing";
import { clearSyncKey, loadSyncKey } from "./lib/keyStore";
import { PAIRING_PREFIX } from "./lib/crypto";

const VALID = `${PAIRING_PREFIX}AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8`;

describe("Pairing", () => {
  beforeEach(async () => {
    await clearSyncKey();
  });

  it("saves the key and calls onPaired for a valid code", async () => {
    const onPaired = vi.fn();
    render(<Pairing onPaired={onPaired} />);
    await userEvent.type(screen.getByLabelText(/연결 코드/), VALID);
    await userEvent.click(screen.getByRole("button", { name: "연결" }));
    await waitFor(() => expect(onPaired).toHaveBeenCalled());
    expect(await loadSyncKey()).not.toBeNull();
  });

  it("attaches the camera stream to a mounted video element when scanning starts", async () => {
    // Regression: the <video> must already be in the DOM when getUserMedia
    // resolves — rendering it only after setScanning(true) left the ref null
    // and the stream was silently dropped (camera "never opened").
    const stream = { getTracks: () => [] } as unknown as MediaStream;
    Object.defineProperty(navigator, "mediaDevices", {
      value: { getUserMedia: vi.fn().mockResolvedValue(stream) },
      configurable: true,
    });
    vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();

    const { container, unmount } = render(<Pairing onPaired={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /QR코드 스캔/ }));

    const video = container.querySelector("video");
    expect(video).not.toBeNull();
    await vi.waitFor(() => expect(video!.srcObject).toBe(stream));
    unmount();
  });

  it("shows an error for a malformed code and keeps the key empty", async () => {
    const onPaired = vi.fn();
    render(<Pairing onPaired={onPaired} />);
    await userEvent.type(screen.getByLabelText(/연결 코드/), "checkon.sync.v1:short");
    await userEvent.click(screen.getByRole("button", { name: "연결" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/올바르지 않습니다/);
    expect(onPaired).not.toHaveBeenCalled();
    expect(await loadSyncKey()).toBeNull();
  });
});
