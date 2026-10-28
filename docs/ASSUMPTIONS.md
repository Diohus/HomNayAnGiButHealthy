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

## Hiểu món ăn bằng LLM (vòng 5) ⚠

| # | Giả định | Vị trí |
|---|---|---|
| K1 | Khớp alias **trọn cụm** ⇒ không gọi LLM. Mention chỉ khớp một phần (“bún bò huế” ⇒ “bún”, “bò”) hoặc không khớp ⇒ LLM chọn trong top-25 nguyên liệu + top-10 món (difflib + tỉ lệ token trùng, bỏ dấu). Từ chỉ số lượng/đơn vị (“2 cây kem”) không tính là “khớp một phần” | `foods/resolve.py`, `chat/engine.py` `_partial` |
| K2 | Mã chỉ được chọn trong enum dựng động mỗi lần gọi; mã ngoài enum ⇒ kết quả bị loại (retry giới hạn) ⇒ giữ hành vi cũ (`need_label`). LLM tắt/lỗi ⇒ như cũ | `foods/resolve.py` |
| K3 ⚠ | Độ tin cậy < 0,6 ⇒ hỏi lại kèm nút chọn nhanh (tối đa 4 lựa chọn). Ngưỡng là giả định | `foods/resolve.py` `CLARIFY_BELOW` |
| K4 ⚠ | Món ghép (vd bún bò huế) ⇒ AI ước tính **khối lượng nguyên liệu** cho 1 phần (sai số cao), kẹp trong [min_g, 2×max_g], tối đa 6 thành phần; dinh dưỡng vẫn tính từ CSDL. Món ghép chiếm trọn một bữa (bữa đó không thêm món chính/nguyên liệu khác) và gắn nhãn “AI ước tính” | `foods/resolve.py`, `planner/solver.py` |
| K5 | Thành phần món ghép bị dị ứng/chế độ ăn loại ⇒ từ chối cả món và nêu thành phần | `chat/engine.py` |
| K6 | Cache LRU 2000 mục, khóa = (mention chuẩn hóa, ngôn ngữ, phiên bản catalog = hash các mã); không chứa user_id hay dị ứng. Mất khi khởi động lại; mỗi tiến trình một cache | `foods/resolve.py` |
| K7 | “I don't like fish” ⇒ “cá” chung chung được hiểu là cá tra/basa (như C9); chưa hỗ trợ “không thích cả nhóm” (mọi loại cá) | `foods/matching.py` |

## Đổi bữa và món không thích (vòng 5)

| # | Giả định | Vị trí |
|---|---|---|
| S1 | Đổi một bữa: các bữa khác giữ nguyên tuyệt đối (khóa đúng slot); cấm món hiện tại, món của các bữa khác trong ngày, món không thích, món lặp quá 3 ngày. Phần nguyên liệu có sẵn đang ở bữa này được phân bổ lại trong bữa mới. Không còn món ⇒ 409 `NO_ALTERNATIVE` | `services/menu.py` `swap` |
| S2 ⚠ | Không thích là ràng buộc **mềm**: phạt 30 (bữa thiếu món chính phạt 50), nên khi buộc phải chọn thì vẫn dùng và báo `USED_DISLIKED:<mã>`. Món có nguyên liệu chính bị “không thích” cũng bị phạt | `planner/solver.py` `DISLIKE_PENALTY` |
| S3 | Câu nói về **dị ứng** trong chat không bao giờ tự sửa hồ sơ (dữ liệu sức khỏe, ràng buộc cứng): chatbot hướng dẫn vào Hồ sơ. Câu “không thích” chỉ thành đề xuất, người dùng bấm Áp dụng mới lưu | `chat/engine.py`, `chat/parser.py` |
| S4 | “Không thích” chỉ lưu mã có trong catalog. Thứ chưa có (vd “hành” — chỉ là gia vị trong công thức) được trả lời rõ là chưa thể loại khỏi thực đơn | `services/preferences.py` |

## Nhật ký đã ăn, cân lại, đi chợ (vòng 6)

| # | Giả định | Vị trí |
|---|---|---|
| L1 | `intake_entries` **không mã hóa** (món + gram + bữa), nhất quán với `menu_days`; xóa theo tài khoản (CASCADE) | `db/models.py` |
| L2 | Đánh dấu “đã ăn” chép đúng item kế hoạch của bữa (source=plan); bỏ đánh dấu xóa các bản ghi đó. Món ngoài kế hoạch vẫn phải qua bộ lọc dị ứng/chế độ ăn | `services/intake.py` |
| L3 ⚠ | Cân lại: bữa đã ăn giữ nguyên theo nhật ký; món ngoài kế hoạch khóa như ăn vặt; mỗi bữa còn lại ≥ 50 % phần năng lượng của nó (phạt rất nặng nếu thấp hơn); đã bị gắn cờ rối loạn ăn uống thì **không** cắt giảm (409 `ED_SUPPORT`); vượt mục tiêu ⇒ các bữa còn lại về mức sàn + cảnh báo, **không** tự bù sang ngày sau | `services/intake.py` `rebalance` |
| L4 | Chat “đã ăn” (thì quá khứ): đề xuất ghi nhật ký + đề xuất cân lại riêng; chưa có bản xem trước thực đơn sau khi cân lại. Không nói lượng ⇒ 1 khẩu phần (`portion`) hoặc khoảng giữa min–max của nguyên liệu; bữa theo giờ (< 11h sáng, < 16h trưa, còn lại tối) | `chat/engine.py` `_log` |
| L5 | Đi chợ: cộng mọi item của các bữa đang dùng (kể cả phần lấy từ đồ có sẵn) × số người, **rồi** trừ đồ có sẵn của các ngày đó (không âm) — đúng cả khi nấu cho nhiều người; bỏ đồ nhập từ nhãn. Làm tròn **lên**: trứng theo quả (≈ 50 g/quả — giả định), đồ có `portion` theo khẩu phần USDA, còn lại bội số 50 g (tối thiểu 100 g), dầu ăn bội số 10 g | `services/shopping.py` |
| L6 | “Không thích” dạng chữ (≤ 40 ký tự, vd “hành”): planner bỏ qua; công thức AI và mẫu tránh từ này (so khớp theo từ; gõ có dấu thì so có dấu để “hành” ≠ “hạnh nhân”) | `services/preferences.py`, `ai/recipes.py` |
| L7 | ≥ 2 alias liền kề (“phở bò”, “bánh mì trứng”) ⇒ gửi cả cụm cho LLM như ứng viên món ghép; LLM trả nguyên liệu rời thì giữ khớp cũ | `chat/engine.py` `_partial` |
| L8 | Cache `parse()` LRU 1000 (khóa = văn bản chuẩn hóa + ngôn ngữ), không cache câu có tín hiệu rối loạn ăn uống/dị ứng. Thời gian từng bước LLM ghi log DEBUG, không kèm nội dung | `chat/parser.py`, `ai/service.py` |

## Dữ liệu món Việt và đa dạng thực đơn (vòng 7)

| # | Giả định | Vị trí |
|---|---|---|
| D1 | Thành phần món (nguyên liệu chính, bữa) là giả định ẩm thực; dinh dưỡng luôn tính từ nguyên liệu USDA | `seed/dishes.json` |
| D2 ⚠ | Cá lóc dùng số liệu cá chó phương Bắc (USDA không có cá lóc); bánh phở/bún tươi dùng “Rice noodles, cooked” (khối lượng **đã nấu**, khác quy ước khối lượng khô của bún/phở khô); sườn heo là phần ăn được (không gồm xương) | `seed/catalog.py` |
| D3 | Gia vị/rau thơm (hành lá, tỏi, gừng, sả, ngò, ớt, chanh) có `slots=""`: bộ tối ưu không tự chọn làm rau của bữa; vẫn dùng được khi người dùng nói/ghi nhật ký/món ghép, và trong danh sách “không thích” | `seed/catalog.py` |
| D4 | Câu **không dấu**: các alias “tỏi, cua, măng, bưởi, ngò” chỉ khớp khi gõ có dấu (bỏ dấu trùng “tôi, của, mang, buổi, ngô”). Không dùng “thơm” trơn (= mùi thơm) cho dứa, “nhãn” trơn (= nhãn sản phẩm) cho quả nhãn | `foods/matching.py` |
| D5 | Món gọi đúng tên trong catalog (“phở bò”, “canh chua cá lóc”) ⇒ dùng món đó, không tách nguyên liệu, không cần LLM. LLM trả món ghép mà catalog có món trùng tên ⇒ dùng món | `foods/matching.py` `find_dishes`, `foods/resolve.py` |
| D6 ⚠ | Đa dạng: nguyên liệu đạm đã dùng trong 2 ngày liền trước bị phạt 2,0 mỗi ngày (lặp món 0,5); trứng (gà/vịt) là nguồn đạm tối đa 1 bữa/ngày (ràng buộc mềm, phạt 40). Đây là lựa chọn **đa dạng thực đơn**, không phải khuyến nghị y khoa về trứng | `planner/solver.py` |

## Chat “muốn ăn / đã ăn”, ghi món, ảnh bữa ăn (vòng 8)

| # | Giả định | Vị trí |
|---|---|---|
| E1 | Bữa của món ⊆ bữa của mọi nguyên liệu chính (test `test_dish_coverage`: mọi món × mọi bữa được phép đều xếp được với hồ sơ chuẩn). Sườn heo, bò thăn dùng được cả bữa sáng (cơm tấm, bún bò, phở buổi sáng) | `seed/`, `tests/planner/test_dish_coverage.py` |
| E2 | Không bao giờ tạo đề xuất có thực đơn xung đột/rỗng: trả lời “Mình chưa xếp được X…” (info) | `chat/engine.py` `_usable` |
| E3 | “Đã ăn” chỉ khi có dấu hiệu quá khứ rõ (vừa/đã/mới/rồi/xong, just/had/ate) **hoặc** LLM nói đã ăn và bữa đó đã qua (sáng ≥ 10h, trưa ≥ 14h, tối ≥ 21h). Không thì là “muốn ăn” | `chat/parser.py` `past_check` |
| E4 | Câu nói về hôm qua (“tối qua”, “yesterday”): chưa hỗ trợ ghi nhật ký ngày trước ⇒ trả lời info, không ghi | `chat/engine.py` |
| E5 ⚠ | Ghi nhật ký một món ⇒ nguyên liệu chính + phần ăn kèm điển hình `log_sides` (vd cơm tấm: 70 g cơm, 30 g dưa leo; phở: 30 g giá). Khẩu phần ăn kèm là **giả định ẩm thực**, gắn nguồn “ước tính”, người dùng xóa/sửa được | `seed/dishes.json` |
| E6 | Tên gọi tắt món chỉ khi không mơ hồ: “cơm tấm” ⇒ cơm tấm sườn. “phở” trơn **không** gán (phở bò hay phở gà) | `foods/matching.py` `DISH_ALIASES` |
| E7 | Hiểu câu bằng 1 lượt LLM (N1): đã thử, đo thật chậm hơn đường 2 bước (10 câu mẫu, p50 ~4,2 s so với ~2,7 s; prompt gộp dài hơn, hay phải thử lại) ⇒ tắt ở vòng 8, **đã gỡ ở vòng 10** (xem git `ab85bd9` để lấy lại `chat/understand.py`, `scripts/bench_chat.py`). Chat luôn: parse ⇒ resolve | `services/chat.py` |
| E8 ⚠ | Ảnh bữa ăn: AI chỉ nhận **tên + khối lượng ước tính** (sai số cao); mã thực phẩm do resolver chọn trong catalog, dinh dưỡng từ USDA; khối lượng kẹp [min, 2×max] của nguyên liệu; món trong catalog ⇒ nguyên liệu chính chia đều khối lượng. Kết quả là **bản nháp**, chỉ ghi khi người dùng bấm “Ghi vào nhật ký”. Ảnh không lưu, không log; tối đa 10 ảnh/giờ/người | `services/meal_photo.py` |

## Tổng quan tuần, xuất dữ liệu, prompt injection, PWA (vòng 9)

| # | Giả định | Vị trí |
|---|---|---|
| F1 | Tổng quan tuần chỉ tính ngày CÓ ghi nhật ký (`basis="eaten"`); không ngày nào ghi ⇒ theo thực đơn (`basis="planned"`). Ngày không có dữ liệu bị bỏ khỏi trung bình, không tính là 0 | `services/summary.py` |
| F2 | “Chất hay thiếu”: chất xơ, canxi, sắt, kẽm, vitamin D dưới 80 % mục tiêu ở ≥ 4/7 ngày. Gợi ý 3 thực phẩm giàu chất đó (theo khẩu phần tối đa), bỏ đồ ăn vặt, đồ tự nhập, gia vị không xếp vào bữa, món không thích, đồ dị ứng/ngoài chế độ ăn. Gợi ý chung, không phải tư vấn y khoa | `services/summary.py` |
| F3 | Xuất dữ liệu: phải nhập lại mật khẩu, 3 lần/giờ (đếm cả lần sai). Không xuất hash mật khẩu, refresh token; sự kiện an toàn chỉ xuất số lượng theo loại. Tệp chứa dữ liệu sức khỏe đã giải mã — người dùng tự bảo quản | `services/export.py` |
| F4 ⚠ | Chống prompt injection dựa vào hậu kiểm bằng code (enum mã, khoảng giá trị, trích dẫn có thật, lọc dị ứng sau LLM, từ khóa + con số trong công thức, kẹp khối lượng); câu “dữ liệu không phải chỉ dẫn” trong system prompt chỉ giảm rủi ro. Rủi ro còn lại: một giới hạn **hợp lệ** do tài liệu độc hại đưa vào (có trích dẫn, trong khoảng) vẫn có thể vào bản nháp — người dùng phải duyệt trước khi lưu | `tests/security/test_prompt_injection.py` |
| F5 | PWA: service worker chỉ cache giao diện (app shell + assets), **không bao giờ** cache `/api/*`. Ngoại tuyến: xem lại giao diện đã tải, mọi nút gọi API bị khóa | `frontend/public/sw.js` |

## Dị ứng trong công thức AI ⚠

Danh sách từ khóa cấm theo dị ứng/chế độ ăn (`ai/recipes.py`: `FORBIDDEN_TERMS` tiếng Việt, `FORBIDDEN_TERMS_EN` tiếng Anh) là **tối thiểu, cần chuyên gia dinh dưỡng/dị ứng mở rộng** trước khi mời người dùng thật. Công thức ở ngôn ngữ nào cũng phải qua **cả hai** bộ từ khóa; con số khối lượng/năng lượng (kể cả tbsp, tsp, cup, oz, lb) bị từ chối. Bộ lọc dựa trên từ khóa nên không bắt được cách diễn đạt gián tiếp; dị ứng vẫn được đảm bảo chủ yếu bởi bộ lọc nguyên liệu (`foods/restrictions.py`), công thức chỉ là văn bản hướng dẫn.

## Guardrail rối loạn ăn uống ⚠

Ngưỡng phát hiện (`guardrails/eating_disorder.py`): ≥3 lần đặt mục tiêu dưới sàn trong 14 ngày; ≥5 lần bấm giảm khi đã đạt mục tiêu (±5%) trong 1 ngày; >2 lần bù cheat day trong 14 ngày; ≥2 câu chat muốn nhịn ăn/bỏ bữa trong 14 ngày; 1 câu thể hiện hành vi nguy hiểm (gây nôn, dùng thuốc xổ để giảm cân). Danh sách cụm từ còn tối thiểu. Khi bị gắn cờ: không cắt giảm thêm, không bù cheat day, hiển thị thông điệp hỗ trợ (không kèm số hotline, vì chưa xác minh được số chính thức).

## Bệnh nền nhạy cảm — tự quản lý (định hướng v2, từ vòng 4)

Ứng dụng **không chuyên về y tế, không có bác sĩ theo dõi**; thực đơn chỉ là gợi ý và có sai số. (Thay cho chính sách cũ “chặn và chờ chuyên gia xác nhận”.)

| # | Giả định | Vị trí |
|---|---|---|
| H1 ⚠ | Có bệnh thận, tim mạch, gan, mang thai hoặc cho con bú ⇒ người dùng **xác nhận một lần** là tự quản lý (`acknowledge_self_managed`), sau đó được sinh thực đơn bình thường | `services/profile.py` `save_profile` |
| H2 ⚠ | Ứng dụng **không tự đặt giới hạn y khoa**. Chưa có giới hạn do người dùng cung cấp ⇒ dùng mục tiêu chung như người khỏe + notice `NO_LIMITS_<BỆNH>` ở màn Hôm nay và Hồ sơ. Giới hạn “áp dụng chung” (không gắn bệnh nào) được coi là đã có giới hạn cho mọi bệnh | `guardrails/medical.py` |
| H3 | Nhiều giới hạn ⇒ lấy giá trị **chặt nhất** cho từng chỉ số; nguồn hiển thị “Do người dùng cung cấp (nhập tay / trích từ tài liệu)” | `services/profile.py` `merged_limits` |
| H4 ⚠ | Giới hạn carb/chất béo làm thiếu năng lượng ⇒ chỉ dồn phần thiếu sang chất còn chỗ **trong AMDR và trong giới hạn của người dùng**; vẫn thiếu ⇒ hạ mục tiêu năng lượng và báo `LIMITS_REDUCE_ENERGY` (không bù ngoài AMDR) | `nutrition/calculator.py` |
| H5 | Khoảng hợp lệ của giới hạn (vd carb 20–600 g, chất béo 10–300 g, natri ≤ 6000 mg) chỉ để chặn gõ nhầm/đọc sai, **không** phải khuyến nghị y khoa | `nutrition/schemas.py` `HealthLimits` |

## Trích xuất giới hạn từ ảnh/văn bản bằng AI ⚠

- AI (LLM vision) **có thể đọc sai**. Kết quả luôn là **bản nháp**: mỗi giá trị kèm trích dẫn nguyên văn; người dùng phải duyệt/sửa rồi mới lưu. Không có bước nào tự lưu.
- Hậu kiểm bằng code, không tin LLM: quy đổi đơn vị xác định (natri mmol × 23, kali mmol × 39,1, phốt pho mmol × 30,97, g ↔ mg); giá trị ngoài khoảng hợp lệ bị loại; với văn bản dán vào, **trích dẫn phải có thật** trong văn bản (so sánh sau khi bỏ dấu, dấu câu, khoảng trắng). Với ảnh không đối chiếu được trích dẫn — người dùng tự so với ảnh gốc.
- “Muối” (NaCl) được quy đổi **xác định** sang natri: 1 g muối = 393 mg natri (NaCl chứa 39,3 % natri theo khối lượng). LLM trả `unit=g_salt`, code nhân hệ số; giao diện ghi “quy đổi từ … g muối”. `g_salt` chỉ hợp lệ cho natri.
- Chỉ dẫn không định lượng được (vd “hạn chế đồ chiên”) chỉ hiển thị, **không** thành ràng buộc của bộ tối ưu.
- Quyền riêng tư: cần đồng ý rõ ràng; ảnh/văn bản chỉ nằm trong bộ nhớ của request, không lưu, không log; ảnh bị xóa metadata (EXIF/GPS) trước khi gửi nhà cung cấp AI.

## Kỹ thuật và bảo mật

| # | Giả định | Ghi chú |
|---|---|---|
| T1 | Mã hóa khi lưu bằng Fernet (AES-128-CBC + HMAC) ở mức field: hồ sơ, giới hạn chuyên gia, chat, đề xuất. **Volume Postgres không mã hóa** ở MVP | Nên bật mã hóa đĩa của máy chủ |
| T2 | Bệnh nền, dị ứng, chế độ ăn nằm **trong payload mã hóa**, thay vì bảng `profile_conditions`/`profile_restrictions` dạng rõ như sơ đồ ban đầu | Thay đổi so với ARCHITECTURE đã duyệt, để tăng bảo mật |
| T3 | `pantry_items` có thêm cột `day` (nguyên liệu có sẵn gắn với một ngày) | Thay đổi so với sơ đồ ban đầu |
| T4 | Refresh token lưu trong `localStorage` (rủi ro nếu bị XSS); access token chỉ giữ trong bộ nhớ, sống 15 phút | Nâng cấp sau: cookie httpOnly |
| T5 | HTTPS do Caddy đảm nhiệm; nginx và Caddy tắt access log | |
| T6 | Server dùng giờ `Asia/Ho_Chi_Minh` để xác định “hôm nay” cho chatbot | `docker-compose.yml` |
| T7 | Rate limit (thêm: đọc tài liệu bằng AI 5 lần/giờ/người) **in-memory, giả định chạy một instance backend (một worker uvicorn)**. Nhiều instance/worker ⇒ mỗi tiến trình đếm riêng, cần chuyển sang kho dùng chung (Redis). Khởi động lại ⇒ bộ đếm về 0. Ngưỡng: đăng nhập sai 5 lần/15 phút theo (email, IP) **và** 30 lần sai/15 phút theo IP trên mọi email (chống credential stuffing), chỉ đếm lần sai, đăng nhập đúng chỉ xóa bộ đếm (email, IP), không xóa bộ đếm theo IP; đăng ký 10/giờ/IP; chat 20/phút/người; công thức AI 10/phút/người; đổi bữa + cân lại 20/phút/người (chung); nút +/− + bỏ cố định 60/phút/người (chung, `RL.ADJUST` — vòng 10: riêng với đổi bữa vì người dùng bấm +/− liên tục dễ vượt 20/phút, nút bị khóa trong lúc chờ solver nên 60/phút vẫn chặn gọi dồn bằng script) | `core/ratelimit.py` |
| T8 | IP người dùng lấy từ `X-Forwarded-For` qua chuỗi Caddy → nginx → backend (uvicorn `--proxy-headers --forwarded-allow-ips=*`). Chỉ an toàn vì cổng backend **không** mở ra ngoài mạng Docker | `Dockerfile`, `nginx.conf` |
| T9 | Refresh token đã thu hồi bị dùng lại ⇒ coi như bị đánh cắp, thu hồi mọi phiên của người dùng (kể cả thiết bị khác). **Khoảng ân hạn 30 giây** sau khi xoay vòng (`refresh_tokens.rotated_at`): dùng lại trong 30 s (các request song song của cùng client) chỉ bị từ chối 401, không thu hồi gì. Quá 30 s, hoặc token đã bị thu hồi do đăng xuất ⇒ thu hồi toàn bộ. Frontend gộp các lần refresh (single-flight trong tab + Web Locks giữa các tab) để không chạm cơ chế này khi dùng bình thường. Đăng xuất (vòng 10) gọi `POST /auth/logout` để thu hồi refresh token; mạng lỗi thì vẫn xóa token phía client | `api/routes.py` `refresh`, `frontend/src/api/client.ts` |
