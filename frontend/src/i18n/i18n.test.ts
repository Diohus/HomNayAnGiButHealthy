import { describe, expect, it } from "vitest";
import { ApiError } from "../api/client";
import { en } from "./en";
import { errorMessage, fmt } from "./index";
import { vi } from "./vi";

function leaves(o: unknown, path = ""): [string, unknown][] {
  if (o && typeof o === "object") return Object.entries(o).flatMap(([k, v]) => leaves(v, path ? `${path}.${k}` : k));
  return [[path, o]];
}

describe("từ điển", () => {
  for (const [name, d] of [["vi", vi], ["en", en]] as const) {
    it(`${name}: mọi giá trị là chuỗi khác rỗng`, () => {
      for (const [p, v] of leaves(d)) {
        expect(typeof v, p).toBe("string");
        expect((v as string).trim(), p).not.toBe("");
      }
    });
  }

  it("en và vi có cùng tập khóa (kể cả các Record)", () => {
    expect(leaves(en).map(([p]) => p).sort()).toEqual(leaves(vi).map(([p]) => p).sort());
  });

  it("errors của en và vi cùng tập khóa", () => {
    expect(Object.keys(en.errors).sort()).toEqual(Object.keys(vi.errors).sort());
  });

  it("placeholder giống nhau giữa hai ngôn ngữ", () => {
    const ph = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort();
    const enMap = new Map(leaves(en));
    for (const [p, v] of leaves(vi)) expect(ph(enMap.get(p) as string), p).toEqual(ph(v as string));
  });
});

describe("thông báo lỗi theo code", () => {
  const err = (code: string, body: Record<string, unknown> = {}, msg = "server") =>
    new ApiError(400, code, msg, { code, ...body });

  it("dùng từ điển theo ngôn ngữ và điền placeholder", () => {
    expect(errorMessage(err("BAD_CREDENTIALS"), en)).toBe("Incorrect email or password.");
    expect(errorMessage(err("RATE_LIMITED", { retry_after_s: 42 }), en)).toContain("42 seconds");
    expect(errorMessage(err("RATE_LIMITED", { retry_after_s: 42 }), vi)).toContain("42 giây");
  });

  it("code lạ ⇒ message server; không phải ApiError ⇒ lỗi chung", () => {
    expect(errorMessage(err("SOMETHING_NEW"), en)).toBe("server");
    expect(errorMessage(err("SOMETHING_NEW", {}, ""), en)).toBe(en.error);
    expect(errorMessage(new Error("x"), vi)).toBe(vi.error);
    expect(errorMessage(err("HTTP_404"), en)).toBe(en.errors.HTTP);
  });

  it("VALIDATION_ERROR: hiển thị thông điệp từng trường (backend đã dịch theo Accept-Language)", () => {
    const e = err("VALIDATION_ERROR", { errors: [{ field: "age", message: "Age must be between 18 and 100." },
                                                 { field: "height_cm", message: "Height must be a number." }] });
    expect(errorMessage(e, en)).toBe("Age must be between 18 and 100.; Height must be a number.");
  });

  it("E10: ALLERGEN_CONFLICT có params ⇒ câu cụ thể, không mã thô", () => {
    const item = err("ALLERGEN_CONFLICT", { reason: "allergy:shellfish",
                                            params: { food: "Shrimp", reason: "shellfish allergy" } });
    expect(errorMessage(item, en)).toBe("Can't add Shrimp: it conflicts with the shellfish allergy you declared.");
    const custom = err("ALLERGEN_CONFLICT", { reason: "allergy:milk", params: { reason: "dị ứng sữa" } });
    expect(errorMessage(custom, vi)).toBe("Sản phẩm này mâu thuẫn với dị ứng sữa bạn đã khai báo.");
    expect(errorMessage(err("ALLERGEN_CONFLICT"), en)).toBe(en.errors.ALLERGEN_CONFLICT);
  });

  it("params của server ghi đè trường cùng tên ở body", () => {
    const e = err("LOW_ENERGY_ACK_REQUIRED", { floor_kcal: 1234, params: { floor_kcal: 1230, requested_kcal: 900 } });
    expect(errorMessage(e, en)).toContain("~1230 kcal/day");
  });

  it("fmt giữ nguyên placeholder thiếu giá trị", () => expect(fmt("{a} {b}", { a: 1 })).toBe("1 {b}"));
});

describe("vòng 4: giới hạn sức khỏe", () => {
  it("nhãn cho mọi chỉ số giới hạn và notice NO_LIMITS cho mọi bệnh nền nhạy cảm", async () => {
    const { LIMIT_FIELDS, SENSITIVE_CONDITIONS } = await import("../types");
    for (const d of [vi, en]) {
      for (const f of LIMIT_FIELDS) expect(d.settings.limits[f], f).toBeTruthy();
      for (const c of SENSITIVE_CONDITIONS) expect(d.notices[`NO_LIMITS_${c.toUpperCase()}`], c).toBeTruthy();
    }
  });

  it("SELF_MANAGED_ACK_REQUIRED điền tên bệnh nền đã dịch từ params", () => {
    const e = new ApiError(409, "SELF_MANAGED_ACK_REQUIRED", "", {
      code: "SELF_MANAGED_ACK_REQUIRED", conditions: ["kidney"], params: { conditions: "kidney disease" } });
    expect(errorMessage(e, en)).toContain("(kidney disease)");
  });
});
