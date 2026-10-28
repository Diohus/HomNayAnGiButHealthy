# Vòng 8 — Sửa lỗi từ E2E vòng 7 + Chat 1 lượt LLM (#3) + Chụp ảnh bữa ăn (#4)

PO đã nghiệm thu vòng 7:
- 310 test pass. Có 1 lần chạy gặp error do WinError 10055 (môi trường), chạy lại thì pass.
- Đối chiếu độc lập 5 nguyên liệu với **API USDA FDC chính thức**: khớp 5/5.
- 7 ngày: 18 món khác nhau, trứng ≤ 1 bữa/ngày, macro lệch ≤ 1 %. Đi chợ 3 ngày × 2 người: còn 4 quả trứng gà (trước là 20).
- Ruff 71 → 0.

Chấp nhận các quyết định 1–5. Quy ước như cũ.

## N0. Lỗi phát hiện khi E2E (làm trước)
- **N0a [HIGH] Món trong catalog không xếp vào thực đơn được.**
  - Tái hiện: "toi muon an bun cha" / "tôi muốn ăn bún chả" ⇒ `detected` có `dish_code=bun_cha`, nhưng proposal `plan_update` có `status=conflict`, `meals=0`, `conflicts=['SOLVER_NO_SOLUTION']`.
  - Việc cần làm: tìm nguyên nhân (slots của món và của nguyên liệu chính, `MAIN_MIN_SHARE`, giới hạn số tinh bột ≤ 2, `slots` của `fresh_rice_noodles`…) và sửa.
  - Thêm **test bao phủ dữ liệu:** với hồ sơ chuẩn (nữ 30 tuổi, hoạt động vừa, không dị ứng), **mọi món** trong catalog, khi `required` ở **mỗi slot nó được phép**, phải giải ra `status != conflict` và có món đó trong thực đơn. Test này phải chặn được loại lỗi dữ liệu như bún chả. Nếu chạy chậm, đánh dấu `@pytest.mark.slow` nhưng vẫn chạy mặc định.
- **N0b [HIGH] Không bao giờ đưa proposal có thực đơn rỗng.**
  - Trong engine (và mọi chỗ tạo proposal có `plan`): nếu `plan.status == "conflict"` hoặc `plan.meals` rỗng thì **không** tạo proposal. Thay vào đó trả `kind="info"` với câu giải thích song ngữ: "Mình chưa xếp được X vào thực đơn hôm nay (…). Bạn thử bữa khác hoặc ngày khác nhé."
  - Thêm test.
- **N0c [MEDIUM] Phân biệt "muốn ăn" và "đã ăn".**
  - "trưa nay ăn cơm tấm" (lúc 4 giờ sáng) đang bị hiểu là `log_food`.
  - Quy tắc: chỉ `log_food` khi có dấu hiệu quá khứ rõ ràng (vừa / đã / mới / rồi / xong / just / had / ate), **hoặc** LLM trả `log_food` **và** slot được nhắc tới đã qua theo giờ hiện tại (sáng < 10 h, trưa < 14 h, tối < 21 h là mốc "chưa qua"). Còn lại ⇒ `want_food`.
  - Cập nhật prompt parser. Thêm test cho các câu: "trưa nay ăn cơm tấm" (08:00 ⇒ want), "trưa nay ăn cơm tấm rồi" (⇒ log), "tối qua ăn phở" (⇒ log, ngày hôm qua; nếu chưa hỗ trợ ghi ngày quá khứ thì trả info).
- **N0d [MEDIUM] Ghi nhật ký món phải gồm cả phần ăn kèm.** "cơm tấm" ⇒ chỉ ghi "160 g sườn heo", thiếu cơm.
  - Thêm trường tùy chọn `log_sides: [{food_code, grams}]` trong `dishes.json` cho các món có tinh bột/rau ăn kèm điển hình: cơm tấm (cơm), bún chả (bún, rau sống), phở (đã có bánh phở trong main), cơm chiên… Đây là khối lượng khẩu phần điển hình, **giả định** ghi trong ASSUMPTIONS, người dùng sửa được.
  - Khi `log_food` một dish ⇒ ghi main (khẩu phần như hiện tại) + `log_sides`, tất cả source=`ai_estimate` hoặc `plan_estimate` để UI gắn nhãn "ước tính".

## N1. Chat 1 lượt LLM (mục tiêu: nhanh gấp đôi)
Hiện tại: parse (LLM) → resolve (LLM) tuần tự. PO đo E2E: 4–13 s.
- **Lấy ứng viên trước, ngay từ văn bản thô:** n-gram 1–4 từ (đã bỏ dấu) ⇒ chấm điểm với tên/alias vi/en của nguyên liệu và món (dùng lại bộ chấm điểm của K1) ⇒ top-25 nguyên liệu + top-10 món + nguyên liệu chính của các món đó ⇒ enum.
- **Một schema gộp:** các trường của `ParsedIntent` + `mentions: [{text, kind, food_code(enum|null), dish_code(enum|null), components, confidence, alternatives}]`. Hậu kiểm y như K1.
- Khớp alias trọn cụm / `find_dishes` **không** có mention mơ hồ ⇒ vẫn gọi LLM 1 lần (cần intent), nhưng với enum nhỏ.
- **Fallback:** lượt gộp lỗi schema sau số lần retry ⇒ chạy đường 2 bước cũ ⇒ cuối cùng là rule-based. Guardrail ED/allergy từ rule vẫn luôn được áp dụng.
- **Cache:** giữ cache parse/resolve. Khóa cache lượt gộp = (văn bản chuẩn hóa, lang, hash catalog). Không cache câu có tín hiệu ED/restrict/allergy.
- **Đo thật:** viết script `backend/scripts/bench_chat.py`, **không chạy trong pytest**, gọi LLM thật qua `.env`, chạy 10 câu cố định (liệt kê bên dưới) × 2 lượt (lượt 2 trúng cache). In p50/p90 trước (đường 2 bước, ép bằng cờ) và sau. Được phép gọi LLM thật cho việc đo này (khoảng 60 lượt). Báo số liệu cho PO.
  - 10 câu: "toi muon an ga ran", "trứg luộc", "trưa nay ăn bún bò huế", "cho tôi ít trái thơm", "tôi không ăn được hành", "I don't like fish", "tôi vừa ăn 1 tô phở bò", "tối nay ăn canh chua cá lóc", "toi muon an bun cha", "hôm nay cheat day, ăn pizza".
- **Frontend:** khi đang chờ chat thì hiển thị trạng thái "Đang hiểu câu của bạn…"; nút gửi bị khóa; có hủy (AbortController) nếu quá 30 s.

## N2. Chụp ảnh bữa ăn để ghi nhật ký
- `POST /api/intake/photo` (multipart: `file`, `day`, `slot` tùy chọn, `consent_ai_processing=true`). Rate limit 10/giờ/user.
- Xử lý ảnh **dùng lại** `limits_extract` (kiểm định dạng thật, xoay EXIF, bỏ metadata, ≤ 2000 px). Không lưu, không log.
- **Bước 1 — vision:** schema `{items: [{name (theo ngôn ngữ người dùng), estimated_grams, confidence}], is_food_photo: bool}`. Prompt: chỉ liệt kê món nhìn thấy; khối lượng là ước lượng; không suy đoán món không thấy.
- **Bước 2:** mỗi `name` ⇒ resolver (enum, K1/N1) ⇒ mã + components. Grams kẹp như K1.
- **Kết quả:** **bản nháp**, không lưu: `{entries: [{food_code, name, grams, confidence, source:"ai_estimate"}], unresolved: [name], rejected: [{name, reason (dị ứng)}], is_food_photo}`. `is_food_photo=false` ⇒ 422 `NOT_FOOD_PHOTO`.
- Người dùng sửa/xóa rồi gửi `POST /api/intake/batch` (danh sách entry; kiểm lại dị ứng; giới hạn 20 mục).
- **Frontend (IntakePanel):** nút "📷 Chụp bữa ăn" (`capture="environment"`) + checkbox đồng ý ⇒ danh sách nháp (sửa gram, xóa dòng, mục không nhận ra hiện kèm ô tìm thủ công) ⇒ "Ghi vào nhật ký". Có nhãn "AI ước tính · sai số cao". Song ngữ.
- **Test (LLM giả lập):** ảnh hợp lệ ⇒ bản nháp; dị ứng ⇒ rejected; không phải ảnh đồ ăn ⇒ 422; không ghi DB khi chỉ phân tích; batch ⇒ ghi; batch có dị ứng ⇒ 422; EXIF bị bỏ; rate limit.

## Tiêu chí nghiệm thu
- Toàn bộ test pass, có test bao phủ món (N0a).
- Có số đo p50/p90 trước/sau (N1).
- PO sẽ E2E: 10 câu ở N1 (đo thời gian), "toi muon an bun cha" ⇒ proposal có thực đơn, ảnh một đĩa cơm tấm thật ⇒ bản nháp hợp lý.
