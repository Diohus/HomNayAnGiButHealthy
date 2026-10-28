import { afterEach, describe, expect, it, vi } from "vitest";
import { dismissHelpBanner, HELP_SEEN_KEY, openSectionId, rich, shouldShowHelpBanner } from "./help";

function fakeStorage(init: Record<string, string> = {}): Storage {
  const m = new Map(Object.entries(init));
  return {
    getItem: (k) => m.get(k) ?? null, setItem: (k, v) => void m.set(k, String(v)), removeItem: (k) => void m.delete(k),
    clear: () => m.clear(), key: (i) => [...m.keys()][i] ?? null, get length() { return m.size; },
  };
}
const throwing = {
  getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); },
} as unknown as Storage;

afterEach(() => vi.unstubAllGlobals());

describe("banner hướng dẫn", () => {
  it("chưa đóng ⇒ hiện; đóng ⇒ lưu hnag_help_seen và không hiện nữa", () => {
    vi.stubGlobal("localStorage", fakeStorage());
    expect(shouldShowHelpBanner()).toBe(true);
    dismissHelpBanner();
    expect(localStorage.getItem(HELP_SEEN_KEY)).toBeTruthy();
    expect(shouldShowHelpBanner()).toBe(false);
  });

  it("đã có hnag_help_seen ⇒ không hiện", () => {
    vi.stubGlobal("localStorage", fakeStorage({ [HELP_SEEN_KEY]: "1" }));
    expect(shouldShowHelpBanner()).toBe(false);
  });

  it("localStorage ném lỗi ⇒ không crash, vẫn hiện banner", () => {
    vi.stubGlobal("localStorage", throwing);
    expect(shouldShowHelpBanner()).toBe(true);
    expect(() => dismissHelpBanner()).not.toThrow();
  });
});

describe("trang hướng dẫn", () => {
  const ids = ["start", "today", "chat"];
  it("mở mục theo hash, mặc định start", () => {
    expect(openSectionId("#chat", ids)).toBe("chat");
    expect(openSectionId("", ids)).toBe("start");
    expect(openSectionId("#khong-co", ids)).toBe("start");
  });

  it("rich: **x** ⇒ đoạn đậm, phần còn lại giữ nguyên", () => {
    expect(rich("Bấm **Tạo thực đơn** nhé")).toEqual([
      { text: "Bấm ", strong: false }, { text: "Tạo thực đơn", strong: true }, { text: " nhé", strong: false }]);
    expect(rich("**Đăng xuất.**")).toEqual([{ text: "Đăng xuất.", strong: true }]);
    expect(rich("không đậm")).toEqual([{ text: "không đậm", strong: false }]);
  });
});
