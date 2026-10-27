"""English display strings. Same keys and placeholders as vi.py (enforced by tests/core/test_i18n.py)."""

EN: dict[str, str] = {
    # ---------- API errors ----------
    "error.ALLERGEN_CONFLICT": "This ingredient conflicts with your allergies or diet.",
    "error.ALLERGEN_CONFLICT.item": "Can't add {food}: it conflicts with the {reason} you declared.",
    "error.ALLERGEN_CONFLICT.custom": "This product conflicts with the {reason} you declared.",
    "error.ALLERGEN_CONFLICT.proposal": "This suggestion contains an ingredient that no longer fits your profile.",
    "error.BAD_CREDENTIALS": "Incorrect email or password.",
    "error.CONFIRMATION_REQUIRED": "You need to confirm that you have consulted a healthcare professional.",
    "error.DAYS_RANGE.view": "You can view 1–14 days at a time.",
    "error.DAYS_RANGE.generate": "You can create 1–7 days at a time.",
    "error.DELTA_RANGE": "Each adjustment must be between 1 and 500 g.",
    "error.ED_SUPPORT": (
        "It seems you may be feeling pressure around eating. You don't need to cut back any further. "
        "If things feel hard, consider talking to someone close to you, a doctor, a registered dietitian or a "
        "mental health professional. The app will pause suggestions that reduce your energy intake."
    ),
    "error.EMAIL_EXISTS": "This email is already registered.",
    "error.EXPERT_CONFIRMATION_REQUIRED":
        "Please confirm you have consulted a professional and enter safe limits before creating a menu.",
    "error.FOOD_NOT_FOUND": "This ingredient is not in the database.",
    "error.GRAMS_RANGE": "Amount must be between 1 and 3000 g.",
    "error.HTTP": "Invalid request.",
    "error.INTERNAL": "Something went wrong.",
    "error.INVALID_REFRESH": "Your session has expired.",
    "error.INVALID_TOKEN": "Your session is invalid or has expired.",
    "error.ITEM_NOT_FOUND": "Ingredient not found in this meal.",
    "error.LIMITS_REQUIRED": "Enter at least one limit provided by your professional (e.g. sodium, protein, potassium).",
    "error.LOW_ENERGY_ACK_REQUIRED": (
        "A target of {requested_kcal} kcal is below the safe minimum of ~{floor_kcal} kcal/day. "
        "Please confirm explicitly if you still want to continue (consulting a professional is recommended)."
    ),
    "error.MEAL_NOT_FOUND": "Meal not found.",
    "error.MENU_NOT_FOUND": "No menu for this day yet.",
    "error.MESSAGE_LENGTH": "Messages must be 1–1000 characters.",
    "error.NOT_SENSITIVE_CONDITION": "This condition does not require professional confirmation.",
    "error.PANTRY_ITEM": "Pantry items are edited in the “Pantry” list.",
    "error.PROFILE_REQUIRED": "Please fill in your health profile first.",
    "error.PROPOSAL_APPLIED": "This suggestion has already been applied.",
    "error.PROPOSAL_EXPIRED": "This suggestion has expired. Please ask the chatbot again.",
    "error.PROPOSAL_NOT_FOUND": "Suggestion not found.",
    "error.RATE_LIMITED": "Too many attempts. Please try again in {retry_after_s} seconds.",
    "error.ROTATION_VIOLATION": "The main dish would repeat more than 3 days in a row.",
    "error.STALE_PROPOSAL": "Your menu changed after this suggestion was made. Please ask the chatbot again.",
    "error.UNAUTHENTICATED": "Please log in.",
    "error.VALIDATION_ERROR": "Invalid data.",

    # ---------- Exclusion reasons ----------
    "reason.allergy": "{name} allergy",
    "reason.diet": "{name} diet",
    "reason.unknown": "allergies or diet",
    "allergen.peanut": "peanut",
    "allergen.tree_nut": "tree nut",
    "allergen.milk": "milk",
    "allergen.egg": "egg",
    "allergen.fish": "fish",
    "allergen.shellfish": "shellfish",
    "allergen.soy": "soy",
    "allergen.wheat": "wheat",
    "allergen.gluten": "gluten",
    "allergen.sesame": "sesame",
    "diet.vegetarian": "vegetarian (eggs/dairy OK)",
    "diet.vegan": "vegan",
    "diet.halal": "halal",
    "diet.gluten_free": "gluten-free",
    "diet.no_pork": "no-pork",
    "diet.no_beef": "no-beef",
    "condition.diabetes_t1": "type 1 diabetes",
    "condition.diabetes_t2": "type 2 diabetes",
    "condition.hypertension": "high blood pressure",
    "condition.kidney": "kidney disease",
    "condition.cardio": "cardiovascular disease",
    "condition.liver": "liver disease",
    "condition.pregnant": "pregnancy",
    "condition.lactating": "breastfeeding",
    "nutrient.energy_kcal": "energy",
    "nutrient.protein_g": "protein",
    "nutrient.carb_g": "carbohydrate",
    "nutrient.fat_g": "fat",
    "nutrient.fiber_g": "fiber",
    "nutrient.calcium_mg": "calcium",
    "nutrient.iron_mg": "iron",
    "nutrient.zinc_mg": "zinc",
    "nutrient.vitamin_d_ug": "vitamin D",
    "nutrient.sodium_mg": "sodium",
    "nutrient.potassium_mg": "potassium",
    "nutrient.phosphorus_mg": "phosphorus",
    "slot.breakfast": "Breakfast",
    "slot.lunch": "Lunch",
    "slot.dinner": "Dinner",
    "slot.snack": "Snacks",

    # ---------- Validation ----------
    "validation.invalid": "Invalid value.",
    "validation.invalid_field": "{field} is invalid.",
    "validation.invalid_values": "Invalid values: {values}.",
    "validation.not_number": "{field} must be a number.",
    "validation.max_decimals": "{field} can have at most {n} decimal place(s).",
    "validation.age_integer": "Age must be a whole number.",
    "validation.age_range": "Age must be between 18 and 100 (the Mifflin-St Jeor equation applies to adults).",
    "validation.height_range": "Height must be between 120 and 230 cm.",
    "validation.weight_range": "Weight must be between 30 and 300 kg.",
    "validation.custom_kcal_range":
        "Energy target must be between 800 and 5000 kcal. Diets under 800 kcal/day require medical supervision.",
    "validation.diabetes_both": "You can't select both type 1 and type 2 diabetes.",
    "validation.pregnancy_sex": "Pregnancy/breastfeeding doesn't match the selected sex.",
    "validation.label_macro_sum": "Protein + carbs + fat can't exceed 100 g per 100 g.",
    "validation.label_energy_mismatch":
        "Energy doesn't match protein/carbs/fat (more than 20% off). Please check the label again.",
    "validation.missing": "This field is required.",
    "validation.greater_than": "Must be greater than {gt}.",
    "validation.greater_than_equal": "Must be at least {ge}.",
    "validation.less_than": "Must be less than {lt}.",
    "validation.less_than_equal": "Must be at most {le}.",
    "validation.string_too_short": "Must be at least {min_length} characters.",
    "validation.string_too_long": "Must be at most {max_length} characters.",
    "validation.too_short": "Must have at least {min_length} item(s).",
    "validation.too_long": "Must have at most {max_length} item(s).",
    "validation.int_parsing": "Must be a whole number.",
    "validation.int_type": "Must be a whole number.",
    "validation.int_from_float": "Must be a whole number.",
    "validation.float_parsing": "Must be a number.",
    "validation.float_type": "Must be a number.",
    "validation.bool_parsing": "Must be true or false.",
    "validation.bool_type": "Must be true or false.",
    "validation.string_type": "Must be text.",
    "validation.list_type": "Must be a list.",
    "validation.enum": "Invalid choice.",
    "validation.literal_error": "Invalid choice.",
    "validation.extra_forbidden": "This field is not supported.",
    "validation.date_parsing": "Invalid date.",
    "validation.date_from_datetime_parsing": "Invalid date.",
    "validation.uuid_parsing": "Invalid ID.",
    "validation.json_invalid": "Invalid JSON.",
    "validation.value_error": "Invalid value.",
    "field.height": "Height",
    "field.weight": "Weight",

    # ---------- Medical notices ----------
    "notice.DISCLAIMER": (
        "This app does not diagnose any illness and does not replace a doctor or registered dietitian. "
        "Menus are for reference only."
    ),
    "notice.CONSULT_DOCTOR_INSULIN": (
        "You are taking insulin or glucose-lowering medication: consult your doctor before changing your diet. "
        "The app does not give insulin or medication doses."
    ),
    "notice.SODIUM_SEASONING": "Sodium from added salt or fish sauce is not counted. Season lightly.",
    "support.message": (
        "It seems you may be feeling pressure around eating. You don't need to cut back any further. "
        "If things feel hard, consider talking to someone close to you, a doctor, a registered dietitian or a "
        "mental health professional. The app will pause suggestions that reduce your energy intake."
    ),

    # ---------- Nutrition needs: sources, applies-to, notes, assumptions ----------
    "ref.applies.male": "male, {age} years",
    "ref.applies.female": "female, {age} years",
    "ref.applies.adults": "adults",
    "ref.applies.athletes": "people who exercise",
    "ref.expert_limit": "Limit provided by the user's healthcare professional",
    "ref.activity_source": "Common PAL factors (McArdle, Katch & Katch, Exercise Physiology) — assumption",
    "ref.energy_floor_source":
        "NHLBI Obesity Education Initiative 1998 (assumed 1200 women / 1500 men, needs verification)",
    "ref.sodium_source": "NASEM. Dietary Reference Intakes for Sodium and Potassium. 2019 (CDRR, age 14+)",
    "ref.sodium_htn_source":
        "American Heart Association – ideal limit ≤1500 mg/day, especially for people with high blood pressure",
    "ref.note.protein_gain": "1.6 g/kg/day",
    "ref.note.protein": "max(RDA 0.8 g/kg, 15% of energy) — 15% is a product assumption within the AMDR",
    "ref.note.amdr": "AMDR: carbohydrate 45–65%, fat 20–35% of energy",
    "ref.note.energy": "BMR={bmr} × factor {factor} = TDEE {tdee}; floor {floor} ({floor_source})",
    "ref.note.sodium": "Only sodium in ingredients is counted; added salt/fish sauce is NOT counted",
    "assumption.goal_energy": "Adjusting energy by goal (−15% / +10% TDEE) is a product assumption",
    "assumption.diabetes_carb": (
        "ADA Standards of Care: there is no ideal carbohydrate ratio for everyone. The app uses the lower AMDR bound "
        "(45%) and no less than 130 g/day (IOM RDA) — ASSUMPTION, needs professional review"
    ),
    "food.portion_default": "1 serving",

    # ---------- Chatbot ----------
    "chat.restrict": (
        "I don't suggest fasting, skipping meals or eating below a safe level. Your menu is already planned to give "
        "you the minimum energy you need (no less than {floor} kcal/day). If you want to lose weight, please talk "
        "to a doctor or registered dietitian."
    ),
    "chat.unknown_named": "{names}",
    "chat.unknown_any": "any food",
    "chat.need_label": (
        "I couldn't find {what} in the verified nutrition data, so I can't estimate it. "
        "You can enter the details from the product label (kcal, protein, carbs and fat per 100 g, plus the serving "
        "size) and I'll add it to your menu."
    ),
    "chat.help": (
        "You can tell me things like: “I want chicken”, “salmon for lunch today”, “I want 2 ice creams” "
        "or “it's my cheat day, I'm having pizza”. I'll adjust your menu accordingly."
    ),
    "chat.refusal": "I can't suggest {food} because it conflicts with the {reason} you declared.",
    "chat.blocked": (
        "You have a health condition that needs professional confirmation before the app can suggest menus "
        "({conditions}). Please complete the confirmation step in Settings."
    ),
    "chat.slot_not_in_plan": "{slot} isn't part of your plan (based on your activity level), so I used the closest meal.",
    "chat.day.today": "today",
    "chat.day.tomorrow": "tomorrow",
    "chat.day.selected": "the selected day",
    "chat.day.date": "{date}",
    "chat.date_fmt": "%m/%d",
    "chat.rotation_blocked": (
        "You've had {food} 3 days in a row; for variety, I haven't added it to {when}."
    ),
    "chat.no_dish_for": "There's no dish with {food} that fits your meals yet.",
    "chat.moved_to_slot": "{food} was placed at {slot}.",
    "chat.no_change": "I can't suggest any changes yet.",
    "chat.propose_around": "Here's a menu for {day} built around {foods}:",
    "chat.label.apply_plan": "Apply this menu",
    "chat.label.apply": "Apply",
    "chat.label.smaller": "Eat less: {desc} (~{kcal} kcal), stay on target",
    "chat.label.cheat_no_comp": "Cheat day: ~{kcal} kcal over, no compensation on later days",
    "chat.label.cheat": "Cheat day: ~{kcal} kcal over; compensate {spread}{forgiven}",
    "chat.none": "none",
    "chat.forgiven": "; the remaining ~{kcal} kcal is let go",
    "chat.snack_out_of_range": (
        "The amount of {food} you entered ({grams} g) is outside a reasonable range (at most {max} servings). "
        "Could you double-check it?"
    ),
    "chat.from_label": " (values you entered from the label)",
    "chat.no_cheat_needed": "This still fits within today's target, so no cheat day is needed.",
    "chat.absorbed": "I trimmed the main meals so {day} still meets the ~{kcal} kcal target:",
    "chat.too_much": (
        "If you eat this much, {day} will go over the ~{kcal} kcal target or the main meals would be too small. "
        "I don't suggest skipping main meals."
    ),
    "chat.cheat_head": "Cheat day — main meals still keep at least {pct}% of your energy:",
    "chat.comp_note": (
        "Compensation is limited to at most 10% per day for 3 days and never below your safe energy level; "
        "any remaining excess is let go."
    ),
    "chat.totals": "Total: ~{kcal} kcal (target ~{target}), protein {protein} g, carbs {carb} g, fat {fat} g.",
    "chat.short.below": "⚠ Low in {what} ({pct}% below target).{add}",
    "chat.short.above": "⚠ Over on {what} ({pct}% above target).",
    "chat.short.add": " You could add: {foods}.",

    # ---------- Recipes (template + LLM prompt) ----------
    "recipe.season.garlic": "Garlic",
    "recipe.season.garlic.note": "Stir-fry until fragrant before adding the main ingredient",
    "recipe.season.scallion": "Spring onion",
    "recipe.season.scallion.note": "Sprinkle on when almost done",
    "recipe.season.pepper": "Black pepper",
    "recipe.season.pepper.note": "Sprinkle on after cooking",
    "recipe.season.ginger": "Ginger",
    "recipe.season.ginger.note": "Removes the fishy smell from fish and chicken",
    "recipe.season.fish_sauce": "Fish sauce",
    "recipe.season.fish_sauce.note": "Season lightly",
    "recipe.season.salt": "Salt",
    "recipe.season.salt.note": "Season to taste",
    "recipe.season.salt.note.low_sodium": "Use very little",
    "recipe.default_dish": "the meal",
    "recipe.step.prep": "Prepare and wash all ingredients, then drain.",
    "recipe.step.main": "Cook the main part of {dish} (pan-sear, steam, boil or braise) with the measured oil.",
    "recipe.step.veg": "Boil or quickly stir-fry the vegetables to keep their colour and fibre.",
    "recipe.step.starch": "Cook the starch (rice, rice noodles, potatoes...) the usual way.",
    "recipe.tip": "Prefer steaming, boiling or pan-searing with little oil.",
    "recipe.tip.low_sodium": "Go easy on salt and dipping sauces.",
    "recipe.none": "none",
    "recipe.low_sodium_hint": "The user needs a low-sodium meal.",
    "recipe.user": "Dish: {dish}\nIngredients: {ingredients}\nForbidden ingredients: {banned}\n{low_sodium}",
    "recipe.system": (
        "You are a Vietnamese home cook. Write short cooking instructions in English for the given meal. "
        "RULES: use only the listed ingredients plus basic seasonings; do NOT write any amounts, weights, kcal, "
        "grams, ml, cups, tablespoons or teaspoons (the system already measured everything); give no medical advice; "
        "strictly avoid every forbidden ingredient listed. Prefer steaming, boiling or pan-searing with little oil."
    ),
}
