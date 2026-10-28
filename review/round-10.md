# Vòng 10 — Dọn code: bỏ trùng lặp, tối ưu truy vấn, sửa đăng xuất

PO rà toàn bộ `backend/app` + `frontend/src` (2026-10-28). Vòng này **không thêm tính năng**, chỉ dọn và tối ưu. Hành vi người dùng thấy giữ nguyên, trừ R1 (sửa lỗi).
Quy ước như cũ: không commit, không sửa `.env`, báo lại file đổi + kết quả test + chỗ làm khác yêu cầu kèm lý do. Cập nhật `docs/CODEMAP.md` và `docs/ASSUMPTIONS.md` cho khớp.

## R1 (lỗi bảo mật, ưu tiên cao) — Đăng xuất không thu hồi refresh token
- Hiện tại: `frontend/src/pages/Settings.tsx:80` chỉ `setTokens(null, null)`; không gọi `POST /api/auth/logout` ⇒ refresh token vẫn dùng được 30 ngày nếu bị lộ.
- Sửa: thêm `logout()` trong `api/client.ts`: đọc refresh token hiện tại, gọi `POST /auth/logout` (lỗi mạng thì bỏ qua), rồi `setTokens(null, null)`. Settings dùng hàm này rồi `qc.clear()` + điều hướng `/login`.
- Test: `client.test.ts` — logout gọi đúng endpoint với refresh token và xóa token cả khi request lỗi.

## R2 — Gộp API ghi nhật ký: bỏ `POST /intake`, chỉ giữ `POST /intake/batch`
- Hai endpoint làm cùng một việc (batch là bản tổng quát, có all-or-nothing). Chat (`services/chat.py::apply_proposal`, nhánh `key == "log"`) cũng tự lặp `add_entry` y hệt `meal_photo.add_batch`.
- Sửa:
  - Chuyển `add_batch` từ `services/meal_photo.py` sang `services/intake.py` (đổi tên `add_entries(s, uid, day, entries, commit=True)`), giữ kiểm tra `BATCH_MAX`, rollback khi lỗi.
  - `add_entries` nạp hồ sơ + catalog **một lần** cho cả lô (hiện `add_entry` gọi `require_profile` + `MS.catalogs` cho từng mục). Tách phần kiểm tra một mục thành hàm nội bộ nhận `allowed`/`profile` đã nạp.
  - `apply_proposal` nhánh log dùng `IN.add_entries(..., commit=False)`.
  - Xóa route `POST /intake` và `IntakeIn` trong `api/routes.py`. `BatchEntry.source` giữ `manual | ai_estimate` (nguồn `chat` chỉ ghi từ service nội bộ).
  - Frontend `IntakePanel.tsx` gửi `POST /intake/batch` với `{ day, entries: [{ slot, food_code, grams, source: "manual" }] }`.
- Xóa luôn `GET /intake` (frontend không dùng; dữ liệu đã có trong `GET /menu` → `intake`). Test nào đang gọi thì chuyển sang đọc `GET /menu`.
- Test: chuyển các test dùng `POST /intake` sang batch 1 mục; thêm test lô 3 mục chỉ gọi `MS.catalogs` 1 lần (monkeypatch đếm).

## R3 — Một helper kiểm tra dị ứng thay cho 4 chỗ chép tay
- Khối "`food_code not in allowed.foods` ⇒ `exclusion_reason` ⇒ `AppError(422, "ALLERGEN_CONFLICT", key="error.ALLERGEN_CONFLICT.item", ...)`" lặp ở `services/intake.py::add_entry`, `services/menu.py::adjust`, `services/menu.py::add_pantry`.
- Sửa: thêm `ensure_allowed(food, allowed: FoodCatalog, profile)` vào `foods/restrictions.py` (hàm thuần, raise `AppError`) và dùng ở cả 3 chỗ. Không đổi mã lỗi/thông điệp.
- `add_pantry` hiện gọi `catalogs()` **hai lần** liên tiếp và `current_needs()` sau `require_profile()` (giải mã hồ sơ 2 lần) ⇒ dùng `Ctx` một lần.

## R4 — `_menu_out` dựng lại `Ctx` cho mỗi ngày / mỗi request
- `MS.Ctx(...)` giải mã hồ sơ + giới hạn, truy vấn đồ riêng, lọc catalog. Hiện:
  - `GET /menu?days=14` dựng `Ctx` 14 lần.
  - Mọi route sửa thực đơn (adjust/unlock/swap/eaten/rebalance/generate/apply) dựng `Ctx` trong service rồi `_menu_out` dựng thêm lần nữa.
- Sửa: `_menu_out(s, uid, day, lang, c: MS.Ctx | None = None)`; `get_menu`/`generate` dựng `Ctx` một lần cho cả vòng lặp. Các service sửa thực đơn có thể nhận `c` tùy chọn — làm nếu gọn, không bắt buộc. Lưu ý: sau khi service ghi DB, `Ctx` cũ vẫn đúng (hồ sơ/catalog không đổi) — **trừ** `apply_proposal` có thể thêm EnergyAdjustment (không nằm trong Ctx, `energy_delta` vẫn truy vấn riêng ⇒ ổn).
- `summary.week`: `IN.entries` rồi `IN.summary` truy vấn cùng ngày 2 lần ⇒ dùng một lần.
- Test: test đếm số lần khởi tạo `Ctx` cho `GET /menu?days=7` == 1.

## R5 — Bỏ nhánh chat "1 lượt LLM" (N1) đã tắt
- `CHAT_SINGLE_PASS` đo thật chậm hơn (ASSUMPTIONS E7) và tắt từ vòng 8. Giữ code chết = thêm prompt trùng gần hết với `foods/resolve.py::SYSTEM`, thêm test, thêm cấu hình.
- Xóa: `app/chat/understand.py`, `tests/chat/test_understand.py`, `scripts/bench_chat.py`, trường `chat_single_pass` trong `core/config.py`, nhánh `understand(...)` + biến `pre` trong `services/chat.py::send` (`resolve_fn` gọi thẳng `resolve_mentions`). Nếu `RS.mention_model(..., key=...)` chỉ còn một kiểu dùng thì bỏ tham số `key`.
- ASSUMPTIONS E7: ghi "đã thử, đo chậm hơn, đã gỡ ở vòng 10 (xem git `ab85bd9`)".

## R6 — Đưa logic nghiệp vụ ra khỏi `api/routes.py`
- `recipe` (route ~30 dòng: tìm bữa, gọi LLM, lưu công thức) ⇒ `services/menu.py::recipe(s, uid, day, slot, lang)` hoặc file `services/recipe.py`.
- `GET/DELETE /pantry` truy vấn DB trực tiếp ⇒ `services/menu.py::list_pantry` / `delete_pantry`.
- `GET /dishes`: bỏ `import` trong thân hàm; chuyển sang `services/foods.py::list_dishes`.
- `Literal["breakfast","lunch","dinner","snack"]` lặp 3 lần ⇒ một alias `Slot` (đặt cạnh `SLOTS` trong `services/intake.py` hoặc `planner/schemas.py`). Các route `{slot}` dạng `str` (`eaten`, `swap`, `recipe`) dùng luôn `Slot` ⇒ slot sai trả 422 thay vì 404.
- `adjust` và `unlock` chạy solver nhưng không có rate limit ⇒ thêm `limiter.hit(f"swap:{uid}", *RL.SWAP)` như `swap`/`rebalance`. **Kiểm tra** hạn mức `RL.SWAP` đủ cho người bấm +/− liên tục; nếu chật thì tạo `RL.ADJUST` riêng (vd 60/phút) và ghi lý do.

## R7 — Frontend: bỏ query trùng, dùng kết quả mutation
- `components/Dislikes.tsx` tự `useQuery(["dishes"])` lặp với `useDishNames` trong `api/hooks.ts` ⇒ thêm `useDishes()` trong hooks, cả hai dùng chung.
- `useMenuMutation`: các API sửa thực đơn đã trả về `MenuDay` mới nhưng UI bỏ qua và refetch `/menu` (2 request/thao tác). Sửa: nếu kết quả có dạng `MenuDay` (có `day` + `plan`) thì `qc.setQueryData(["menu", day], [result])`, chỉ invalidate các ngày khác. `apply` của chat trả `{ menu }` ⇒ dùng `menu`. Giữ invalidate cho mutation không trả menu (`recipe`).
- Test: hooks test (hoặc test thuần cho hàm chọn dữ liệu) — kết quả MenuDay được ghi vào cache, không refetch.

## Không làm trong vòng này
- Không đổi schema DB, không đổi số liệu dinh dưỡng, không đổi prompt LLM (trừ việc xóa N1).
- `AnthropicProvider` sau cờ: **giữ** (lựa chọn nhà cung cấp, không phải code chết).

## Tiêu chí nghiệm thu
1. Backend toàn bộ test pass (số test giảm do xóa `test_understand.py` là bình thường; báo số cũ/mới), `ruff check` 0 lỗi.
2. Frontend `npm test` pass, `npm run build` (tsc) không lỗi.
3. `grep -rn "chat_single_pass\|understand" backend/app` không còn kết quả (ngoài từ thường trong comment).
4. `grep -rn "\"/intake\"" frontend/src` chỉ còn batch/photo/xóa.
5. PO chạy lại E2E (đăng ký → hồ sơ → tạo thực đơn → +/− → đổi món → ghi nhật ký tay → chat "trưa nay ăn phở" → áp dụng → cân lại → đăng xuất rồi dùng refresh token cũ phải bị 401).
