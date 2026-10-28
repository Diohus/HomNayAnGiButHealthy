// Access token ngắn hạn giữ trong bộ nhớ; refresh token trong localStorage (đánh đổi của MVP — xem docs/ASSUMPTIONS.md).
let accessToken: string | null = null;
const REFRESH_KEY = "hnag_refresh";
// Ngôn ngữ giao diện, gửi qua Accept-Language (I18nProvider cập nhật khi người dùng đổi)
let lang = "vi";

export function setApiLang(l: string) {
  lang = l;
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public body: Record<string, unknown>) {
    super(message);
  }
}

function getRefresh(): string | null {
  try {
    return localStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

export function setTokens(access: string | null, refresh: string | null) {
  accessToken = access;
  try {
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
    else localStorage.removeItem(REFRESH_KEY);
  } catch {
    /* bỏ qua khi trình duyệt chặn storage */
  }
}

export function hasSession(): boolean {
  return !!accessToken || !!getRefresh();
}

// Refresh token xoay vòng mỗi lần dùng; backend coi việc dùng lại token cũ là dấu hiệu bị đánh cắp.
// ⇒ Mọi lời gọi đồng thời trong tab dùng chung MỘT request (single-flight), và giữa các tab tuần tự qua Web Locks.
let inflight: Promise<boolean> | null = null;

export function refresh(): Promise<boolean> {
  if (!inflight) {
    const before = getRefresh();
    inflight = withRefreshLock(() => doRefresh(before)).finally(() => {
      inflight = null;
    });
  }
  return inflight;
}

function withRefreshLock<T>(fn: () => Promise<T>): Promise<T> {
  const locks = typeof navigator !== "undefined" ? navigator.locks : undefined;
  return locks?.request ? locks.request("hnag_refresh", fn) : fn();
}

async function doRefresh(before: string | null): Promise<boolean> {
  const rt = getRefresh(); // đọc lại trong lock: tab khác có thể vừa xoay vòng token
  if (!rt) return false;
  if (rt !== before && accessToken) return true;
  const r = await fetch("/api/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept-Language": lang },
    body: JSON.stringify({ refresh_token: rt }),
  });
  if (!r.ok) {
    // Chỉ đăng xuất nếu token trong storage vẫn là token vừa gửi (không xóa token mới của tab khác)
    if (getRefresh() === rt) {
      setTokens(null, null);
      return false;
    }
    // Trình duyệt không có Web Locks và tab khác vừa xoay vòng ⇒ thử lại với token mới đó
    accessToken = null;
    return doRefresh(rt);
  }
  const j = await r.json();
  setTokens(j.access_token, j.refresh_token);
  return true;
}

export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  if (!accessToken && retry && getRefresh()) await refresh();
  const sentAccess = accessToken;
  const r = await fetch(`/api${path}`, {
    ...init,
    headers: {
      // FormData (upload ảnh): để trình duyệt tự đặt multipart boundary
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      "Accept-Language": lang,
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init.headers,
    },
  });
  if (r.status === 401 && retry) {
    // Một request khác đã lấy access token mới trong lúc chờ ⇒ chỉ cần gửi lại, không refresh thêm lần nữa
    if (accessToken && accessToken !== sentAccess) return api<T>(path, init, false);
    if (await refresh()) return api<T>(path, init, false);
  }
  if (r.status === 204) return undefined as T;
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    // Giao diện hiển thị theo code (i18n errorMessage); message server chỉ là dự phòng
    const msg = body.errors?.length
      ? body.errors.map((e: { field: string; message: string }) => e.message).join("; ")
      : body.message ?? "";
    throw new ApiError(r.status, body.code ?? "ERROR", msg, body);
  }
  return body as T;
}

export const post = <T>(path: string, data?: unknown, init: RequestInit = {}) =>
  api<T>(path, { ...init, method: "POST", body: data === undefined ? undefined : JSON.stringify(data) });
export const postForm = <T>(path: string, form: FormData) => api<T>(path, { method: "POST", body: form });
export const put = <T>(path: string, data: unknown) => api<T>(path, { method: "PUT", body: JSON.stringify(data) });
export const del = <T>(path: string) => api<T>(path, { method: "DELETE" });
