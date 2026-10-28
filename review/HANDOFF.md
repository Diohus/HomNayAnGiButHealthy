Bạn tiếp quản vai **PO/leader/reviewer** của dự án `D:\HomNayAnGiButHealthy` ("Hôm Nay Ăn Gì": app đề xuất thực đơn theo sức khỏe). Đây là bàn giao từ phiên PO trước. Bạn **không tự viết code tính năng**. Bạn rà soát, test, viết yêu cầu, giao cho phiên dev, rồi nghiệm thu.

## Quy trình chủ sản phẩm muốn
1. Rà code + chạy test + **E2E với LLM thật** ⇒ tìm lỗi (cấu trúc, bảo mật, dữ liệu/model lỗi thời, UX).
2. Brainstorm tính năng ưu tiên 1–10 (độ cần thiết, cải thiện trải nghiệm). Mỗi vấn đề kèm giải pháp, **ưu tiên LLM thay vì rule-based quá đơn giản**, vì người dùng viết tiếng địa phương, sai chính tả, không dấu.
3. Viết yêu cầu chi tiết vào `review/round-N.md` (file nào, sửa thế nào, test gì, tiêu chí nghiệm thu) ⇒ gửi phiên dev bằng **SendMessage** (`notify_when_idle: true`). Dev làm theo, không tự nghĩ ý tưởng.
4. Dev báo xong ⇒ PO **tự chạy lại** test + E2E (không tin báo cáo suông) ⇒ phản hồi hoặc giao vòng tiếp.
5. Mỗi chu kỳ 3 vòng ⇒ viết `report-vN.md` ⇒ commit + push.
6. Sắp chạm hạn mức usage ⇒ dừng ở điểm ổn định, ghi tiến độ vào `review/STATE.md`, hẹn giờ làm tiếp (CronCreate một lần).

## Định hướng sản phẩm (đã chốt)
- App **không chuyên về y tế**, không có bác sĩ can thiệp. App chỉ đề xuất, chấp nhận sai số và nói rõ điều đó. Có chỉ định bác sĩ ⇒ người dùng tự nhập, hoặc đưa ảnh/văn bản để LLM trích xuất (người dùng duyệt trước khi lưu).
- Số liệu dinh dưỡng **chỉ lấy từ DB/USDA FDC SR Legacy**. LLM không được bịa số; chỗ nào AI ước tính thì gắn nhãn "AI ước tính" và người dùng sửa được.
- Dị ứng/chế độ ăn là ràng buộc cứng (lọc **sau** LLM). Có guardrail rối loạn ăn uống; dữ liệu sức khỏe được mã hóa và không ghi vào log.

## Trạng thái hiện tại (2026-10-28 ~05:40)
- Nhánh `feat/mvp-review-v1` (đã push lên origin `github.com/Diohus/HomNayAnGiButHealthy`): v1 `18e1046`, v2 `0625404`, v3 `ab85bd9`. **Chưa merge vào main** (chờ chủ sản phẩm tạo PR). Git identity đã đặt riêng cho repo này.
- Đã xong 3 chu kỳ / 9 vòng. Báo cáo: `report.md` (v1), `report-v2.md`, `report-v3.md`. Brainstorm: `review/brainstorm-v2.md`, `review/brainstorm-v3.md`. Yêu cầu từng vòng: `review/round-1..9.md`. Tiến độ: `review/STATE.md`.
- Số liệu cuối: backend **493 test pass** (gồm 133 test bao phủ món × bữa, chạy ~5 phút), frontend **40 pass**, ruff 0, npm audit 0 high (chấp nhận 2 moderate react-router: chỉ hết khi lên v7, app không dùng SSR). Dữ liệu: 115 nguyên liệu / 65 món.
- Stack: FastAPI + SQLAlchemy 2 + Alembic + PuLP (pin <4) | React + TS + Vite | Postgres/Docker (dev dùng SQLite). LLM: OpenAI-compatible `gpt-6-luna` (đã xác minh còn tồn tại, hỗ trợ ảnh); provider Claude ẩn sau cờ. Lượt chat gộp 1 lần gọi LLM (`CHAT_SINGLE_PASS`) **cố ý để tắt** vì đo thật chậm hơn.

## Phiên
- Dev: `homnayangibuthealthy-3c` (dùng `ListAgents` để xác nhận; nếu đã đóng, nhờ chủ sản phẩm mở phiên dev mới). Dev đã được báo "hết việc".
- Quy ước với dev: không commit (PO commit sau khi nghiệm thu), không sửa `.env`, báo lại gồm file đổi + kết quả test + chỗ làm khác yêu cầu kèm lý do.

## Lưu ý môi trường (quan trọng)
- Windows Smart App Control **chặn DLL Cython của SQLAlchemy** trong `backend/.venv`. Chạy test bằng venv pure-Python: `C:\Users\nguye\AppData\Local\Temp\claude\d--HomNayAnGiButHealthy\5efd6715-9e6e-43d6-a648-f4274eb04742\scratchpad\venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` (trong `backend/`). Nếu scratchpad đó mất: `python -m venv <dir>`, `set DISABLE_SQLALCHEMY_CEXT=1`, `pip install --no-binary sqlalchemy -e ".[dev]"` cùng `pillow python-multipart python-dotenv truststore`.
- Antivirus chặn TLS ⇒ gọi mạng cần `import truststore; truststore.inject_into_ssl()`, pip cần `PIP_USE_FEATURE=truststore`.
- Đôi khi test lỗi `WinError 10055` (hết socket) ⇒ chạy lại.
- Docker không chạy ⇒ chưa thử UI trên trình duyệt thật.
- `.env` có `LLM_API_KEY` thật; **`JWT_SECRET` và `HEALTH_DATA_KEY` còn trống** (app sẽ từ chối khởi động). PO bị chặn quyền ghi `.env`, việc này thuộc về chủ sản phẩm. **Không nhờ dev làm thay.**
- Script E2E mẫu (TestClient + SQLite + LLM thật, tự tạo khóa tạm): `scratchpad\e2e2.py` … `e2e9.py`.

## Việc còn mở (ứng viên cho chu kỳ v4, xem `report-v3.md` mục 3)
1. **Tổng quan tuần** coi ngày ghi nhật ký dở dang là "đã ghi" ⇒ trung bình thấp giả, dễ gây lo lắng cho người nhạy cảm chuyện ăn uống. Chỉ tính ngày ghi đủ bữa hoặc ngày người dùng bấm "xong ngày".
2. Ảnh bữa ăn **chưa test với ảnh thật + LLM thật** (Wikipedia trả 403).
3. Chưa ghi nhật ký được cho ngày trước ("tối qua ăn phở").
4. Thiếu một số rau/trái Việt mà USDA không có tương đương (rau muống, cải ngọt, thanh long…) ⇒ cân nhắc Bảng thành phần thực phẩm Việt Nam khi có bản số hóa hợp lệ.
5. Đăng ký dạng hội thoại; kho có sẵn tự trừ khi ăn.
6. Tách lệnh test nhanh `pytest -m "not slow"`.
7. Rủi ro injection còn lại: tài liệu độc hại đưa vào giới hạn hợp lệ (đã giảm thiểu vì người dùng phải duyệt bản nháp).

## Việc của chủ sản phẩm
Điền `JWT_SECRET` và `HEALTH_DATA_KEY` (lệnh ở `report.md` mục 1) · thử ảnh bữa ăn thật và PWA trên điện thoại · tạo PR vào main.

Viết báo cáo/yêu cầu bằng tiếng Việt, ngắn gọn; tên kỹ thuật giữ tiếng Anh. Trước khi làm gì, hãy hỏi chủ sản phẩm muốn tiếp tục chu kỳ v4 hay việc khác.

## Cập nhật 2026-10-28 ~10:30 (PO phiên `homnayangibuthealthy-34`)
- Chu kỳ v4 (vòng 10 dọn code, vòng 11 trang Hướng dẫn) ✅ DONE. Xem `report-v4.md` và bảng v4 trong `review/STATE.md`.
- Số liệu mới: backend 492 test, frontend 52 test, ruff app 0. Dev hiện tại là `homnayangibuthealthy-41`.
- Phiên sau chỉ cần đọc file này + `review/STATE.md` + `report-v4.md`. Không cần đọc lại các round-*.md đã DONE.
