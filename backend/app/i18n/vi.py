"""Chuỗi hiển thị tiếng Việt (catalog gốc). Khóa phẳng; placeholder dạng {ten} (str.format).
Thêm khóa mới: thêm cả ở en.py (test kiểm tra hai catalog cùng tập khóa và cùng placeholder)."""

VI: dict[str, str] = {
    # ---------- Lỗi API (code ổn định, xem frontend t.errors) ----------
    "error.ALLERGEN_CONFLICT": "Nguyên liệu này không phù hợp với dị ứng/chế độ ăn của bạn.",
    "error.ALLERGEN_CONFLICT.item": "Không thể thêm {food}: mâu thuẫn với {reason} bạn đã khai báo.",
    "error.ALLERGEN_CONFLICT.custom": "Sản phẩm này mâu thuẫn với {reason} bạn đã khai báo.",
    "error.ALLERGEN_CONFLICT.proposal": "Đề xuất chứa nguyên liệu không còn phù hợp với hồ sơ.",
    "error.BAD_CREDENTIALS": "Email hoặc mật khẩu không đúng.",
    "error.BAD_PASSWORD": "Mật khẩu không đúng.",
    "error.DAYS_RANGE.view": "Chỉ xem được 1–14 ngày mỗi lần.",
    "error.DAYS_RANGE.generate": "Chỉ sinh được 1–7 ngày mỗi lần.",
    "error.DELTA_RANGE": "Mỗi lần chỉ chỉnh từ 1 đến 500 g.",
    "error.ED_SUPPORT": (
        "Mình nhận thấy bạn có thể đang gặp áp lực với việc ăn uống. Bạn không cần phải cắt giảm thêm. "
        "Nếu cảm thấy khó khăn, hãy trò chuyện với người thân, bác sĩ, chuyên gia dinh dưỡng hoặc chuyên gia tâm lý. "
        "Ứng dụng sẽ tạm dừng các đề xuất cắt giảm năng lượng."
    ),
    "error.EMAIL_EXISTS": "Email đã được đăng ký.",
    "error.FOOD_NOT_FOUND": "Không có nguyên liệu này trong cơ sở dữ liệu.",
    "error.GRAMS_RANGE": "Khối lượng phải trong khoảng 1–3000 g.",
    "error.HTTP": "Yêu cầu không hợp lệ.",
    "error.INTERNAL": "Đã có lỗi xảy ra.",
    "error.INVALID_REFRESH": "Phiên đăng nhập đã hết hạn.",
    "error.INVALID_TOKEN": "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
    "error.ITEM_NOT_FOUND": "Không tìm thấy nguyên liệu trong bữa này.",
    "error.LIMITS_REQUIRED": "Cần nhập ít nhất một giới hạn (ví dụ natri, đạm, kali).",
    "error.LOW_ENERGY_ACK_REQUIRED": (
        "Mục tiêu {requested_kcal} kcal thấp hơn mức an toàn ~{floor_kcal} kcal/ngày. "
        "Hãy xác nhận rõ ràng nếu bạn vẫn muốn tiếp tục (nên hỏi ý kiến chuyên gia)."
    ),
    "error.MEAL_NOT_FOUND": "Không tìm thấy bữa ăn.",
    "error.MENU_NOT_FOUND": "Chưa có thực đơn cho ngày này.",
    "error.MESSAGE_LENGTH": "Tin nhắn phải có 1–1000 ký tự.",
    "error.PANTRY_ITEM": "Nguyên liệu có sẵn được chỉnh trong danh sách “Có sẵn trong nhà”.",
    "error.PROFILE_REQUIRED": "Bạn cần nhập hồ sơ sức khỏe trước.",
    "error.PROPOSAL_APPLIED": "Đề xuất này đã được áp dụng.",
    "error.PROPOSAL_EXPIRED": "Đề xuất đã hết hạn, hãy hỏi lại chatbot.",
    "error.PROPOSAL_NOT_FOUND": "Không tìm thấy đề xuất.",
    "error.RATE_LIMITED": "Bạn thao tác quá nhanh, vui lòng thử lại sau {retry_after_s} giây.",
    "error.ROTATION_VIOLATION": "Món chính sẽ bị lặp quá 3 ngày liên tiếp.",
    "error.STALE_PROPOSAL": "Thực đơn đã thay đổi sau khi đề xuất được tạo. Hãy hỏi lại chatbot.",
    "error.UNAUTHENTICATED": "Bạn cần đăng nhập.",
    "error.VALIDATION_ERROR": "Dữ liệu không hợp lệ.",
    # ---------- Vòng 8 ----------
    "chat.cannot_schedule": "Mình chưa xếp được {foods} vào thực đơn {day} (không tìm được phương án hợp lệ với mục tiêu và ràng buộc của bạn). Bạn thử bữa khác hoặc ngày khác nhé.",
    "chat.log_past_day": "Hiện mình chỉ ghi được nhật ký cho hôm nay. Món ăn của ngày trước chưa ghi được — bạn có thể bỏ qua hoặc ghi lại món hôm nay.",
    "error.PHOTO_UNAVAILABLE": "Hiện chưa phân tích được ảnh bằng AI. Bạn vẫn có thể ghi món bằng tay.",
    "error.NOT_FOOD_PHOTO": "Ảnh này có vẻ không phải ảnh món ăn. Bạn thử chụp lại đĩa/bát thức ăn nhé.",
    "error.INTAKE_BATCH_SIZE": "Mỗi lần chỉ ghi được 1–{max} món.",
    # ---------- Vòng 6: nhật ký đã ăn, đi chợ, không thích dạng chữ ----------
    "error.SERVINGS_RANGE": "Số người ăn phải trong khoảng 1–10.",
    "error.SLOT_INVALID": "Bữa không hợp lệ.",
    "error.INTAKE_NOT_FOUND": "Không tìm thấy mục này trong nhật ký.",
    "error.NOTHING_TO_REBALANCE": "Các bữa hôm nay đều đã đánh dấu ăn; không còn bữa nào để cân lại.",
    "chat.dislike_text_label": "Mình sẽ tránh {food} trong cách chế biến",
    "chat.log_confirm": "Ghi vào nhật ký {slot} hôm nay: {items}?",
    "chat.log_label": "Ghi vào nhật ký hôm nay",
    "chat.rebalance_label": "Cân lại các bữa còn lại",
    "chat.ai_estimate_short": "AI ước tính",
    "chat.estimate_short": "ước tính",
    "shop.category.protein": "Thịt, cá, trứng, đậu",
    "shop.category.carb": "Tinh bột",
    "shop.category.vegetable": "Rau củ",
    "shop.category.dairy": "Sữa và chế phẩm",
    "shop.category.fruit": "Trái cây",
    "shop.category.nut": "Các loại hạt",
    "shop.category.fat": "Dầu ăn",
    "shop.category.snack": "Đồ ăn vặt",
    # ---------- Vòng 5: hiểu món bằng LLM, đổi bữa, không thích ----------
    "error.NO_ALTERNATIVE": "Không còn món nào khác phù hợp cho bữa này (đã loại món hiện tại, món không thích và món lặp quá 3 ngày).",
    "error.PREFERENCE_NOT_FOUND": "Không tìm thấy mục này trong danh sách không thích.",
    "chat.clarify": "Mình chưa chắc bạn muốn nói món nào. Bạn chọn giúp mình nhé:",
    "chat.refusal_component": "Mình không thể đề xuất {food} vì có {component} — mâu thuẫn với {reason} bạn đã khai báo.",
    "chat.ai_estimate_note": (
        "Khối lượng nguyên liệu của {dishes} do AI ước tính (sai số cao); dinh dưỡng vẫn tính từ cơ sở dữ liệu. "
        "Bạn có thể chỉnh +/- sau khi áp dụng."
    ),
    "chat.allergy_redirect": (
        "Dị ứng là thông tin sức khỏe quan trọng nên mình không tự sửa hồ sơ qua trò chuyện. Hãy cập nhật mục "
        "Dị ứng trong Hồ sơ; sau đó thực đơn sẽ tự loại hoàn toàn thực phẩm đó."
    ),
    "chat.dislike_confirm": "Bạn muốn mình hạn chế những món này trong thực đơn? Bấm Áp dụng để thêm vào danh sách không thích.",
    "chat.dislike_label": "Thêm “{food}” vào danh sách không thích",
    "chat.dislike_unknown": (
        "Mình chưa có “{names}” trong dữ liệu nguyên liệu nên chưa thể loại khỏi thực đơn. "
        "Bạn có thể bỏ khi nấu, hoặc thêm món/nguyên liệu không thích trong Hồ sơ."
    ),
    "chat.dislike_none": (
        "Mình chưa nhận ra bạn không thích món nào. Bạn có thể thêm món/nguyên liệu không thích trong Hồ sơ."
    ),
    # ---------- Vòng 4: tự quản lý + giới hạn do người dùng cung cấp ----------
    "error.SELF_MANAGED_ACK_REQUIRED": (
        "Bạn đã chọn tình trạng cần theo dõi đặc biệt ({conditions}). Ứng dụng không có bác sĩ theo dõi; thực đơn "
        "chỉ là gợi ý và có sai số. Nếu bác sĩ đã cho bạn giới hạn (đạm, natri, kali…), hãy nhập trong Cài đặt. "
        "Vui lòng xác nhận bạn tự quản lý chế độ ăn để tiếp tục."
    ),
    "error.LIMIT_NOT_FOUND": "Không tìm thấy giới hạn này.",
    "error.AI_CONSENT_REQUIRED": "Bạn cần đồng ý gửi ảnh/văn bản tới nhà cung cấp AI để xử lý.",
    "error.EXTRACT_INPUT_REQUIRED": "Hãy gửi đúng một ảnh hoặc một đoạn văn bản.",
    "error.TEXT_TOO_LONG": "Văn bản tối đa {max} ký tự.",
    "error.FILE_TOO_LARGE": "Ảnh tối đa {max_mb} MB.",
    "error.INVALID_IMAGE": "Tệp không phải ảnh hợp lệ (chỉ nhận JPEG, PNG, WebP).",
    "error.EXTRACTION_UNAVAILABLE": "Hiện chưa đọc được tài liệu bằng AI. Bạn vẫn có thể nhập giới hạn bằng tay.",
    "notice.NO_LIMITS_KIDNEY": (
        "Bạn có bệnh thận nhưng chưa nhập giới hạn riêng (đạm, natri, kali, phốt pho). Thực đơn đang dùng mục tiêu "
        "chung nên có thể không phù hợp. Nếu bác sĩ đã cho chỉ định, hãy nhập trong Cài đặt → Giới hạn sức khỏe."
    ),
    "notice.NO_LIMITS_CARDIO": (
        "Bạn có bệnh tim mạch nhưng chưa nhập giới hạn riêng (natri, chất béo). Thực đơn đang dùng mục tiêu chung nên "
        "có thể không phù hợp. Nếu bác sĩ đã cho chỉ định, hãy nhập trong Cài đặt → Giới hạn sức khỏe."
    ),
    "notice.NO_LIMITS_LIVER": (
        "Bạn có bệnh gan nhưng chưa nhập giới hạn riêng (đạm, natri, năng lượng). Thực đơn đang dùng mục tiêu chung "
        "nên có thể không phù hợp. Nếu bác sĩ đã cho chỉ định, hãy nhập trong Cài đặt → Giới hạn sức khỏe."
    ),
    "notice.NO_LIMITS_PREGNANT": (
        "Bạn đang mang thai nhưng chưa nhập giới hạn riêng. Nhu cầu năng lượng và vi chất thay đổi theo giai đoạn; "
        "thực đơn đang dùng mục tiêu chung nên có thể không phù hợp. Nếu bác sĩ đã cho chỉ định, hãy nhập trong "
        "Cài đặt → Giới hạn sức khỏe."
    ),
    "notice.NO_LIMITS_LACTATING": (
        "Bạn đang cho con bú nhưng chưa nhập giới hạn riêng. Nhu cầu năng lượng và vi chất cao hơn bình thường; "
        "thực đơn đang dùng mục tiêu chung nên có thể không phù hợp. Nếu bác sĩ đã cho chỉ định, hãy nhập trong "
        "Cài đặt → Giới hạn sức khỏe."
    ),
    "ref.user_limit.manual": "Do người dùng cung cấp (nhập tay)",
    "ref.user_limit.document": "Do người dùng cung cấp (trích từ tài liệu)",
    "extract.reject.out_of_range": "Giá trị ngoài khoảng hợp lý, có thể đọc sai.",
    "extract.reject.unit_mismatch": "Đơn vị không phù hợp với chỉ số này.",
    "extract.reject.quote_not_found": "Không tìm thấy đoạn trích dẫn trong văn bản gốc.",
    "extract.reject.empty_quote": "Thiếu trích dẫn nguyên văn từ tài liệu.",

    # ---------- Lý do loại nguyên liệu (thay cho mã thô "allergy:fish") ----------
    "reason.allergy": "dị ứng {name}",
    "reason.diet": "chế độ ăn {name}",
    "reason.unknown": "dị ứng/chế độ ăn",
    "allergen.peanut": "đậu phộng",
    "allergen.tree_nut": "các loại hạt",
    "allergen.milk": "sữa",
    "allergen.egg": "trứng",
    "allergen.fish": "cá",
    "allergen.shellfish": "hải sản có vỏ",
    "allergen.soy": "đậu nành",
    "allergen.wheat": "lúa mì",
    "allergen.gluten": "gluten",
    "allergen.sesame": "mè",
    "diet.vegetarian": "chay (có trứng/sữa)",
    "diet.vegan": "thuần chay",
    "diet.halal": "halal",
    "diet.gluten_free": "không gluten",
    "diet.no_pork": "không thịt heo",
    "diet.no_beef": "không thịt bò",
    "condition.diabetes_t1": "tiểu đường type 1",
    "condition.diabetes_t2": "tiểu đường type 2",
    "condition.hypertension": "tăng huyết áp",
    "condition.kidney": "bệnh thận",
    "condition.cardio": "bệnh tim mạch",
    "condition.liver": "bệnh gan",
    "condition.pregnant": "đang mang thai",
    "condition.lactating": "đang cho con bú",
    "nutrient.energy_kcal": "năng lượng",
    "nutrient.protein_g": "đạm",
    "nutrient.carb_g": "carbohydrate",
    "nutrient.fat_g": "chất béo",
    "nutrient.fiber_g": "chất xơ",
    "nutrient.calcium_mg": "canxi",
    "nutrient.iron_mg": "sắt",
    "nutrient.zinc_mg": "kẽm",
    "nutrient.vitamin_d_ug": "vitamin D",
    "nutrient.sodium_mg": "natri",
    "nutrient.potassium_mg": "kali",
    "nutrient.phosphorus_mg": "phốt pho",
    "slot.breakfast": "Bữa sáng",
    "slot.lunch": "Bữa trưa",
    "slot.dinner": "Bữa tối",
    "slot.snack": "Ăn vặt",

    # ---------- Validation (không bao giờ trả lại giá trị người dùng nhập) ----------
    "validation.invalid": "Giá trị không hợp lệ.",
    "validation.invalid_field": "{field} không hợp lệ.",
    "validation.invalid_values": "Giá trị không hợp lệ: {values}.",
    "validation.not_number": "{field} phải là số.",
    "validation.max_decimals": "{field} chỉ được có tối đa {n} chữ số thập phân.",
    "validation.age_integer": "Tuổi phải là số nguyên.",
    "validation.age_range": "Tuổi phải trong khoảng 18–100 (công thức Mifflin-St Jeor áp dụng cho người trưởng thành).",
    "validation.height_range": "Chiều cao phải trong khoảng 120–230 cm.",
    "validation.weight_range": "Cân nặng phải trong khoảng 30–300 kg.",
    "validation.custom_kcal_range":
        "Mục tiêu năng lượng phải trong khoảng 800–5000 kcal. Chế độ dưới 800 kcal/ngày cần giám sát y tế.",
    "validation.diabetes_both": "Không thể chọn đồng thời tiểu đường type 1 và type 2.",
    "validation.pregnancy_sex": "Tình trạng mang thai/cho con bú không khớp với giới tính đã chọn.",
    "validation.label_macro_sum": "Tổng đạm + carb + béo không thể vượt 100 g trên 100 g.",
    "validation.label_energy_mismatch":
        "Năng lượng không khớp với đạm/carb/béo (sai lệch > 20%). Vui lòng kiểm tra lại nhãn.",
    "validation.missing": "Thiếu thông tin bắt buộc.",
    "validation.greater_than": "Giá trị phải lớn hơn {gt}.",
    "validation.greater_than_equal": "Giá trị phải từ {ge} trở lên.",
    "validation.less_than": "Giá trị phải nhỏ hơn {lt}.",
    "validation.less_than_equal": "Giá trị không được vượt quá {le}.",
    "validation.string_too_short": "Cần ít nhất {min_length} ký tự.",
    "validation.string_too_long": "Tối đa {max_length} ký tự.",
    "validation.too_short": "Cần ít nhất {min_length} mục.",
    "validation.too_long": "Tối đa {max_length} mục.",
    "validation.int_parsing": "Phải là số nguyên.",
    "validation.int_type": "Phải là số nguyên.",
    "validation.int_from_float": "Phải là số nguyên.",
    "validation.float_parsing": "Phải là số.",
    "validation.float_type": "Phải là số.",
    "validation.bool_parsing": "Phải là đúng/sai.",
    "validation.bool_type": "Phải là đúng/sai.",
    "validation.string_type": "Phải là chuỗi ký tự.",
    "validation.list_type": "Phải là danh sách.",
    "validation.enum": "Lựa chọn không hợp lệ.",
    "validation.literal_error": "Lựa chọn không hợp lệ.",
    "validation.extra_forbidden": "Trường này không được hỗ trợ.",
    "validation.date_parsing": "Ngày không hợp lệ.",
    "validation.date_from_datetime_parsing": "Ngày không hợp lệ.",
    "validation.uuid_parsing": "Mã không hợp lệ.",
    "validation.json_invalid": "Dữ liệu JSON không hợp lệ.",
    "validation.value_error": "Giá trị không hợp lệ.",
    "field.height": "Chiều cao",
    "field.weight": "Cân nặng",

    # ---------- Thông báo y tế (theo code) ----------
    "notice.DISCLAIMER": (
        "Ứng dụng không chẩn đoán bệnh và không thay thế bác sĩ hay chuyên gia dinh dưỡng. "
        "Thực đơn chỉ mang tính tham khảo."
    ),
    "notice.CONSULT_DOCTOR_INSULIN": (
        "Bạn đang dùng insulin hoặc thuốc hạ đường huyết: hãy tham khảo bác sĩ trước khi thay đổi chế độ ăn. "
        "Ứng dụng không đưa ra liều insulin hay thuốc."
    ),
    "notice.SODIUM_SEASONING": "Natri từ muối/nước mắm nêm thêm chưa được tính. Hãy nêm nhạt.",
    "support.message": (
        "Mình nhận thấy bạn có thể đang gặp áp lực với việc ăn uống. Bạn không cần phải cắt giảm thêm. "
        "Nếu cảm thấy khó khăn, hãy trò chuyện với người thân, bác sĩ, chuyên gia dinh dưỡng hoặc chuyên gia tâm lý. "
        "Ứng dụng sẽ tạm dừng các đề xuất cắt giảm năng lượng."
    ),

    # ---------- Nhu cầu dinh dưỡng: nguồn, đối tượng áp dụng, ghi chú, giả định ----------
    "ref.applies.male": "nam, {age} tuổi",
    "ref.applies.female": "nữ, {age} tuổi",
    "ref.applies.adults": "người trưởng thành",
    "ref.applies.athletes": "người tập luyện",
    "ref.activity_source": "Hệ số PAL phổ biến (McArdle, Katch & Katch, Exercise Physiology) — giả định",
    "ref.energy_floor_source": "NHLBI Obesity Education Initiative 1998 (giả định 1200 nữ / 1500 nam, cần xác minh)",
    "ref.sodium_source": "NASEM. Dietary Reference Intakes for Sodium and Potassium. 2019 (CDRR, ≥14 tuổi)",
    "ref.sodium_htn_source":
        "American Heart Association – khuyến nghị lý tưởng ≤1500 mg/ngày, đặc biệt người tăng huyết áp",
    "ref.note.protein_gain": "1.6 g/kg/ngày",
    "ref.note.protein": "max(RDA 0.8 g/kg, 15% năng lượng) — 15% là giả định sản phẩm, nằm trong AMDR",
    "ref.note.amdr": "AMDR: carbohydrate 45–65%, chất béo 20–35% năng lượng",
    "ref.note.energy": "BMR={bmr} × hệ số {factor} = TDEE {tdee}; sàn {floor} ({floor_source})",
    "ref.note.sodium": "Chỉ tính natri trong nguyên liệu; muối/nước mắm nêm thêm CHƯA được tính",
    "assumption.goal_energy": "Điều chỉnh năng lượng theo mục tiêu (−15% / +10% TDEE) là giả định sản phẩm",
    "assumption.diabetes_carb": (
        "ADA Standards of Care: không có tỉ lệ carbohydrate lý tưởng cho mọi người. Ứng dụng dùng cận dưới AMDR (45%) "
        "và không thấp hơn 130 g/ngày (IOM RDA) — GIẢ ĐỊNH, cần chuyên gia duyệt"
    ),
    "food.portion_default": "1 phần",

    # ---------- Chatbot ----------
    "chat.restrict": (
        "Mình không đề xuất nhịn ăn, bỏ bữa hay ăn dưới mức an toàn. Thực đơn của bạn đã được tính để đủ "
        "năng lượng tối thiểu (không dưới {floor} kcal/ngày). Nếu muốn giảm cân, hãy trao đổi với bác sĩ hoặc "
        "chuyên gia dinh dưỡng."
    ),
    "chat.unknown_named": "món {names}",
    "chat.unknown_any": "món nào",
    "chat.need_label": (
        "Mình chưa nhận ra {what} trong dữ liệu dinh dưỡng đã xác minh nên không thể ước tính. "
        "Bạn có thể nhập thông tin từ nhãn sản phẩm (kcal, đạm, carb, béo trên 100 g và khối lượng một phần) "
        "để mình tính vào thực đơn."
    ),
    "chat.help": (
        "Bạn có thể nói với mình như: “tôi muốn ăn gà”, “trưa nay ăn cá hồi”, “tôi muốn ăn 2 cây kem” "
        "hoặc “hôm nay cheat day, ăn pizza”. Mình sẽ điều chỉnh thực đơn cho phù hợp."
    ),
    "chat.refusal": "Mình không thể đề xuất {food} vì mâu thuẫn với {reason} bạn đã khai báo.",
    "chat.slot_not_in_plan": "{slot} không có trong thực đơn của bạn (theo mức hoạt động), mình xếp vào bữa gần nhất.",
    "chat.day.today": "hôm nay",
    "chat.day.tomorrow": "ngày mai",
    "chat.day.selected": "ngày đã chọn",
    "chat.day.date": "ngày {date}",
    "chat.date_fmt": "%d/%m",
    "chat.rotation_blocked": "Bạn đã ăn món {food} 3 ngày liên tiếp; để đa dạng, mình chưa xếp món này vào {when}.",
    "chat.no_dish_for": "Chưa có món nào dùng {food} phù hợp với các bữa của bạn.",
    "chat.moved_to_slot": "{food} được xếp vào {slot}.",
    "chat.no_change": "Mình chưa thể đề xuất thay đổi.",
    "chat.propose_around": "Mình đề xuất thực đơn {day} xoay quanh {foods}:",
    "chat.label.apply_plan": "Áp dụng thực đơn này",
    "chat.label.apply": "Áp dụng",
    "chat.label.smaller": "Ăn ít hơn: {desc} (~{kcal} kcal), giữ mục tiêu",
    "chat.label.cheat_no_comp": "Cheat day: vượt ~{kcal} kcal, không bù vào các ngày sau",
    "chat.label.cheat": "Cheat day: vượt ~{kcal} kcal; bù {spread}{forgiven}",
    "chat.none": "không",
    "chat.forgiven": "; bỏ qua ~{kcal} kcal còn lại",
    "chat.snack_out_of_range": (
        "Lượng {food} bạn nhập ({grams} g) nằm ngoài khoảng hợp lý (tối đa {max} phần). "
        "Bạn kiểm tra lại giúp mình nhé."
    ),
    "chat.from_label": " (số liệu bạn nhập từ nhãn)",
    "chat.no_cheat_needed": "Lượng này vẫn nằm trong mục tiêu của ngày nên không cần cheat day.",
    "chat.absorbed": "Mình đã giảm bớt các bữa chính để {day} vẫn đạt mục tiêu ~{kcal} kcal:",
    "chat.too_much": (
        "Nếu ăn lượng này, {day} sẽ vượt mục tiêu ~{kcal} kcal hoặc các bữa chính sẽ còn quá ít. "
        "Mình không đề xuất bỏ bữa chính."
    ),
    "chat.cheat_head": "Cheat day — các bữa chính vẫn giữ ít nhất {pct}% năng lượng:",
    "chat.comp_note": (
        "Việc bù được giới hạn tối đa 10%/ngày trong 3 ngày và không dưới mức năng lượng an toàn; "
        "phần vượt còn lại được bỏ qua."
    ),
    "chat.totals": "Tổng: ~{kcal} kcal (mục tiêu ~{target}), đạm {protein} g, carb {carb} g, béo {fat} g.",
    "chat.short.below": "⚠ Thiếu {what} ({pct}% dưới mục tiêu).{add}",
    "chat.short.above": "⚠ Vượt {what} ({pct}% trên mục tiêu).",
    "chat.short.add": " Có thể bổ sung: {foods}.",

    # ---------- Công thức (template + prompt LLM) ----------
    "recipe.season.garlic": "Tỏi",
    "recipe.season.garlic.note": "Phi thơm trước khi cho nguyên liệu chính",
    "recipe.season.scallion": "Hành lá",
    "recipe.season.scallion.note": "Rắc khi gần chín",
    "recipe.season.pepper": "Tiêu",
    "recipe.season.pepper.note": "Rắc sau khi nấu",
    "recipe.season.ginger": "Gừng",
    "recipe.season.ginger.note": "Khử mùi tanh cho cá, gà",
    "recipe.season.fish_sauce": "Nước mắm",
    "recipe.season.fish_sauce.note": "Nêm nhạt",
    "recipe.season.salt": "Muối",
    "recipe.season.salt.note": "Nêm vừa ăn",
    "recipe.season.salt.note.low_sodium": "Nêm rất ít",
    "recipe.default_dish": "món ăn",
    "recipe.step.prep": "Sơ chế và rửa sạch các nguyên liệu, để ráo.",
    "recipe.step.main": "Chế biến phần chính của {dish} (áp chảo, hấp, luộc hoặc kho) với ít dầu đã định lượng.",
    "recipe.step.veg": "Luộc hoặc xào nhanh rau để giữ màu và chất xơ.",
    "recipe.step.starch": "Nấu chín phần tinh bột (cơm, bún, khoai...) theo cách quen thuộc.",
    "recipe.tip": "Ưu tiên hấp, luộc, áp chảo ít dầu.",
    "recipe.tip.low_sodium": "Hạn chế muối và nước chấm.",
    "recipe.none": "không có",
    "recipe.low_sodium_hint": "Người dùng cần ăn nhạt (hạn chế natri).",
    "recipe.user": "Món: {dish}\nNguyên liệu: {ingredients}\nThành phần bị cấm: {banned}\n{low_sodium}",
    "recipe.system": (
        "Bạn là đầu bếp gia đình Việt Nam. Viết cách chế biến ngắn gọn bằng tiếng Việt cho bữa ăn được cung cấp. "
        "QUY TẮC: chỉ dùng nguyên liệu trong danh sách cùng gia vị cơ bản; KHÔNG ghi bất kỳ con số khối lượng, "
        "kcal, gram, ml nào (hệ thống đã định lượng); không đưa lời khuyên y khoa; tuyệt đối tránh các thành phần "
        "bị cấm được liệt kê. Ưu tiên hấp, luộc, áp chảo ít dầu."
    ),
}
