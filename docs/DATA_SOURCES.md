# Nguồn dữ liệu

## Thành phần dinh dưỡng nguyên liệu

| Mục | Nguồn | Ghi chú |
|---|---|---|
| 94 nguyên liệu nấu ăn + 21 đồ ăn vặt | USDA FoodData Central, **SR Legacy (2018-04)**, public domain | Mỗi nguyên liệu có `fdc_id`, mô tả gốc USDA và URL kiểm chứng `https://fdc.nal.usda.gov/food-details/<fdc_id>/nutrients`. Số liệu được sinh tự động bằng `backend/seed/build_ingredients.py`. |
| Khẩu phần đồ ăn vặt | USDA `food_portion.csv` (cùng bộ dữ liệu) | Build script kiểm tra khẩu phần có tồn tại trong USDA. |
| Chỉ số đường huyết (GI) | Atkinson FS et al., *International tables of GI and GL values: 2008*, Diabetes Care 2008;31:2281-3 | **Chưa xác minh** (`gi_verified=false`): nhập theo bảng, chưa đối chiếu lại bản gốc. Chỉ dùng làm phạt mềm cho người tiểu đường. |
| Nguyên liệu do người dùng nhập | Nhãn sản phẩm | Được đánh dấu “người dùng cung cấp”. Có kiểm tra năng lượng khớp với đạm/carb/béo (Atwater, sai lệch ≤ 20%). Không bao giờ được dùng làm gợi ý bổ sung chất. |

Chỉ số USDA không có số liệu được lưu là `null` và hiển thị là “chưa xác minh”: fiber và vitamin D của tôm, kẽm của rau lang, vitamin D của một số bánh kẹo và nước cam. Hệ thống tính các chỉ số này bằng 0, nên có thể báo thiếu nhiều hơn thực tế.

**Thay thế do USDA không có:** rau muống → rau lang (Sweet potato leaves); cá tra/basa → cá da trơn Mỹ (Channel catfish); bún/phở → Rice noodles, dry; **cá lóc → cá chó phương Bắc (Fish, pike, northern, raw — cá nước ngọt, thịt trắng, ít béo)**; bánh phở/bún tươi → Rice noodles, cooked; nấm rơm → Mushrooms, straw, canned, drained solids.

**Vòng 7 (+35 nguyên liệu, +39 món, tổng 65 món):** FDC ID được tra lại trong `food.csv` của chính bộ dữ liệu; mỗi mục trong `backend/seed/catalog.py` có comment là description gốc USDA. 80 nguyên liệu cũ được build lại từ cùng bộ CSV và **không đổi** (test so snapshot). **Đã bỏ qua vì SR Legacy không có tương đương tốt** (không dùng thực phẩm sai để lấp chỗ): rau muống (đã có thay thế rau lang), cải ngọt (choy sum), bạc hà/dọc mùng, bắp chuối, thanh long, chôm chôm (chỉ có loại đóng hộp ngâm siro), bánh tráng, hủ tiếu dạng bánh gạo (USDA chỉ có bánh gạo phồng — giữ alias “hủ tiếu” cho bún/phở khô), cá cơm khô (chỉ có cá cơm tươi/đóng hộp dầu — đã thêm cá cơm tươi), chè đậu, bánh mì Việt (đã có “Bánh mì” = French bread).

**Món ăn:** thành phần món (nguyên liệu chính `main`, bữa phù hợp) là **giả định ẩm thực** do nhóm phát triển khai báo, không phải số liệu dinh dưỡng; số liệu luôn tính từ từng nguyên liệu USDA.

**Chưa dùng** Bảng thành phần thực phẩm Việt Nam (Viện Dinh dưỡng). Bảng này không có API công khai, và việc dùng cần xem xét bản quyền.

## Khuyến nghị dinh dưỡng

| Chỉ số | Giá trị | Nguồn | Áp dụng |
|---|---|---|---|
| BMR | 10W + 6.25H − 5A + 5 (nam) / −161 (nữ) | Mifflin MD et al., Am J Clin Nutr 1990;51:241-7 | Người trưởng thành (ứng dụng nhận 18–100 tuổi) |
| Hệ số hoạt động | 1.2 / 1.375 / 1.55 / 1.725 / 1.9 | Bộ hệ số PAL phổ biến (McArdle, Katch & Katch, *Exercise Physiology*) | Giả định, sai số cá nhân ±10% |
| AMDR | Carb 45–65%, béo 20–35%, đạm 10–35% | IOM, *DRI for Energy, Carbohydrate, Fiber, Fat, Fatty Acids, Cholesterol, Protein, and Amino Acids*, 2005 | Người trưởng thành |
| Đạm | RDA 0.8 g/kg; tăng cơ 1.6 g/kg | IOM 2005; Jäger R et al., ISSN Position Stand, JISSN 2017;14:20 | |
| Carb tối thiểu | 130 g/ngày | IOM 2005 (RDA) | Người trưởng thành |
| Chất xơ | 14 g / 1000 kcal | IOM 2005 (AI) | |
| Sắt (RDA/UL, mg) | 18 t: 11/15; 19–50: 8 nam/18 nữ; ≥51: 8; UL 45 | NIH ODS Iron Fact Sheet | theo tuổi/giới |
| Kẽm (RDA/UL, mg) | 18 t: 11/9; ≥19: 11 nam/8 nữ; UL 40 | NIH ODS Zinc Fact Sheet | theo tuổi/giới |
| Canxi (RDA/UL, mg) | 18 t: 1300 (UL 3000); 19–50: 1000 (UL 2500); 51–70: 1000 nam/1200 nữ (UL 2000); ≥71: 1200 | NIH ODS Calcium Fact Sheet | theo tuổi/giới |
| Vitamin D (RDA/UL, µg) | 18–70: 15; ≥71: 20; UL 100 | NIH ODS Vitamin D Fact Sheet | theo tuổi |
| Natri (tối đa) | 2300 mg (CDRR); 1500 mg nếu tăng huyết áp | NASEM, *DRI for Sodium and Potassium* 2019; American Heart Association | ≥14 tuổi |
| Sàn năng lượng | max(BMR, 1200 nữ / 1500 nam) | NHLBI Obesity Guidelines 1998 (1000–1200 nữ, 1200–1600 nam) | **Cần xác minh lại** |
| Tối thiểu tuyệt đối | 800 kcal | Chế độ < 800 kcal (VLCD) cần giám sát y tế (NHLBI) | Không cho đặt thấp hơn |

Các giá trị vi chất được nhập theo các fact sheet trên; khuyến nghị đối chiếu lại với bản hiện hành trước khi mở cho người dùng thử.
