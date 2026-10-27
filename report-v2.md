# Báo cáo nghiệm thu v2 — Chu kỳ 2 (vòng 4–6)

**Ngày:** 2026-10-28 · **Nhánh:** `feat/mvp-review-v1` · **Brainstorm:** [review/brainstorm-v2.md](review/brainstorm-v2.md)
**Định hướng chu kỳ này:** app không chuyên về y tế, không có bác sĩ can thiệp. Người dùng tự nhập hoặc đưa ảnh/văn bản chỉ định của bác sĩ. Xử lý ngôn ngữ ưu tiên LLM (sai chính tả, tiếng địa phương, không dấu); rule-based chỉ làm lưới an toàn.
Mọi kết quả dưới đây PO đã **tự chạy lại** (test + E2E với LLM thật `gpt-6-luna`), không chỉ dựa vào báo cáo của dev.

## 1. Đã làm (5 tính năng ưu tiên cao nhất trong brainstorm v2)

| Ưu tiên | Tính năng | Người dùng được gì | Kiểm chứng E2E (LLM thật) |
|---|---|---|---|
| 1 | **Giới hạn sức khỏe tự cung cấp** (nhập tay / chụp ảnh / dán văn bản) + bỏ chặn y tế | Người có bệnh nền dùng được ngay sau một lần xác nhận "tự quản lý". Có đơn bác sĩ thì chụp ảnh, app tự điền giới hạn, người dùng duyệt rồi lưu | Ảnh đơn: đạm 45 g, natri 87 mmol ⇒ 2001 mg, kali 2 g ⇒ 2000 mg ✅. Văn bản: trích dẫn khớp nguyên văn ✅. "Muối < 5 g" ⇒ 1965 mg natri ✅. Ảnh bị xóa EXIF/GPS và không lưu ✅ |
| 2 | **Hiểu món ăn bằng LLM** | Gõ sai chính tả, không dấu, từ địa phương, món ghép vẫn hiểu; không chắc thì hỏi lại kèm nút chọn | "toi muon an ga ran" ✅, "trứg luộc" ✅, "bún bò huế" / "phở bò" ⇒ món ghép (gắn nhãn "AI ước tính") ✅. LLM chỉ được chọn mã trong danh sách cho sẵn, không bịa được |
| 4 | **Đổi một bữa + món không thích** | Đổi 1 chạm, các bữa khác giữ nguyên; app nhớ khẩu vị (kể cả gia vị như "hành") | Đổi bữa trưa: bữa khác giữ nguyên, năng lượng lệch 0 % ✅. "I don't like fish" ⇒ đề xuất ✅. "Không ăn được hành" ⇒ công thức AI không còn hành ✅. "Dị ứng tôm" ⇒ hướng dẫn sửa Hồ sơ, **không** tự sửa ✅ |
| 3 | **Nhật ký "đã ăn"** + cân lại các bữa còn lại | Vòng tiến độ hiện đã ăn / mục tiêu; ăn ngoài kế hoạch thì app cân lại các bữa chưa ăn | Đánh dấu bữa sáng + 200 g kem ⇒ cân lại bữa trưa/tối ✅. Chat "tôi vừa ăn 1 bát phở" ⇒ đề xuất ghi nhật ký + cân lại ✅. Không cắt giảm nếu đã bị gắn cờ rối loạn ăn uống ✅ |
| 5 | **Danh sách đi chợ** | Một danh sách cho N ngày × số người, đã trừ đồ có sẵn, quy về đơn vị mua; sao chép/chia sẻ | 3 ngày × 2 người, nhóm theo loại, trứng tính theo quả, làm tròn lên ✅ (20 ms) |

Kèm theo: cache parse và resolve, log thời gian từng bước LLM (không kèm nội dung), mọi tính năng mới đều có cả vi/en.

## 2. Số liệu

| | Đầu chu kỳ (sau v1) | Cuối chu kỳ |
|---|---|---|
| Test backend | 196 | **288 pass** |
| Test frontend | 27 | **35 pass** (typecheck + build sạch) |
| npm audit (high) | 0 | 0 (2 moderate react-router, đã chấp nhận) |
| Migration mới | — | 4 (health_limits, food_preferences, intake_entries + chuyển dữ liệu), lên/xuống/lên OK |

## 3. Vấn đề còn lại (đưa vào brainstorm v3)
- **Độ trễ chat** 3–8 s (parse + resolve = 2 lượt LLM tuần tự); cache chỉ giúp câu lặp lại.
- **Dữ liệu thiếu:** "trái thơm" (dứa), hành, nhiều món Việt chưa có ⇒ `need_label`. "1 bát phở" chỉ ghi được bánh phở.
- **Đa dạng thực đơn:** trứng xuất hiện dày (danh sách đi chợ 3 ngày × 2 người ra 20 quả).
- **Cảnh báo thừa** `NO_MAIN_DISH` trên bữa đã ăn sau khi cân lại.
- **Proposal "cân lại"** trong chat chưa có bản xem trước.
- **Ruff** tăng lên 71 (chủ yếu B008 `Depends` theo đúng mẫu FastAPI hiện có; nên cấu hình bỏ qua B008 cho thư mục api).

## 4. Việc của bạn (không đổi so với report.md)
Điền `JWT_SECRET` và `HEALTH_DATA_KEY` trong `.env` (lệnh tạo có trong report.md). Ảnh/văn bản chỉ định bác sĩ sẽ được gửi tới nhà cung cấp LLM: README có mục quyền riêng tư, nên báo cho người dùng thử.
