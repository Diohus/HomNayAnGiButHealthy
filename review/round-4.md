# Vòng 4 — Giới hạn sức khỏe do người dùng cung cấp (nhập tay / ảnh / văn bản), bỏ chặn y tế

Bối cảnh: xem `review/brainstorm-v2.md` (định hướng mới + mục ưu tiên #1). Môi trường test như `round-1.md` mục 0 (venv scratchpad đã có Pillow).
Làm trên nhánh git hiện tại `feat/mvp-review-v1`. **Không commit** (PO sẽ commit sau khi nghiệm thu). Không sửa `.env`.

## H1. Bỏ chặn sinh thực đơn với bệnh nền nhạy cảm
Hiện trạng: `guardrails/medical.py: pending_expert_confirmations` + `Ctx.ensure_allowed()` ⇒ 403 `EXPERT_CONFIRMATION_REQUIRED` cho tới khi nhập "xác nhận chuyên gia". Thay bằng:
- Hồ sơ thêm trường `acknowledge_self_managed: bool = False`. Có bệnh nền nhạy cảm mà trường này `false` ⇒ `PUT /profile` trả 409 `SELF_MANAGED_ACK_REQUIRED`. Thông điệp: app không có bác sĩ theo dõi, chỉ là gợi ý có sai số; nếu có chỉ định của bác sĩ thì nên nhập. Khi đã xác nhận ⇒ **được sinh thực đơn**.
- `ensure_allowed()` không còn chặn vì thiếu xác nhận chuyên gia. Bỏ mã `EXPERT_CONFIRMATION_REQUIRED` khỏi luồng sinh thực đơn, cập nhật mọi chỗ gọi (generate, adjust, unlock, apply_plan, chat engine `blocked_conditions`).
- Thiếu giới hạn cho một bệnh nền nhạy cảm ⇒ dùng mục tiêu chung như người khỏe. `menu_notices` thêm notice `NO_LIMITS_<CONDITION>` (song ngữ), nói rõ chưa có giới hạn riêng (vd thận: đạm/kali/phốt pho), thực đơn có thể không phù hợp, nên nhập chỉ định bác sĩ nếu có. Notice hiện ở màn Hôm nay và Hồ sơ.
- **Không** tự đặt giới hạn y khoa nào mới (không bịa số). Disclaimer giữ nguyên.

## H2. Mô hình "giới hạn sức khỏe" (đổi tên từ expert confirmation)
- Bảng mới `health_limits` (migration mới, có chuyển dữ liệu từ `expert_confirmations` rồi drop bảng cũ trong cùng migration; downgrade làm ngược lại): `id, user_id (FK CASCADE), condition_code nullable (null = áp dụng chung), encrypted_payload (ExpertLimits), source ("manual" | "document"), confirmed_at`.
- Mở rộng `ExpertLimits` (đổi tên `HealthLimits`, giữ alias import cũ nếu tiện): thêm `carb_g_max`, `fat_g_max`, `sugar` **không** thêm (chưa có dữ liệu). Mỗi trường giữ khoảng hợp lệ như hiện tại; `carb_g_max` 20–600, `fat_g_max` 10–300.
- API mới (thay `/expert-confirmations`):
  - `GET /api/health-limits` ⇒ danh sách (đã giải mã) + `source`.
  - `PUT /api/health-limits` body `{condition: Condition|null, limits: HealthLimits, source}` ⇒ upsert theo (user, condition). Cần ít nhất 1 giá trị.
  - `DELETE /api/health-limits/{id}`.
- `compute_needs` áp mọi giới hạn (gộp lấy chặt nhất như hiện tại) và thêm `carb_g_max` / `fat_g_max`. Nếu cap carb/béo làm năng lượng không đủ ⇒ **không tự bù** bằng chất khác ngoài AMDR; thêm warning `LIMITS_REDUCE_ENERGY` để UI báo. Nguồn tham chiếu hiển thị "Do người dùng cung cấp (nhập tay)" hoặc "(trích từ tài liệu)".

## H3. Trích xuất giới hạn từ ảnh / văn bản bằng LLM
`POST /api/health-limits/extract`, multipart:
- `file` (jpeg/png/webp, ≤ 5 MB) **hoặc** `text` (≤ 5000 ký tự), kèm `consent_ai_processing=true` (thiếu ⇒ 422 `AI_CONSENT_REQUIRED`).
- Ảnh: mở bằng Pillow, kiểm tra đúng định dạng thật (không tin content-type), xoay theo EXIF rồi **bỏ toàn bộ metadata**, thu nhỏ cạnh dài ≤ 2000 px, mã hóa lại JPEG ⇒ base64 gửi LLM. Không lưu ảnh/văn bản xuống đĩa hay DB, không log.
- Provider: thêm `complete_json_with_image(system, user, image_b64, schema, name)` cho `OpenAICompatibleProvider` (content dạng `[{"type":"text"},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}]`). PO đã kiểm chứng gpt-6-luna nhận ảnh. `AnthropicProvider` làm tương ứng (block `image` base64) hoặc ném `LLMError("unsupported")`.
- Schema đầu ra (strict): `items: [{field: enum[energy_kcal_max, protein_g_max, carb_g_max, fat_g_max, sodium_mg_max, potassium_mg_max, phosphorus_mg_max], value: number, unit: enum[kcal, g, mg, mmol], quote: string}]`, `other_instructions: [string]` (chỉ dẫn không định lượng được, vd "hạn chế đồ chiên"), `language: vi|en|other`. Prompt nói rõ: chỉ trích những gì **ghi rõ trong tài liệu**, không suy đoán, không tự thêm khuyến nghị.
- Hậu kiểm bằng code (không tin LLM):
  - Quy đổi đơn vị xác định: natri mmol × 23 = mg; kali mmol × 39.1; g → mg cho natri/kali/phốt pho.
  - Loại giá trị ngoài khoảng hợp lệ (đưa vào `rejected` kèm lý do).
  - Với đầu vào văn bản: `quote` phải xuất hiện trong văn bản (so sánh sau chuẩn hóa khoảng trắng/dấu); không có ⇒ loại.
  - Dùng `call_structured` (retry có giới hạn). LLM lỗi ⇒ 503 `EXTRACTION_UNAVAILABLE`, người dùng vẫn nhập tay được.
- Trả về **bản nháp**, không lưu: `{limits: {...}, items: [...với quote...], rejected: [...], other_instructions: [...]}`. Người dùng sửa rồi gọi `PUT /health-limits` với `source="document"`.
- Rate limit: 5 lần / giờ / user.
- Test (LLM giả lập): quy đổi mmol; giá trị ngoài khoảng bị loại; quote không có trong văn bản bị loại; thiếu consent ⇒ 422; file không phải ảnh (vd PDF đổi đuôi .png) ⇒ 422 `INVALID_IMAGE`; ảnh có EXIF ⇒ bytes gửi LLM không còn EXIF; không ghi gì vào DB khi gọi extract.

## H4. Frontend
- Trang Cài đặt ⇒ mục **"Giới hạn sức khỏe của tôi"** (thay phần xác nhận chuyên gia):
  - Danh sách giới hạn hiện có (nguồn, ngày), sửa/xóa.
  - Thêm giới hạn với 3 tab: **Nhập tay** | **Chụp/tải ảnh** (`<input type="file" accept="image/*" capture="environment">`) | **Dán văn bản**.
  - Ảnh/văn bản: checkbox đồng ý (bắt buộc), nội dung kiểu "Ảnh/văn bản sẽ được gửi tới nhà cung cấp AI để đọc, không được lưu lại"; nút "Đọc tài liệu" (có trạng thái đang xử lý). Kết quả hiện thành form đã điền sẵn, mỗi giá trị kèm **trích dẫn nguyên văn**; mục bị loại hiện kèm lý do; chỉ dẫn khác hiện dạng danh sách. Người dùng sửa rồi bấm "Lưu giới hạn".
- Hồ sơ: chọn bệnh nền nhạy cảm ⇒ hiện checkbox `acknowledge_self_managed` kèm giải thích và link tới mục giới hạn.
- Today: bỏ banner "Cần xác nhận chuyên gia"; hiện notice `NO_LIMITS_*` khi có.
- Song ngữ đầy đủ (vi/en), giữ test parity từ điển.

## H5. Docs
`work.txt` **không sửa** (là brief gốc). Cập nhật `docs/ASSUMPTIONS.md` (định hướng tự quản lý, trích xuất bằng AI có sai số, không lưu ảnh) và README (tính năng mới, quyền riêng tư khi gửi ảnh tới nhà cung cấp AI).

## Tiêu chí nghiệm thu
1. Toàn bộ test backend + frontend pass; typecheck/build sạch; migration upgrade → downgrade → upgrade OK trên SQLite.
2. Test guardrail cũ về "chặn khi chưa xác nhận chuyên gia" được **thay** bằng test mới (ack bắt buộc, sinh thực đơn được khi đã ack, notice NO_LIMITS đúng).
3. Báo PO qua SendMessage: file đã đổi, kết quả test, chỗ làm khác yêu cầu.
