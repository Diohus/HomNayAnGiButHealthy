# Báo cáo nghiệm thu v3 — Chu kỳ 3 (vòng 7–9)

**Ngày:** 2026-10-28 · **Nhánh:** `feat/mvp-review-v1` · **Brainstorm:** [review/brainstorm-v3.md](review/brainstorm-v3.md) · Báo cáo trước: [report.md](report.md) (v1), [report-v2.md](report-v2.md)
Mọi kết quả dưới đây PO đã **tự chạy lại** (test, E2E với LLM thật, đối chiếu USDA), không chỉ dựa vào báo cáo của dev.

## 1. Đã làm (7 mục ưu tiên cao nhất trong brainstorm v3)

| Ưu tiên | Tính năng | Người dùng được gì | PO kiểm chứng |
|---|---|---|---|
| 1 | **Mở rộng dữ liệu món Việt:** 80 → 115 nguyên liệu, 26 → 65 món (phở, bún chả, bún bò Huế, cơm tấm, canh chua cá lóc, thịt kho trứng…); alias địa phương (thơm/khóm/dứa, củ sắn, ba rọi, cá quả, ngao) | Chatbot hiểu món người Việt ăn hằng ngày; thực đơn quen thuộc | Đối chiếu ngẫu nhiên 5 nguyên liệu với **API USDA chính thức: khớp 5/5**. 80 nguyên liệu cũ không đổi (test snapshot). Những thực phẩm không có tương đương tốt bị **bỏ qua**, không lấp bằng số sai (danh sách ở `docs/DATA_SOURCES.md`) |
| 2 | **Thực đơn đa dạng hơn** + bỏ cảnh báo thừa + xem trước khi cân lại | Hết cảnh "ngày nào cũng trứng" | 7 ngày: 15 → **20** món khác nhau; 9 → **14** nguồn đạm; trứng ≤ **1 bữa/ngày**; đi chợ 3 ngày × 2 người: 20 → **4 quả** trứng; macro trong ±1 % |
| — | **Sửa lỗi phát hiện qua E2E:** "bún chả" làm chatbot đề xuất thực đơn rỗng; "trưa nay ăn cơm tấm" bị hiểu là "đã ăn"; ghi món thiếu cơm | Không còn câu trả lời vô nghĩa | Thêm **test bao phủ: 133 cặp món × bữa đều xếp được**. Đề xuất rỗng bị chặn ở engine. Phân biệt muốn ăn / đã ăn đúng |
| 3 | **Chat nhanh hơn** | Trước: 4–13 s ⇒ nay **2,8–4,9 s** | Phương án "gộp 2 lượt LLM thành 1" đã làm nhưng **đo thật lại chậm hơn** (p50 4,6 s so với 3,1 s) ⇒ **giữ tắt** (bật bằng `CHAT_SINGLE_PASS=true`). Tốc độ tăng chủ yếu nhờ dữ liệu món và alias, vì nhiều câu không còn cần LLM resolve |
| 4 | **Chụp ảnh bữa ăn để ghi nhật ký** | Ghi nhật ký bằng 1 tấm ảnh, sửa gram rồi lưu | Ảnh không phải đồ ăn ⇒ từ chối (LLM thật) ✅. Luồng ảnh món thật mới test bằng LLM giả lập (Wikipedia chặn tải ảnh mẫu) ⇒ **nên tự thử bằng 1 ảnh bữa ăn thật** |
| 5 | **Tổng quan tuần** (tab "Tuần" trong Hôm nay) | Biểu đồ 7 ngày, trung bình, "chất hay thiếu" kèm gợi ý thực phẩm | API trả đúng `basis`, chỉ tính ngày đã ghi; gợi ý bỏ đồ dị ứng / không thích |
| 6 | **Tải dữ liệu của tôi** + bộ test **chống prompt injection** | Minh bạch dữ liệu; an toàn trước tài liệu/tin nhắn độc hại | Sai mật khẩu ⇒ 401; file JSON đủ 13 mục, **không lộ** hash, token hay mật khẩu. 10/10 test injection pass (LLM giả lập "nghe lời kẻ tấn công" mà vẫn bị hậu kiểm bằng code chặn) |
| 7 | **PWA** (cài lên điện thoại) | Mở như app, banner khi mất mạng | `dist/` có manifest, `sw.js`, icon; service worker **không bao giờ cache `/api`** (dữ liệu sức khỏe) |

Kèm theo: ruff 71 → **0**.

## 2. Số liệu

| | Đầu v3 | Cuối v3 |
|---|---|---|
| Test backend | 288 | **493 pass** (gồm 133 test bao phủ món, 10 test injection) |
| Test frontend | 35 | **40 pass** (typecheck + build sạch) |
| Nguyên liệu / món | 80 / 26 | **115 / 65** |
| Thời gian trả lời chat (LLM thật) | 4–13 s | **2,8–4,9 s** |
| npm audit (high) | 0 | 0 (2 moderate react-router, đã chấp nhận) |
| ruff | 71 | 0 |

## 3. Vấn đề còn lại và đề xuất cho chu kỳ sau

| # | Vấn đề | Đề xuất |
|---|---|---|
| 1 | **Tổng quan tuần coi ngày chỉ ghi một phần là "đã ghi"** ⇒ trung bình thấp giả (PO thử: ghi 2/3 bữa ⇒ trung bình 1164 kcal). Với người nhạy cảm chuyện ăn uống, con số này dễ gây lo lắng | Chỉ tính ngày người dùng ghi đủ các bữa hoặc tự bấm "ngày đã xong"; ngày dở dang hiển thị riêng |
| 2 | Chưa test ảnh bữa ăn thật với LLM thật | Bạn tự thử vài ảnh; nếu sai nhiều thì thêm bước "chọn món từ gợi ý" |
| 3 | Chưa ghi nhật ký được cho ngày trước ("tối qua ăn phở") | Cho phép chọn ngày trong 3 ngày gần nhất |
| 4 | Một số rau Việt chưa có trong USDA (rau muống, cải ngọt, thanh long…) | Nhập **Bảng thành phần thực phẩm Việt Nam (Viện Dinh dưỡng)** khi có bản số hóa hợp lệ |
| 5 | Rủi ro injection còn lại: tài liệu độc hại có thể đưa vào một giới hạn **hợp lệ** (có trích dẫn thật, trong khoảng cho phép) | Đã giảm thiểu: chỉ là bản nháp, người dùng phải duyệt. Có thể thêm cảnh báo khi giới hạn lệch xa mức thường gặp |
| 6 | Đăng ký dạng hội thoại; kho có sẵn tự trừ khi ăn (mục 8–9 brainstorm v3) | Chu kỳ sau |
| 7 | Bộ test backend chạy ~5 phút (do 133 test bao phủ món) | Tách lệnh `pytest -m "not slow"` cho vòng lặp phát triển nhanh |

## 4. Việc của bạn
1. Điền `JWT_SECRET` và `HEALTH_DATA_KEY` vào `.env` (lệnh tạo có trong [report.md](report.md) mục 1), nếu chưa làm.
2. Chạy thử trên điện thoại: chế độ tối, tiếng Anh, chụp ảnh đơn bác sĩ, chụp ảnh bữa ăn, cài PWA.
3. Tạo PR từ `feat/mvp-review-v1` vào `main` khi đã hài lòng (PO chưa tự merge).
