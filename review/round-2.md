# Vòng 2 — Song ngữ ở backend + an toàn dị ứng khi dùng tiếng Anh (PO → Dev)

Chỉ làm sau khi vòng 1 đã được PO nghiệm thu. Cùng lưu ý môi trường như `round-1.md` mục 0.

## Bối cảnh (PO đã test với LLM thật)
- Chat "I want to eat chicken for dinner": LLM trả `mentions=["chicken"]`, nhưng `foods/matching.py` chỉ so với alias tiếng Việt ⇒ trả `need_label` ("chưa nhận ra món chicken"). Người dùng tiếng Anh không dùng được chatbot.
- Lời từ chối dị ứng lộ mã thô: "…vì bạn đã khai báo dị ứng (fish)." (`chat/engine.py`, đoạn `refusal_text`).
- Khoảng 160 chuỗi tiếng Việt viết cứng ở backend (engine.py 52, recipes.py 37, menu.py 20, medical.py 13, foods.py 10, profile.py 8, routes.py 8…).
- **Rủi ro an toàn:** bộ lọc `violations()` trong `ai/recipes.py` chỉ có từ khóa tiếng Việt (`FORBIDDEN_TERMS`). Nếu cho LLM viết công thức tiếng Anh ("fish sauce", "peanut butter", "shrimp paste"…), bộ lọc dị ứng sẽ **không bắt được**. Chưa bổ sung bộ lọc tiếng Anh thì không được bật công thức tiếng Anh.

## Yêu cầu

**E1. Hạ tầng i18n backend.** `app/core/i18n.py`: `Lang = Literal["vi","en"]`; dependency `get_lang(accept_language: str | None = Header(None)) -> Lang` (tag chính `en*` ⇒ "en", còn lại ⇒ "vi"); `tr(key, lang, **params)` đọc từ `app/i18n/vi.py` và `app/i18n/en.py` (dict phẳng, khóa dạng `"error.EMAIL_EXISTS"`, `"chat.refusal.allergy"`…). Thiếu khóa trong `en` ⇒ fallback `vi` và log WARNING tên khóa (không log params).

**E2. Lỗi.** `AppError` giữ `code` + `params`; exception handler trong `main.py` render `message` theo `get_lang` của request. Thông báo validation (`schemas.py`: tuổi, chiều cao, cân nặng, kcal…) cũng phải có bản tiếng Anh: validator ném `ValueError` mang **khóa**, handler dịch. Không trả lại `input`, giữ nguyên quy tắc không log dữ liệu sức khỏe.

**E3. Chatbot.** Truyền `lang` vào `ChatContext`; mọi câu trả lời trong `chat/engine.py` (gồm `SLOT_VI`, `_day_vi`, `_plan_lines`, nhãn proposal, SUPPORT_MESSAGE, câu từ chối) lấy từ catalog theo `lang`. Lý do dị ứng hiển thị bằng **tên dị nguyên đã dịch** (vd "fish" ⇒ "cá" / "fish"), không bao giờ là mã thô. Tin nhắn đã lưu trong lịch sử giữ nguyên ngôn ngữ lúc gửi (không cần dịch lại).

**E4. Hiểu tiếng Anh.** Thêm alias tiếng Anh cho nguyên liệu: sinh từ `name_en` (phần trước dấu phẩy, viết thường) + danh sách alias tay ngắn gọn trong `seed/catalog.py` cho các món hay gặp (chicken, beef, pork, salmon, fish, egg, rice, noodles, tofu, ice cream, milk, banana…). Matching phải tìm được cả alias Anh. Cập nhật `SYSTEM` của parser: câu chat có thể bằng tiếng Việt hoặc tiếng Anh. Thêm các cụm `RESTRICT_PHRASES` / `DISTRESS_PHRASES` tiếng Anh tương đương (skip meals, starve, make myself throw up, laxatives to lose weight…) — guardrail rối loạn ăn uống phải hoạt động ở cả hai ngôn ngữ. Test: "I want to eat chicken for dinner" ⇒ proposal; "I want to starve myself" ⇒ support; "I want salmon" với dị ứng cá ⇒ refusal.

**E5. Công thức theo ngôn ngữ.** `generate_recipe(..., lang)`: SYSTEM prompt và `template_recipe` có bản tiếng Anh; tên nguyên liệu gửi cho LLM theo ngôn ngữ. **Bắt buộc** thêm `FORBIDDEN_TERMS_EN` (peanut, peanut butter, cashew, walnut, almond, milk, butter, cheese, cream, egg, mayonnaise, fish, fish sauce, anchovy, shrimp, crab, squid, oyster sauce, soy sauce, tofu, miso, wheat flour, bread, sesame, sesame oil, pork, lard, beef, bacon, gelatin, honey (vegan), wine/alcohol (halal)…) và `violations()` kiểm tra **cả hai bộ** bất kể `lang`. `NUMERIC_CLAIM` thêm đơn vị tiếng Anh (tbsp, tsp, cup, oz, lb). Test: công thức giả lập chứa "fish sauce" cho người dị ứng cá ⇒ bị loại ⇒ rơi về template.

**E6. Tên món tiếng Anh.** Thêm `name_en` cho 26 món trong `seed/dishes.json`; cột `dishes.name_en` + migration Alembic mới (không sửa migration cũ); `foods_repo.seed` cập nhật; `GET /dishes` trả `name_en`; frontend dùng theo `lang`.

**E7. Notices.** `menu_notices(..., lang)` trả `text` theo ngôn ngữ (frontend đã map theo code ở vòng 1, giữ fallback).

**E8. Docs.** README: mục "Ngôn ngữ & giao diện" (đổi ngôn ngữ/theme ở đâu; backend đọc `Accept-Language`). `docs/ASSUMPTIONS.md`: ghi rõ danh sách từ khóa dị ứng Anh/Việt là tối thiểu, cần chuyên gia mở rộng. Sửa README dòng "125 test" thành số test thực tế.

## Tiêu chí nghiệm thu vòng 2
1. Toàn bộ test pass; có test song ngữ cho: lỗi API, validation, chat (proposal/refusal/support), công thức (bộ lọc dị ứng tiếng Anh), notices.
2. `grep -rnP '[à-ỹÀ-Ỹđ]' backend/app --include=*.py`: chuỗi hiển thị cho người dùng chỉ còn trong `app/i18n/vi.py` (comment/docstring được phép giữ, cùng các danh sách từ khóa và alias tiếng Việt dùng để so khớp).
3. Báo lại PO qua SendMessage như vòng 1.
