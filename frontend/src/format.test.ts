import { describe, expect, it } from "vitest";
import { addDays, fmtGrams, fmtKcal, fmtPct, fmtSig, foldText } from "./format";

describe("hiển thị không có độ chính xác giả", () => {
  it("kcal làm tròn 10", () => {
    expect(fmtKcal(1913.47)).toBe("1910");
    expect(fmtKcal(1915)).toBe("1920");
  });
  it("gram làm tròn số nguyên", () => expect(fmtGrams(132.6)).toBe("133"));
  it("vi chất 2 chữ số có nghĩa", () => {
    expect(fmtSig(8.0473)).toBe("8");
    expect(fmtSig(1051.8)).toBe("1100");
    expect(fmtSig(0.0347)).toBe("0.035");
  });
  it("phần trăm số nguyên", () => expect(fmtPct(-0.0123)).toBe("-1%"));
  it("cộng ngày", () => expect(addDays("2026-10-31", 1)).toBe("2026-11-01"));
});

describe("tìm kiếm không dấu", () => {
  it("bỏ dấu tiếng Việt và đ", () => {
    expect(foldText("Cá Hồi")).toBe("ca hoi");
    expect(foldText("Đậu hũ")).toBe("dau hu");
  });
});
