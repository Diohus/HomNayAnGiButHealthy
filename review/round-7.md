# Vòng 7 — Mở rộng CSDL món Việt (#1) + Đa dạng thực đơn & dọn cảnh báo (#2) + nợ kỹ thuật nhẹ (#10)

Chu kỳ v3, xem `review/brainstorm-v3.md`. PO đã nghiệm thu v2 (288 test; E2E với LLM thật), commit `0625404` đã push.
Quy ước: không commit, không sửa `.env`. Sắp chạm hạn mức usage ⇒ dừng ở điểm test pass, ghi "Tiến độ dev" ở cuối file này, báo PO.

## M1. Mở rộng dữ liệu (nguyên tắc: không bịa số liệu)
- **Nguồn số liệu:** chỉ dùng **USDA FDC SR Legacy**, qua `seed/build_ingredients.py`.
  - Tải `https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip` vào thư mục tạm **ngoài repo** (scratchpad hoặc %TEMP%; dùng truststore nếu TLS lỗi). Giải nén vào **thư mục mới, trống**.
  - Không commit CSV.
  - Chạy lại script để sinh `ingredients.json`. Giá trị **80 nguyên liệu cũ phải giữ nguyên**; nếu đổi thì dừng và báo PO.
- **Nguyên liệu (~40 mới), ưu tiên những thứ người Việt dùng hằng ngày:**
  - Thịt, cá, hải sản: thịt ba chỉ heo, sườn heo, thịt heo xay, gan gà, cua, nghêu, cá lóc (không có thì chọn cá nước ngọt tương đương trong USDA và ghi rõ), cá cơm khô.
  - Rau, gia vị tươi: hành tây, hành lá, tỏi, gừng, sả, rau muống, mồng tơi, cải ngọt, bạc hà (dọc mùng), măng, nấm rơm/nấm hương, bắp chuối.
  - Trái cây: dứa/thơm, thanh long, chôm chôm, nhãn, bưởi, mít.
  - Tinh bột: bánh phở tươi, bún tươi, bánh mì Việt (dùng bánh mì trắng), xôi/gạo nếp, bánh tráng, hủ tiếu (dùng bánh gạo).
  - Khác: đậu hũ chiên, trứng vịt, nước dừa, sữa đặc (snack), chè đậu (bỏ nếu USDA không có phù hợp).

  Mỗi mục cần: FDC ID, `name_vi`, `name_en`, `display_en`, alias vi (kể cả từ địa phương, vd thơm/khóm/dứa, củ sắn/củ đậu), alias en, `category`, tags dị ứng/chế độ ăn (cua/nghêu ⇒ `allergen:shellfish`, cá cơm ⇒ `allergen:fish`, đậu hũ ⇒ `allergen:soy`), min/max/step, slots, portion nếu USDA có.
- **Quy trình chọn FDC ID:** được dùng LLM để gợi ý, nhưng **phải tra lại** bằng `food.csv` (description khớp). Trong `seed/catalog.py`, mỗi mục ghi comment description USDA. Thực phẩm Việt **không có tương đương tốt** ⇒ bỏ qua và liệt kê vào báo cáo, **không** dùng thực phẩm sai để lấp chỗ.
- **Món (~40 mới):** phở bò, phở gà, bún chả, bún riêu (nếu có cua), cơm tấm sườn, canh chua cá lóc, canh rau muống, rau muống xào tỏi, canh mồng tơi, thịt kho trứng, sườn ram, gà xào sả ớt, cá kho tộ (đã có, bổ sung), bò lúc lắc, đậu hũ dồn thịt, trứng chiên hành, canh bí đao tôm, cháo gà, xôi đậu xanh (sáng), bánh mì trứng (sáng), cơm chiên trứng…
  - Món chỉ khai báo `main` (nguyên liệu chính) + `slots` + `name_vi/name_en`, theo mô hình hiện có.
  - Ghi chú ở `docs/ASSUMPTIONS.md`: thành phần món là giả định ẩm thực, không phải số liệu.
- **Món ghép trong resolver:** món có trong catalog thì resolver ưu tiên `dish` thay vì `composite` (vd "phở bò" giờ nên ra dish `pho_bo`). Test.
- **Test dữ liệu:**
  - Mọi FDC ID tồn tại và khác nhau.
  - Mọi món tham chiếu nguyên liệu có thật.
  - Mỗi nguyên liệu mới có alias vi + display_en.
  - Tag dị ứng của nhóm hải sản/cá/đậu nành đúng.
  - 80 nguyên liệu cũ: số liệu không đổi (so với snapshot trong test).
  - `DATA_SOURCES.md` cập nhật số lượng.

## M2. Đa dạng thực đơn
- **Phạt dùng lặp nguyên liệu protein** (category `protein`) đã có trong **2 ngày liền trước**: hệ số lớn hơn phạt món (dish) hiện có. Truyền `recent_foods: dict[code, so_ngay]` giống `recent_dishes`.
- **Trứng:** chỉ được là nguyên liệu protein chính tối đa **1 bữa/ngày** (ràng buộc mềm, phạt nặng). Ghi lý do vào ASSUMPTIONS (đa dạng, không phải khuyến nghị y khoa).
- **Chỉ số đa dạng trong test:** sinh 7 ngày cho hồ sơ chuẩn ⇒ ≥ 5 món chính khác nhau trên 7 ngày, trứng không xuất hiện ở > 1 bữa/ngày, ít nhất 4 nguồn protein khác nhau. So sánh trước/sau trong báo cáo.

## M3. Dọn cảnh báo + xem trước
- Bỏ cảnh báo `NO_MAIN_DISH` cho bữa đã ăn / frozen. Test.
- Proposal `rebalance` trong chat có `plan` xem trước. Engine vẫn không I/O: service tính trước và truyền vào context (callback `rebalance_preview`, giống `plan_fn`).

## M4. Nợ kỹ thuật nhẹ
`pyproject.toml`: `[tool.ruff.lint.per-file-ignores]` bỏ B008 cho `app/api/*` (mẫu `Depends` chuẩn của FastAPI). Sửa các lỗi ruff còn lại nếu đơn giản; báo số trước/sau.

## Tiêu chí nghiệm thu
Toàn bộ test pass; build sạch; seed idempotent (`python -m app.seed` chạy 2 lần không lỗi). PO sẽ E2E: "cho tôi ít trái thơm", "trưa nay ăn cơm tấm", "tôi vừa ăn 1 tô phở bò", "tối nay ăn canh chua cá lóc"; sinh 7 ngày và đếm độ đa dạng; danh sách đi chợ 3 ngày × 2 người (số trứng).
