import "fake-indexeddb/auto";
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
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
    expect(onPaired).toHaveBeenCalled();
    expect(await loadSyncKey()).not.toBeNull();
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
