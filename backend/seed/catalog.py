"""Danh mục nguyên liệu seed — chỉ chứa metadata (tên, nhóm, tag, khẩu phần).

Giá trị dinh dưỡng KHÔNG được gõ tay ở đây: `build_ingredients.py` đọc chúng từ
USDA FoodData Central (SR Legacy, bản 2018-04) theo `fdc_id`.

Khối lượng trong ứng dụng là khối lượng SỐNG / chưa chế biến (gạo khô, thịt sống).

`gi`: chỉ số đường huyết (glucose = 100) từ Atkinson FS et al., "International tables of
glycemic index and glycemic load values: 2008", Diabetes Care 2008;31(12):2281-2283.
Các giá trị này được nhập từ trí nhớ về bảng gốc → `gi_verified=False` ("chưa xác minh")
cho đến khi đối chiếu lại với bản gốc. Chúng chỉ dùng làm phạt mềm trong bộ tối ưu.
"""

# category: protein | carb | vegetable | fruit | dairy | nut | fat
# tags: allergen:* | animal | meat | poultry | pork | beef | fish | shellfish | egg | dairy | gluten
# slots: bữa được phép dùng (B=sáng, L=trưa, D=tối)
# (code, name_vi, name_en, fdc_id, category, tags, min_g, max_g, step_g, gi, slots)
CATALOG: list[tuple] = [
    # --- Protein ---
    ("chicken_breast", "Ức gà", "Chicken breast, skinless", 171077, "protein", ["animal", "meat", "poultry"], 50, 250, 10, None, "LD"),
    ("chicken_thigh", "Đùi gà (bỏ da)", "Chicken thigh, meat only", 173627, "protein", ["animal", "meat", "poultry"], 50, 250, 10, None, "LD"),
    ("beef_lean", "Thịt bò nạc xay (95% nạc)", "Ground beef 95% lean", 171790, "protein", ["animal", "meat", "beef"], 50, 200, 10, None, "LD"),
    ("pork_tenderloin", "Thăn heo", "Pork tenderloin, lean", 168249, "protein", ["animal", "meat", "pork"], 50, 200, 10, None, "LD"),
    ("salmon", "Cá hồi", "Atlantic salmon, farmed", 175167, "protein", ["animal", "fish", "allergen:fish"], 50, 200, 10, None, "LD"),
    ("tuna", "Cá ngừ tươi", "Yellowfin tuna", 175159, "protein", ["animal", "fish", "allergen:fish"], 50, 200, 10, None, "LD"),
    ("catfish", "Cá da trơn (cá tra/basa)", "Channel catfish, farmed", 175165, "protein", ["animal", "fish", "allergen:fish"], 50, 250, 10, None, "LD"),
    ("tilapia", "Cá rô phi", "Tilapia", 175176, "protein", ["animal", "fish", "allergen:fish"], 50, 250, 10, None, "LD"),
    ("mackerel", "Cá thu", "Spanish mackerel", 173673, "protein", ["animal", "fish", "allergen:fish"], 50, 200, 10, None, "LD"),
    ("shrimp", "Tôm", "Shrimp", 175179, "protein", ["animal", "shellfish", "allergen:shellfish"], 50, 200, 10, None, "LD"),
    ("squid", "Mực", "Squid", 174223, "protein", ["animal", "shellfish", "allergen:shellfish"], 50, 200, 10, None, "LD"),
    ("egg", "Trứng gà", "Whole egg", 171287, "protein", ["animal", "egg", "allergen:egg"], 50, 150, 50, None, "BLD"),
    ("tofu", "Đậu hũ", "Firm tofu", 172475, "protein", ["allergen:soy"], 50, 300, 10, None, "BLD"),
    ("lentils", "Đậu lăng", "Lentils, raw", 172420, "protein", [], 30, 100, 10, 32, "LD"),
    ("mung_beans", "Đậu xanh", "Mung beans, raw", 174256, "protein", [], 30, 100, 10, None, "BLD"),
    ("black_beans", "Đậu đen", "Black beans, raw", 173734, "protein", [], 30, 100, 10, None, "LD"),
    # --- Carb ---
    ("white_rice", "Gạo trắng", "White rice, raw, unenriched", 169756, "carb", [], 40, 150, 10, 73, "LD"),
    ("brown_rice", "Gạo lứt", "Brown rice, raw", 169703, "carb", [], 40, 150, 10, 68, "LD"),
    ("rice_noodles", "Bún/phở khô", "Rice noodles, dry", 169742, "carb", [], 40, 150, 10, 53, "BLD"),
    ("glass_noodles", "Miến", "Cellophane noodles (mung bean)", 174258, "carb", [], 30, 100, 10, None, "BLD"),
    ("wholewheat_bread", "Bánh mì nguyên cám", "Whole-wheat bread", 172688, "carb", ["gluten", "allergen:gluten", "allergen:wheat"], 30, 150, 10, 74, "B"),
    ("baguette", "Bánh mì", "French bread", 172675, "carb", ["gluten", "allergen:gluten", "allergen:wheat"], 40, 150, 10, None, "B"),
    ("oats", "Yến mạch", "Oats, dry", 173904, "carb", [], 30, 100, 10, 55, "B"),
    ("sweet_potato", "Khoai lang", "Sweet potato, raw", 168482, "carb", [], 80, 350, 10, 63, "BLD"),
    ("potato", "Khoai tây", "Potato, raw", 170026, "carb", [], 80, 350, 10, 78, "LD"),
    ("corn", "Bắp ngọt", "Sweet corn, raw", 169998, "carb", [], 80, 300, 10, 52, "BLD"),
    ("taro", "Khoai môn", "Taro, raw", 169308, "carb", [], 80, 300, 10, 53, "LD"),
    # --- Vegetable ---
    ("bok_choy", "Cải thìa", "Pak-choi", 170390, "vegetable", [], 50, 250, 10, None, "LD"),
    ("mustard_greens", "Cải xanh", "Mustard greens", 169256, "vegetable", [], 50, 250, 10, None, "LD"),
    ("napa_cabbage", "Cải thảo", "Napa cabbage (pe-tsai)", 169979, "vegetable", [], 50, 250, 10, None, "LD"),
    ("sweet_potato_leaves", "Rau lang", "Sweet potato leaves", 169303, "vegetable", [], 50, 250, 10, None, "LD"),
    ("spinach", "Cải bó xôi", "Spinach", 168462, "vegetable", [], 50, 250, 10, None, "LD"),
    ("broccoli", "Bông cải xanh", "Broccoli", 170379, "vegetable", [], 50, 250, 10, None, "LD"),
    ("cabbage", "Bắp cải", "Cabbage", 169975, "vegetable", [], 50, 250, 10, None, "LD"),
    ("carrot", "Cà rốt", "Carrot", 170393, "vegetable", [], 30, 200, 10, 39, "LD"),
    ("tomato", "Cà chua", "Tomato", 170457, "vegetable", [], 30, 200, 10, None, "BLD"),
    ("cucumber", "Dưa leo", "Cucumber", 168409, "vegetable", [], 50, 250, 10, None, "BLD"),
    ("green_beans", "Đậu que", "Green beans", 169961, "vegetable", [], 50, 250, 10, None, "LD"),
    ("pumpkin", "Bí đỏ", "Pumpkin", 168448, "vegetable", [], 50, 250, 10, 64, "LD"),
    ("bitter_melon", "Khổ qua", "Bitter gourd", 168393, "vegetable", [], 50, 200, 10, None, "LD"),
    ("eggplant", "Cà tím", "Eggplant", 169228, "vegetable", [], 50, 250, 10, None, "LD"),
    ("bean_sprouts", "Giá đỗ", "Mung bean sprouts", 169957, "vegetable", [], 30, 200, 10, None, "BLD"),
    ("mushroom", "Nấm mỡ", "White mushrooms", 169251, "vegetable", [], 50, 200, 10, None, "LD"),
    ("okra", "Đậu bắp", "Okra", 169260, "vegetable", [], 50, 200, 10, None, "LD"),
    ("lettuce", "Xà lách", "Green leaf lettuce", 169249, "vegetable", [], 30, 150, 10, None, "BLD"),
    ("chayote", "Su su", "Chayote", 170402, "vegetable", [], 50, 250, 10, None, "LD"),
    ("winter_melon", "Bí đao", "Waxgourd", 170069, "vegetable", [], 50, 250, 10, None, "LD"),
    # --- Fruit ---
    ("banana", "Chuối", "Banana", 173944, "fruit", [], 50, 200, 10, 51, "BLD"),
    ("orange", "Cam", "Orange", 169097, "fruit", [], 80, 250, 10, 43, "BLD"),
    ("apple", "Táo", "Apple, with skin", 171688, "fruit", [], 80, 250, 10, 36, "BLD"),
    ("papaya", "Đu đủ", "Papaya", 169926, "fruit", [], 80, 250, 10, None, "BLD"),
    ("guava", "Ổi", "Guava", 173044, "fruit", [], 80, 250, 10, None, "BLD"),
    ("mango", "Xoài", "Mango", 169910, "fruit", [], 80, 250, 10, 51, "BLD"),
    ("watermelon", "Dưa hấu", "Watermelon", 167765, "fruit", [], 100, 300, 10, 76, "BLD"),
    # --- Dairy / soy drink ---
    ("milk_lowfat", "Sữa tươi ít béo", "Milk 1% fat", 170872, "dairy", ["animal", "dairy", "allergen:milk"], 100, 300, 50, 37, "B"),
    ("yogurt_lowfat", "Sữa chua không đường ít béo", "Plain low-fat yogurt", 170886, "dairy", ["animal", "dairy", "allergen:milk"], 100, 250, 50, None, "B"),
    ("soymilk", "Sữa đậu nành không đường", "Soymilk, unfortified", 172446, "dairy", ["allergen:soy"], 100, 300, 50, None, "B"),
    # --- Nut ---
    ("peanuts", "Đậu phộng", "Peanuts, raw", 172430, "nut", ["allergen:peanut"], 10, 40, 5, None, "BLD"),
    ("cashews", "Hạt điều", "Cashews, raw", 170162, "nut", ["allergen:tree_nut"], 10, 40, 5, None, "BLD"),
    # --- Fat ---
    ("soybean_oil", "Dầu đậu nành", "Soybean oil", 171411, "fat", ["allergen:soy"], 0, 20, 5, None, "BLD"),
    ("olive_oil", "Dầu ô liu", "Olive oil", 171413, "fat", [], 0, 20, 5, None, "BLD"),
    # --- Vòng 7: món Việt hằng ngày (FDC ID tra trong food.csv; comment = description USDA) ---
    ("pork_belly", "Thịt ba chỉ heo", "Pork belly, raw", 167812, "protein", ["animal", "meat", "pork"], 50, 200, 10, None, "LD"),  # Pork, fresh, belly, raw
    ("pork_ribs", "Sườn heo", "Pork spareribs, raw", 167853, "protein", ["animal", "meat", "pork"], 80, 250, 10, None, "BLD"),  # Pork, fresh, spareribs, separable lean and fat, raw
    ("pork_ground", "Thịt heo xay", "Ground pork, raw", 167902, "protein", ["animal", "meat", "pork"], 50, 200, 10, None, "BLD"),  # Pork, fresh, ground, raw
    ("chicken_whole", "Thịt gà (cả da)", "Chicken, meat and skin, raw", 171447, "protein", ["animal", "meat", "poultry"], 80, 250, 10, None, "BLD"),  # Chicken, broilers or fryers, meat and skin, raw
    ("chicken_liver", "Gan gà", "Chicken liver, raw", 171060, "protein", ["animal", "meat", "poultry"], 30, 100, 10, None, "LD"),  # Chicken, liver, all classes, raw
    ("beef_sirloin", "Thịt bò thăn", "Beef top sirloin steak, raw", 168726, "protein", ["animal", "meat", "beef"], 50, 200, 10, None, "BLD"),  # Beef, top sirloin, steak, separable lean and fat, trimmed to 1/8" fat, all grades, raw
    ("crab", "Cua", "Blue crab, raw", 174204, "protein", ["animal", "shellfish", "allergen:shellfish"], 50, 200, 10, None, "LD"),  # Crustaceans, crab, blue, raw
    ("clam", "Nghêu", "Clams, raw", 174214, "protein", ["animal", "shellfish", "allergen:shellfish"], 50, 250, 10, None, "LD"),  # Mollusks, clam, mixed species, raw
    # Cá lóc (snakehead) KHÔNG có trong SR Legacy ⇒ dùng số liệu cá chó phương Bắc (cá nước ngọt, thịt trắng, ít béo) — GIẢ ĐỊNH
    ("snakehead", "Cá lóc", "Northern pike, raw (used for snakehead)", 173680, "protein", ["animal", "fish", "allergen:fish"], 50, 250, 10, None, "LD"),  # Fish, pike, northern, raw
    ("anchovy", "Cá cơm tươi", "European anchovy, raw", 174182, "protein", ["animal", "fish", "allergen:fish"], 30, 150, 10, None, "LD"),  # Fish, anchovy, european, raw
    ("duck_egg", "Trứng vịt", "Duck egg", 172189, "protein", ["animal", "egg", "allergen:egg"], 70, 140, 70, None, "BLD"),  # Egg, duck, whole, fresh, raw
    ("fried_tofu", "Đậu hũ chiên", "Fried tofu", 172451, "protein", ["allergen:soy"], 50, 200, 10, None, "BLD"),  # Tofu, fried
    ("fresh_rice_noodles", "Bánh phở / bún tươi", "Rice noodles, cooked (fresh)", 168914, "carb", [], 100, 400, 10, None, "BLD"),  # Rice noodles, cooked
    ("glutinous_rice", "Gạo nếp", "Glutinous rice, raw", 168883, "carb", [], 40, 150, 10, None, "BLD"),  # Rice, white, glutinous, unenriched, uncooked
    ("onion", "Hành tây", "Onions, raw", 170000, "vegetable", [], 20, 150, 10, None, "LD"),  # Onions, raw
    ("malabar_spinach", "Mồng tơi", "Malabar spinach (vine spinach)", 170474, "vegetable", [], 50, 250, 10, None, "LD"),  # Vinespinach, (basella), raw
    ("bamboo_shoots", "Măng tươi", "Bamboo shoots, raw", 169210, "vegetable", [], 50, 200, 10, None, "LD"),  # Bamboo shoots, raw
    ("straw_mushroom", "Nấm rơm", "Straw mushrooms, canned, drained", 168582, "vegetable", [], 50, 200, 10, None, "LD"),  # Mushrooms, straw, canned, drained solids
    ("shiitake", "Nấm hương tươi", "Shiitake mushrooms, raw", 169242, "vegetable", [], 20, 100, 10, None, "LD"),  # Mushrooms, shiitake, raw
    ("kohlrabi", "Su hào", "Kohlrabi, raw", 168424, "vegetable", [], 50, 250, 10, None, "LD"),  # Kohlrabi, raw
    ("jicama", "Củ đậu (củ sắn)", "Jicama, raw", 170073, "vegetable", [], 50, 250, 10, None, "BLD"),  # Yambean (jicama), raw
    ("lotus_root", "Củ sen", "Lotus root, raw", 169250, "vegetable", [], 50, 200, 10, None, "LD"),  # Lotus root, raw
    ("scallion", "Hành lá", "Scallions, raw", 170005, "vegetable", [], 5, 50, 5, None, ""),  # Onions, spring or scallions (includes tops and bulb), raw
    ("garlic", "Tỏi", "Garlic, raw", 169230, "vegetable", [], 5, 30, 5, None, ""),  # Garlic, raw
    ("ginger", "Gừng", "Ginger root, raw", 169231, "vegetable", [], 5, 30, 5, None, ""),  # Ginger root, raw
    ("lemongrass", "Sả", "Lemongrass, raw", 168573, "vegetable", [], 5, 30, 5, None, ""),  # Lemon grass (citronella), raw
    ("coriander", "Ngò (rau mùi)", "Coriander (cilantro) leaves, raw", 169997, "vegetable", [], 5, 30, 5, None, ""),  # Coriander (cilantro) leaves, raw
    ("chili", "Ớt", "Hot chili peppers, red, raw", 170106, "vegetable", [], 5, 30, 5, None, ""),  # Peppers, hot chili, red, raw
    ("lime", "Chanh", "Limes, raw", 168155, "fruit", [], 5, 50, 5, None, ""),  # Limes, raw
    ("pineapple", "Dứa (thơm, khóm)", "Pineapple, raw", 169124, "fruit", [], 80, 250, 10, None, "BLD"),  # Pineapple, raw, all varieties
    ("longan", "Nhãn", "Longans, raw", 169089, "fruit", [], 50, 200, 10, None, "BLD"),  # Longans, raw
    ("pomelo", "Bưởi", "Pomelo, raw", 167754, "fruit", [], 80, 250, 10, None, "BLD"),  # Pummelo, raw
    ("jackfruit", "Mít", "Jackfruit, raw", 174687, "fruit", [], 50, 200, 10, None, "BLD"),  # Jackfruit, raw
]

# --- Đồ ăn vặt (slot "S" = ngoài bữa chính; planner không tự chọn, chỉ dùng khi người dùng muốn ăn) ---
# Tag dị ứng của đồ chế biến sẵn là GIẢ ĐỊNH BẢO THỦ theo công thức phổ biến; người dùng vẫn cần đọc nhãn.
# portion: khẩu phần chuẩn lấy từ USDA food_portion.csv (build script kiểm tra tồn tại).
# (code, name_vi, name_en, fdc_id, tags, portion_description, portion_g)
SNACKS: list[tuple] = [
    ("ice_cream_vanilla", "Kem vani", "Vanilla ice cream", 167575, ["animal", "dairy", "allergen:milk", "allergen:egg"], "1/2 cup", 66),
    ("ice_cream_chocolate", "Kem sô-cô-la", "Chocolate ice cream", 168809, ["animal", "dairy", "allergen:milk", "allergen:egg"], "0.5 cup (4 fl oz)", 66),
    ("milk_chocolate", "Sô-cô-la sữa", "Milk chocolate", 167587, ["animal", "dairy", "allergen:milk", "allergen:soy"], "1 bar (1.55 oz)", 44),
    ("dark_chocolate", "Sô-cô-la đen 70–85%", "Dark chocolate 70-85%", 170273, ["allergen:soy", "allergen:milk"], "1 oz", 28.35),
    ("butter_cookies", "Bánh quy bơ", "Butter cookies", 172819, ["animal", "dairy", "gluten", "allergen:gluten", "allergen:wheat", "allergen:milk", "allergen:egg"], "1 oz", 28.35),
    ("choc_chip_cookies", "Bánh quy sô-cô-la chip", "Chocolate chip cookies", 172820, ["animal", "dairy", "gluten", "allergen:gluten", "allergen:wheat", "allergen:milk", "allergen:egg", "allergen:soy"], "1 oz", 28.35),
    ("potato_chips", "Snack khoai tây", "Potato chips, salted", 169677, [], "1 oz", 28.35),
    ("sponge_cake", "Bánh bông lan", "Sponge cake", 172706, ["animal", "gluten", "allergen:gluten", "allergen:wheat", "allergen:egg", "allergen:milk"], "1 piece (1/12 of 16 oz cake)", 38),
    ("chocolate_cake", "Bánh kem sô-cô-la", "Chocolate cake with frosting", 174934, ["animal", "dairy", "gluten", "allergen:gluten", "allergen:wheat", "allergen:egg", "allergen:milk", "allergen:soy"], "1 piece (1/8 of 18 oz cake)", 64),
    ("cola", "Nước ngọt có ga (cola)", "Cola", 174852, [], "1 can or bottle (12 fl oz)", 370),
    ("croissant", "Bánh sừng bò", "Butter croissant", 174987, ["animal", "dairy", "gluten", "allergen:gluten", "allergen:wheat", "allergen:milk", "allergen:egg"], "1 croissant, medium", 57),
    ("popcorn", "Bắp rang (không bơ)", "Popcorn, air-popped", 167959, [], "1 oz", 28.35),
    ("vanilla_pudding", "Pudding vani", "Vanilla pudding", 169608, ["animal", "dairy", "allergen:milk"], "1 container refrigerated 4 oz", 110),
    ("french_fries", "Khoai tây chiên", "French fries", 170698, [], "1 serving medium", 117),
    ("fried_chicken", "Gà rán", "Fried chicken breast with skin & breading", 170756, ["animal", "meat", "poultry", "gluten", "allergen:gluten", "allergen:wheat", "allergen:egg", "allergen:milk"], "1 breast, bone and skin removed", 107),
    ("cheese_pizza", "Pizza phô mai", "Cheese pizza", 170317, ["animal", "dairy", "gluten", "allergen:gluten", "allergen:wheat", "allergen:milk"], "1 serving 9 servings per 24 oz package", 81),
    ("cheeseburger", "Hamburger phô mai", "Cheeseburger", 170690, ["animal", "meat", "beef", "dairy", "gluten", "allergen:gluten", "allergen:wheat", "allergen:milk", "allergen:sesame"], "1 sandwich", 91),
    ("banana_chips", "Chuối sấy", "Banana chips", 168849, [], "1 oz", 28.35),
    ("orange_drink", "Nước cam đóng hộp", "Orange juice drink", 169044, [], "1 cup", 249),
    ("coconut_water", "Nước dừa", "Coconut water", 170174, [], "1 cup", 240),  # Nuts, coconut water (liquid from coconuts)
    ("condensed_milk", "Sữa đặc có đường", "Sweetened condensed milk", 171275, ["animal", "dairy", "allergen:milk"], "1 fl oz", 38.2),  # Milk, canned, condensed, sweetened
]

# Từ đồng nghĩa tiếng Việt cho chatbot (so khớp cụm dài nhất, không phân biệt dấu).
ALIASES: dict[str, list[str]] = {
    "chicken_breast": ["ức gà", "gà", "thịt gà", "lườn gà"],
    "chicken_thigh": ["đùi gà", "má đùi gà"],
    "beef_lean": ["bò", "thịt bò", "bò băm"],
    "pork_tenderloin": ["heo", "lợn", "thịt heo", "thịt lợn", "thăn heo", "thăn lợn"],
    "salmon": ["cá hồi"],
    "tuna": ["cá ngừ"],
    "catfish": ["cá tra", "cá basa", "cá ba sa", "cá da trơn", "cá kho"],
    "tilapia": ["cá rô phi", "cá diêu hồng"],
    "mackerel": ["cá thu"],
    "shrimp": ["tôm"],
    "squid": ["mực"],
    "egg": ["trứng", "trứng gà"],
    "tofu": ["đậu hũ", "đậu phụ", "tàu hũ"],
    "lentils": ["đậu lăng"],
    "mung_beans": ["đậu xanh"],
    "black_beans": ["đậu đen"],
    "white_rice": ["cơm", "cơm trắng", "gạo"],
    "brown_rice": ["gạo lứt", "cơm gạo lứt"],
    "rice_noodles": ["bún", "phở", "hủ tiếu"],
    "glass_noodles": ["miến"],
    "wholewheat_bread": ["bánh mì nguyên cám"],
    "baguette": ["bánh mì"],
    "oats": ["yến mạch"],
    "sweet_potato": ["khoai lang"],
    "potato": ["khoai tây"],
    "corn": ["bắp", "ngô"],
    "taro": ["khoai môn"],
    "banana": ["chuối"], "orange": ["cam"], "apple": ["táo"], "papaya": ["đu đủ"], "guava": ["ổi"],
    "mango": ["xoài"], "watermelon": ["dưa hấu"],
    "milk_lowfat": ["sữa", "sữa tươi"], "yogurt_lowfat": ["sữa chua"], "soymilk": ["sữa đậu nành"],
    "peanuts": ["đậu phộng", "lạc"], "cashews": ["hạt điều"],
    "broccoli": ["bông cải", "súp lơ"], "spinach": ["cải bó xôi", "rau bina"], "cabbage": ["bắp cải"],
    "carrot": ["cà rốt"], "tomato": ["cà chua"], "cucumber": ["dưa leo", "dưa chuột"],
    "bitter_melon": ["khổ qua", "mướp đắng"], "eggplant": ["cà tím"], "mushroom": ["nấm"],
    "pumpkin": ["bí đỏ"], "winter_melon": ["bí đao"], "bok_choy": ["cải thìa"], "mustard_greens": ["cải xanh"],
    "ice_cream_vanilla": ["kem", "kem vani", "kem vanilla"],
    "ice_cream_chocolate": ["kem sô-cô-la", "kem socola", "kem chocolate"],
    "milk_chocolate": ["sô-cô-la", "socola", "chocolate", "sô cô la"],
    "dark_chocolate": ["sô-cô-la đen", "socola đen", "chocolate đen"],
    "butter_cookies": ["bánh quy", "bánh quy bơ"],
    "choc_chip_cookies": ["bánh quy sô-cô-la", "cookie"],
    "potato_chips": ["snack", "bim bim", "snack khoai tây"],
    "sponge_cake": ["bánh bông lan"],
    "chocolate_cake": ["bánh kem", "bánh sinh nhật"],
    "cola": ["nước ngọt", "coca", "cola", "pepsi"],
    "croissant": ["bánh sừng bò", "croissant"],
    "popcorn": ["bắp rang", "bỏng ngô"],
    "vanilla_pudding": ["pudding"],
    "french_fries": ["khoai tây chiên"],
    "fried_chicken": ["gà rán", "gà chiên giòn", "kfc"],
    "cheese_pizza": ["pizza"],
    "cheeseburger": ["hamburger", "burger"],
    "banana_chips": ["chuối sấy"],
    "orange_drink": ["nước cam"],
    # --- vòng 7 (gồm từ địa phương) ---
    "pork_belly": ["ba chỉ", "thịt ba chỉ", "ba rọi", "thịt ba rọi"],
    "pork_ribs": ["sườn", "sườn heo", "sườn non", "sườn lợn"],
    "pork_ground": ["thịt xay", "thịt băm", "thịt bằm", "heo xay", "thịt heo xay", "thịt lợn xay"],
    "chicken_whole": ["gà ta", "gà luộc", "thịt gà có da", "gà nguyên con"],
    "chicken_liver": ["gan gà"],
    "beef_sirloin": ["bò thăn", "thịt bò thăn", "bò bít tết", "thăn bò"],
    "crab": ["cua", "cua biển", "ghẹ"],
    "clam": ["nghêu", "ngao"],
    "snakehead": ["cá lóc", "cá quả", "cá chuối"],
    "anchovy": ["cá cơm"],
    "duck_egg": ["trứng vịt"],
    "fried_tofu": ["đậu hũ chiên", "đậu phụ rán", "tàu hũ chiên", "đậu rán"],
    "fresh_rice_noodles": ["bánh phở", "bún tươi", "phở tươi", "sợi phở"],
    "glutinous_rice": ["gạo nếp", "nếp", "xôi"],
    "onion": ["hành tây"],
    "malabar_spinach": ["mồng tơi", "rau mồng tơi"],
    "bamboo_shoots": ["măng", "măng tươi"],
    "straw_mushroom": ["nấm rơm"],
    "shiitake": ["nấm hương", "nấm đông cô"],
    "kohlrabi": ["su hào"],
    "jicama": ["củ đậu", "củ sắn"],
    "lotus_root": ["củ sen"],
    "scallion": ["hành lá", "hành", "hành hoa"],
    "garlic": ["tỏi"],
    "ginger": ["gừng"],
    "lemongrass": ["sả"],
    "coriander": ["ngò", "ngò rí", "rau mùi"],
    "chili": ["ớt"],
    "lime": ["chanh"],
    "pineapple": ["dứa", "trái thơm", "quả thơm", "khóm", "trái khóm"],  # không dùng "thơm" trơn (= mùi thơm)
    "longan": ["quả nhãn", "trái nhãn", "nhãn lồng"],  # không dùng "nhãn" trơn (= nhãn sản phẩm)
    "pomelo": ["bưởi"],
    "jackfruit": ["mít"],
    "coconut_water": ["nước dừa"],
    "condensed_milk": ["sữa đặc", "sữa ông thọ"],
}


# Từ đồng nghĩa tiếng Anh (ngắn gọn, món hay gặp). Ngoài ra matching tự sinh alias từ name_en
# (phần trước dấu phẩy, viết thường). build_ingredients.py gộp ALIASES + ALIASES_EN vào trường `aliases`.
ALIASES_EN: dict[str, list[str]] = {
    "chicken_breast": ["chicken", "chicken breast", "grilled chicken"],
    "chicken_thigh": ["chicken thigh", "chicken thighs"],
    "beef_lean": ["beef", "ground beef", "minced beef", "steak"],
    "pork_tenderloin": ["pork", "pork loin", "pork tenderloin"],
    "salmon": ["salmon"],
    "tuna": ["tuna"],
    "catfish": ["fish", "catfish", "basa", "pangasius"],
    "tilapia": ["tilapia"],
    "mackerel": ["mackerel"],
    "shrimp": ["shrimp", "shrimps", "prawn", "prawns"],
    "squid": ["squid", "calamari"],
    "egg": ["egg", "eggs"],
    "tofu": ["tofu", "bean curd"],
    "lentils": ["lentil", "lentils"],
    "white_rice": ["rice", "white rice", "steamed rice"],
    "brown_rice": ["brown rice"],
    "rice_noodles": ["noodles", "rice noodles", "pho", "vermicelli"],
    "glass_noodles": ["glass noodles"],
    "baguette": ["bread", "baguette", "banh mi"],
    "oats": ["oats", "oatmeal", "porridge"],
    "sweet_potato": ["sweet potato", "sweet potatoes"],
    "potato": ["potato", "potatoes"],
    "corn": ["corn"],
    "banana": ["banana", "bananas"], "orange": ["orange", "oranges"], "apple": ["apple", "apples"],
    "mango": ["mango", "mangoes"], "watermelon": ["watermelon"],
    "milk_lowfat": ["milk"], "yogurt_lowfat": ["yogurt", "yoghurt"], "soymilk": ["soy milk", "soymilk"],
    "peanuts": ["peanut", "peanuts"], "cashews": ["cashew", "cashews"],
    "broccoli": ["broccoli"], "spinach": ["spinach"], "carrot": ["carrot", "carrots"],
    "tomato": ["tomato", "tomatoes"], "mushroom": ["mushroom", "mushrooms"],
    "ice_cream_vanilla": ["ice cream", "ice creams", "vanilla ice cream"],
    "ice_cream_chocolate": ["chocolate ice cream"],
    "milk_chocolate": ["chocolate", "chocolate bar"],
    "dark_chocolate": ["dark chocolate"],
    "butter_cookies": ["cookies", "biscuits"],
    "choc_chip_cookies": ["chocolate chip cookie", "chocolate chip cookies"],
    "potato_chips": ["chips", "crisps", "potato chips"],
    "sponge_cake": ["sponge cake"],
    "chocolate_cake": ["cake", "birthday cake", "chocolate cake"],
    "cola": ["soda", "coke", "coca cola", "soft drink"],
    "popcorn": ["popcorn"],
    "french_fries": ["fries", "french fries"],
    "fried_chicken": ["fried chicken", "kfc"],
    "cheese_pizza": ["pizza", "pizzas"],
    "cheeseburger": ["burger", "burgers", "hamburger", "cheeseburger"],
    "banana_chips": ["banana chips"],
    "orange_drink": ["orange juice"],
    "pork_belly": ["pork belly"],
    "pork_ribs": ["pork ribs", "ribs", "spare ribs", "spareribs"],
    "pork_ground": ["ground pork", "minced pork"],
    "chicken_whole": ["whole chicken", "boiled chicken"],
    "chicken_liver": ["chicken liver", "chicken livers"],
    "beef_sirloin": ["sirloin", "beef sirloin"],
    "crab": ["crab", "crabs"],
    "clam": ["clam", "clams"],
    "snakehead": ["snakehead", "snakehead fish"],
    "anchovy": ["anchovy", "anchovies"],
    "duck_egg": ["duck egg", "duck eggs"],
    "fried_tofu": ["fried tofu"],
    "fresh_rice_noodles": ["fresh rice noodles", "pho noodles"],
    "glutinous_rice": ["sticky rice", "glutinous rice"],
    "onion": ["onion", "onions"],
    "malabar_spinach": ["malabar spinach"],
    "bamboo_shoots": ["bamboo shoots", "bamboo shoot"],
    "straw_mushroom": ["straw mushrooms", "straw mushroom"],
    "shiitake": ["shiitake"],
    "kohlrabi": ["kohlrabi"],
    "jicama": ["jicama"],
    "lotus_root": ["lotus root"],
    "scallion": ["scallion", "scallions", "green onion", "green onions", "spring onion", "spring onions"],
    "garlic": ["garlic"],
    "ginger": ["ginger"],
    "lemongrass": ["lemongrass", "lemon grass"],
    "coriander": ["cilantro", "coriander"],
    "chili": ["chili", "chilli", "chili pepper"],
    "lime": ["lime", "limes"],
    "pineapple": ["pineapple"],
    "longan": ["longan", "longans"],
    "pomelo": ["pomelo"],
    "jackfruit": ["jackfruit"],
    "coconut_water": ["coconut water"],
    "condensed_milk": ["condensed milk"],
}


# Tên hiển thị tiếng Anh ngắn, tự nhiên (name_en là mô tả USDA, giữ làm dữ liệu nguồn).
DISPLAY_EN: dict[str, str] = {
    "chicken_breast": "Chicken breast",
    "chicken_thigh": "Chicken thigh",
    "beef_lean": "Lean ground beef",
    "pork_tenderloin": "Pork tenderloin",
    "salmon": "Salmon",
    "tuna": "Tuna",
    "catfish": "Catfish (basa)",
    "tilapia": "Tilapia",
    "mackerel": "Mackerel",
    "shrimp": "Shrimp",
    "squid": "Squid",
    "egg": "Eggs",
    "tofu": "Tofu",
    "lentils": "Lentils",
    "mung_beans": "Mung beans",
    "black_beans": "Black beans",
    "white_rice": "White rice",
    "brown_rice": "Brown rice",
    "rice_noodles": "Rice noodles",
    "glass_noodles": "Glass noodles",
    "wholewheat_bread": "Whole-wheat bread",
    "baguette": "Baguette",
    "oats": "Oats",
    "sweet_potato": "Sweet potato",
    "potato": "Potato",
    "corn": "Sweet corn",
    "taro": "Taro",
    "bok_choy": "Bok choy",
    "mustard_greens": "Mustard greens",
    "napa_cabbage": "Napa cabbage",
    "sweet_potato_leaves": "Sweet potato leaves",
    "spinach": "Spinach",
    "broccoli": "Broccoli",
    "cabbage": "Cabbage",
    "carrot": "Carrot",
    "tomato": "Tomato",
    "cucumber": "Cucumber",
    "green_beans": "Green beans",
    "pumpkin": "Pumpkin",
    "bitter_melon": "Bitter melon",
    "eggplant": "Eggplant",
    "bean_sprouts": "Bean sprouts",
    "mushroom": "Mushrooms",
    "okra": "Okra",
    "lettuce": "Lettuce",
    "chayote": "Chayote",
    "winter_melon": "Winter melon",
    "banana": "Banana",
    "orange": "Orange",
    "apple": "Apple",
    "papaya": "Papaya",
    "guava": "Guava",
    "mango": "Mango",
    "watermelon": "Watermelon",
    "milk_lowfat": "Low-fat milk",
    "yogurt_lowfat": "Plain low-fat yogurt",
    "soymilk": "Unsweetened soy milk",
    "peanuts": "Peanuts",
    "cashews": "Cashews",
    "soybean_oil": "Soybean oil",
    "olive_oil": "Olive oil",
    "ice_cream_vanilla": "Vanilla ice cream",
    "ice_cream_chocolate": "Chocolate ice cream",
    "milk_chocolate": "Milk chocolate",
    "dark_chocolate": "Dark chocolate (70–85%)",
    "butter_cookies": "Butter cookies",
    "choc_chip_cookies": "Chocolate chip cookies",
    "potato_chips": "Potato chips",
    "sponge_cake": "Sponge cake",
    "chocolate_cake": "Chocolate cake",
    "cola": "Cola",
    "croissant": "Croissant",
    "popcorn": "Popcorn",
    "vanilla_pudding": "Vanilla pudding",
    "french_fries": "French fries",
    "fried_chicken": "Fried chicken",
    "cheese_pizza": "Cheese pizza",
    "cheeseburger": "Cheeseburger",
    "banana_chips": "Banana chips",
    "orange_drink": "Orange juice drink",
    "pork_belly": "Pork belly", "pork_ribs": "Pork ribs", "pork_ground": "Ground pork",
    "chicken_whole": "Chicken (with skin)", "chicken_liver": "Chicken liver", "beef_sirloin": "Beef sirloin",
    "crab": "Crab", "clam": "Clams", "snakehead": "Snakehead fish", "anchovy": "Fresh anchovies",
    "duck_egg": "Duck eggs", "fried_tofu": "Fried tofu", "fresh_rice_noodles": "Fresh rice noodles",
    "glutinous_rice": "Sticky rice", "onion": "Onion", "malabar_spinach": "Malabar spinach",
    "bamboo_shoots": "Bamboo shoots", "straw_mushroom": "Straw mushrooms", "shiitake": "Shiitake mushrooms",
    "kohlrabi": "Kohlrabi", "jicama": "Jicama", "lotus_root": "Lotus root", "scallion": "Scallions",
    "garlic": "Garlic", "ginger": "Ginger", "lemongrass": "Lemongrass", "coriander": "Cilantro",
    "chili": "Chili", "lime": "Lime", "pineapple": "Pineapple", "longan": "Longan", "pomelo": "Pomelo",
    "jackfruit": "Jackfruit", "coconut_water": "Coconut water", "condensed_milk": "Sweetened condensed milk",
}
