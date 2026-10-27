# Kiến trúc đề xuất — HomNayAnGi (MVP)

> Trạng thái: **Đã xác nhận và triển khai MVP** (2026-10-21). Các điểm khác so với bản đề xuất ban đầu được ghi ở §10.

## 1. Quyết định đã chốt

| Hạng mục | Lựa chọn |
|---|---|
| Frontend | React + TypeScript + Vite, TanStack Query, React Router, i18n `vi`/`en` (I18nProvider + useI18n), chế độ sáng/tối |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| DB | PostgreSQL 16 (Docker Compose) |
| Tối ưu | **PuLP + CBC** (CBC đi kèm PuLP, không cần cài thêm solver) |
| Auth | JWT access 15 phút + refresh token 7 ngày (lưu hash trong DB, rotate mỗi lần dùng) |
| Dữ liệu dinh dưỡng | USDA FoodData Central, ~60 nguyên liệu, mỗi dòng có `fdc_id` |
| LLM | Interface `LLMProvider`; mặc định OpenAI-compatible, `LLM_MODEL=gpt-6-luna` từ env. Adapter Claude/khác có sẵn nhưng tắt (`LLM_PROVIDER`) |
| Bệnh nền nhạy cảm | Thận, tim mạch, gan, mang thai, cho con bú → **chặn sinh thực đơn**, chờ xác nhận chuyên gia + giới hạn do chuyên gia cung cấp |

## 2. Kiến trúc tổng thể

```
┌──────────────┐   HTTPS   ┌────────────────────────── backend (FastAPI) ──────────────────────────┐
│  frontend    │ ────────▶ │  api/  (routers, auth, validation)                                     │
│  React/Vite  │           │    │                                                                   │
└──────────────┘           │    ├─▶ guardrails/   (safety checks, chạy TRƯỚC và SAU mỗi bước)       │
                           │    ├─▶ nutrition/    (b) tính nhu cầu — thuần Python, không I/O        │
                           │    ├─▶ foods/        (a) repository nguyên liệu + giá trị dinh dưỡng   │
                           │    ├─▶ planner/      (c) ILP sinh thực đơn + rebalance +/-, pantry     │
                           │    └─▶ ai/           diễn giải, cách chế biến (LLM, có schema+fallback)│
                           └───────────────────────────────┬────────────────────────────────────────┘
                                                           ▼
                                                     PostgreSQL
```

- **Modular monolith** cho MVP: 4 package `nutrition`, `foods`, `planner`, `ai` chỉ giao tiếp qua interface (Pydantic DTO), không import chéo nội bộ. Tách thành service riêng sau này chỉ cần thay lớp gọi hàm bằng HTTP.
- `nutrition` và `planner` là **pure function** (input DTO → output DTO) ⇒ test độc lập không cần DB.
- LLM **không** sinh số liệu. Đầu ra LLM chỉ là text (cách chế biến, gia vị gợi ý định tính, giải thích); mọi gram/kcal do `planner` tính. Gia vị có kcal đáng kể (dầu ăn) được `planner` đưa vào như nguyên liệu có khối lượng.

## 3. Sơ đồ dữ liệu

```
users ─1:1─ health_profiles ─1:n─ profile_conditions
  │                       └─1:n─ profile_restrictions (allergy / diet: vegetarian, halal, gluten_free...)
  ├─1:n─ refresh_tokens
  ├─1:n─ expert_confirmations       (xác nhận đã tham khảo chuyên gia + giới hạn chuyên gia cung cấp)
  ├─1:n─ pantry_items ──n:1─ ingredients
  ├─1:n─ safety_events              (tín hiệu rối loạn ăn uống: chỉ loại sự kiện + thời điểm)
  └─1:n─ menu_days ─1:n─ meals ─1:n─ meal_dishes ─1:n─ meal_items ──n:1─ ingredients
                                         │
                                         └──n:1─ dishes ─1:n─ dish_components (vai trò: protein/carb/veg/fat)
                                                   └─1:n─ recipes (cách chế biến; nguồn: template | llm)

ingredients ─1:n─ ingredient_nutrients ──n:1─ nutrients
ingredients ─1:n─ ingredient_tags (allergen: peanut, shellfish, gluten...; diet: animal, pork...)
```

### Bảng chính (rút gọn)

| Bảng | Cột quan trọng |
|---|---|
| `users` | id (UUID), email, password_hash (argon2), created_at |
| `health_profiles` | user_id, **encrypted_payload** (sex, age, height, weight, activity, goal — mã hóa Fernet/AES), version, updated_at |
| `profile_conditions` | profile_id, code (`diabetes_t1`, `diabetes_t2`, `hypertension`, `kidney`, `cardio`, `liver`, `pregnant`, `lactating`), uses_insulin_or_meds |
| `profile_restrictions` | profile_id, kind (`allergy`/`diet`), code |
| `nutrients` | code (`energy`, `protein`, `carb`, `fat`, `fiber`, `iron`, `zinc`, `calcium`, `vit_d`, `sodium`...), unit |
| `ingredients` | id, name_vi, name_en, category, **fdc_id**, source, verified (bool), gi (nullable + nguồn), min_g, max_g, step_g |
| `ingredient_nutrients` | ingredient_id, nutrient_code, amount_per_100g, source_ref |
| `dishes` | id, name_vi, is_main (bool), meal_slots (sáng/trưa/tối) |
| `dish_components` | dish_id, role, allowed_ingredient_category |
| `menu_days` | user_id, date, target_snapshot (JSON nhu cầu lúc sinh), status, solver_report (thiếu hụt) |
| `meals` | menu_day_id, slot (`breakfast`/`lunch`/`dinner`), active (bool — **giữ dữ liệu khi đổi 2↔3 bữa**) |
| `meal_items` | meal_dish_id, ingredient_id, grams, locked (bool), origin (`optimizer`/`user_adjust`/`pantry`) |
| `pantry_items` | user_id, ingredient_id, grams_available |
| `expert_confirmations` | user_id, condition_code, confirmed_at, limits (JSON, do người dùng nhập từ chuyên gia) |

Dữ liệu sức khỏe (cân nặng, bệnh nền, dị ứng) chỉ nằm trong `health_profiles.encrypted_payload` + bảng điều kiện; `DELETE /me` xóa cascade toàn bộ.

## 4. Thông số tính toán (đề xuất — mỗi số có nguồn)

| Thông số | Giá trị | Nguồn / ghi chú |
|---|---|---|
| BMR | Mifflin-St Jeor: 10W + 6.25H − 5A + 5 (nam) / −161 (nữ) | Mifflin et al., Am J Clin Nutr 1990;51:241-7 |
| Hệ số hoạt động | sedentary 1.2 · light 1.375 · moderate 1.55 · active 1.725 · very_active 1.9 | Hệ số phổ biến (McArdle, Exercise Physiology). **Giả định**: chấp nhận ±10% |
| Số bữa | sedentary, light → **2 bữa** (trưa, tối); moderate, active, very_active → **3 bữa** | Quyết định sản phẩm (không phải khuyến nghị y khoa) |
| Mục tiêu | giảm cân −15% TDEE · giữ 0 · tăng cơ +10% TDEE | **Giả định**, cần duyệt |
| Sàn năng lượng | max(BMR, 1200 nữ / 1500 nam) | NHLBI Obesity Guidelines 1998 (1000–1200 nữ, 1200–1600 nam). **Cần xác minh lại** |
| Protein | 0.8 g/kg (RDA); tăng cơ 1.6 g/kg | IOM DRI 2005; ISSN Position Stand 2017 |
| Carb/Fat | AMDR carb 45–65%, fat 20–35% | IOM DRI 2005 |
| Tiểu đường | carb = cận dưới AMDR (45%), ưu tiên GI thấp; sàn carb 130 g/ngày (RDA) để tránh hạ đường huyết | IOM 2005 (RDA carb 130 g). ADA Standards of Care: không có tỉ lệ lý tưởng → **giả định, cần chuyên gia duyệt** |
| Chất xơ | 14 g / 1000 kcal | IOM DRI 2005 |
| Vi chất (RDA/AI/UL) | Bảng theo tuổi/giới từ NIH ODS Fact Sheets | Mỗi dòng ghi nhóm tuổi/giới |
| Sai số chấp nhận | kcal, protein, carb, fat: **±5%**; fiber, vi chất: chỉ báo thiếu (không ràng buộc cứng) | Theo work.txt |
| Hiển thị | kcal làm tròn 10; macro làm tròn 1 g; vi chất 2 chữ số có nghĩa | Tránh độ chính xác giả |

## 5. Bộ sinh thực đơn (ILP)

- **Biến**: `x[i,m]` = số bước khối lượng (`step_g`, mặc định 10 g) của nguyên liệu i trong bữa m (nguyên); `y[d,m]` ∈ {0,1} chọn món d cho bữa m.
- **Ràng buộc cứng**: dị ứng/diet loại khỏi tập biến; nguyên liệu `locked` (pantry, chỉnh tay) cố định; mỗi bữa 1 món chính; món chính không xuất hiện ở ngày D nếu đã có ở D-1, D-2, D-3 (≤3 ngày liên tiếp); min/max gram từng nguyên liệu.
- **Mục tiêu**: minimize Σ độ lệch tuyệt đối (biến slack) so với target kcal/macro + phạt nhẹ số nguyên liệu khác nhau (khuyến khích dùng chung nguyên liệu giữa các bữa).
- **Không khả thi**: slack luôn tồn tại ⇒ solver luôn trả phương án tốt nhất; `solver_report` liệt kê chỉ số vượt ±5% + nguyên liệu gợi ý bổ sung (giàu chất thiếu nhất, hợp lệ với hạn chế).
- **Rebalance +/-**: nguyên liệu bị chỉnh → `locked`, giải lại ILP chỉ cho phần còn lại trong ngày.

## 6. Guardrail — điểm chặn

| Guardrail | Nơi kiểm tra |
|---|---|
| Disclaimer onboarding + màn thực đơn | Frontend + API trả cờ `disclaimer_required` |
| Bệnh nền nhạy cảm | `guardrails.can_generate()` → 403 `EXPERT_CONFIRMATION_REQUIRED` |
| Insulin/thuốc hạ đường | Cảnh báo cố định trên màn thực đơn |
| Sàn năng lượng | `nutrition` kẹp target; mục tiêu thấp hơn → cần `acknowledge_low_energy=true` |
| Rối loạn ăn uống | `safety_events`: ≥3 lần đặt mục tiêu dưới sàn trong 14 ngày **hoặc** ≥5 lần giảm khi đã đạt ≥100% kcal trong 1 ngày → dừng tối ưu cắt giảm, hiển thị thông điệp hỗ trợ. **Ngưỡng là giả định** |
| Dị ứng | Lọc ở repository + kiểm tra lại ở API khi thêm tay (422 `ALLERGEN_CONFLICT`) |
| LLM | JSON schema validate, retry tối đa 2, timeout 15 s, fallback template; không ghi đè thực đơn |
| Log | Logging filter loại field sức khỏe; không log request body; không analytics |

## 7. Bảo mật

- Truyền: HTTPS qua reverse proxy (Caddy trong compose, cert local cho demo).
- Lưu: mã hóa field-level payload sức khỏe (Fernet, key từ env `HEALTH_DATA_KEY`). Volume Postgres không mã hóa ở MVP → **ghi vào giả định**.
- Mọi query lọc theo `user_id` từ JWT; không có endpoint truy cập dữ liệu người khác.

## 8. Cấu trúc thư mục

```
backend/app/{api,core,guardrails,nutrition,foods,planner,ai,db}
backend/tests/{nutrition,foods,planner,guardrails,robustness,api}
backend/alembic/   backend/seed/ingredients_usda.json
frontend/src/{api,pages,components,i18n,hooks}
docs/{ARCHITECTURE.md,ASSUMPTIONS.md,DATA_SOURCES.md}
docker-compose.yml  .env.example  README.md
```

## 9b. Chatbot (yêu cầu bổ sung)

```
tin nhắn ─► parser ─────────────► engine (xác định, không LLM) ─────────────► đề xuất ─► người dùng bấm "Áp dụng"
            LLM có schema         ├─ nhận diện món: catalog + từ đồng nghĩa          (lưu mã hóa, hết hạn 1h,
            + validate + retry    ├─ vai trò: món chính / món phụ / ăn vặt            kiểm tra version thực đơn,
            ↳ dự phòng: quy tắc   │   (từ catalog: nguyên liệu chính của món =        dị ứng, lặp món khi áp dụng)
                                  │    món chính; category snack = ăn vặt)
                                  ├─ món chính → Requirement(dish, slot) → planner
                                  ├─ món phụ   → Requirement(food) → planner
                                  ├─ ăn vặt    → snack cố định → planner giảm bữa khác
                                  │   ↳ vượt: [ăn ít hơn] / [cheat day + bù ≤10%/ngày ≤3 ngày]
                                  └─ guardrail: dị ứng, bệnh nền chặn, nhịn ăn/rối loạn ăn uống
```

- LLM chỉ trích ý định (intent, tên món, số lượng, bữa, ngày). Số lượng LLM trả về phải xuất hiện trong câu gốc, nếu không thì bị loại.
- Món chưa có dữ liệu → mời người dùng nhập từ nhãn (lưu dạng `ingredients.owner_user_id`, nhóm snack).
- Bù cheat day được lưu thành `energy_adjustments`; thực đơn đã có của các ngày được bù sẽ được cân bằng lại tự động.

## 10. Khác biệt so với bản đề xuất

| Điểm | Đề xuất | Triển khai | Lý do |
|---|---|---|---|
| Bệnh nền / dị ứng | bảng `profile_conditions`, `profile_restrictions` | nằm trong `health_profiles.encrypted_payload` | Không lưu bệnh nền dạng rõ |
| `pantry_items` | không có ngày | thêm cột `day` | Nguyên liệu có sẵn gắn với một ngày cụ thể |
| `meal_dishes` | bảng riêng | `meals.dish_code` (1 món chính/bữa) | Mô hình 1 món chính + phụ đủ cho MVP |
| ILP | toàn bộ nguyên liệu | nhóm ứng viên mỗi bữa | Giải < 1–2 giây thay vì ~20 giây |
| Bảng mới | — | `energy_adjustments`, `safety_events`, `chat_messages`, `chat_proposals`, `refresh_tokens` | Chatbot, cheat day, guardrail, auth |

## 9. Thứ tự triển khai (mỗi bước có test)

1. Skeleton + Docker Compose + CI test chạy được
2. (a) `nutrition` — nhu cầu dinh dưỡng + nguồn
3. (b) `foods` — schema, seed USDA ~60 nguyên liệu
4. (c) `planner` — ILP + lặp món + báo thiếu hụt
5. (d) +/- và pantry
6. Guardrails + auth + xóa dữ liệu
7. `ai` service + fallback
8. (e) Frontend kiểu YAZIO
