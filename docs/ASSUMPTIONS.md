# Danh sách giả định

Mọi mục dưới đây là **giả định sản phẩm hoặc kỹ thuật**, chưa được chuyên gia dinh dưỡng hay bác sĩ duyệt. Mục đánh dấu ⚠ cần duyệt trước khi mời người dùng thử thật.

## Dinh dưỡng

| # | Giả định | Vị trí trong code |
|---|---|---|
| N1 ⚠ | Mục tiêu năng lượng: giảm cân −15% TDEE, tăng cơ +10% TDEE | `nutrition/references.py` `GOAL_ENERGY_ADJ` |
| N2 ⚠ | Đạm khi giữ/giảm cân = max(0.8 g/kg, 15% năng lượng) | `nutrition/calculator.py` |
| N3 | Chất béo mặc định 30% năng lượng, carb là phần còn lại, kẹp trong AMDR | `nutrition/calculator.py` |
| N4 ⚠ | Tiểu đường: carb = 45% năng lượng (cận dưới AMDR), không dưới 130 g; ưu tiên GI thấp. ADA không có tỉ lệ lý tưởng chung | `nutrition/calculator.py` |
| N5 ⚠ | Sàn năng lượng 1200 nữ / 1500 nam (NHLBI 1998), không dưới BMR | `nutrition/references.py` |
| N6 | Ứng dụng chỉ phục vụ người 18–100 tuổi (Mifflin-St Jeor dành cho người trưởng thành) | `nutrition/schemas.py` |
| N7 | Chiều cao 120–230 cm, cân nặng 30–300 kg, tối đa 1 chữ số thập phân | `nutrition/schemas.py` |
| N8 ⚠ | Natri chỉ tính từ nguyên liệu; **muối, nước mắm nêm thêm chưa được tính**. Người tăng huyết áp được nhắc nêm nhạt | `guardrails/medical.py` |
| N9 | Khi năng lượng ngày thay đổi (bù cheat day), giữ nguyên đạm và co giãn carb/béo theo tỉ lệ | `services/targets.py` |
| N10 | Ngưỡng sai số ±5% áp dụng cho kcal, đạm, carb, béo, và cho chỉ tiêu tối thiểu (chất xơ, vi chất) khi đánh giá “đạt” | `planner/solver.py` |

## Thực đơn

| # | Giả định | Vị trí |
|---|---|---|
| P1 | Ít vận động / nhẹ → 2 bữa (trưa, tối); vừa trở lên → 3 bữa | `nutrition/references.py` `MEAL_SLOTS` |
| P2 | Tỉ lệ năng lượng giữa các bữa: 2 bữa 50/50; 3 bữa 25/40/35 (±8%, phạt mềm) | `planner/solver.py` `MEAL_SHARE` |
| P3 | Khối lượng tính theo **nguyên liệu sống/khô** (gạo khô, thịt sống) | `seed/catalog.py` |
| P4 | Khẩu phần min/max/bước của từng nguyên liệu; 1 quả trứng ≈ 50 g | `seed/catalog.py` |
| P5 | Nguyên liệu chính của món ≥ 40% khẩu phần tối đa (để “món gà” có lượng gà đáng kể) | `planner/solver.py` `MAIN_MIN_SHARE` |
| P6 | Một nguyên liệu tự do trong ngày ≤ 1,5 × khẩu phần tối đa một bữa | `planner/solver.py` |
| P7 | Mỗi bữa chỉ đưa một nhóm ứng viên vào ILP (6 món chính, 4 tinh bột, 6 rau…), chọn xác định theo ngày. Đây là heuristic có kiểm soát để giải nhanh (< 1–2 giây) và đa dạng giữa các ngày | `planner/solver.py` `POOL` |
| P8 | Món chính = món (dish), không phải nguyên liệu. “Ức gà áp chảo” và “Gà luộc xé” là hai món khác nhau đối với quy tắc lặp quá 3 ngày | `planner/rotation.py` |
| P9 | Vi chất và chất xơ là mục tiêu mềm: thiếu thì báo và gợi ý, không chặn thực đơn | `planner/solver.py` |
| P10 | GI chưa có số liệu thì coi là 70 (bảo thủ) | `planner/solver.py` `UNKNOWN_GI` |
| P11 | Dầu đậu nành được gắn tag dị ứng đậu nành (bảo thủ, dù dầu tinh luyện thường được miễn trừ) | `seed/catalog.py` |
| P12 | Halal: chỉ loại thịt heo, **không** xác minh chứng nhận halal của thịt | `foods/restrictions.py` |
| P13 | Tag dị ứng của đồ ăn vặt chế biến sẵn theo công thức phổ biến; người dùng vẫn cần đọc nhãn | `seed/catalog.py` |

## Chatbot và cheat day (người dùng đã chọn “bù có giới hạn”)

| # | Giả định | Vị trí |
|---|---|---|
| C1 ⚠ | Bù cheat day: mỗi ngày sau giảm tối đa 10% mục tiêu, tối đa 3 ngày, không dưới sàn; phần vượt còn lại được bỏ qua | `nutrition/compensation.py` |
| C2 ⚠ | Ngày ăn vặt hoặc cheat day: bữa chính luôn giữ ≥ 50% năng lượng mục tiêu (không bỏ bữa để bù) | `nutrition/compensation.py` `MEAL_FLOOR_SHARE` |
| C3 | Món ăn vặt mặc định 1 khẩu phần USDA; tối đa 10 khẩu phần một lần; đồ uống 1 ml ≈ 1 g | `chat/engine.py` |
| C4 | Không nói bữa nào thì xếp vào bữa tiếp theo theo giờ: < 10h sáng, < 14h trưa, còn lại tối; ngày mai thì mặc định bữa trưa | `chat/engine.py` |
| C5 | Món ghép chưa có dữ liệu (“trà sữa”, “cà phê sữa”, “xôi”, “chè”…) không bị hiểu nhầm thành nguyên liệu thành phần; người dùng được mời nhập từ nhãn | `foods/matching.py` |
| C6 | Câu gõ có dấu thì so khớp giữ dấu; câu không dấu mới bỏ dấu khi so khớp. “1 lon …” là vật chứa, không phải “lợn” | `foods/matching.py` |
| C7 | Đề xuất của chatbot hết hạn sau 1 giờ; bị từ chối nếu thực đơn đã thay đổi kể từ lúc đề xuất | `services/chat.py` |
| C8 | Lịch sử chat lưu mã hóa 30 ngày, bị xóa cùng khi xóa tài khoản | `services/chat.py` |
| C9 | Tiếng Anh: alias tay ngắn gọn (`seed/catalog.py` `ALIASES_EN`) + alias tự sinh từ `name_en` (phần trước dấu phẩy, bỏ ngoặc). “fish” chung chung ⇒ cá tra/basa (như “cá kho”). Câu tiếng Anh không dấu được so khớp cả với alias tiếng Việt không dấu, nên một số từ trùng hiếm gặp (vd tên “Tom” ≡ “tôm”) có thể bị hiểu nhầm | `foods/matching.py` |
| C10 ⚠ | Cụm từ guardrail rối loạn ăn uống tiếng Anh (“starve myself”, “skip meals”, “make myself throw up”, “laxatives to lose weight”…) là danh sách tối thiểu; cố ý **không** dùng “starving” đứng một mình (nghĩa thông dụng là “rất đói”) | `guardrails/eating_disorder.py` |

## Dị ứng trong công thức AI ⚠

Danh sách từ khóa cấm theo dị ứng/chế độ ăn (`ai/recipes.py`: `FORBIDDEN_TERMS` tiếng Việt, `FORBIDDEN_TERMS_EN` tiếng Anh) là **tối thiểu, cần chuyên gia dinh dưỡng/dị ứng mở rộng** trước khi mời người dùng thật. Công thức ở ngôn ngữ nào cũng phải qua **cả hai** bộ từ khóa; con số khối lượng/năng lượng (kể cả tbsp, tsp, cup, oz, lb) bị từ chối. Bộ lọc dựa trên từ khóa nên không bắt được cách diễn đạt gián tiếp; dị ứng vẫn được đảm bảo chủ yếu bởi bộ lọc nguyên liệu (`foods/restrictions.py`), công thức chỉ là văn bản hướng dẫn.

## Guardrail rối loạn ăn uống ⚠

Ngưỡng phát hiện (`guardrails/eating_disorder.py`): ≥3 lần đặt mục tiêu dưới sàn trong 14 ngày; ≥5 lần bấm giảm khi đã đạt mục tiêu (±5%) trong 1 ngày; >2 lần bù cheat day trong 14 ngày; ≥2 câu chat muốn nhịn ăn/bỏ bữa trong 14 ngày; 1 câu thể hiện hành vi nguy hiểm (gây nôn, dùng thuốc xổ để giảm cân). Danh sách cụm từ còn tối thiểu. Khi bị gắn cờ: không cắt giảm thêm, không bù cheat day, hiển thị thông điệp hỗ trợ (không kèm số hotline, vì chưa xác minh được số chính thức).

## Bệnh nền nhạy cảm (người dùng đã chọn “chặn và chờ số liệu”)

Với bệnh thận, tim mạch, gan, mang thai, cho con bú: ứng dụng **không tự đặt giới hạn an toàn**. Thực đơn chỉ được sinh sau khi người dùng xác nhận đã tham khảo chuyên gia **và** nhập ít nhất một giới hạn (năng lượng, đạm, natri, kali hoặc phốt pho tối đa). Planner áp các giới hạn này dưới dạng ràng buộc tối đa.

## Kỹ thuật và bảo mật

| # | Giả định | Ghi chú |
|---|---|---|
| T1 | Mã hóa khi lưu bằng Fernet (AES-128-CBC + HMAC) ở mức field: hồ sơ, giới hạn chuyên gia, chat, đề xuất. **Volume Postgres không mã hóa** ở MVP | Nên bật mã hóa đĩa của máy chủ |
| T2 | Bệnh nền, dị ứng, chế độ ăn nằm **trong payload mã hóa**, thay vì bảng `profile_conditions`/`profile_restrictions` dạng rõ như sơ đồ ban đầu | Thay đổi so với ARCHITECTURE đã duyệt, để tăng bảo mật |
| T3 | `pantry_items` có thêm cột `day` (nguyên liệu có sẵn gắn với một ngày) | Thay đổi so với sơ đồ ban đầu |
| T4 | Refresh token lưu trong `localStorage` (rủi ro nếu bị XSS); access token chỉ giữ trong bộ nhớ, sống 15 phút | Nâng cấp sau: cookie httpOnly |
| T5 | HTTPS do Caddy đảm nhiệm; nginx và Caddy tắt access log | |
| T6 | Server dùng giờ `Asia/Ho_Chi_Minh` để xác định “hôm nay” cho chatbot | `docker-compose.yml` |
| T7 | Rate limit **in-memory, giả định chạy một instance backend (một worker uvicorn)**. Nhiều instance/worker ⇒ mỗi tiến trình đếm riêng, cần chuyển sang kho dùng chung (Redis). Khởi động lại ⇒ bộ đếm về 0. Ngưỡng: đăng nhập sai 5 lần/15 phút theo (email, IP) **và** 30 lần sai/15 phút theo IP trên mọi email (chống credential stuffing), chỉ đếm lần sai, đăng nhập đúng chỉ xóa bộ đếm (email, IP), không xóa bộ đếm theo IP; đăng ký 10/giờ/IP; chat 20/phút/người; công thức AI 10/phút/người | `core/ratelimit.py` |
| T8 | IP người dùng lấy từ `X-Forwarded-For` qua chuỗi Caddy → nginx → backend (uvicorn `--proxy-headers --forwarded-allow-ips=*`). Chỉ an toàn vì cổng backend **không** mở ra ngoài mạng Docker | `Dockerfile`, `nginx.conf` |
| T9 | Refresh token đã thu hồi bị dùng lại ⇒ coi như bị đánh cắp, thu hồi mọi phiên của người dùng (kể cả thiết bị khác). **Khoảng ân hạn 30 giây** sau khi xoay vòng (`refresh_tokens.rotated_at`): dùng lại trong 30 s (các request song song của cùng client) chỉ bị từ chối 401, không thu hồi gì. Quá 30 s, hoặc token đã bị thu hồi do đăng xuất ⇒ thu hồi toàn bộ. Frontend gộp các lần refresh (single-flight trong tab + Web Locks giữa các tab) để không chạm cơ chế này khi dùng bình thường | `api/routes.py` `refresh`, `frontend/src/api/client.ts` |
