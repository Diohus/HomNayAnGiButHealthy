# CODEMAP — Bản đồ mã nguồn HomNayAnGi

> Mục đích: cho AI/dev đọc để hiểu dự án **mà không cần đọc lại toàn bộ code**. Mô tả từng thư mục/file, vai trò, hàm chính và **kiểu dữ liệu đầu ra**.
> Cập nhật lần cuối: 2026-10-27. Khi sửa code, hãy cập nhật file này cho khớp.
> Tài liệu liên quan: [ARCHITECTURE.md](ARCHITECTURE.md) (thiết kế), [ASSUMPTIONS.md](ASSUMPTIONS.md) (giả định), [DATA_SOURCES.md](DATA_SOURCES.md) (nguồn số liệu), [../work.txt](../work.txt) (yêu cầu gốc).

---

## 0. Tóm tắt 30 giây

- **Sản phẩm**: web app tiếng Việt đề xuất thực đơn theo hồ sơ sức khỏe. MVP ~10 người dùng.
- **Stack**: FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic + PostgreSQL · React 18 + TS + Vite + TanStack Query + React Router · PuLP/CBC (ILP) · Docker Compose + Caddy (HTTPS) + nginx.
- **Luồng chính**: đăng ký → nhập hồ sơ (mã hóa) → `nutrition.compute_needs` tính nhu cầu → `planner.solve_day` (ILP) sinh thực đơn → người dùng +/−, thêm pantry, chat → planner cân bằng lại.
- **Nguyên tắc bất biến** (KHÔNG được phá khi phát triển tiếp):
  1. Mọi con số dinh dưỡng do code xác định (nutrition/planner) tính từ dữ liệu USDA. **LLM không sinh số liệu**.
  2. Dị ứng/chế độ ăn là ràng buộc cứng; nguồn sự thật duy nhất: `foods/restrictions.py::exclusion_reason`.
  3. Dữ liệu sức khỏe (hồ sơ, giới hạn chuyên gia, chat, đề xuất) lưu **mã hóa Fernet**; không log body/dữ liệu sức khỏe.
  4. Món chính không lặp quá 3 ngày liên tiếp (`planner/rotation.py`).
  5. Tổng kcal/đạm/carb/béo nằm trong ±5% (`PLANNER_TOLERANCE`), nếu không đạt phải báo `shortfalls` + `suggestions`.
  6. `nutrition/`, `planner/`, `chat/engine.py`, `guardrails/` là **hàm thuần, không I/O** — test không cần DB. I/O chỉ nằm ở `services/`, `db/`, `api/`.
  7. Thay đổi từ chatbot chỉ áp dụng khi người dùng bấm xác nhận (proposal).
  8. Hiển thị không có độ chính xác giả: kcal làm tròn 10, gram làm tròn 1, vi chất 2 chữ số có nghĩa.

---

## 1. Cây thư mục

```
HomNayAnGiButHealthy/
├── README.md               Hướng dẫn chạy, tính năng, test
├── work.txt                Yêu cầu gốc của sản phẩm (spec) — đọc khi cần biết "tại sao"
├── .env.example            Biến môi trường mẫu (DB, JWT, HEALTH_DATA_KEY, LLM_*)
├── .gitignore
├── docker-compose.yml      4 service: db (postgres16), backend, frontend (nginx), caddy (HTTPS)
├── deploy/Caddyfile        Reverse proxy HTTPS → frontend:80, header bảo mật, không access log
├── docs/                   ARCHITECTURE / ASSUMPTIONS / DATA_SOURCES / CODEMAP (file này)
├── backend/
│   ├── Dockerfile          python:3.11-slim; CMD: alembic upgrade head → python -m app.seed → uvicorn
│   ├── pyproject.toml      deps; extra [dev]=pytest,ruff; extra [claude]=anthropic
│   ├── alembic.ini, alembic/env.py, alembic/script.py.mako
│   ├── alembic/versions/f35083266e75_initial_schema.py   Migration duy nhất (tạo toàn bộ 18 bảng)
│   ├── app/
│   │   ├── main.py         Tạo FastAPI app, CORS, exception handlers, /api/health
│   │   ├── seed.py         `python -m app.seed` — nạp seed JSON vào DB (idempotent)
│   │   ├── core/           config, crypto, errors, logging, security
│   │   ├── db/             models (ORM), session, foods_repo
│   │   ├── api/            routes (mọi endpoint), deps (auth)
│   │   ├── nutrition/      (b) tính nhu cầu — thuần
│   │   ├── foods/          (a) DTO nguyên liệu, lọc dị ứng, so khớp tên — thuần
│   │   ├── planner/        (c)(d) ILP sinh thực đơn, rebalance, pantry, xoay vòng món — thuần
│   │   ├── chat/           chatbot: parser (LLM+quy tắc), engine (logic xác định)
│   │   ├── ai/             provider LLM, gọi có schema/retry, sinh công thức
│   │   ├── guardrails/     y tế + rối loạn ăn uống — thuần
│   │   └── services/       tầng điều phối DB ↔ các module thuần
│   ├── seed/
│   │   ├── catalog.py            Metadata nguyên liệu (tên, fdc_id, nhóm, tag, khẩu phần, GI, alias)
│   │   ├── build_ingredients.py  Sinh ingredients.json từ CSV USDA
│   │   ├── ingredients.json      80 nguyên liệu (61 nấu ăn + 19 ăn vặt) — SINH TỰ ĐỘNG, không sửa tay
│   │   └── dishes.json           26 món chính (code, name_vi, main[], slots)
│   └── tests/              pytest (~125 test), SQLite in-memory, LLM giả lập
└── frontend/
    ├── Dockerfile          build node20 → nginx:1.27
    ├── nginx.conf          /api/ → backend:8000; SPA fallback; access_log off
    ├── package.json, vite.config.ts (proxy /api → :8000), tsconfig.json, index.html
    └── src/
        ├── main.tsx        Router + Shell (bắt đăng nhập, bắt onboarding) + tab nav
        ├── types.ts        Kiểu TS khớp JSON backend
        ├── format.ts       Định dạng số (chống độ chính xác giả) + tiện ích ngày
        ├── format.test.ts  Vitest
        ├── styles.css      CSS thuần, biến màu, dark mode
        ├── api/client.ts   fetch wrapper, token, refresh tự động, ApiError
        ├── api/hooks.ts    TanStack Query hooks
        ├── i18n/           vi.ts (toàn bộ chuỗi UI), index.ts (export `t`)
        ├── components/     DaySummary, MealCard, Notices, Progress
        └── pages/          Auth, Profile (onboarding), Today, Chat, Pantry, Settings
```

---

## 2. Backend — chi tiết từng file

### 2.1 `app/main.py`
- `create_app() -> FastAPI`: gọi `setup_logging()`, thêm CORS (`CORS_ORIGINS` tách dấu phẩy), đăng ký handlers, mount `router` (prefix `/api`).
- Định dạng lỗi trả về **thống nhất**:
  - `AppError` → `{code, message, **extra}` với status tùy lỗi.
  - Validation Pydantic → 422 `{code:"VALIDATION_ERROR", message, errors:[{field, message}]}` (không trả lại `input`).
  - HTTPException → `{code:"HTTP_<status>", message}`; Exception khác → 500 `{code:"INTERNAL"}` (chỉ log method + path).
- `GET /api/health` → `{"status":"ok"}`.
- `app = create_app()` (uvicorn dùng `app.main:app`).

### 2.2 `app/core/`
| File | Nội dung | Đầu ra |
|---|---|---|
| `config.py` | `Settings` (pydantic-settings, đọc `.env`). Trường: `database_url, jwt_secret, access_token_minutes=15, refresh_token_days=7, health_data_key, cors_origins, llm_provider="openai", llm_experimental_providers=False, llm_model, llm_base_url, llm_api_key, llm_timeout_s=15, llm_max_retries=2, anthropic_api_key, anthropic_model, planner_tolerance=0.05`. | `get_settings() -> Settings` (lru_cache — đổi env trong test phải trước khi import) |
| `crypto.py` | `HealthDataCipher(key)`: Fernet. | `encrypt(dict) -> bytes`; `decrypt(bytes) -> dict` (lỗi → `RuntimeError`, không lộ nội dung). `get_cipher() -> HealthDataCipher` |
| `errors.py` | `AppError(status, code, message, **extra)` — lỗi nghiệp vụ, thông điệp tiếng Việt. | — |
| `logging.py` | `SENSITIVE_KEYS`, `RedactingFilter` (thay giá trị nhạy cảm bằng `[REDACTED]`), `setup_logging()`. | — |
| `security.py` | argon2 hash mật khẩu; JWT HS256 access (`type:"access"`, `sub`=user_id); refresh token ngẫu nhiên, lưu SHA-256. | `hash_password(str)->str`, `verify_password(pw, hash)->bool`, `create_access_token(uuid)->str`, `decode_access_token(str)->UUID|None`, `new_refresh_token()->(raw, hash)`, `hash_refresh_token(raw)->str` |

### 2.3 `app/db/`
**`session.py`**: `Base` (DeclarativeBase); `init_engine(url=None, **kw)`, `get_engine()`, `get_session()` (dependency FastAPI, yield `Session`). Biến module `_SessionLocal`.

**`models.py`** — schema (mọi bảng user có `ON DELETE CASCADE` từ `users` ⇒ xóa user = xóa toàn bộ dữ liệu):

| Bảng (class) | Khóa / cột chính | Ghi chú |
|---|---|---|
| `users` (User) | id UUID, email unique, password_hash, created_at | |
| `refresh_tokens` | user_id, token_hash unique, expires_at, revoked | rotate mỗi lần refresh |
| `health_profiles` | **user_id PK**, `encrypted_payload` (= `HealthProfileIn` JSON mã hóa), version | bệnh nền/dị ứng/diet nằm TRONG payload |
| `health_limits` | user_id, condition_code (NULL = chung), `encrypted_payload` (= `HealthLimits`), source `manual`/`document`, confirmed_at, unique(user, condition) | thay `expert_confirmations` (migration `d4e5f6a7b8c9`) |
| `nutrients` | code PK, unit | |
| `ingredients` | **code PK (str)**, owner_user_id (NULL = global; có = món user nhập từ nhãn), name_vi, name_en, category, tags JSON, aliases JSON, min_g/max_g/step_g, slots (chuỗi con của "BLDS"), gi, gi_verified, source JSON, portion JSON, unverified_nutrients JSON | |
| `ingredient_nutrients` | (ingredient_code, nutrient_code) PK, amount_per_100g (NULL = chưa xác minh), source_ref | |
| `dishes` | code PK, name_vi, slots | |
| `dish_components` | (dish_code, ingredient_code) PK, role="main" | |
| `menu_days` | user_id, day, **version** (tăng mỗi lần lưu), status `ok|partial|conflict`, targets JSON (snapshot PlannerTarget), report JSON {deviations, shortfalls, suggestions, conflicts, warnings}; unique(user, day) | |
| `meals` | menu_day_id, slot (`breakfast|lunch|dinner|snack`), **active** (False = bữa bị tắt khi đổi 3→2 bữa, dữ liệu giữ lại), dish_code | |
| `meal_items` | meal_id, ingredient_code, grams, locked, origin `optimizer|user_adjust|pantry|snack` | |
| `recipes` | meal_id unique, content JSON {steps, seasonings, tip}, source `llm|template` | bị xóa khi cấu trúc bữa đổi |
| `pantry_items` | user_id, **day**, ingredient_code, grams | gắn với 1 ngày |
| `energy_adjustments` | user_id, day, delta_kcal (âm khi bù), reason="cheat_day_compensation", source_day | |
| `safety_events` | user_id, kind, at | chỉ loại + thời điểm, không nội dung |
| `chat_messages` | user_id, role, `encrypted_content` ({text, kind?}), created_at | giữ 30 ngày |
| `chat_proposals` | id UUID, user_id, message_id, `encrypted_payload` (= `Proposal`), base_version, expires_at, applied | TTL 1h |

**`foods_repo.py`** — cầu nối DB ↔ `FoodCatalog`:
- `seed(session) -> int`: upsert nutrients, ingredients (+nutrients), dishes từ `seed/*.json`; xóa cache. Trả số nguyên liệu.
- `global_catalog(session) -> FoodCatalog`: catalog nguyên liệu global + món, **cache trong process** (`_cache`, xóa khi seed).
- `user_foods(session, user_id) -> list[Food]`: nguyên liệu user tự nhập (`user_provided=True`).
- `visible_ingredient(session, user_id, code) -> Ingredient|None`: global hoặc của chính user.

### 2.4 `app/api/`
**`deps.py`**: `current_user(Authorization header) -> UUID`; lỗi 401 `UNAUTHENTICATED` / `INVALID_TOKEN`.

**`routes.py`** — toàn bộ endpoint (prefix `/api`, trừ auth đều cần `Authorization: Bearer <access>`):

| Method & path | Body | Trả về |
|---|---|---|
| POST `/auth/register` (201) | `{email, password(8–128)}` | `{access_token, refresh_token, token_type}`; 409 `EMAIL_EXISTS` |
| POST `/auth/login` | như trên | như trên; 401 `BAD_CREDENTIALS` |
| POST `/auth/refresh` | `{refresh_token}` | token mới (cũ bị revoke); 401 `INVALID_REFRESH` |
| POST `/auth/logout` (204) | `{refresh_token}` | — |
| DELETE `/me` (204) | — | xóa user + cascade |
| GET `/profile` | — | `{profile: HealthProfileIn | null}` |
| PUT `/profile` | `HealthProfileIn` | giống `/needs`; 409 `LOW_ENERGY_ACK_REQUIRED` (kèm `floor_kcal`) / `ED_SUPPORT` |
| GET `/needs` | — | `{needs: NutritionNeeds, notices: [{code,text}], conditions_without_limits: [condition]}`; 409 `PROFILE_REQUIRED` |
| GET `/health-limits` | — | `[{id, condition, source, confirmed_at, limits}]` (đã giải mã) |
| PUT `/health-limits` | `{condition: Condition\|null, limits: HealthLimits, source: manual\|document}` | upsert theo (user, condition); 422 `LIMITS_REQUIRED` |
| DELETE `/health-limits/{id}` (204) | — | 404 `LIMIT_NOT_FOUND` |
| POST `/health-limits/extract` (multipart) | `file` (ảnh ≤ 5 MB) **hoặc** `text` (≤ 5000), `consent_ai_processing=true` | bản nháp `{limits, items[quote], rejected, other_instructions, language}`, không lưu; 422 `AI_CONSENT_REQUIRED`/`EXTRACT_INPUT_REQUIRED`/`TEXT_TOO_LONG`/`INVALID_IMAGE`, 413 `FILE_TOO_LARGE`, 503 `EXTRACTION_UNAVAILABLE`, 429 (5/giờ) |
| GET `/foods` | — | `[Food + {role, excluded_reason}]` (gồm cả món bị loại, có lý do) |
| GET `/dishes` | — | `[{code, name_vi, main, slots}]` |
| POST `/foods/custom` (201) | `CustomFoodIn` | `{code, name_vi}`; 422 `ALLERGEN_CONFLICT` |
| GET `/menu?start=YYYY-MM-DD&days=1..14` | — | `[MenuOut | null]` mỗi ngày |
| POST `/menu/generate` | `{start, days 1..7}` | `[MenuOut]` (không còn chặn bệnh nền nhạy cảm từ vòng 4) |
| POST `/menu/{day}/adjust` | `{slot, food_code, delta_g}` | `MenuOut`; lỗi `MENU_NOT_FOUND`, `ITEM_NOT_FOUND`, `ALLERGEN_CONFLICT`, `PANTRY_ITEM`, `DELTA_RANGE`, `ED_SUPPORT` |
| POST `/menu/{day}/unlock` | `{slot, food_code}` | `MenuOut` |
| POST `/menu/{day}/meals/{slot}/recipe` | — | `Recipe {steps, seasonings[{name,note}], tip, source}`; nếu LLM lỗi và đã có công thức cũ → công thức cũ + `kept_previous: true` |
| GET `/pantry?day=` | — | `[{id, food_code, grams}]` |
| POST `/pantry` (201) | `{day, food_code, grams}` | `{warnings: ["PANTRY_EXCEEDS_ENERGY"?]}`; 422 `GRAMS_RANGE`/`ALLERGEN_CONFLICT`, 404 `FOOD_NOT_FOUND` |
| DELETE `/pantry/{id}` (204) | — | — |
| POST `/chat` | `{message}` | `{kind, text, parser, detected[], unknown_mentions[], proposals[{id,key,label,day,plan,compensation}]}` |
| GET `/chat/history` | — | `[{id, role, at, text, kind?}]` (50 tin gần nhất) |
| POST `/chat/proposals/{id}/apply` | — | `{day, version, regenerated_days[], menu: MenuOut}`; 404/409 `PROPOSAL_NOT_FOUND`/`PROPOSAL_APPLIED`/`PROPOSAL_EXPIRED`/`STALE_PROPOSAL`/`ROTATION_VIOLATION`/`ED_SUPPORT` |

`MenuOut` (hàm `_menu_out`): `{day, version, plan: DayPlan, targets: [PlannerTarget], recipes: {slot: Recipe}, inactive_meals: [slot], energy_adjustment_kcal, notices}`.

> Lưu ý: logic nghiệp vụ nằm ở `services/`; route chỉ parse + gọi service + định dạng. Thêm endpoint mới: theo mẫu này.

### 2.5 `app/nutrition/` — (b) nhu cầu dinh dưỡng (thuần)
**`schemas.py`**
- Enum: `Sex(male,female)`, `ActivityLevel(sedentary,light,moderate,active,very_active)`, `Goal(lose,maintain,gain_muscle)`, `Condition(diabetes_t1,diabetes_t2,hypertension,kidney,cardio,liver,pregnant,lactating)`, `Allergen(peanut,tree_nut,milk,egg,fish,shellfish,soy,wheat,gluten,sesame)`, `Diet(vegetarian,vegan,halal,gluten_free,no_pork,no_beef)`.
- Hằng: `SENSITIVE_CONDITIONS = {kidney,cardio,liver,pregnant,lactating}`, `DIABETES = {t1,t2}`.
- `HealthProfileIn` (extra=forbid): `sex, age(18–100 int), height_cm(120–230, ≤1 thập phân), weight_kg(30–300, ≤1 thập phân), activity_level, goal, conditions[], uses_insulin_or_glucose_meds, allergies[], diets[], custom_target_kcal(800–5000|None), acknowledge_low_energy`. Validator: từ chối bool/NaN/inf, t1+t2 cùng lúc, nam + mang thai; sort+dedupe list.
- `HealthLimits` (alias cũ `ExpertLimits`): `energy_kcal_max, protein_g_max, carb_g_max, fat_g_max, sodium_mg_max, potassium_mg_max, phosphorus_mg_max` (đều optional). `HealthProfileIn.acknowledge_self_managed` bắt buộc khi có bệnh nền nhạy cảm.
- `Reference{source, applies_to, note}`; `NutrientTarget{code, unit, kind: target|min|max, value, lower, upper, reference, adjusted_for[]}`.
- `NutritionNeeds{bmr_kcal, activity_factor, tdee_kcal, energy_floor_kcal, meals_per_day, meal_slots[], targets[], warnings[], assumptions[]}` + `.get(code) -> NutrientTarget|None`.
- `LowEnergyNotAcknowledged(requested, floor)` (exception).

**`references.py`**: hằng số có nguồn — `ACTIVITY_FACTORS` (1.2/1.375/1.55/1.725/1.9), `MEAL_SLOTS` (sedentary/light → [lunch,dinner]; còn lại → [breakfast,lunch,dinner]), `GOAL_ENERGY_ADJ` (−15%/0/+10%), `ENERGY_FLOOR` (nữ 1200, nam 1500), `AMDR`, `PROTEIN_RDA_G_PER_KG=0.8`, `PROTEIN_GAIN_G_PER_KG=1.6`, `CARB_RDA_G=130`, `FIBER_G_PER_1000_KCAL=14`, `MICRO_RDA` (iron/zinc/calcium/vitamin_d theo băng tuổi × giới + UL), `SODIUM_CDRR_MG=2300`, `SODIUM_HTN_MG=1500`, các chuỗi nguồn. Hàm `band_value(bands, age, sex)`, `band_ul(bands, age)`.

**`calculator.py`**
- `mifflin_st_jeor(sex, weight, height, age) -> float` (BMR).
- `compute_needs(p: HealthProfileIn, limits=None, tolerance=0.05, lang="vi", limit_sources=None) -> NutritionNeeds`. Giới hạn carb/béo của người dùng: dồn phần thiếu trong AMDR, vẫn thiếu ⇒ hạ năng lượng + warning `LIMITS_REDUCE_ENERGY`. Thứ tự: BMR × hệ số = TDEE → năng lượng (custom hoặc TDEE×goal, kẹp sàn `max(BMR, sàn giới tính)`; custom dưới sàn không ack ⇒ raise `LowEnergyNotAcknowledged`) → kẹp theo giới hạn người dùng → đạm (gain: 1.6 g/kg; khác: max(0.8 g/kg, 15% E)) → carb/béo (tiểu đường: carb = max(45% E, 130 g); khác: béo 30%, carb phần còn lại, kẹp AMDR) → chất xơ (min) → vi chất (min, có UL) → natri (max; 1500 nếu tăng huyết áp; giới hạn người dùng ghi đè) → kali/phốt pho (max nếu người dùng nhập).
- `targets` codes: `energy_kcal, protein_g, carb_g, fat_g` (kind target, có lower/upper ±tol), `fiber_g, iron_mg, zinc_mg, calcium_mg, vitamin_d_ug` (min), `sodium_mg` [+ `potassium_mg`, `phosphorus_mg`] (max).
- `warnings` có thể: `LOW_ENERGY_ACKNOWLEDGED`, `ENERGY_RAISED_TO_FLOOR`, `CONSULT_DOCTOR_INSULIN`.

**`compensation.py`** (cheat day): `MAX_DAILY_REDUCTION_PCT=0.10`, `MAX_DAYS=3`, `MEAL_FLOOR_SHARE=0.5`.
- `plan_compensation(overflow_kcal, next_days: list[DayEnergy]) -> CompensationPlan{overflow_kcal, reductions:[Reduction{day,kcal}], forgiven_kcal}`.
- `cheat_day_energy(target, snack_kcal) -> float` = max(target, snack + 50% target).

### 2.6 `app/foods/` — (a) dữ liệu nguyên liệu (thuần)
**`catalog.py`**
- `SEED_DIR` = `backend/seed`; `NUTRIENT_CODES` (12 mã: energy_kcal, protein_g, fat_g, carb_g, fiber_g, calcium_mg, iron_mg, phosphorus_mg, potassium_mg, sodium_mg, zinc_mg, vitamin_d_ug).
- `Food` (Pydantic): `code, name_vi, name_en, category (protein|carb|vegetable|fruit|dairy|nut|fat|snack), tags, min_g, max_g, step_g, slots, gi, gi_verified, per_100g{code: float|None}, unverified_nutrients, source: FoodSource, aliases, portion: Portion|None, user_provided`. Phương thức: `nutrient(code, grams) -> float` (None → 0), `allowed_in(slot) -> bool`.
- `Dish{code, name_vi, main: [food_code], slots}` + `allowed_in(slot)`.
- `FoodCatalog(foods, dishes)`: `.foods: dict`, `.dishes: dict`; `food(code)`, `with_foods(extra) -> FoodCatalog`, `role(code) -> "main"|"side"|"snack"` (main = là nguyên liệu chính của một món nào đó), `filtered(allergies, diets) -> FoodCatalog` (loại món nếu nguyên liệu chính bị loại). Validate món tham chiếu nguyên liệu tồn tại.
- `load_seed_catalog() -> FoodCatalog` (đọc JSON trực tiếp, dùng trong test planner).

**`restrictions.py`**: `ALLERGEN_TAGS`, `DIET_EXCLUDED_TAGS` (vegetarian loại meat/fish/shellfish; vegan loại animal; halal/no_pork loại pork; no_beef loại beef; gluten_free loại gluten). `exclusion_reason(food, allergies, diets) -> "allergy:<x>"|"diet:<x>"|None`. **Nguồn sự thật duy nhất** cho lọc.

**`matching.py`** (so khớp tên trong câu chat, không LLM):
- `normalize(text, keep_diacritics=False) -> str` (có khoảng trắng 2 đầu), `has_diacritics(text)`.
- `find_foods(text, catalog) -> list[FoodMatch{food_code, alias, start, end, qty_value, qty_unit: portion|g|ml|None}]` — ưu tiên alias dài nhất, không chồng lấn, gắn số lượng đứng trước.
- `find_unknown_compounds(text) -> list[str]` — các món ghép chưa có dữ liệu (`UNKNOWN_COMPOUNDS`: trà sữa, xôi, chè…).
- `CONTAINER_WORDS` xử lý "1 lon coca" ≠ "lợn".

### 2.7 `app/planner/` — (c)(d) sinh thực đơn (thuần)
**`schemas.py`**
- `MACROS = (energy_kcal, protein_g, carb_g, fat_g)`.
- `PlannerTarget{code, kind, value}`.
- `LockedItem{food_code, grams, slot: str|None, origin}` — `user_adjust` (cố định trong slot), `pantry` (slot None, solver tự phân bổ), `snack` (slot "snack", hằng số).
- `MealStructure{dish_code, food_codes}` — giữ cấu trúc khi rebalance.
- `Requirement{kind: dish|food, code, slot|None}` — yêu cầu từ chatbot.
- `PlanRequest{day, slots, targets, tolerance=0.05, forbidden_dishes, recent_dishes{dish:count}, locked[], structure: dict[slot, MealStructure]|None (None = sinh mới), required[], min_meal_energy_kcal, prefer_low_gi, time_limit_s=10}`.
- **Đầu ra**: `DayPlan{day, status: ok|partial|conflict, meals: [MealPlan{slot, dish_code, items:[PlanItem{food_code, grams, locked, origin}], totals{code: float}}], totals, deviations:[Deviation{code, kind, target, actual, pct, within}], shortfalls:[code], suggestions:[Suggestion{nutrient, food_codes(≤3)}], conflicts:[str], warnings:[str]}` + `.main_dishes() -> set`.

**`solver.py`**
- Hằng: `MEAL_SHARE` (2 bữa 50/50; 3 bữa 25/40/35, ±8% phạt mềm), `SLOT_ORDER`, `REPORT_CODES` (12 chỉ số trong `totals`), `CATEGORY_ORDER`, `UNKNOWN_GI=70`, `DAILY_MAX_FACTOR=1.5`, `MAIN_MIN_SHARE=0.4`, `POOL` (số ứng viên mỗi bữa: dish 6, carb 4, vegetable 6, fruit 3, dairy 3, nut 2, fat 2).
- `solve_day(req: PlanRequest, catalog: FoodCatalog) -> DayPlan` — **catalog phải đã lọc dị ứng**. Các bước: tiền kiểm tra locked (→ conflicts) → chọn pool ứng viên (xác định theo hash ngày `_jitter`) → biến ILP (q nguyên × step_g, u nhị phân, y món, p pantry) → ràng buộc cấu trúc bữa (≤1 món chính, protein tự do chỉ khi thuộc món, dairy chỉ bữa sáng, ≤2 carb, ≤3 rau…) → slack cho mục tiêu (luôn khả thi, vượt ±tol phạt ×10) → giải CBC → làm tròn gram, bảo toàn tổng pantry → `finalize`.
- `finalize(req, catalog, meals, conflicts, warnings) -> DayPlan`: tính lại tổng **từ nguyên liệu**, deviations, shortfalls, suggestions (không gợi ý snack/món user nhập), status (`partial` nếu target/max ngoài ngưỡng; `conflict` nếu thêm có conflicts).
- `totals_of(items, catalog) -> dict[code, float]`.
- Mã `conflicts`: `FORBIDDEN_LOCKED_ITEM:<food>`, `LOCKED_EXCEEDS_ENERGY`, `LOCKED_EXCEEDS:<macro>`, `REQUIRED_NOT_ALLOWED:<code>`, `REQUIRED_DISH_ROTATION:<dish>`, `REQUIRED_SLOT_INVALID:<code>:<slot>`, `SOLVER_NO_SOLUTION`. Mã `warnings`: `LOCKED_SLOT_INACTIVE:<food>:<slot>`, `NO_MAIN_DISH:<slot>`.

**`rotation.py`**: `MAX_RUN=3`; `forbidden_mains(day, mains_by_date: dict[date, set[dish]], candidates) -> set[dish]` (xét cả ngày trước và sau); `max_consecutive_run(mains_by_date) -> int` (dùng trong test).

### 2.8 `app/chat/` — chatbot
**`schemas.py`**
- `ParsedIntent{intent: want_food|question|restrict|other, mentions[≤5], quantity_value, quantity_unit: portion|g|ml|None, slot, day: today|tomorrow|None, cheat_day}` — schema đầu ra LLM và parser quy tắc.
- `DetectedFood{food_code, name, role: main|side|snack, allowed, reason}`.
- `Proposal{key: absorb|plan_update|smaller_portion|cheat_day, label, day, plan: DayPlan, compensation: CompensationPlan|None, snacks:[{food_code, grams}], records_compensation_event}`.
- `ChatReply{kind: info|proposal|warning|refusal|support|need_label, text, detected, unknown_mentions, proposals, safety_events, parser: llm|rules}`.

**`parser.py`**
- `rule_parse(text) -> ParsedIntent` (từ khóa không dấu: `SLOT_WORDS`, `CHEAT_WORDS`, `WANT_WORDS`, regex `QTY`).
- `parse(text, provider, max_retries) -> (ParsedIntent, "llm"|"rules")` — gọi LLM qua `call_structured`; validator từ chối số lượng không có trong câu gốc; tín hiệu `restrict` từ quy tắc luôn thắng.

**`engine.py`** (thuần; mọi dữ liệu qua `ChatContext`)
- `ChatContext` (dataclass): `now, slots, allergies, diets, catalog_full (chưa lọc), catalog (đã lọc + món user), energy_target(day)->float, energy_floor, plan_fn, mains_by_date, snacks_by_date, blocked_conditions, safety_events, ed_flagged`.
- `PlanFn = (day, required, snack_items, energy_override, min_meal_energy) -> DayPlan`.
- `handle(text, parsed, ctx, parser_name) -> ChatReply`. Thứ tự xử lý: (1) guardrail rối loạn ăn uống → `support`; (2) nhận diện món (catalog_full + mentions LLM + món user), món lạ → `need_label`; (3) dị ứng → `refusal`; bệnh nền chưa xác nhận → `refusal`; (4) món chính/phụ → `Requirement` → `plan_fn` → proposal `plan_update`; (5) đồ ăn vặt → thử hấp thụ (`absorb`) → nếu không vừa: `smaller_portion` (thử ×0.75/0.5/0.33/0.25) + `cheat_day` (bù có giới hạn, hoặc không bù nếu có nguy cơ ED).
- Tiện ích: `kcal(v) -> int` (làm tròn 10), `_default_slot` (<10h sáng, <14h trưa, còn lại tối; ngày mai → trưa), `NUTRIENT_VI`.

### 2.9 `app/ai/` — LLM (chỉ diễn giải)
**`providers.py`**: `LLMProvider` (Protocol: `name`, `complete_json(system, user, schema, schema_name) -> dict`); `LLMError`. `OpenAICompatibleProvider` (POST `{base_url}/chat/completions`, `response_format=json_schema strict`). `AnthropicProvider` (ẩn sau `LLM_EXPERIMENTAL_PROVIDERS=true` + `LLM_PROVIDER=anthropic`, cần extra `[claude]`). `get_provider(settings) -> LLMProvider|None` — **None khi không có API key ⇒ chế độ fallback**.

**`service.py`**: `strict_schema(model) -> dict` (additionalProperties=false, mọi field required). `call_structured(provider, system, user, model, max_retries=2, validate=None) -> (obj|None, "ok"|"disabled"|"invalid"|"error")` — **không bao giờ raise**; validate Pydantic + validator nghiệp vụ, retry, dừng khi `refusal`.

**`recipes.py`**: `RecipeOut{steps[1..8], seasonings[{name, note}] ≤8, tip}`, `Recipe(RecipeOut){source: llm|template}`. `FORBIDDEN_TERMS` (từ khóa cấm theo dị ứng/diet), `NUMERIC_CLAIM` (cấm LLM ghi số gram/kcal). `violations(text, allergies, diets, allowed_phrases) -> list[str]`. `template_recipe(...) -> Recipe` (fallback an toàn). `generate_recipe(provider, dish_name, ingredient_names, allergies, diets, low_sodium, max_retries) -> Recipe`.

### 2.10 `app/guardrails/` (thuần)
**`medical.py`**: `sensitive_conditions(conditions)`, `conditions_without_limits(conditions, covered)` (chỉ để hiện notice, **không chặn**). `menu_notices(conditions, uses_meds, lang, no_limits) -> list[{code, text}]` (luôn có `DISCLAIMER`; thêm `CONSULT_DOCTOR_INSULIN`, `SODIUM_SEASONING`, `NO_LIMITS_<BỆNH>`). Chữ hiển thị trong `app/i18n`.

**`eating_disorder.py`**: `SUPPORT_MESSAGE`; `RULES` (kind → (số lần, cửa sổ)): `LOW_TARGET_ATTEMPT` 3/14d, `DECREASE_WHEN_MET` 5/1d, `COMPENSATION` 3/14d, `RESTRICT_INTENT` 2/14d, `DISTRESS` 1/30d. `RESTRICT_PHRASES`, `DISTRESS_PHRASES` (không dấu). `SafetyEventIn{kind, at}`, `EDStatus{flagged, reasons}`. `assess(events, now) -> EDStatus`, `would_flag(events, new_kind, now) -> bool`, `detect_text_signals(text) -> ["DISTRESS"?, "RESTRICT_INTENT"?]`.
Khi flagged: không cắt giảm thêm (adjust −, low target), không bù cheat day, hiển thị `SUPPORT_MESSAGE` (409 `ED_SUPPORT`).

### 2.11 `app/services/` — điều phối (có I/O)
**`profile.py`**
- `load_profile(s, uid) -> HealthProfileIn|None` (giải mã); `require_profile(...)` (409 `PROFILE_REQUIRED`).
- `record_event(s, uid, kind)` (không commit); `events(s, uid) -> list[SafetyEventIn]` (30 ngày); `ed_status(s, uid) -> EDStatus`.
- `merged_limits(s, uid) -> (HealthLimits|None, sources: {field: source}, covered: set[condition|None])` — lấy giới hạn chặt nhất từng chỉ số. `list_limits`, `upsert_limits`, `delete_limit`.
- `save_profile(s, uid, p) -> NutritionNeeds` (ghi `LOW_TARGET_ATTEMPT`, có thể raise `LOW_ENERGY_ACK_REQUIRED`/`ED_SUPPORT`).
- `current_needs(s, uid) -> (HealthProfileIn, NutritionNeeds, blocked_conditions[])` — **hàm hay dùng nhất**.
- `services/limits_extract.py`: `prepare_image` (kiểm tra định dạng thật, xoay EXIF, bỏ metadata, ≤ 2000 px, JPEG), `review` (quy đổi đơn vị, khoảng hợp lệ, trích dẫn phải có trong văn bản), `extract` (LLM vision qua `call_structured(..., image_b64=)`).

**`targets.py`**: `day_energy(needs, delta_kcal) -> float` (không dưới sàn khi giảm); `planner_targets(needs, energy_kcal=None) -> list[PlannerTarget]` (giữ đạm, co giãn carb/béo, chất xơ theo năng lượng).

**`menu.py`**
- `WINDOW=4` (ngày xung quanh để xét lặp món).
- `catalogs(s, uid, profile) -> (full_with_user_foods, allowed_filtered)`.
- `energy_delta(s, uid, day) -> float`, `energy_target(s, uid, needs, day) -> float`, `targets_for(s, uid, needs, day, energy_override=None) -> list[PlannerTarget]`.
- `get_day(s, uid, day) -> MenuDay|None`; `to_plan(md, catalog, tol, include_inactive=False) -> DayPlan` (tổng tính lại từ nguyên liệu); `save_plan(s, uid, plan, targets) -> MenuDay` (tăng version, giữ bữa inactive, xóa recipe nếu cấu trúc đổi, xóa bữa snack nếu không còn).
- `mains_by_date(s, uid, center) -> dict[date, set[dish]]`; `locked_items(s, uid, day, md) -> list[LockedItem]` (items locked + pantry của ngày).
- **`Ctx(s, uid, lang)`**: nạp `profile, needs, no_limits, full, catalog, tol` (`no_limits` chỉ để hiện notice); `solve(day, required=None, snacks=None, energy_override=None, keep_structure=False, min_meal_energy=None) -> (DayPlan, targets)` — dựng `PlanRequest` đầy đủ (rotation, recent, locked, structure, low GI cho tiểu đường).
- `generate(s, uid, start, days) -> list[DayPlan]` (tuần tự để ngày sau thấy món ngày trước).
- `adjust(s, uid, day, slot, food_code, delta_g) -> DayPlan` (khóa item ở gram mới, rebalance giữ cấu trúc; ghi `DECREASE_WHEN_MET`).
- `unlock(s, uid, day, slot, food_code) -> DayPlan`.
- `add_pantry(s, uid, day, food_code, grams) -> list[warning]`.
- `apply_plan(s, uid, plan) -> MenuDay` (kiểm tra lại dị ứng + rotation, `finalize` lại rồi lưu).

**`chat.py`**: `RETENTION=30 ngày`, `PROPOSAL_TTL=1h`. `send(s, uid, text, now=None) -> dict` (parse → dựng `ChatContext` → `engine.handle` → ghi safety events → lưu tin nhắn + proposal mã hóa). `history(s, uid, limit=50) -> list[dict]`. `snacks_on(s, uid, day) -> list[LockedItem]`. `apply_proposal(s, uid, proposal_id) -> {day, version, regenerated_days}` (kiểm tra hết hạn/đã áp dụng/version; ghi `EnergyAdjustment`, sự kiện `COMPENSATION`, rebalance các ngày bù đã có thực đơn).

**`foods.py`**: `LabelNutrients` (kiểm tra Atwater ±20%, tổng macro ≤100 g), `CustomFoodIn{name_vi, per_100g, portion_g, portion_description, contains_allergens, contains}`. `create_custom_food(s, uid, data) -> Ingredient` (code `user_<hex12>`, category snack, slots "S"). `list_foods(s, uid) -> list[dict]`.

### 2.12 `app/seed.py`, `seed/`, `alembic/`
- `python -m app.seed`: `foods_repo.seed`, in số nguyên liệu.
- `seed/catalog.py`: `CATALOG` (tuple: code, name_vi, name_en, fdc_id, category, tags, min_g, max_g, step_g, gi, slots), `SNACKS` (code, name_vi, name_en, fdc_id, tags, portion_desc, portion_g), `ALIASES` (code → từ đồng nghĩa tiếng Việt cho chatbot).
- `seed/build_ingredients.py <csv_dir> <out.json>`: đọc USDA SR Legacy CSV, map `nutrient_nbr` → mã nội bộ, kiểm tra khẩu phần snack có trong `food_portion.csv`, thiếu chỉ số cốt lõi → dừng; chỉ số thiếu khác → `null` + `unverified_nutrients`.
- `seed/dishes.json`: 26 món, ví dụ `ga_ap_chao`, `ca_kho_to`, `trung_hap`, `sua_chua_yen_mach`… (`main` = danh sách food code, `slots` ⊂ "BLD").
- **Quy trình thêm nguyên liệu**: thêm vào `catalog.py` (+ALIASES) → chạy `build_ingredients.py` → `python -m app.seed`. Thêm món: sửa `dishes.json` → seed.
- **Thay đổi schema DB**: sửa `db/models.py` → `alembic revision --autogenerate -m "..."` → kiểm tra file sinh ra.

### 2.13 `tests/`
- `conftest.py`: đặt env (Fernet key ngẫu nhiên, JWT secret, `LLM_API_KEY=""`, SQLite) **trước khi import app**. Fixtures: `catalog` (seed catalog), `engine` (SQLite in-memory + seed), `client` (TestClient), `auth` (header đã đăng ký + hồ sơ `BASE_PROFILE`: nữ 30t, 160 cm, 55 kg, moderate). Helper `register(client, email, profile)`.
- Nhóm: `nutrition/` (calculator, compensation), `foods/` (nguồn USDA, lọc, matching), `planner/` (±5%, rotation, pantry, rebalance, deterministic), `chat/` (vai trò món, snack/cheat day, parser LLM giả lập), `guardrails/` (mục 3 work.txt), `robustness/` (mục 4 work.txt), `api/test_flow.py` (end-to-end).
- LLM được giả lập bằng class fake có `complete_json` (xem `tests/chat`, `tests/robustness`).
- Chạy: `cd backend && pytest`.

---

## 3. Frontend — chi tiết từng file

| File | Vai trò | Ghi chú cho người phát triển |
|---|---|---|
| `src/main.tsx` | `QueryClient` (retry 1), `BrowserRouter`. Routes: `/login`, `/onboarding`, `/`, `/chat`, `/pantry`, `/profile`, `/settings`. `Shell` chuyển hướng `/login` nếu chưa có session, `/onboarding` nếu chưa có hồ sơ; thanh tab dưới. | Thêm trang: tạo `pages/X.tsx`, thêm Route + NavLink |
| `src/types.ts` | Interface TS khớp JSON backend: `PlanItem, MealPlan, Deviation, Suggestion, DayPlan, Notice, Recipe, MenuDay, Food, Dish, Target, Needs, Proposal, ChatReply, Profile`. | Đổi response backend ⇒ cập nhật đây |
| `src/api/client.ts` | `api<T>(path, init, retry)`: thêm `/api`, Bearer token, tự refresh khi 401, ném `ApiError(status, code, message, body)` (message ghép từ `errors[]` nếu là lỗi validation). `post/put/del`, `setTokens`, `hasSession`. | Access token chỉ trong bộ nhớ; refresh token trong `localStorage["hnag_refresh"]` |
| `src/api/hooks.ts` | `useFoods()`, `useFoodNames() -> (code)=>name_vi`, `useDishNames() -> (code)=>name|null`, `useProfile()`, `useNeeds(enabled)`, `useMenu(day)` (queryKey `["menu", day]`), `useMenuMutation(fn)` (invalidate `["menu"]`), `generateDay(day)`. | |
| `src/format.ts` | `fmtKcal` (làm tròn 10), `fmtGrams` (số nguyên), `fmtSig` (2 chữ số có nghĩa), `fmtPct`, `isoDay(Date)`, `addDays(iso, n)`. | **Luôn dùng** khi hiển thị số |
| `src/i18n/vi.ts`, `index.ts` | Toàn bộ chuỗi UI tiếng Việt; `t` = từ điển hiện tại. | Không hard-code chuỗi mới trong component, thêm vào `vi.ts` |
| `components/Progress.tsx` | `CalorieRing{actual, target}` (SVG, đỏ nếu > +5%), `MacroBar{code, actual, target}`. | |
| `components/DaySummary.tsx` | Vòng kcal + 3 thanh macro + danh sách chỉ số chưa đạt kèm gợi ý + mâu thuẫn ràng buộc. | |
| `components/MealCard.tsx` | Thẻ bữa có thể mở/đóng; mỗi nguyên liệu có nút −/+ (bước 10 g, ẩn với pantry), tag "có sẵn/ăn vặt/đã chỉnh", nút "Bỏ cố định", nút "Cách chế biến" + hiển thị công thức. | |
| `components/Notices.tsx` | Hiển thị `notices` (DISCLAIMER thường, còn lại kiểu cảnh báo). | |
| `pages/Auth.tsx` | Đăng nhập/đăng ký. | |
| `pages/Profile.tsx` | Form hồ sơ (cũng là onboarding: bắt tick disclaimer); xử lý `LOW_ENERGY_ACK_REQUIRED` → hiện checkbox xác nhận; bảng nhu cầu kèm nguồn + giả định. | |
| `pages/Today.tsx` | Điều hướng ngày, notices, cảnh báo cần xác nhận chuyên gia, nút tạo/tạo lại thực đơn, `DaySummary` + `MealCard` (adjust/unlock/recipe). | |
| `pages/Chat.tsx` | Lịch sử + gửi tin; `ProposalCard` (nút Áp dụng → `/chat/proposals/{id}/apply`); `LabelForm` khi `kind=need_label` (POST `/foods/custom`). | |
| `pages/Pantry.tsx` | Chọn ngày, thêm/xóa nguyên liệu có sẵn (chỉ liệt kê món không bị loại). | Sau khi thêm, người dùng phải "Tạo lại" thực đơn |
| `pages/Settings.tsx` | `ExpertForm` cho từng bệnh nền nhạy cảm chưa xác nhận; xóa toàn bộ dữ liệu; đăng xuất. | |
| `styles.css` | CSS thuần, biến màu `:root`, dark mode, max-width 640px (mobile-first). | |
| `format.test.ts` | Vitest cho `format.ts`. Chạy `npm test`, `npm run typecheck`. | |

---

## 4. Luồng dữ liệu chính (sequence rút gọn)

**Sinh thực đơn** `POST /menu/generate`
→ `MS.generate` → `Ctx(s, uid)` (= `P.current_needs` + `catalogs`) → mỗi ngày `Ctx.solve(day)`: `locked_items` + `mains_by_date` + `targets_for` + `forbidden_mains` → `PlanRequest` → `solve_day` → `DayPlan` → `save_plan` → commit → `_menu_out`.

**Nút +/−** `POST /menu/{day}/adjust`
→ `MS.adjust`: kiểm tra; nếu giảm khi đã đủ ⇒ `DECREASE_WHEN_MET` (có thể 409 ED) → item.locked=True, grams mới → `Ctx.solve(day, keep_structure=True)` (giữ món + tập nguyên liệu) → `save_plan`.

**Chat** `POST /chat`
→ `CS.send` → `parser.parse` (LLM hoặc quy tắc) → `ChatContext` (plan_fn = `Ctx.solve`) → `engine.handle` → `ChatReply` → lưu mã hóa → trả proposals (có id). Người dùng bấm → `apply_proposal` → `MS.apply_plan` (+ energy_adjustments, rebalance ngày bù).

**Công thức** `POST /menu/{day}/meals/{slot}/recipe`
→ `generate_recipe(get_provider(...))` → `call_structured` (schema + `violations`) → lỗi ⇒ template; nếu đã có công thức cũ ⇒ giữ cũ.

---

## 5. Biến môi trường (xem `.env.example`)
`POSTGRES_USER/PASSWORD/DB`, `DATABASE_URL` (compose tự dựng), `JWT_SECRET`, `HEALTH_DATA_KEY` (Fernet — **mất là mất dữ liệu**), `ACCESS_TOKEN_MINUTES`, `REFRESH_TOKEN_DAYS`, `CORS_ORIGINS`, `SITE_ADDRESS`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY` (trống = fallback), `LLM_TIMEOUT_S`, `LLM_MAX_RETRIES`, `LLM_EXPERIMENTAL_PROVIDERS`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `PLANNER_TOLERANCE`, `TZ=Asia/Ho_Chi_Minh` (compose; dùng cho "hôm nay" của chatbot).

---

## 6. Hướng dẫn mở rộng nhanh (checklist cho AI)

| Muốn làm | Sửa ở đâu |
|---|---|
| Thêm chỉ số dinh dưỡng mới | `foods/catalog.py::NUTRIENT_CODES`, `seed/build_ingredients.py::NUTRIENTS`, chạy lại build + seed; `nutrition/calculator.py` (target + nguồn trong `references.py`); `planner/solver.py::REPORT_CODES` (+ `MICROS` nếu là min mềm); `chat/engine.py::NUTRIENT_VI`; `frontend/src/components/DaySummary.tsx::NUTRIENT_VI` |
| Thêm bệnh nền | `nutrition/schemas.py::Condition` (+ `SENSITIVE_CONDITIONS` nếu cần chặn), logic trong `calculator.py`, `guardrails/medical.py`, `frontend/src/i18n/vi.ts::conditionNames` |
| Thêm dị ứng / chế độ ăn | `nutrition/schemas.py` (`Allergen`/`Diet`), `foods/restrictions.py`, tag trong `seed/catalog.py`, `ai/recipes.py::FORBIDDEN_TERMS`, `vi.ts` |
| Thêm endpoint | `api/routes.py` (mỏng) + logic trong `services/`; lỗi dùng `AppError`; cập nhật `frontend/src/types.ts` |
| Đổi ràng buộc thực đơn | `planner/solver.py` (giữ "slack luôn khả thi"); thêm test trong `tests/planner` |
| Thêm loại guardrail ED | `guardrails/eating_disorder.py::RULES` + nơi `record_event` trong services |
| Dùng LLM cho việc mới | Định nghĩa Pydantic schema → `call_structured` với `validate` → luôn có fallback không cần LLM |
| Thêm bảng DB | `db/models.py` (FK `users.id` với `ondelete="CASCADE"` nếu là dữ liệu user; mã hóa nếu là dữ liệu sức khỏe) + migration Alembic |

---

## 7. Điểm cần lưu ý / chưa nhất quán (quan sát khi đọc code)

- `docs/ARCHITECTURE.md §8` ghi `seed/ingredients_usda.json` nhưng file thực tế là `seed/ingredients.json`.
- `ARCHITECTURE.md` mô tả bảng `profile_conditions`, `profile_restrictions`, `meal_dishes` — **không tồn tại** trong code (đã gộp vào payload mã hóa / `meals.dish_code`, xem §10 của tài liệu đó).
- `MS.add_pantry` gọi `catalogs()` hai lần (thừa, chỉ ảnh hưởng hiệu năng).
- `foods_repo._cache` là cache trong process: chạy nhiều worker thì sau khi seed lại cần restart.
- `chat/parser.py::WANT_WORDS` chứa `"an "` (rất rộng) — hầu hết câu có chữ "ăn" sẽ là `want_food`.
- GI trong seed là `gi_verified=False` (chưa đối chiếu nguồn).
- Natri từ muối/nước mắm nêm thêm **không** được tính.
