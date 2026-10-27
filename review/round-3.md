# Vòng 3 — Sửa lỗi phát hiện khi chạy E2E với LLM thật (PO → Dev)

PO đã tự kiểm chứng lại vòng 2:
- Backend 190/190 pass, frontend 27/27 pass, build OK, audit 0 high.
- Race refresh đã sửa: refresh token mới của request thắng vẫn trả 200.
- E2E với gpt-6-luna chạy đúng ở cả vi và en: validation, notices, sinh thực đơn 3 ngày, công thức (LLM), chat (proposal / refusal dị ứng / support), lỗi ALLERGEN_CONFLICT đã dịch.

Còn 2 lỗi cần sửa.

## G1. [HIGH, có từ trước vòng 1] Tạo lại cách chế biến cho cùng một bữa ⇒ 500

Tái hiện: `POST /api/menu/{day}/meals/lunch/recipe` lần 1 ⇒ 200; gọi lần 2 (người dùng bấm lại "Cách chế biến", hoặc đổi ngôn ngữ rồi bấm) ⇒ **500**, log `IntegrityError: UNIQUE constraint failed: recipes.meal_id`.

Nguyên nhân: `app/api/routes.py` (endpoint recipe) gán `meal.recipe = M.Recipe(...)`. Khi flush, SQLAlchemy INSERT bản mới trước khi DELETE bản cũ (delete-orphan), nên vi phạm UNIQUE(meal_id). PostgreSQL cũng bị y hệt.

Sửa: nếu `meal.recipe` đã có thì cập nhật tại chỗ (`content`, `source`, `created_at`); chưa có mới tạo bản mới. Rà xem trong `services/menu.py:save_plan` có chỗ nào cùng mẫu này không.

Test API: gọi recipe 2 lần liên tiếp (một lần vi, một lần en; LLM giả lập) ⇒ cả hai 200, lần 2 trả nội dung tiếng Anh, DB còn đúng 1 dòng recipe cho bữa đó.

## G2. [MEDIUM, UX tiếng Anh] Tên nguyên liệu tiếng Anh là mô tả USDA, lại bị viết thường sai

Văn bản thực tế:
- "Here's a menu for today built around **chicken breast, skinless**: … 100 g **whole egg**"
- "I can't suggest **atlantic salmon, farmed** because …"

`name_en` là mô tả kỹ thuật (giữ làm dữ liệu nguồn), không phải tên để hiển thị. Ngoài ra `.lower()` trong engine làm hỏng chữ hoa của danh từ riêng ("atlantic").

Sửa:
- Thêm `display_en` ngắn, tự nhiên cho cả 80 nguyên liệu, khai báo trong `seed/catalog.py`. Ví dụ: "Chicken breast", "Salmon", "Eggs", "Brown rice", "Ice cream". Sinh vào `ingredients.json` theo đúng bước gộp như ở E4.
- Lưu `display_en` vào DB (cột mới + migration mới, hoặc gộp vào cột JSON có sẵn — chọn cách đơn giản hơn).
- `name_of(food, "en")` trả `display_en`; `GET /foods` trả thêm trường này để frontend dùng thay cho `name_en`.
- Bỏ `.lower()` khi `lang == "en"`. Với tiếng Việt vẫn giữ như hiện tại.

Test: chat en "I want salmon tonight" với dị ứng cá ⇒ câu trả lời chứa "salmon", không chứa "atlantic" hay ", farmed".

## Tiêu chí
Toàn bộ test pass, frontend build và test pass. Báo PO một lần khi xong. Không sửa `.env`, không commit.
