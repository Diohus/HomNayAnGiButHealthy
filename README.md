# Hôm Nay Ăn Gì (HomNayAnGiButHealthy)

Ứng dụng đề xuất thực đơn và nguyên liệu theo tình trạng sức khỏe và mức hoạt động của người dùng. Bản MVP dành cho khoảng 10 người dùng thử.

> ⚠️ Ứng dụng không chẩn đoán bệnh và không thay thế bác sĩ hay chuyên gia dinh dưỡng.

Hướng dẫn sử dụng cho người dùng: [docs/USER_GUIDE.md](docs/USER_GUIDE.md) (trong app: trang `/help`).

## Tính năng

- **Hồ sơ → nhu cầu hằng ngày**: Mifflin-St Jeor × hệ số hoạt động, macro theo AMDR, vi chất theo RDA/UL (NIH ODS). Mọi chỉ số đều kèm nguồn, độ tuổi và giới tính áp dụng.
- **Thực đơn 2 hoặc 3 bữa** theo mức hoạt động. Mỗi nguyên liệu có khối lượng cụ thể. Tổng kcal/đạm/carb/béo nằm trong **±5%** mục tiêu, do bộ giải ILP (PuLP + CBC) tính.
- **Nút +/−** cho từng nguyên liệu: hệ thống cân bằng lại phần còn lại và giữ nguyên các món đã chọn.
- **Nguyên liệu có sẵn trong nhà** là ràng buộc cứng; hệ thống tự đề xuất phần còn thiếu.
- **Chatbot** hiểu các câu như “tôi muốn ăn gà”, “tôi muốn ăn 2 cây kem” — kể cả sai chính tả, không dấu, từ địa phương, tiếng Anh và món ghép (“bún bò huế”: AI ước tính nguyên liệu, gắn nhãn “AI ước tính”), nhờ LLM chọn trong danh sách nguyên liệu/món có sẵn (không bịa mã); chưa chắc thì hỏi lại kèm nút chọn nhanh:
  - Món chính → xây thực đơn xoay quanh món đó (vẫn tuân thủ quy tắc không lặp món quá 3 ngày liên tiếp).
  - Món phụ → thêm vào bữa.
  - Đồ ăn vặt → điều chỉnh cả ngày. Nếu vượt mục tiêu thì đưa ra hai phương án: “ăn ít hơn” hoặc “cheat day” (bù có giới hạn vào các ngày sau).
  - Mọi thay đổi chỉ được áp dụng khi người dùng bấm xác nhận.
- **Đổi món** cho một bữa (giữ nguyên các bữa khác) và danh sách **Không thích** trong Hồ sơ (hoặc nói với chatbot “tôi không thích cá hồi”); thực đơn hạn chế tối đa các món này. Nói về dị ứng trong chat thì app hướng dẫn cập nhật Hồ sơ, không tự sửa.
- **Nhật ký “đã ăn”**: tick bữa đã ăn, thêm món ngoài kế hoạch (hoặc nói với chatbot “tôi vừa ăn 1 quả chuối”); vòng tiến độ hiện **đã ăn / mục tiêu** (kế hoạch mờ phía sau); “Cân lại các bữa còn lại” giữ mức tối thiểu mỗi bữa và không cắt giảm khi có tín hiệu rối loạn ăn uống.
- **Danh sách đi chợ** cho 1–7 ngày × 1–10 người: gộp nguyên liệu, trừ đồ có sẵn, quy về đơn vị mua, đánh dấu đã mua, sao chép/chia sẻ.
- **Giới hạn sức khỏe của tôi** (Cài đặt): người dùng tự nhập giới hạn bác sĩ đã cho (năng lượng, đạm, carb, chất béo, natri, kali, phốt pho), hoặc **chụp/tải ảnh** hay **dán văn bản** chỉ định để AI trích xuất. AI chỉ trả **bản nháp**, mỗi giá trị kèm trích dẫn nguyên văn; code tự quy đổi đơn vị (mmol → mg, g muối → mg natri) và loại giá trị vô lý; người dùng duyệt/sửa rồi mới lưu.
- **Cách chế biến** do AI viết (LLM), có kiểm tra dị ứng. Khi AI lỗi hoặc timeout thì dùng công thức mẫu và giữ nguyên công thức cũ.
- **Guardrail**: disclaimer; ứng dụng **không có bác sĩ theo dõi** — người có bệnh thận/tim/gan/mang thai/cho con bú xác nhận một lần là tự quản lý chế độ ăn, chưa nhập giới hạn thì dùng mục tiêu chung kèm cảnh báo rõ; sàn năng lượng; phát hiện tín hiệu rối loạn ăn uống; dị ứng là ràng buộc cứng; mã hóa dữ liệu sức khỏe; không ghi log dữ liệu sức khỏe; xóa toàn bộ dữ liệu.

## Quyền riêng tư khi đọc tài liệu bằng AI

- Chỉ gửi khi người dùng **tích đồng ý** (thiếu ⇒ 422). Ảnh/văn bản được gửi tới **nhà cung cấp LLM đã cấu hình** (`LLM_BASE_URL`, mặc định OpenAI) để đọc; chính sách lưu trữ phía nhà cung cấp do hợp đồng/API của họ quyết định.
- Backend **không lưu** ảnh hay văn bản xuống đĩa/DB và không ghi log nội dung. Ảnh được kiểm tra định dạng thật (JPEG/PNG/WebP, ≤ 5 MB), xoay theo EXIF rồi **xóa toàn bộ metadata** (vị trí GPS, máy chụp…), thu nhỏ ≤ 2000 px trước khi gửi.
- Chỉ giới hạn mà người dùng bấm “Lưu” mới được lưu (mã hóa như hồ sơ sức khỏe) và bị xóa khi xóa tài khoản. Giới hạn 5 lần đọc/giờ/người.

## Ngôn ngữ & giao diện

- **Tiếng Việt / English**: đổi ở trang **Cài đặt** hoặc ngay trên trang **Đăng nhập** (chưa đăng nhập vẫn đổi được). Lựa chọn lưu trong trình duyệt (`localStorage["hnag_lang"]`), mặc định tiếng Việt.
- Frontend gửi header `Accept-Language` với mọi request. Backend (`app/core/i18n.py`) trả theo ngôn ngữ đó: thông báo lỗi và validation, notices y tế, nguồn/ghi chú nhu cầu dinh dưỡng, câu trả lời chatbot, công thức (AI và mẫu), tên món. Tag `en*` ⇒ tiếng Anh, còn lại ⇒ tiếng Việt. Chuỗi hiển thị nằm trong `backend/app/i18n/{vi,en}.py` và `frontend/src/i18n/{vi,en}.ts`.
- Đổi ngôn ngữ thì dữ liệu từ server được tải lại theo ngôn ngữ mới. Tin nhắn chat đã lưu giữ nguyên ngôn ngữ lúc gửi.
- Chatbot hiểu cả câu tiếng Anh (“I want chicken for dinner”); bộ lọc dị ứng của công thức AI luôn kiểm tra từ khóa **cả tiếng Việt lẫn tiếng Anh**.
- **Sáng / Tối**: trang Cài đặt → “Giao diện” (Theo hệ thống / Sáng / Tối), lưu ở `localStorage["hnag_theme"]`.

## Kiến trúc tóm tắt

```
frontend (React+TS+Vite) ──► Caddy (HTTPS) ──► nginx ──► backend (FastAPI)
                                                          ├─ nutrition/  (b) tính nhu cầu — thuần Python
                                                          ├─ foods/      (a) dữ liệu nguyên liệu USDA
                                                          ├─ planner/    (c)(d) ILP + rebalance + pantry
                                                          ├─ chat/       chatbot (logic xác định)
                                                          ├─ ai/         LLM: hiểu câu + cách chế biến
                                                          └─ guardrails/
                                                          ▼
                                                     PostgreSQL
```

Chi tiết: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Giả định: [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md) · Nguồn dữ liệu: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)

## Chạy demo bằng Docker Compose

Yêu cầu: Docker Desktop đang chạy.

```bash
cp .env.example .env
# Điền POSTGRES_PASSWORD, JWT_SECRET, HEALTH_DATA_KEY (lệnh tạo khóa có trong .env.example)
# Muốn dùng LLM thì điền LLM_API_KEY. Để trống thì chạy chế độ dự phòng (không cần AI).
docker compose up -d --build
```

Mở `https://localhost`. Trình duyệt sẽ cảnh báo chứng chỉ nội bộ của Caddy; với tên miền thật, đặt `SITE_ADDRESS=ten-mien.vn` và Caddy sẽ tự cấp chứng chỉ.

Khi khởi động, backend tự chạy `alembic upgrade head` rồi seed nguyên liệu (idempotent).

**Sao lưu `HEALTH_DATA_KEY`.** Mất khóa này thì không giải mã được hồ sơ sức khỏe và lịch sử chat.

## Chạy khi phát triển (không cần Docker)

```bash
# Backend (Python 3.11+)
cd backend
python -m venv .venv && .venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
# Postgres local, hoặc SQLite để thử nhanh:
export DATABASE_URL=sqlite:///./dev.db
export HEALTH_DATA_KEY=$(python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())")
export JWT_SECRET=dev-secret-dai-it-nhat-32-ky-tu-xxxxxxxx
alembic upgrade head && python -m app.seed
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxy /api → :8000)
```

Nếu `pip` báo lỗi chứng chỉ SSL (thường gặp khi mạng hoặc antivirus chặn TLS), đặt `PIP_USE_FEATURE=truststore`. Với npm, đặt `NODE_USE_SYSTEM_CA=1`.

Backend không khởi động nếu `JWT_SECRET` ngắn hơn 32 ký tự / là giá trị mẫu, hoặc `HEALTH_DATA_KEY` không phải khóa Fernet hợp lệ. Backend đọc `.env` ở thư mục đang chạy hoặc thư mục cha (chạy từ `backend/` vẫn đọc `.env` ở gốc repo).

LLM bị chặn TLS (log WARNING `llm call failed ... ConnectError`, app tự chuyển chế độ dự phòng): đặt `SSL_CERT_FILE` trỏ tới file PEM có chứng chỉ gốc của antivirus/proxy (httpx đọc biến này),
hoặc `pip install truststore` rồi gọi `truststore.inject_into_ssl()` trước khi chạy để dùng kho chứng chỉ của hệ điều hành.

## Test

```bash
cd backend && pytest            # 493 test (gồm 133 test chậm `-m slow`): nutrition, foods, planner, chat, guardrails (mục 3), robustness (mục 4), API
cd frontend && npm test && npm run typecheck
```

Test backend chạy bằng SQLite in-memory và không gọi LLM thật (LLM được giả lập).

| Nhóm | Thư mục |
|---|---|
| (a) Nhu cầu dinh dưỡng | `backend/tests/nutrition` |
| (b) Dữ liệu nguyên liệu | `backend/tests/foods` |
| (c)(d) Bộ sinh thực đơn, +/−, pantry | `backend/tests/planner` |
| Chatbot | `backend/tests/chat` |
| Guardrail mục 3 | `backend/tests/guardrails` |
| Robustness mục 4 | `backend/tests/robustness` |
| End-to-end API | `backend/tests/api` |

## Cập nhật dữ liệu nguyên liệu

Giá trị dinh dưỡng **không gõ tay**, mà được sinh từ bộ CSV USDA FoodData Central SR Legacy:

```bash
# tải và giải nén FoodData_Central_sr_legacy_food_csv_2018-04.zip, rồi:
python backend/seed/build_ingredients.py <thư_mục_csv> backend/seed/ingredients.json
```

Thêm nguyên liệu: khai báo trong `backend/seed/catalog.py` (tên, FDC ID, nhóm, tag dị ứng), chạy lại lệnh trên, rồi chạy `python -m app.seed`.

## LLM

- Mặc định: provider OpenAI-compatible, `LLM_MODEL=gpt-6-luna`.
- Provider ẩn: Claude (`LLM_EXPERIMENTAL_PROVIDERS=true`, `LLM_PROVIDER=anthropic`, `pip install -e ".[claude]"`, mặc định `claude-opus-5-5`).
- LLM **không** sinh số liệu. Đầu ra được kiểm tra bằng schema và bộ lọc dị ứng/số liệu, retry tối đa 2 lần, sau đó chuyển sang chế độ dự phòng.
