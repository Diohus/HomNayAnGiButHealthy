export interface PlanItem { food_code: string; grams: number; locked: boolean; origin: string }
export interface MealPlan { slot: string; dish_code: string | null; items: PlanItem[]; totals: Record<string, number> }
export interface Deviation { code: string; kind: string; target: number; actual: number; pct: number; within: boolean }
export interface Suggestion { nutrient: string; food_codes: string[] }
export interface DayPlan {
  day: string; status: string; meals: MealPlan[]; totals: Record<string, number>; deviations: Deviation[];
  shortfalls: string[]; suggestions: Suggestion[]; conflicts: string[]; warnings: string[];
}
export interface Notice { code: string; text: string }
export interface Recipe { steps: string[]; seasonings: { name: string; note: string }[]; tip: string; source: string }
export interface MenuDay {
  day: string; version: number; plan: DayPlan; recipes: Record<string, Recipe>; inactive_meals: string[];
  energy_adjustment_kcal: number; notices: Notice[];
}
export interface Food {
  code: string; name_vi: string; name_en: string; display_en: string | null; category: string; role: string; excluded_reason: string | null;
  unverified_nutrients: string[]; user_provided: boolean; per_100g: Record<string, number | null>;
  portion: { description: string; grams: number } | null; source: { dataset: string; fdc_id?: number; url?: string };
}
export interface Dish { code: string; name_vi: string; name_en: string }
export interface Target {
  code: string; unit: string; kind: string; value: number; upper: number | null;
  reference: { source: string; applies_to: string | null; note: string | null }; adjusted_for: string[];
}
export interface Needs {
  bmr_kcal: number; activity_factor: number; tdee_kcal: number; energy_floor_kcal: number; meals_per_day: number;
  meal_slots: string[]; targets: Target[]; warnings: string[]; assumptions: string[];
}
export interface Proposal {
  id: string; key: string; label: string; day: string; plan: DayPlan;
  compensation: { overflow_kcal: number; reductions: { day: string; kcal: number }[]; forgiven_kcal: number } | null;
}
export interface ChatReply {
  kind: string; text: string; parser: string; detected: { food_code: string; name: string; role: string }[];
  unknown_mentions: string[]; proposals: Proposal[];
}
export interface Profile {
  sex: string; age: number; height_cm: number; weight_kg: number; activity_level: string; goal: string;
  conditions: string[]; uses_insulin_or_glucose_meds: boolean; allergies: string[]; diets: string[];
  custom_target_kcal: number | null; acknowledge_low_energy: boolean;
}
