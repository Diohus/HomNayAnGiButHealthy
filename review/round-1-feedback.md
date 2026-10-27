# Phản hồi vòng 1 (PO → Dev)

PO đã tự kiểm chứng lại: backend 152/152 pass, frontend 20/20 pass, typecheck sạch, audit 0 high, grep i18n chỉ còn ký tự "×" (bị bắt nhầm, chấp nhận). Các mục A1–A7, B, C, D: **đạt**. Chấp nhận 2 lỗi moderate của react-router (không dùng SSR, không điều hướng tới URL do người dùng nhập). Chấp nhận các quyết định 1–14 mà bạn đã báo, **trừ mục 3** — xem F1.

## F1. [HIGH, regression] Tải lại trang hoặc access token hết hạn ⇒ người dùng bị đăng xuất

PO đã tái hiện ở backend: gọi 2 lần `POST /auth/refresh` cùng một token ⇒ lần 1 trả 200, lần 2 trả 401, và **refresh token mới của lần 1 cũng bị thu hồi (401)**.

Ở frontend, đây không chỉ là chuyện "hai tab". Trong `src/api/client.ts`, hàm `api()` gọi `refresh()` mỗi khi `!accessToken`. Lúc tải lại trang, trang Hôm nay chạy song song useProfile, useNeeds, useMenu, useDishNames, foods ⇒ 4–5 lần refresh với **cùng một token** ⇒ lần đầu xoay vòng token, các lần sau kích hoạt "phát hiện dùng lại" ⇒ thu hồi mọi phiên ⇒ đăng xuất. Mỗi lần F5 đều bị, và cứ 15 phút (khi access token hết hạn) lại bị. Thêm nữa, nhánh lỗi gọi `setTokens(null, null)` sẽ xóa luôn token mới mà lần thắng vừa ghi.

Sửa cả hai phía:
1. **Frontend (single-flight).** `refresh()` dùng chung một promise đang chạy (`let inflight: Promise<boolean> | null`). Giữa các tab: dùng `navigator.locks.request("hnag_refresh", …)` nếu trình duyệt có. Trong lock, đọc lại localStorage: nếu token đã khác token ban đầu (tab khác vừa refresh) thì chỉ refresh bằng token mới đó, hoặc dùng luôn nếu đã có access token. Nhánh lỗi chỉ `setTokens(null, null)` khi token trong storage **vẫn là token vừa gửi**.
2. **Backend (khoảng ân hạn).** Thêm cột `refresh_tokens.rotated_at` (timestamp, nullable), qua migration Alembic **mới**. Khi xoay vòng thì ghi `rotated_at`. Token đã xoay vòng bị dùng lại **trong vòng 30 giây** ⇒ chỉ trả 401 `INVALID_REFRESH`, không thu hồi các token khác. Quá 30 giây, hoặc token bị revoke do logout ⇒ thu hồi toàn bộ như hiện tại. Ghi giả định này vào ASSUMPTIONS (T9).
3. **Test.**
   - Backend: dùng lại trong khoảng ân hạn ⇒ token mới vẫn dùng được; dùng lại sau 30 giây (giả lập thời gian) ⇒ mọi token bị thu hồi.
   - Frontend vitest (stub `fetch`): 3 lời gọi `api()` song song khi chưa có access token ⇒ đúng **1** request `/auth/refresh`.

## F2. [LOW] Rate limit đăng nhập chỉ tính theo (email, IP)

Kẻ tấn công thử nhiều email từ cùng một IP (credential stuffing) sẽ không bị chặn. Thêm ngưỡng thứ hai: tối đa **30 lần sai / 15 phút / IP**, tính trên mọi email. Thêm test.

## Chuyển sang vòng 2
Sau khi xong F1 và F2, làm tiếp `review/round-2.md` **trong cùng lượt này**, không cần chờ PO. Bổ sung cho vòng 2:
- **E9.** Khi đổi ngôn ngữ, gọi `queryClient.invalidateQueries()` để nội dung từ server (nhu cầu, notices, thực đơn, tên món) tải lại theo ngôn ngữ mới.
- **E10.** `ALLERGEN_CONFLICT` cần có `params` (tên nguyên liệu đã dịch, lý do đã dịch), để frontend hiển thị câu cụ thể thay vì câu chung. Khi backend đã dịch validation thì bỏ ngoại lệ VALIDATION_ERROR ở frontend (quyết định số 7 của bạn).

Đừng sửa `.env`. Việc điền `JWT_SECRET` / `HEALTH_DATA_KEY` thuộc về chủ sản phẩm.
Báo lại PO một lần khi xong cả F1, F2 và vòng 2, theo đúng định dạng như lần trước.
