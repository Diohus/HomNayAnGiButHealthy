# Vòng 1 — Yêu cầu chỉnh sửa (PO → Dev)

Người viết: phiên PO/reviewer `homnayangibuthealthy-44`. Người làm: phiên dev.
Làm **đúng phạm vi** dưới đây, không tự thêm tính năng khác. Khi xong, gửi lại cho PO bằng SendMessage tới `homnayangibuthealthy-44`: danh sách file đã đổi, kết quả test, và mọi chỗ bạn làm khác yêu cầu (kèm lý do).

## 0. Lưu ý môi trường (đọc trước)

- Windows Smart App Control **chặn DLL Cython của SQLAlchemy** trong `backend/.venv` ⇒ `pytest` lỗi `ImportError: DLL load failed ... _util_cy`. Hãy dùng venv PO đã dựng (SQLAlchemy pure-Python, cài editable trỏ vào `backend/`):
  `C:\Users\nguye\AppData\Local\Temp\claude\d--HomNayAnGiButHealthy\5efd6715-9e6e-43d6-a648-f4274eb04742\scratchpad\venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` (chạy trong `backend/`).
  Nếu thêm dependency Python, cài vào venv đó với `PIP_USE_FEATURE=truststore`.
- Mạng máy này chặn TLS (antivirus MITM) ⇒ httpx báo `CERTIFICATE_VERIFY_FAILED`. Dùng `truststore` khi cần gọi mạng.
- **Không** đụng `.env` (chứa API key thật). Không commit.
- Baseline hiện tại: backend 125/125 pass; frontend 5/5 pass, typecheck sạch.

## A. Bảo mật — làm trước (bắt buộc)

**A1. [CRITICAL] JWT secret mặc định cho phép giả mạo token.** `app/core/config.py:11` `jwt_secret = "change-me"`, không kiểm tra. PO đã chứng minh: ký token bằng `"change-me"` ⇒ `GET /api/profile` trả 200 (đọc được hồ sơ sức khỏe của người khác nếu biết user id). Còn nếu `.env` để `JWT_SECRET=` rỗng (đúng như `.env` hiện tại) ⇒ PyJWT ném lỗi ⇒ đăng ký trả 500.
- Thêm validator trong `Settings` (hoặc hàm `validate_settings()` gọi trong `create_app()`): `jwt_secret` phải ≥ 32 ký tự và khác `"change-me"`; `health_data_key` phải là khóa Fernet hợp lệ (thử `Fernet(key)`). Sai ⇒ `RuntimeError` với thông báo rõ biến nào sai, **app không khởi động**.
- Bỏ default `"change-me"` (để `""`, validator sẽ chặn).
- Test: `tests/core/test_config.py` — secret rỗng / "change-me" / quá ngắn / Fernet sai ⇒ lỗi; hợp lệ ⇒ ok.

**A2. [HIGH] "Xóa toàn bộ dữ liệu" không xóa gì khi chạy SQLite.** `DELETE /api/me` dựa vào `ON DELETE CASCADE`, nhưng SQLite chỉ bật FK khi có `PRAGMA foreign_keys=ON` — hiện pragma này **chỉ có trong `tests/conftest.py`**. PO chạy app với SQLite (đúng hướng dẫn README mục dev): sau khi xóa còn nguyên `health_profiles`, `chat_messages`, `menu_days`, `refresh_tokens`.
- Chuyển listener `PRAGMA foreign_keys=ON` vào `app/db/session.py:init_engine` (chỉ khi URL bắt đầu bằng `sqlite`), xóa bản trùng trong conftest.
- Test: thêm assert trong `tests/api/test_flow.py::test_delete_all_data` đếm 0 dòng ở mọi bảng có `user_id` (dùng `Base.metadata`, đừng liệt kê tay).

**A3. [HIGH] Không có rate limit.** 12 lần sai mật khẩu liên tiếp đều trả 401 (brute-force được). `/api/chat` và `/recipe` gọi LLM trả phí, không giới hạn.
- Thêm `app/core/ratelimit.py`: limiter in-memory (sliding window, thread-safe, không thêm dependency). Ghi giả định "một instance" vào `docs/ASSUMPTIONS.md`.
- Áp dụng: login sai 5 lần / 15 phút theo (email, IP) ⇒ 429 `RATE_LIMITED` (kèm `retry_after_s`); register 10 / giờ / IP; `/api/chat` 20 / phút / user; `/menu/{day}/meals/{slot}/recipe` 10 / phút / user.
- Có fixture autouse trong conftest reset limiter giữa các test. Test cho từng ngưỡng.

**A4. [MEDIUM] Guardrail bị bỏ qua ở `unlock`.** `app/services/menu.py:466` `unlock()` không gọi `c.ensure_allowed()` ⇒ người dùng có bệnh nền nhạy cảm chưa xác nhận chuyên gia vẫn kích hoạt solver sinh lại thực đơn. Thêm `c.ensure_allowed()` + test trong `tests/guardrails`.

**A5. [MEDIUM] Refresh token bị đánh cắp không bị phát hiện.** `routes.py:refresh`: token đã `revoked` dùng lại chỉ bị từ chối. Khi gặp token đã revoked ⇒ revoke **toàn bộ** refresh token của user đó (phát hiện reuse). Test.

**A6. [HIGH] Dependency frontend có lỗ hổng.** `npm audit --omit=dev`: 3 high (react-router open redirect / XSS, GHSA-2w69-qvjg-hvjx, GHSA-2j2x-hqr9-3h42). Nâng `react-router-dom` lên bản 6.x đã vá (≥ 6.30.3, giữ pin chính xác như file hiện tại), chạy lại `npm audit --omit=dev` ⇒ 0 high.

**A7. [LOW] CSP.** Thêm `Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"` vào `deploy/Caddyfile`. ⇒ Mọi script (kể cả script chống nháy theme ở mục B) phải là **file ngoài**, không inline.

## B. Chế độ Sáng / Tối (yêu cầu của chủ sản phẩm)

Hiện tại `styles.css` chỉ đổi theo `prefers-color-scheme`, người dùng không chọn được, và dark chưa đủ token.
- `src/theme.ts`: `type Theme = "system" | "light" | "dark"`; `getTheme()/setTheme()` lưu `localStorage["hnag_theme"]` (bọc try/catch); `applyTheme()` đặt `document.documentElement.dataset.theme` = `light|dark`, xóa thuộc tính khi `system`.
- `styles.css`: giữ token ở `:root`; dark đặt ở **cả hai** chỗ: `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {…} }` và `:root[data-theme="dark"] {…}`. Thêm `color-scheme: light` / `dark` tương ứng (để input date, scrollbar đổi theo). Rà mọi màu cứng (`#fff` trong `.bubble.user`, `.chip.on`, `button`…) — chữ trên nền accent phải đạt tương phản ≥ 4.5:1 ở cả hai chế độ; `--muted` trên `--card` ≥ 4.5:1.
- Chống nháy: `frontend/public/theme-init.js` (đọc localStorage, đặt `data-theme` trước khi React render), nạp bằng `<script src="/theme-init.js"></script>` trong `<head>` của `index.html` (không inline — xem A7). Thêm `<meta name="theme-color">`.
- UI: trang Cài đặt có mục "Giao diện" với điều khiển 3 lựa chọn (Theo hệ thống / Sáng / Tối), dùng `<fieldset>` + radio có label (truy cập được bằng bàn phím).
- Test vitest cho `theme.ts` (lưu/đọc, storage ném lỗi vẫn chạy, `system` xóa thuộc tính).

## C. Tiếng Việt / English — phần frontend (vòng 1)

Hiện `i18n/index.ts` cố định tiếng Việt, `t` là hằng số import tĩnh (đổi ngôn ngữ sẽ không re-render), và còn ~40 chuỗi tiếng Việt viết cứng trong TSX (PO đã grep: `DaySummary.tsx` NUTRIENT_VI + "Thiếu/Vượt", `MealCard.tsx` tag "có sẵn/ăn vặt/đã chỉnh", aria-label "giảm/tăng", "Gia vị", "Gợi ý bởi AI/Công thức mẫu", "Đạm/Carb/Béo"; `Today.tsx` "Hôm nay", aria "ngày trước/sau", thông báo chuyên gia, thông báo bù cheat day; `Settings.tsx` LIMITS, câu xác nhận, "Xác nhận", "Dữ liệu"; `Pantry.tsx` các thông báo, "Ngày", "Xóa"; `Chat.tsx` form nhãn; `Profile.tsx` disclaimer viết cứng; `client.ts` "Đã có lỗi xảy ra."; `index.html` title).
- `src/i18n/en.ts` cùng kiểu `Dict` (TS bắt đủ khóa). Bản dịch tự nhiên, thuật ngữ dinh dưỡng chuẩn (Protein, Carbs, Fat, Fiber, Sodium…). Disclaimer y tế tiếng Anh phải tương đương đầy đủ nghĩa bản Việt.
- `i18n/index.ts`: `I18nProvider` (React context) + hook `useI18n()` trả `{ lang, setLang, t, fmtDate }`. Lưu `localStorage["hnag_lang"]` (try/catch), mặc định `vi`. Đổi `document.documentElement.lang` và `document.title`.
- Thay **mọi** `import { t }` bằng hook; đưa toàn bộ chuỗi cứng nêu trên vào từ điển. Sau khi xong, lệnh `grep -rnP '[à-ỹÀ-Ỹđ]' frontend/src --include=*.tsx` chỉ được còn kết quả trong `i18n/`.
- Lỗi API: thêm `t.errors: Record<string,string>` cho các `code` backend (EMAIL_EXISTS, BAD_CREDENTIALS, INVALID_REFRESH, PROFILE_REQUIRED, LOW_ENERGY_ACK_REQUIRED, ED_SUPPORT, EXPERT_CONFIRMATION_REQUIRED, ALLERGEN_CONFLICT, MENU_NOT_FOUND, ITEM_NOT_FOUND, DELTA_RANGE, PANTRY_ITEM, GRAMS_RANGE, FOOD_NOT_FOUND, PROPOSAL_*, STALE_PROPOSAL, ROTATION_VIOLATION, MESSAGE_LENGTH, RATE_LIMITED, VALIDATION_ERROR, INTERNAL…). Lấy danh sách đầy đủ bằng grep `AppError(` trong backend. UI hiển thị `t.errors[code] ?? message server`.
- `api()` gửi header `Accept-Language: <lang>` (backend sẽ dùng ở vòng 2).
- Tên nguyên liệu: khi `lang === "en"` dùng `name_en` (API `/foods` đã trả). Notices: hiển thị theo `code` (DISCLAIMER, CONSULT_DOCTOR_INSULIN, SODIUM_SEASONING) từ từ điển, fallback `text`.
- Bộ chọn ngôn ngữ: ở trang Cài đặt **và** trang Đăng nhập (người chưa đăng nhập cũng cần đổi).
- Test vitest: mọi giá trị trong `en`/`vi` khác rỗng (duyệt đệ quy); `errors` của `en` và `vi` cùng tập khóa.

## D. Bảo trì / dữ liệu

- **D1.** PuLP 3.3 phát 19k DeprecationWarning: `LpVariable(...)` trực tiếp và `PULP_CBC_CMD` sẽ **bị xóa ở PuLP 4.0** ⇒ `pip install` mới có thể làm hỏng solver. Pin `pulp>=2.8,<4` trong `pyproject.toml` (không migrate API ở vòng này) và thêm `filterwarnings` cho đúng 2 cảnh báo đó trong `[tool.pytest.ini_options]`.
- **D2.** LLM lỗi kết nối hiện chỉ log INFO ⇒ khi TLS bị chặn, app âm thầm chạy chế độ dự phòng mà không ai biết. Đổi log của nhánh `LLMError` trong `app/ai/service.py` sang WARNING (vẫn không log nội dung). README: thêm 2 dòng về TLS bị chặn (`SSL_CERT_FILE` / truststore).
- **D3.** `Settings.model_config env_file=".env"` là đường dẫn tương đối theo cwd ⇒ chạy từ `backend/` không đọc được `.env` ở gốc repo. Dùng `env_file=(".env", "../.env")`.
- **D4.** Model LLM: `gpt-6-luna` PO đã xác minh **còn tồn tại và hoạt động** (structured output OK, 3–6 s/lần). `claude-opus-5-5` + tham số `fallbacks`/beta trong `AnthropicProvider` là đúng API hiện hành. **Không đổi model.**

## Tiêu chí nghiệm thu vòng 1
1. Backend: toàn bộ test pass (125 cũ + test mới), `ruff check app` không tăng lỗi so với hiện tại (51).
2. Frontend: `npm test`, `npm run typecheck`, `npm run build` pass; `npm audit --omit=dev` 0 high.
3. Grep chuỗi tiếng Việt trong `.tsx` ngoài `i18n/` = 0.
4. Báo cáo lại cho PO qua SendMessage.
