# Trạng thái quy trình PO ↔ Dev (để tiếp tục nếu bị gián đoạn)

## Yêu cầu của chủ sản phẩm (2026-10-28 ~00:00)
1. Commit + push ✅ (nhánh `feat/mvp-review-v1`, commit 18e1046).
2. Brainstorm tính năng (ưu tiên 1–10), vấn đề, giải pháp LLM-first ⇒ giao dev 3 vòng ⇒ viết `report-v2.md`.
3. Lặp lại một lần nữa: brainstorm v3 ⇒ 3 vòng ⇒ `report-v3.md`.
4. Sắp hết usage ⇒ tạm dừng, tiếp tục lúc **03:15 ngày 28/10/2026** (cron một lần đã đặt trong phiên PO).
5. Định hướng: app không chuyên y tế, không có bác sĩ; người dùng tự nhập hoặc đưa ảnh/văn bản chỉ định của bác sĩ; ưu tiên LLM thay vì rule-based.

## Phiên
- PO: `homnayangibuthealthy-44`. Dev: `homnayangibuthealthy-3c`.
- Test backend: `C:\Users\nguye\AppData\Local\Temp\claude\d--HomNayAnGiButHealthy\5efd6715-9e6e-43d6-a648-f4274eb04742\scratchpad\venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` (trong `backend/`).
- Script E2E của PO (LLM thật): `scratchpad\e2e2.py`.

## Tiến độ
| Bước | Trạng thái |
|---|---|
| Brainstorm v2 (`review/brainstorm-v2.md`) | ✅ |
| Vòng 4 — giới hạn sức khỏe tự cung cấp + trích xuất ảnh/văn bản | ✅ nghiệm thu (221 test, E2E ảnh/văn bản OK) |
| Vòng 5 — hiểu món bằng LLM + đổi món/không thích (`review/round-5.md`) | ✅ nghiệm thu (264 test, E2E 9 câu + swap OK) |
| Vòng 6 — nhật ký đã ăn + danh sách đi chợ + sửa nhỏ (`review/round-6.md`) | ⏳ đã giao dev |
| report-v2.md + commit/push | chưa |
| Brainstorm v3, vòng 7–9, report-v3.md + commit/push | chưa |

## Cách tiếp tục
Đọc bảng trên ⇒ hỏi dev (SendMessage) đang ở đâu ⇒ nghiệm thu bằng cách tự chạy test + E2E ⇒ giao bước tiếp theo. Mỗi chu kỳ xong thì commit + push lên nhánh `feat/mvp-review-v1`.
