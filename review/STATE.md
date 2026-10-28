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
| Vòng 6 — nhật ký đã ăn + danh sách đi chợ + sửa nhỏ (`review/round-6.md`) | ✅ nghiệm thu (288 test, E2E OK) |
| report-v2.md + commit/push | ✅ commit 0625404 |
| Brainstorm v3 (`review/brainstorm-v3.md`) | ✅ |
| Vòng 7 — dữ liệu món Việt + đa dạng + dọn cảnh báo (`review/round-7.md`) | ✅ nghiệm thu (310 test, USDA 5/5 khớp, đa dạng 7 ngày OK) |
| Vòng 8 — sửa bún chả/proposal rỗng + chat 1 lượt LLM + ảnh bữa ăn (`review/round-8.md`) | ✅ nghiệm thu (474 test; N1 giữ tắt theo số đo) |
| Vòng 9 — tổng quan tuần + xuất dữ liệu/chống injection + PWA (`review/round-9.md`) | ✅ nghiệm thu (493 test) |
| report-v3.md + commit/push | ✅ |

## Cách tiếp tục
Đọc bảng trên ⇒ hỏi dev (SendMessage) đang ở đâu ⇒ nghiệm thu bằng cách tự chạy test + E2E ⇒ giao bước tiếp theo. Mỗi chu kỳ xong thì commit + push lên nhánh `feat/mvp-review-v1`.

---
## Chu kỳ v4 — Dọn code + Hướng dẫn sử dụng (PO phiên `homnayangibuthealthy-34`, dev `homnayangibuthealthy-41`, 2026-10-28)
> Quy ước: mục ✅ DONE = đã nghiệm thu, phiên sau **không cần đọc lại** file yêu cầu tương ứng.

| Bước | Trạng thái |
|---|---|
| Vòng 1–9, report v1–v3 | ✅ DONE (đừng đọc lại round-1..9, brainstorm-v2/v3) |
| Rà code tìm trùng/tối ưu ⇒ `review/round-10.md` (R1–R7) | ✅ DONE |
| Viết `docs/USER_GUIDE.md` + yêu cầu tích hợp `review/round-11.md` (G1–G3) | ✅ DONE |
| Nghiệm thu vòng 10 | ✅ DONE (492 test, E2E LLM thật OK) — đừng đọc lại round-10.md |
| Nghiệm thu vòng 11 | ✅ DONE (frontend 52 test) — đừng đọc lại round-11.md |
| report-v4.md + commit/push | ✅ DONE |

Test nền trước vòng 10: backend 493 passed (3:53).
