import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// F1: tải lại trang ⇒ nhiều query song song khi chưa có access token ⇒ chỉ được gửi MỘT request refresh.
function fakeStorage(init: Record<string, string> = {}): Storage {
  const m = new Map(Object.entries(init));
  return {
    getItem: (k) => m.get(k) ?? null, setItem: (k, v) => void m.set(k, String(v)), removeItem: (k) => void m.delete(k),
    clear: () => m.clear(), key: (i) => [...m.keys()][i] ?? null, get length() { return m.size; },
  };
}

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

let calls: { url: string; body?: string; auth?: string }[];

async function load() {
  vi.resetModules(); // module state (access token, inflight) mới cho mỗi test
  return import("./client");
}

beforeEach(() => {
  calls = [];
  vi.stubGlobal("localStorage", fakeStorage({ hnag_refresh: "rt-1" }));
  vi.stubGlobal("fetch", vi.fn(async (url: string, init: RequestInit = {}) => {
    const auth = (init.headers as Record<string, string> | undefined)?.Authorization;
    calls.push({ url, body: init.body as string | undefined, auth });
    await new Promise((r) => setTimeout(r, 5));
    if (url === "/api/auth/refresh") {
      const { refresh_token } = JSON.parse(init.body as string);
      return refresh_token === "rt-1" ? json(200, { access_token: "at-2", refresh_token: "rt-2" })
        : json(401, { code: "INVALID_REFRESH", message: "" });
    }
    return auth === "Bearer at-2" ? json(200, { ok: url }) : json(401, { code: "INVALID_TOKEN", message: "" });
  }));
});
afterEach(() => vi.unstubAllGlobals());

describe("refresh single-flight", () => {
  it("3 lời gọi song song khi chưa có access token ⇒ đúng 1 request refresh", async () => {
    const { api } = await load();
    const res = await Promise.all([api("/profile"), api("/needs"), api("/menu?start=2026-10-27")]);
    expect(res).toHaveLength(3);
    expect(calls.filter((c) => c.url === "/api/auth/refresh")).toHaveLength(1);
    expect(localStorage.getItem("hnag_refresh")).toBe("rt-2");
    expect(calls.filter((c) => c.url !== "/api/auth/refresh").every((c) => c.auth === "Bearer at-2")).toBe(true);
  });

  it("access token hết hạn (401) ở nhiều request ⇒ vẫn chỉ 1 refresh", async () => {
    const { api, setTokens } = await load();
    setTokens("at-expired", "rt-1");
    await Promise.all([api("/a"), api("/b"), api("/c")]);
    expect(calls.filter((c) => c.url === "/api/auth/refresh")).toHaveLength(1);
  });

  it("có Web Locks ⇒ refresh chạy trong lock hnag_refresh; tab khác đã xoay vòng ⇒ dùng token mới", async () => {
    const names: string[] = [];
    vi.stubGlobal("navigator", {
      locks: {
        request: async (name: string, fn: () => Promise<unknown>) => {
          names.push(name);
          localStorage.setItem("hnag_refresh", "rt-1"); // giả lập: tab khác vừa ghi token mới trước khi ta có lock
          return fn();
        },
      },
    });
    localStorage.setItem("hnag_refresh", "rt-0");
    const { refresh } = await load();
    expect(await refresh()).toBe(true);
    expect(names).toEqual(["hnag_refresh"]);
    expect(calls.map((c) => JSON.parse(c.body!).refresh_token)).toEqual(["rt-1"]);
  });

  it("refresh thất bại chỉ xóa token nếu storage vẫn là token vừa gửi", async () => {
    const { refresh } = await load();
    localStorage.setItem("hnag_refresh", "rt-bad");
    expect(await refresh()).toBe(false);
    expect(localStorage.getItem("hnag_refresh")).toBeNull();
  });

  it("gửi Accept-Language theo ngôn ngữ đang chọn", async () => {
    const { api, setApiLang } = await load();
    setApiLang("en");
    await api("/profile");
    const f = fetch as unknown as { mock: { calls: [string, RequestInit][] } };
    for (const [, init] of f.mock.calls) expect((init.headers as Record<string, string>)["Accept-Language"]).toBe("en");
  });
});

describe("upload ảnh (FormData)", () => {
  it("không đặt Content-Type JSON để trình duyệt tự thêm multipart boundary", async () => {
    const { postForm, setTokens } = await load();
    setTokens("at-2", "rt-1");
    const form = new FormData();
    form.append("text", "Natri 2000 mg");
    await postForm("/health-limits/extract", form);
    const f = fetch as unknown as { mock: { calls: [string, RequestInit][] } };
    const [, init] = f.mock.calls[0];
    expect((init.headers as Record<string, string>)["Content-Type"]).toBeUndefined();
    expect(init.body).toBe(form);
  });
});
