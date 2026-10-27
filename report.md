# Báo cáo nghiệm thu — Review và hoàn thiện HomNayAnGiButHealthy

**Ngày:** 2026-10-27
**Cách làm:** hai phiên Claude. Phiên PO/reviewer (`homnayangibuthealthy-44`) đọc code, chạy test, test end-to-end với LLM thật, viết yêu cầu và nghiệm thu. Phiên dev (`homnayangibuthealthy-3c`) sửa code theo yêu cầu.
**Trạng thái:** ✅ Hoàn tất sau 3 vòng (vòng 1: bảo mật + sáng/tối + i18n frontend; vòng 2: i18n backend + sửa race refresh; vòng 3: 2 lỗi phát hiện khi test E2E). Mọi mục dưới đây PO đã tự chạy lại để kiểm chứng, không chỉ dựa vào báo cáo của dev.

---

## 1. Bạn cần làm trước khi chạy app

`.env` đang để trống `JWT_SECRET` và `HEALTH_DATA_KEY`. App giờ **chặn khởi động** khi thiếu hoặc khi khóa yếu (trước đây khóa mặc định `change-me` cho phép giả mạo đăng nhập). PO đã thử tự điền nhưng bị chặn quyền ghi file bí mật, nên bạn chạy hai lệnh dưới và dán kết quả vào `.env`:

```
python -c "import secrets;print(secrets.token_urlsafe(48))"                                  # JWT_SECRET
python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"   # HEALTH_DATA_KEY (sao lưu riêng)
```

**Hai lưu ý về máy của bạn:**
- **Windows chặn DLL Cython của SQLAlchemy** trong `backend/.venv` (Smart App Control). Vì vậy `pytest`/`uvicorn` từ venv đó lỗi `DLL load failed ... _util_cy`. Cách xử lý: cài lại SQLAlchemy dạng pure-Python (`set DISABLE_SQLALCHEMY_CEXT=1` rồi `pip install --force-reinstall --no-binary sqlalchemy sqlalchemy`), hoặc chạy bằng Docker.
- **Phần mềm diệt virus chặn TLS (MITM)** ⇒ gọi LLM báo `CERTIFICATE_VERIFY_FAILED`, app rơi về chế độ dự phòng. Giờ app ghi log WARNING khi điều này xảy ra; README có hướng dẫn `SSL_CERT_FILE` / truststore.

## 2. Kết quả theo yêu cầu của bạn

| Yêu cầu | Kết quả |
|---|---|
| Chế độ sáng/tối | Có 3 lựa chọn: Theo hệ thống / Sáng / Tối, ở trang Cài đặt và trang Đăng nhập. Lựa chọn được lưu lại, không nháy khi tải trang. Màu chữ đạt tương phản WCAG AA ở cả hai chế độ. |
| Tiếng Việt / English | Toàn bộ giao diện, thông báo lỗi, chatbot, cách chế biến (LLM), nhu cầu dinh dưỡng, tên món và notices đều có hai ngôn ngữ. Chatbot hiểu câu tiếng Anh ("I want to eat chicken for dinner"). Backend đọc `Accept-Language`. |
| Test với LLM thật | `gpt-6-luna` hoạt động: hiểu câu chat 2–5 s, viết công thức 5–8 s, structured output đúng schema, cả vi và en. |
| Model lỗi thời? | **Không.** `gpt-6-luna` vẫn có trong `/models` (họ `gpt-6.1-*` đã ra, có thể đánh giá sau). `claude-opus-5-5` và tham số `fallbacks`/beta của provider Anthropic đúng API hiện hành. |

## 3. Lỗi đã phát hiện và đã sửa

| # | Mức | Vấn đề | Cách phát hiện | Trạng thái |
|---|---|---|---|---|
| A1 | **Critical** | JWT secret mặc định `"change-me"` ⇒ ký được token giả, đọc hồ sơ sức khỏe người khác. `.env` để trống ⇒ đăng ký lỗi 500 | PO ký token giả và nhận 200 | Đã sửa: chặn khởi động nếu secret yếu hoặc khóa Fernet sai |
| A2 | High | "Xóa toàn bộ dữ liệu" không xóa gì khi chạy SQLite (thiếu `PRAGMA foreign_keys`) | E2E: còn dữ liệu sau khi xóa | Đã sửa; test dò mọi bảng có FK tới users |
| A3 | High | Không có rate limit: dò mật khẩu không giới hạn, chat/LLM trả phí không giới hạn | E2E: 12 lần sai đều 401 | Đã sửa: login 5 lần/(email,IP) + 30 lần/IP mỗi 15 phút; register; chat 20/phút; recipe 10/phút |
| A4 | Medium | `unlock` bỏ qua guardrail xác nhận chuyên gia | Đọc code | Đã sửa và có test |
| A5 | Medium | Refresh token bị đánh cắp không bị phát hiện | Đọc code | Đã sửa (phát hiện dùng lại, có khoảng ân hạn 30 s) |
| A6 | High | react-router-dom có 3 lỗ hổng mức high | `npm audit` | Đã sửa: lên 6.30.6. Còn 2 lỗi moderate, chỉ sửa được khi lên v7; không ảnh hưởng vì app không dùng SSR |
| A7 | Low | Thiếu Content-Security-Policy | Đọc config | Đã thêm vào Caddyfile |
| F1 | **High (phát sinh từ A5)** | Mỗi lần F5 hoặc mỗi 15 phút người dùng bị đăng xuất: các query song song cùng refresh một token | PO tái hiện ở backend | Đã sửa: single-flight + Web Locks ở frontend, khoảng ân hạn ở backend, có test cả hai phía |
| G1 | High | Bấm "Cách chế biến" lần 2 ⇒ lỗi 500 (UNIQUE recipes.meal_id), lỗi có từ trước | E2E với LLM thật | Đã sửa: cập nhật tại chỗ; test xác nhận FAIL với code cũ, PASS với code mới |
| G2 | Medium | Tiếng Anh hiển thị mô tả USDA ("atlantic salmon, farmed") | E2E với LLM thật | Đã sửa: thêm `display_en` cho 80 nguyên liệu ("Salmon", "Chicken breast"…) |
| D1 | Medium | PuLP 3.3 cảnh báo API sẽ bị xóa ở 4.0 (19.000 cảnh báo khi test) ⇒ cài mới có thể làm hỏng solver | pytest | Đã pin `pulp<4` |
| D2 | Medium | Khi LLM lỗi, app âm thầm chạy chế độ dự phòng (chỉ ghi log INFO) | Gặp thực tế do TLS | Đổi sang WARNING, README có hướng dẫn |
| D3 | Low | Chạy từ `backend/` không đọc được `.env` ở gốc repo | Smoke test | Đã sửa |
| E5 | **Bắt buộc về an toàn** | Bộ lọc dị ứng của công thức AI chỉ có từ khóa tiếng Việt; bật tiếng Anh mà không bổ sung thì "fish sauce" sẽ lọt qua | Đọc code | Đã thêm bộ từ khóa tiếng Anh; luôn kiểm tra cả hai bộ; có test |

## 4. Số liệu kiểm thử

| | Trước | Sau |
|---|---|---|
| Test backend | 125 | **196 pass** |
| Test frontend | 5 | **27 pass** (typecheck + build sạch) |
| npm audit (high) | 3 | 0 |
| ruff | 51 | 46 |

## 4b. Kiểm thử E2E cuối cùng (LLM thật, cả vi/en)

| Kịch bản | Kết quả |
|---|---|
| Sinh thực đơn 3 ngày, dị ứng cá + đậu phộng | 3/3 ngày `ok`, kcal/macro trong ±5% |
| Cách chế biến bằng AI, bấm lại cho cùng bữa (vi → en) | 200 / 200, không chứa nguyên liệu dị ứng |
| "I want to eat chicken for dinner" | Đề xuất thực đơn xoay quanh ức gà |
| "I want salmon tonight" / "tối nay ăn cá hồi" (dị ứng cá) | Từ chối, nêu rõ lý do bằng đúng ngôn ngữ |
| "I want to starve myself" | Thông điệp hỗ trợ (guardrail rối loạn ăn uống) |
| "I want 2 ice creams" / "tôi muốn ăn 2 cây kem" | Đề xuất ăn kem và giảm bớt các bữa chính để vẫn đạt mục tiêu |
| Nhập tuổi 200 (en) | 422 "Age must be between 18 and 100…" |
| Thêm cá hồi vào nguyên liệu có sẵn khi dị ứng cá (en) | 422 "Can't add Salmon: it conflicts with the fish allergy you declared." |

## 5. Còn lại và đề xuất (chưa làm, cần bạn quyết)

- Từ khóa dị ứng (vi/en), các cụm phát hiện rối loạn ăn uống và mọi ngưỡng ⚠ trong `docs/ASSUMPTIONS.md` vẫn cần **chuyên gia dinh dưỡng/y tế duyệt** trước khi mời người dùng thật.
- Rate limit đang lưu trong bộ nhớ, chỉ đúng khi chạy một instance backend.
- 2 lỗi moderate của react-router chỉ hết khi lên v7 (thay đổi lớn).
- Chưa kiểm tra giao diện bằng trình duyệt thật (máy không có Docker đang chạy). Nên tự mở thử chế độ tối và tiếng Anh một lượt.
- Câu tiếng Anh giữ chữ hoa đầu tên món giữa câu ("I can't suggest Salmon"), chỉ là chuyện thẩm mỹ.
- **Chưa commit.** Toàn bộ thay đổi nằm trong working tree để bạn tự review/commit.
- Các file trong `review/` là yêu cầu từng vòng, giữ lại để truy vết.
