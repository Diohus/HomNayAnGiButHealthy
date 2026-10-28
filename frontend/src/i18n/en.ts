import type { Dict, HelpSection } from "./vi";

// English UI strings. Same keys as vi.ts (enforced by the Dict type and i18n.test.ts).
export const en: Dict = {
  appName: "Hôm Nay Ăn Gì",
  login: "Log in",
  register: "Sign up",
  logout: "Log out",
  email: "Email",
  password: "Password (8+ characters)",
  noAccount: "No account yet? Sign up",
  haveAccount: "Already have an account? Log in",
  nav: { today: "Today", week: "Week", chat: "Chat", pantry: "Pantry", shopping: "Shopping", profile: "Profile", settings: "Settings" },
  disclaimerAccept: "I understand this app does not replace a doctor or registered dietitian",
  profile: {
    title: "Health profile",
    sex: "Sex", male: "Male", female: "Female",
    age: "Age", height: "Height (cm)", weight: "Weight (kg)",
    activity: "Activity level",
    activities: {
      sedentary: "Sedentary (2 meals)", light: "Light, 1–3 sessions/week (2 meals)",
      moderate: "Moderate, 3–5 sessions/week (3 meals)", active: "Active, 6–7 sessions/week (3 meals)",
      very_active: "Very active / manual labor (3 meals)",
    },
    goal: "Goal",
    goals: { lose: "Lose weight", maintain: "Maintain weight", gain_muscle: "Build muscle" },
    conditions: "Health conditions",
    conditionNames: {
      diabetes_t1: "Type 1 diabetes", diabetes_t2: "Type 2 diabetes", hypertension: "High blood pressure",
      kidney: "Kidney disease", cardio: "Cardiovascular disease", liver: "Liver disease", pregnant: "Pregnant",
      lactating: "Breastfeeding",
    },
    meds: "Taking insulin or glucose-lowering medication",
    allergies: "Allergies",
    allergenNames: {
      peanut: "Peanuts", tree_nut: "Tree nuts", milk: "Milk", egg: "Eggs", fish: "Fish", shellfish: "Shellfish",
      soy: "Soy", wheat: "Wheat", gluten: "Gluten", sesame: "Sesame",
    },
    diets: "Diet",
    dietNames: {
      vegetarian: "Vegetarian (eggs/dairy OK)", vegan: "Vegan", halal: "Halal (no pork)",
      gluten_free: "Gluten-free", no_pork: "No pork", no_beef: "No beef",
    },
    customKcal: "Custom energy target (leave blank to calculate)",
    lowEnergyAck: "I confirm I want a target below the safe minimum",
    selfManagedHelp: "No doctor monitors this app. With this condition, menus are only suggestions and may be "
      + "inaccurate. If your doctor gave you limits (protein, sodium, potassium…), enter them so menus follow them.",
    selfManaged: "I understand and manage my own diet",
    limitsLink: "Enter my health limits",
    save: "Save profile",
    saved: "Saved",
  },
  needs: {
    title: "Daily needs", source: "Source", appliesTo: "Applies to", bmr: "BMR", tdee: "TDEE",
    mealsPerDay: "{n} meals/day", assumption: "Assumption: {text}",
    limitsReduceEnergy: "The carb/fat limits you entered make your energy target lower than usual.",
  },
  today: {
    today: "Today", prevDay: "Previous day", nextDay: "Next day",
    generate: "Create menu", regenerate: "Regenerate", empty: "No menu for this day yet.",
    remaining: "left", over: "over", recipe: "How to cook", unlock: "Unpin",
    shortfall: "Targets not met", suggest: "Could add",
    below: "Low in", above: "Over on",
    conflicts: "Some constraints conflict: {list}. The menu below is the best possible option.",
    energyAdjusted: "This day's target was adjusted by {kcal} kcal (cheat-day compensation).",
    tags: { pantry: "pantry", snack: "snack", adjusted: "adjusted", aiEstimate: "AI estimate · high uncertainty", estimate: "estimate" },
    swap: "Swap dish",
    eaten: "Eaten",
    usedDisliked: "This meal had to use something you dislike because no other suitable option was left.",
    ringAria: "Eaten {eaten} / target {target} kcal; full-day plan {planned} kcal",
    eatenOf: "eaten {eaten}/{target}",
    decrease: "Decrease {name}", increase: "Increase {name}",
    seasonings: "Seasonings: {list}",
    sourceLlm: "Suggested by AI", sourceTemplate: "Template recipe",
  },
  slots: { breakfast: "Breakfast", lunch: "Lunch", dinner: "Dinner", snack: "Snacks" },
  macros: { energy_kcal: "Energy", protein_g: "Protein", carb_g: "Carbs", fat_g: "Fat", fiber_g: "Fiber" },
  nutrients: {
    energy_kcal: "energy", protein_g: "protein", carb_g: "carbs", fat_g: "fat", fiber_g: "fiber",
    calcium_mg: "calcium", iron_mg: "iron", zinc_mg: "zinc", vitamin_d_ug: "vitamin D", sodium_mg: "sodium",
    potassium_mg: "potassium", phosphorus_mg: "phosphorus",
  },
  chat: {
    placeholder: "E.g. I want chicken, salmon for lunch today, I want 2 ice creams…",
    message: "Message",
    send: "Send", apply: "Apply", applied: "Applied to your menu",
    details: "Details ({kcal} kcal)",
    labelTitle: "Enter details from the product label",
    clarifyFor: "Choose a food for “{mention}”",
    understanding: "Understanding your message…", cancel: "Cancel",
    timedOut: "This took too long, so I stopped. Please try again or write a shorter message.",
    cancelled: "Cancelled.",
    dislikeSaved: "Added to your dislike list",
    openProfile: "Open Profile to update allergies",
    label: {
      name: "Name", kcal: "kcal/100 g", protein: "Protein g/100 g", carb: "Carbs g/100 g", fat: "Fat g/100 g",
      portion: "1 serving (g)", contains: "Contains", save: "Save",
      saved: "Saved “{name}” ({source}). Send your message again and I'll add it to your menu.",
    },
  },
  pantry: {
    title: "Ingredients you have at home", add: "Add", grams: "Amount (g)", food: "Ingredient", day: "Date",
    remove: "Remove", removeItem: "Remove {name}",
    exceeds: "Your pantry items already exceed this day's energy needs. The menu will show the excess.",
    added: "Added. Regenerate this day's menu so the rest can be calculated.",
  },
  week: {
    views: "View", range: "{from} – {to}", prev: "Previous week", next: "Next week",
    eaten: "Eaten", planned: "Planned", target: "Target", day: "Day",
    noData: "no data", chartLabel: "Energy over 7 days: {what} vs target",
    basisPlanned: "Nothing logged this week — figures are based on your menu.",
    empty: "No menus or food log in these 7 days yet.",
    averageTitle: "Daily average ({n} days)", within: "Energy within ±10% of target: {n}/{of} days",
    lowTitle: "Often low", lowDays: "below 80% of target on {n}/7 days", tryFoods: "try adding: {foods}",
    avgVsTarget: "average {avg} / target {target} {unit}",
    loadError: "Couldn't load the weekly overview.",
  },
  offline: {
    banner: "You're offline — data may be out of date.",
    tooltip: "You need a connection to do this",
  },
  settings: {
    limits: {
      energy_kcal_max: "Max energy (kcal)", protein_g_max: "Max protein (g)", carb_g_max: "Max carbs (g)",
      fat_g_max: "Max fat (g)", sodium_mg_max: "Max sodium (mg)", potassium_mg_max: "Max potassium (mg)",
      phosphorus_mg_max: "Max phosphorus (mg)",
    },
    appearance: "Appearance",
    themes: { system: "System", light: "Light", dark: "Dark" },
    language: "Language",
    dataTitle: "Data",
    deleteAll: "Delete all my data",
    deleteConfirm: "Permanently delete your profile, menus and chat history? This cannot be undone.",
    export: "Download my data",
    exportHint: "Re-enter your password to download all your data (JSON file). It contains health data — keep it safe.",
    password: "Password", exportDo: "Download", exportDone: "Your data has been downloaded.",
  },
  dislikes: {
    title: "Dislikes",
    help: "Menus will avoid these foods/dishes as much as possible (unlike allergies, which are fully excluded).",
    empty: "Nothing yet.",
    search: "Add a dish or ingredient",
    placeholder: "Type a name, e.g. salmon",
    add: "Add",
    remove: "Remove {name} from the list",
    dish: "dish",
    text: "not in our data — avoided in recipes",
    addText: "Add “{name}” (not in our data — only avoided in cooking instructions)",
  },
  intake: {
    offPlan: "Off-plan",
    none: "Nothing off-plan yet.",
    addOpen: "+ Add something you ate",
    search: "What you ate",
    choose: "Choose",
    meal: "Meal",
    add: "Log it",
    photo: {
      open: "📷 Snap your meal", file: "Meal photo",
      consent: "I agree to send this photo to the AI provider to recognise the food (the photo is not stored).",
      analyze: "Analyse photo", analyzing: "Analysing photo…", draft: "Draft from photo — check before logging",
      empty: "No food recognised in the photo.", gramsFor: "Weight of {name} (g)",
      unresolved: "Not recognised: {names}. You can add them by hand.", rejected: "Removed {food}: {reason}.",
    },
    diff: "Based on your log, today is heading for ~{projected} kcal vs a ~{target} kcal target.",
    rebalance: "Rebalance the remaining meals",
    over: "You're ~{kcal} kcal over today's target. Remaining meals are at their minimum; nothing is carried over to later days.",
  },
  shopping: {
    title: "Shopping list",
    start: "From",
    days: "Days",
    servings: "People",
    missing: "No menu yet for: {days} (skipped).",
    empty: "Nothing to buy for these days.",
    copy: "Copy",
    share: "Share",
    copied: "List copied.",
    until: "Through {end}. Amounts are raw/dry weights, pantry already subtracted.",
    exportTitle: "Shopping for {days} day(s) × {servings} people, from {start}",
    countUnits: { egg: "{n} eggs" },
    portion: "{n} × {portion}",
    weight: "{grams} g",
  },
  limits: {
    title: "My health limits",
    help: "Enter limits your doctor gave you (if any). The app never sets medical limits itself; without limits it "
      + "uses general targets.",
    empty: "No limits yet.",
    add: "Add limits",
    edit: "Edit",
    remove: "Delete",
    deleteConfirm: "Delete these limits?",
    general: "General (all conditions)",
    condition: "Applies to",
    sources: { manual: "Entered by hand", document: "Extracted from a document" },
    tabs: { manual: "Enter by hand", image: "Photo/upload", text: "Paste text" },
    imageLabel: "Photo of your doctor's instructions",
    textLabel: "Text of your doctor's instructions",
    consent: "I agree to send this image/text to the AI provider to read it. It is not stored.",
    read: "Read document",
    reading: "Reading…",
    reviewHint: "The AI can misread. Check each value against its quote and the original, fix anything, then save.",
    converted: "(converted from {value} {unit})",
    convertedSalt: "(converted from {value} g of salt)",
    rejected: "Rejected values",
    others: "Other instructions (not saved as numbers)",
    save: "Save limits",
    cancel: "Cancel",
  },
  notices: {
    DISCLAIMER: "This app does not diagnose any illness and does not replace a doctor or registered dietitian. "
      + "Menus are for reference only.",
    CONSULT_DOCTOR_INSULIN: "You are taking insulin or glucose-lowering medication: consult your doctor before "
      + "changing your diet. The app does not give insulin or medication doses.",
    SODIUM_SEASONING: "Sodium from added salt or fish sauce is not counted. Season lightly.",
    NO_LIMITS_KIDNEY: "You have kidney disease but haven't entered your own limits (protein, sodium, potassium, "
      + "phosphorus). Menus use general targets and may not suit you. If your doctor gave you instructions, enter them "
      + "in Settings → Health limits.",
    NO_LIMITS_CARDIO: "You have cardiovascular disease but haven't entered your own limits (sodium, fat). Menus use "
      + "general targets and may not suit you. If your doctor gave you instructions, enter them in Settings → Health "
      + "limits.",
    NO_LIMITS_LIVER: "You have liver disease but haven't entered your own limits (protein, sodium, energy). Menus use "
      + "general targets and may not suit you. If your doctor gave you instructions, enter them in Settings → Health "
      + "limits.",
    NO_LIMITS_PREGNANT: "You're pregnant but haven't entered your own limits. Energy and micronutrient needs change "
      + "by trimester; menus use general targets and may not suit you. If your doctor gave you instructions, enter "
      + "them in Settings → Health limits.",
    NO_LIMITS_LACTATING: "You're breastfeeding but haven't entered your own limits. Energy and micronutrient needs "
      + "are higher than usual; menus use general targets and may not suit you. If your doctor gave you "
      + "instructions, enter them in Settings → Health limits.",
  },
  errors: {
    ALLERGEN_CONFLICT: "This ingredient conflicts with the allergies or diet you declared.",
    ALLERGEN_CONFLICT_ITEM: "Can't add {food}: it conflicts with the {reason} you declared.",
    ALLERGEN_CONFLICT_CUSTOM: "This product conflicts with the {reason} you declared.",
    BAD_CREDENTIALS: "Incorrect email or password.",
    DAYS_RANGE: "Invalid number of days (create 1–7 days, view 1–14 days at a time).",
    DELTA_RANGE: "Each adjustment must be between 1 and 500 g.",
    ED_SUPPORT: "It seems you may be feeling pressure around eating. You don't need to cut back any further. "
      + "If things feel hard, consider talking to someone close to you, a doctor, a registered dietitian or a "
      + "mental health professional. The app will pause suggestions that reduce your energy intake.",
    EMAIL_EXISTS: "This email is already registered.",
    FOOD_NOT_FOUND: "This ingredient is not in the database.",
    GRAMS_RANGE: "Amount must be between 1 and 3000 g.",
    HTTP: "Invalid request.",
    INTERNAL: "Something went wrong.",
    INVALID_REFRESH: "Your session has expired.",
    INVALID_TOKEN: "Your session is invalid or has expired.",
    ITEM_NOT_FOUND: "Ingredient not found in this meal.",
    LOW_ENERGY_ACK_REQUIRED: "This target is below the safe minimum of ~{floor_kcal} kcal/day. "
      + "Please confirm explicitly if you still want to continue (consulting a professional is recommended).",
    MEAL_NOT_FOUND: "Meal not found.",
    MENU_NOT_FOUND: "No menu for this day yet.",
    MESSAGE_LENGTH: "Messages must be 1–1000 characters.",
    PANTRY_ITEM: "Pantry items are edited in the “Pantry” list.",
    PROFILE_REQUIRED: "Please fill in your health profile first.",
    PROPOSAL_APPLIED: "This suggestion has already been applied.",
    PROPOSAL_EXPIRED: "This suggestion has expired. Please ask the chatbot again.",
    PROPOSAL_NOT_FOUND: "Suggestion not found.",
    RATE_LIMITED: "Too many attempts. Please try again in {retry_after_s} seconds.",
    ROTATION_VIOLATION: "The main dish would repeat more than 3 days in a row.",
    STALE_PROPOSAL: "Your menu changed after this suggestion was made. Please ask the chatbot again.",
    UNAUTHENTICATED: "Please log in.",
    VALIDATION_ERROR: "Invalid data.",
    SERVINGS_RANGE: "Number of people must be between 1 and 10.",
    SLOT_INVALID: "Invalid meal.",
    INTAKE_NOT_FOUND: "This log entry was not found.",
    NOT_FOOD_PHOTO: "This doesn't look like a photo of food. Please try again with a photo of your plate or bowl.",
    INTAKE_BATCH_SIZE: "You can log 1–{max} items at a time.",
    NOTHING_TO_REBALANCE: "All of today's meals are marked as eaten; there is nothing left to rebalance.",
    NO_ALTERNATIVE: "No other suitable dish for this meal (excluding the current dish, disliked dishes and dishes repeated over 3 days).",
    PREFERENCE_NOT_FOUND: "This item is not in your dislike list.",
    LIMITS_REQUIRED: "Enter at least one limit (e.g. sodium, protein, potassium).",
    SELF_MANAGED_ACK_REQUIRED: "You selected a condition that needs special care ({conditions}). No doctor monitors "
      + "this app; menus are only suggestions and may be inaccurate. Please confirm you manage your own diet to continue.",
    LIMIT_NOT_FOUND: "Limit not found.",
    AI_CONSENT_REQUIRED: "You need to agree to send the image/text to the AI provider for processing.",
    BAD_PASSWORD: "Incorrect password.",
    PHOTO_UNAVAILABLE: "The AI can't analyse photos right now. You can still log foods by hand.",
    EXTRACT_INPUT_REQUIRED: "Send exactly one image or one piece of text.",
    TEXT_TOO_LONG: "Text can be at most {max} characters.",
    FILE_TOO_LARGE: "Images can be at most {max_mb} MB.",
    INVALID_IMAGE: "This file is not a valid image (JPEG, PNG or WebP only).",
    EXTRACTION_UNAVAILABLE: "The AI can't read documents right now. You can still enter limits by hand.",
  },
  help: {
    title: "How to use Hôm Nay Ăn Gì",
    entry: "User guide",
    more: "See the guide",
    back: "‹ Back",
    login: "Log in",
    banner: "New here? Read the 1-minute guide",
    bannerClose: "Close",
    intro: {
      title: "What the app does",
      paragraphs: [
        "Hôm Nay Ăn Gì suggests a daily menu based on your body, goals, allergies and tastes. Nutrition figures come "
          + "from the USDA database. Wherever the AI makes an estimate, the app labels it **\"AI estimate\"**.",
        "**Note:** the app does not replace a doctor or dietitian. Menus are for reference only and have a margin of "
          + "error.",
      ],
    },
    sections: [
      {
        id: "start", title: "Get started in 3 steps", paragraphs: [],
        steps: [
          "**Sign up** with your email and a password (at least 8 characters).",
          "**Fill in your profile:** sex, age, height, weight, activity level, goal (lose weight, maintain weight, gain "
            + "muscle). Add health conditions, allergies and diets if you have any. The app works out your daily "
            + "energy and nutrient needs.",
          "Go to the **Today** tab and tap **Create menu**.",
        ],
      },
      {
        id: "today", title: "Today tab: the day's menu", paragraphs: [],
        bullets: [
          "Each meal shows the dish name, ingredients and weights (grams, raw/dry weight). The ring at the top shows "
            + "how much you have eaten compared with your target.",
          "**+ / −** next to an ingredient: increase or decrease its weight. The app keeps exactly what you set and "
            + "rebalances the rest. Tap **Unpin** to let the app choose that weight again.",
          "**Swap dish:** don't like this meal? Tap to change it to another dish. The other meals stay the same.",
          "**How to cook:** the AI suggests how to cook it. Suggestions always avoid ingredients you are allergic to.",
          "**Previous day / Next day:** view or create the menu for another day.",
          "A main dish is never repeated more than 3 days in a row.",
        ],
      },
      {
        id: "log", title: "Logging what you ate", paragraphs: [],
        bullets: [
          "**Eaten:** if you ate exactly what the menu says, tap this button on that meal.",
          "**+ Add something you ate:** if you ate something off the menu, search for it, enter the grams and add it to "
            + "your log.",
          "**📷 Snap your meal:** take or choose a photo, agree to send it to the AI, then tap **Analyse photo**. The "
            + "app creates a draft with the foods and estimated grams. Check and correct it before logging. The app "
            + "does not store the photo.",
          "**Rebalance the remaining meals:** if you ate more or less than planned, tap this button. The app adjusts "
            + "the meals you haven't eaten yet, and each one still keeps a minimum amount. The app never makes you "
            + "make up for it the next day.",
        ],
      },
      {
        id: "week", title: "Week tab: 7-day overview",
        paragraphs: [
          "Tap **Week** in the Today tab to see your energy for the last 7 days against your target, and your daily "
            + "average. The app lists nutrients you often fall short on (fibre, calcium, iron…) and suggests foods to "
            + "make up for them. For a week with no log, the app uses your menus instead.",
        ],
      },
      {
        id: "chat", title: "Chat tab: talk as you would to a person",
        paragraphs: ["Type naturally, with or without Vietnamese accents. For example:"],
        bullets: [
          "\"I just had beef phở for lunch\" → logs it and rebalances the later meals.",
          "\"I want salmon for dinner tonight\" → suggests a menu with salmon.",
          "\"I had 2 ice creams today\" → counts the ice cream in your day and suggests how to balance it.",
          "\"I don't like bitter melon\" → adds it to your dislikes.",
        ],
        after: [
          "Nothing changes until you tap **Apply**. If the chatbot asks \"which dish do you mean?\", pick the right one.",
          "For a food that is not in our data (for example a packaged product), enter it from the **product label**: "
            + "the name and the kcal, protein, carbs and fat per 100 g.",
        ],
      },
      {
        id: "pantry", title: "Pantry tab: ingredients you have at home",
        paragraphs: [
          "Add what you already have in the fridge, with the date and grams. Then **regenerate the menu** for that day "
            + "so the app uses these ingredients first.",
        ],
      },
      {
        id: "shopping", title: "Shopping tab",
        paragraphs: [
          "Choose the start date, number of days and number of people. The app adds up the ingredients of the menus you "
            + "have created and subtracts what you already have. Tap **Copy** or **Share** to send the list to "
            + "whoever does the shopping.",
        ],
      },
      {
        id: "profile", title: "Profile tab", paragraphs: [],
        bullets: [
          "Edit your body details, goal, allergies and diets. The app recalculates your needs as soon as you save.",
          "**Dislikes:** dishes or ingredients you'd rather not eat. The app uses them as little as possible but does "
            + "not exclude them completely. Allergies are different: the app excludes them completely.",
        ],
      },
      {
        id: "settings", title: "Settings (⚙)", paragraphs: [],
        bullets: [
          "**Health limits:** if your doctor has given you limits (sodium, protein, potassium…), enter them by hand, "
            + "take a photo or paste the text of the instructions. The AI reads the document and creates a draft. The "
            + "AI can misread, so compare it with the original before saving.",
          "**Appearance** (light/dark) and **Language** (Tiếng Việt/English).",
          "**Download my data:** downloads a JSON file with all your data. The file contains health data, so keep it "
            + "safe.",
          "**Delete all my data:** deletes everything permanently; it cannot be recovered.",
          "**Log out.**",
        ],
      },
      {
        id: "tips", title: "Tips", paragraphs: [],
        bullets: [
          "You can install the app on your phone: open it in the browser and choose **Add to Home Screen**.",
          "When you are offline, the app still shows data it has already loaded but doesn't let you make changes.",
          "If a menu misses a target, the app says which nutrients are short or over and suggests foods to add.",
        ],
      },
      {
        id: "faq", title: "Frequently asked questions", paragraphs: [],
        bullets: [
          "**Why can't I find dish X?** It may contain something you are allergic to, not fit your diet, or not be in "
            + "our data yet. Try entering it from the product label in the Chat tab.",
          "**How accurate are the numbers?** They are estimates from standard data. Real home-cooked dishes may differ. "
            + "Salt and fish sauce added while cooking are not counted.",
          "**Is my health data safe?** Your profile, limits and chat messages are all encrypted. Photos sent to the AI "
            + "are not stored.",
        ],
      },
    ] as HelpSection[],
  },
  unverified: "unverified",
  userProvided: "user-provided",
  error: "Something went wrong.",
};
