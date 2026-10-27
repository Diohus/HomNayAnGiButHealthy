# Vòng 6 — Nhật ký "đã ăn" (#3) + Danh sách đi chợ (#5) + sửa nhỏ từ E2E vòng 5

PO đã nghiệm thu vòng 5 (264 test pass) và chạy E2E với LLM thật:
- "toi muon an ga ran", "trứg luộc", "bún bò huế" (món ghép), "I don't like fish" (đề xuất thêm vào danh sách không thích), "dị ứng tôm" (chuyển hướng sang Hồ sơ): ✅
- Đổi bữa: các bữa khác giữ nguyên, năng lượng lệch 0 %. ✅
- Chấp nhận các quyết định 1–8.

Quy ước như cũ: không commit, không sửa `.env`. Nếu sắp chạm hạn mức usage: dừng ở điểm test pass, ghi "Tiến độ dev" ở cuối file này, rồi báo PO.

## L0. Sửa nhỏ từ E2E vòng 5
- **L0a — "phở bò" bị tách làm hai:** "tối nay ăn phở bò nha" ⇒ "xoay quanh thịt bò nạc xay (95% nạc), bún/phở khô" (2 nguyên liệu rời), trong khi "bún bò huế" lại thành món ghép. Nguyên nhân có lẽ là cả cụm được phủ kín bởi 2 alias liền nhau nên không tính là "khớp một phần". Quy tắc mới: **≥ 2 alias liền kề nhau** (không có từ khác chen giữa) ⇒ gửi cả cụm cho LLM như ứng viên món ghép; LLM trả về ingredient rời thì vẫn dùng như cũ. Thêm test.
- **L0b — món không thích nằm ngoài catalog ("hành", "ngò", "sả"):** hiện chỉ trả lời "chưa thể loại".
  - Cho phép lưu dạng `kind="text"`, kèm `label` do người dùng nói (tối đa 40 ký tự).
  - Planner bỏ qua loại này. Nhưng **trình viết công thức** đưa nó vào danh sách "không dùng" trong prompt, và `violations()` kiểm tra thêm các từ này (so khớp theo từ, không dấu), giống cách xử lý dị ứng.
  - Proposal chat với câu "tôi không ăn được hành" ⇒ "Mình sẽ tránh hành trong cách chế biến" ⇒ Áp dụng.
  - Test: công thức giả lập có "hành" ⇒ bị loại ⇒ thử lại, cuối cùng rơi về template **không chứa hành** (template cũng phải lọc).
- **L0c:** UI hiện warning `USED_DISLIKED` (notice nhỏ trên bữa đó).

## L1. Nhật ký "đã ăn"
Mục tiêu: vòng tiến độ phản ánh **thực tế**; ăn khác kế hoạch thì app cân lại các bữa **chưa ăn**.
- **Bảng `intake_entries`** (migration mới): `id, user_id FK CASCADE, day, slot (breakfast|lunch|dinner|snack), food_code, grams, source (plan|chat|manual|ai_estimate), created_at`. Không mã hóa, nhất quán với `menu_days`; ghi chú ở ASSUMPTIONS.
- **API:**
  - `POST /api/menu/{day}/meals/{slot}/eaten` `{eaten: true|false}`:
    - `true` ⇒ chép item của bữa vào `intake_entries` (source=plan, thay thế bản ghi plan cũ của bữa đó).
    - `false` ⇒ xóa các bản ghi source=plan của bữa đó.
  - `POST /api/intake` `{day, slot, food_code, grams}`: ăn ngoài kế hoạch. Mã phải hợp lệ và **không** vi phạm dị ứng/chế độ ăn ⇒ 422 `ALLERGEN_CONFLICT`. Grams 1–3000.
  - `DELETE /api/intake/{id}`, `GET /api/intake?day=`.
  - `_menu_out` trả thêm `intake: {entries, totals}` và `eaten_slots`.
- **Cân lại phần còn lại:** `POST /api/menu/{day}/rebalance` sinh lại các bữa **chưa đánh dấu đã ăn**:
  - Bữa đã ăn ⇒ `frozen_slots` với item **theo nhật ký thực tế**.
  - Món ngoài kế hoạch ⇒ khóa như snack.
  - Mỗi bữa còn lại giữ ≥ `MEAL_FLOOR_SHARE` năng lượng phần của nó, không bỏ bữa (dùng lại logic `min_meal_energy`).
  - Trước khi cắt giảm phải kiểm tra guardrail rối loạn ăn uống: đã bị gắn cờ ED ⇒ không cắt, trả `ED_SUPPORT`.
  - Đã vượt mục tiêu ⇒ các bữa còn lại về mức sàn, kèm notice "hôm nay đã vượt ~X kcal", **không** tự bù sang ngày sau (cơ chế bù vẫn chỉ qua chat cheat day như cũ).
- **Chat:** intent mới `log_food` cho câu thì quá khứ ("tôi vừa ăn 1 bát phở", "trưa nay ăn bánh mì rồi", "I just had a banana").
  - Resolve món qua K1.
  - Trả proposal `key="log"` "Ghi vào nhật ký hôm nay?", sau đó gợi ý "Cân lại các bữa còn lại?" (proposal thứ hai, kèm plan xem trước).
  - LLM parser phân biệt `want_food` và `log_food`; rule fallback dùng các từ "vừa ăn", "đã ăn", "ăn rồi", "just ate", "had".
- **Frontend (Hôm nay):**
  - Mỗi bữa có checkbox/nút "Đã ăn".
  - Vòng tròn chính hiển thị **đã ăn / mục tiêu**; kế hoạch hiển thị mờ phía sau (2 lớp vòng).
  - Mục "Ngoài kế hoạch" liệt kê bản ghi intake kèm nút xóa; nút "+ Thêm món đã ăn" mở ô tìm (dùng lại tìm kiếm không dấu từ `Dislikes`) + ô gram.
  - Nút "Cân lại các bữa còn lại" chỉ hiện khi có chênh lệch > 5 %.
- **Test:**
  - Đánh dấu ăn/bỏ đánh dấu.
  - Totals intake đúng.
  - Rebalance giữ nguyên bữa đã ăn, bữa còn lại không dưới sàn.
  - Rebalance khi đã bị gắn cờ ED ⇒ 409.
  - Intake vi phạm dị ứng ⇒ 422.
  - Xóa tài khoản ⇒ xóa sạch intake.
  - Chat `log_food` (LLM giả lập + rule).

## L2. Danh sách đi chợ
- `GET /api/shopping-list?start=YYYY-MM-DD&days=1..7&servings=1..10`:
  - Gộp item của các bữa **active** trong các ngày đó (bỏ snack nhập từ nhãn, bỏ item có origin=pantry).
  - Trừ pantry của các ngày đó; không âm.
  - Nhân `servings` (số người ăn).
  - Nhóm theo `category`, mỗi nguyên liệu có `grams` (khối lượng sống/khô, đúng như catalog) và `purchase`:
    - Có `portion` (vd 1 quả trứng 50 g) ⇒ "n quả", làm tròn **lên**.
    - Không có ⇒ làm tròn lên bội số 50 g (≥ 100 g) hoặc 10 g với gia vị/dầu.
  - Kèm `days_used` (ngày nào cần).
  - Tên theo ngôn ngữ.
- Frontend: tab hoặc trang "Đi chợ" (thêm vào thanh điều hướng):
  - Chọn số ngày + số người.
  - Danh sách nhóm theo loại, có checkbox "đã mua" lưu localStorage theo khóa (start, days) và bọc try/catch.
  - Nút "Sao chép" (clipboard) và "Chia sẻ" (Web Share API, ẩn nếu không hỗ trợ), xuất dạng văn bản thuần.
  - Song ngữ.
- Test backend: gộp đúng giữa nhiều bữa/ngày; trừ pantry; servings; làm tròn đơn vị mua; ngày không có thực đơn bị bỏ qua và liệt kê ở `missing_days`. Test frontend: hàm định dạng văn bản xuất.

## L3. Hiệu năng LLM (nhẹ)
Một số câu chat mất 8–12 s (parse + resolve = 2 lượt LLM tuần tự). Ghi `timing_ms` (tổng, từng bước LLM) vào log ở mức DEBUG, **không** kèm nội dung. Thêm cache cho `parse()` (LRU 1000, khóa = văn bản chuẩn hóa + lang; **không** cache các câu có tín hiệu ED/restrict). Không đổi model.

## Tiêu chí nghiệm thu
Toàn bộ test pass; typecheck/build sạch; migration lên/xuống/lên OK. PO sẽ E2E với LLM thật: đánh dấu đã ăn ⇒ cân lại; "tôi vừa ăn 1 bát phở" ⇒ log; "tối nay ăn phở bò" ⇒ món ghép; "tôi không ăn được hành" ⇒ công thức không có hành; danh sách đi chợ 3 ngày × 2 người.
