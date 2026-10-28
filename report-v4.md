# Báo cáo v4 — Dọn code + Hướng dẫn sử dụng (vòng 10–11)

Ngày 2026-10-28. PO tự nghiệm thu: chạy lại test và E2E với LLM thật.

## Kết quả
| | Trước | Sau |
|---|---|---|
| Backend test | 493 pass | 492 pass (bỏ 11 test của nhánh chat 1 lượt, thêm 10 test vòng 10) |
| Frontend test | 40 pass | 52 pass |
| `ruff check app` | 0 | 0 |
| Code | — | 42 file, +699 / −684 dòng (đã gồm nội dung hướng dẫn vi/en) |

## Vòng 10 — tối ưu, bỏ trùng (`review/round-10.md`)
- **Bảo mật:** nút Đăng xuất giờ thu hồi refresh token. E2E: dùng lại token cũ sau khi đăng xuất bị 401.
- **API trùng đã bỏ:** `POST /intake` và `GET /intake`. Chỉ còn `POST /intake/batch`; app, ảnh bữa ăn và chat đều ghi nhật ký qua một hàm `add_entries`. Cả lô chỉ nạp hồ sơ/catalog một lần.
- **Code chết đã bỏ:** nhánh chat 1 lượt LLM (`understand.py`, script đo, cờ cấu hình, các hàm n-gram trong resolve).
- **Kiểm tra dị ứng:** gom từ 3 chỗ chép tay về một hàm `ensure_allowed`.
- **Hiệu năng:** dựng ngữ cảnh người dùng (`Ctx`) một lần mỗi request. Trước đây `GET /menu?days=7` dựng 7 lần và mỗi thao tác sửa thực đơn dựng 2 lần; E2E đo được còn 1. Frontend dùng luôn thực đơn API trả về, không tải lại; truy vấn `/dishes` dùng chung một hook.
- **Cấu trúc:** logic công thức nấu, đồ có sẵn và danh sách món chuyển từ routes sang services. Slot dùng kiểu `Slot` (slot sai trả 422). Nút +/− và Bỏ cố định có giới hạn tần suất riêng, 60 lần/phút.

## Vòng 11 — Hướng dẫn sử dụng (`review/round-11.md`)
- Nội dung: `docs/USER_GUIDE.md`. Trong app là trang `/help` song ngữ, gồm 11 mục mở/đóng được, xem được cả khi chưa đăng nhập.
- Lối vào: trang đăng nhập, đầu trang Cài đặt, banner "Mới dùng?" ở Hôm nay (đóng được), và link theo ngữ cảnh ở Hôm nay khi chưa có thực đơn, Trò chuyện, Có sẵn, Giới hạn sức khỏe.

## E2E (LLM thật)
Đã chạy các bước: tạo thực đơn → +/− → bỏ cố định → đổi món → ghi nhật ký bằng batch (chặn tôm khi dị ứng hải sản) → 3 câu chat (2,4–4,1 s, đều áp dụng được) → gợi ý cách nấu bằng LLM → đăng xuất. Tất cả đạt.

## Còn mở
- Chưa thử giao diện trên trình duyệt thật (360 px, sáng/tối, `/help` khi offline) vì Docker không chạy.
- `ruff check .` (cả tests/alembic) có 27 lỗi cũ từ trước, không phát sinh ở vòng này.
- Các việc còn mở trong `report-v3.md` mục 3 vẫn giữ nguyên.
