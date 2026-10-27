# Vòng 5 — Hiểu món ăn bằng LLM (#2) + Đổi món / Món không thích (#4)

PO đã nghiệm thu vòng 4: 221 test pass; E2E với LLM thật — ảnh đơn trích đúng (87 mmol natri ⇒ 2001 mg), văn bản có trích dẫn khớp nguyên văn, notice NO_LIMITS tắt sau khi lưu giới hạn. Chấp nhận mọi quyết định 1–9 của dev.
Cùng quy ước: nhánh `feat/mvp-review-v1`, không commit, không sửa `.env`, venv scratchpad.

## K0. (nhỏ, nối tiếp vòng 4) Quy đổi muối sang natri khi trích xuất
"Muối < 5 g" là chỉ dẫn rất phổ biến. NaCl chứa 39,3 % natri theo khối lượng, nên quy đổi này là **xác định**, không phải ước lượng. Vì vậy:
- Cho phép LLM trả `field=sodium_mg_max`, `unit="g_salt"` khi tài liệu ghi muối.
- Code quy đổi: `× 393 mg/g`. Item có `converted_from="salt"` để UI ghi "quy đổi từ 5 g muối".
- Test.

## K1. Hiểu món ăn bằng LLM (thay thế phần dò alias cứng làm đường chính)
Vấn đề: `foods/matching.py` chỉ khớp alias đúng chữ. "ga ran", "trứg", "trái thơm", "củ sắn", "bún bò huế", "xôi gà" ⇒ không nhận ra ⇒ bắt nhập nhãn.

Thiết kế `app/foods/resolve.py`:
1. **Bước 1 (xác định):** `find_foods` hiện có. Khớp chính xác ⇒ confidence 1.0, không gọi LLM.
2. **Bước 2 (ứng viên):** với mention chưa khớp, lấy top-k (k = 25) ứng viên từ catalog **đã lọc dị ứng VÀ chưa lọc** (cần biết để giải thích từ chối). Chấm điểm bằng `difflib` / tỉ lệ token trùng trên tên vi (bỏ dấu), alias vi/en, display_en. Không thêm dependency.
3. **Bước 3 (LLM):** structured output, schema dựng **động mỗi lần gọi**. `food_code` và `dish_code` là `enum` gồm đúng các mã ứng viên + `null` ⇒ LLM không bịa được mã. Mỗi mention trả về:
   - `kind`: ingredient | dish | composite | not_food | unknown
   - `food_code`, `dish_code`
   - `components: [{food_code(enum), grams}]` — chỉ dùng cho composite, vd "phở bò" = bánh phở + bò + rau
   - `confidence` 0–1
   - `alternatives`: tối đa 3 mã (enum)

   Prompt nêu rõ: người dùng có thể viết sai chính tả, không dấu, dùng từ địa phương hoặc tiếng Anh.
4. **Hậu kiểm bằng code:** mã phải nằm trong tập ứng viên; `grams` của component phải trong `[min_g, 2×max_g]` của nguyên liệu, ngoài khoảng thì kẹp lại và ghi warning. Composite tối đa 6 component.
5. **Xử lý theo confidence:**
   - `< 0.6`, hoặc có nhiều alternatives ngang nhau ⇒ chatbot **hỏi lại**, kind `clarify`: "Ý bạn là A hay B?", kèm `options` (mã + tên đã dịch). Frontend hiện thành nút bấm nhanh; bấm ⇒ gửi lại tin nhắn kèm `resolved: {mention: code}`. API chat nhận thêm trường tùy chọn `resolved`.
   - Composite ⇒ các item mang `origin="ai_estimate"`. UI gắn tag "AI ước tính · sai số cao", người dùng chỉnh +/- như thường. Dinh dưỡng **vẫn tính từ DB** theo từng nguyên liệu.
   - not_food / unknown ⇒ giữ luồng `need_label` hiện có.
6. **Fallback:** LLM tắt hoặc lỗi ⇒ dùng `find_foods` như hiện tại.
7. **Cache** in-memory LRU (≤ 2000 mục), khóa = (mention đã chuẩn hóa, lang, phiên bản catalog = hash các mã). Cache **không** chứa user_id hay dị ứng: kết quả cache là ánh xạ ngôn ngữ thuần, việc lọc dị ứng làm **sau** cache.
8. **Dị ứng vẫn là ràng buộc cứng sau khi resolve.** Món ghép có component dị ứng ⇒ từ chối và nêu component nào.

Test (LLM giả lập):
- LLM trả mã ngoài enum ⇒ loại, rơi về fallback.
- confidence thấp ⇒ `clarify` có options; gửi `resolved` ⇒ đi tiếp như mã đó.
- composite ⇒ items `ai_estimate`; component dị ứng ⇒ refusal.
- Cache hit thì không gọi LLM lần 2.
- LLM tắt ⇒ hành vi cũ.
- Grams vượt khoảng ⇒ bị kẹp.

## K2. Đổi một bữa
- `POST /api/menu/{day}/meals/{slot}/swap` (rate limit 20/phút/user):
  - Sinh lại **chỉ bữa đó**. Các bữa khác giữ nguyên, được truyền vào solver như item khóa ở đúng slot của chúng.
  - Cấm món chính hiện tại của bữa, các món không thích, và giữ ràng buộc lặp món.
  - Pantry và đồ ăn vặt giữ nguyên. Tổng ngày vẫn nhắm ±5% như thường.
  - Không còn món nào khác ⇒ 409 `NO_ALTERNATIVE` (song ngữ).
- Lưu trực tiếp (version +1), xóa recipe của bữa đó. Trả `_menu_out`.
- Test: món mới ≠ món cũ; bữa khác giữ nguyên gram; tổng trong ±5% (hoặc báo deviation như thường); không vi phạm dị ứng; không lặp quá 3 ngày.

## K3. Món / nguyên liệu không thích
- Bảng `food_preferences`: `id, user_id FK CASCADE, kind (food | dish), code, created_at`; unique (user, kind, code). Migration mới.
- API `GET/POST/DELETE /api/preferences/dislikes`. Mã phải tồn tại trong catalog mà user nhìn thấy được.
- Planner: món / nguyên liệu không thích bị **phạt nặng** (ràng buộc mềm, khác dị ứng là ràng buộc cứng). Không còn lựa chọn nào khác thì vẫn dùng và thêm warning `USED_DISLIKED:<code>`. Vì phạt mềm, ILP luôn có nghiệm.
- Chatbot: thêm intent `dislike` ("tôi không ăn được hành", "ghét rau mùi", "i don't like fish"):
  - Resolve qua K1 ⇒ trả proposal kind `preference` "Thêm X vào danh sách không thích?". Người dùng bấm Áp dụng ⇒ lưu.
  - Nếu câu nói **dị ứng** ("tôi bị dị ứng tôm") ⇒ **không** tự sửa hồ sơ. Trả lời hướng dẫn cập nhật dị ứng trong Hồ sơ (kèm link), vì dị ứng là dữ liệu sức khỏe và là ràng buộc cứng.
- Frontend:
  - Mỗi MealCard có nút "Đổi món" (đổi bữa này).
  - Trang Hồ sơ có mục "Không thích": chip danh sách + ô tìm nguyên liệu/món để thêm (lọc client-side từ `/foods` và `/dishes`), bấm × để xóa.
  - Chat hiển thị nút clarify và proposal preference.
  - Song ngữ đầy đủ.
- Test backend + frontend tương ứng (parity từ điển).

## Tiêu chí nghiệm thu
1. Toàn bộ test pass; typecheck/build sạch; migration upgrade/downgrade/upgrade OK.
2. PO sẽ chạy E2E với LLM thật các câu: "toi muon an ga ran", "trứg luộc", "trưa nay ăn bún bò huế", "cho tôi ít trái thơm", "tôi không ăn được hành", "I don't like fish", "tôi bị dị ứng tôm". Hãy tự thử trước bằng LLM giả lập để luồng không vỡ.
3. Báo PO như các vòng trước. Nếu sắp chạm hạn mức usage: dừng ở điểm test pass, ghi tiến độ vào cuối file này, rồi báo PO.
