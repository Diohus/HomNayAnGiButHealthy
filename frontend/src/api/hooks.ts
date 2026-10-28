import { type QueryClient, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Dish, Food, HealthLimitRow, MenuDay, Needs, Notice, Profile } from "../types";
import { useI18n } from "../i18n";
import { api, post } from "./client";

export function useFoods() {
  return useQuery({ queryKey: ["foods"], queryFn: () => api<Food[]>("/foods"), staleTime: 5 * 60_000 });
}

export function useFoodNames() {
  const { data } = useFoods();
  const { lang } = useI18n();
  const map = new Map((data ?? []).map((f) => [f.code, f]));
  return (code: string) => {
    const f = map.get(code);
    return (lang === "en" ? f?.display_en || f?.name_en || f?.name_vi : f?.name_vi) ?? code;
  };
}

export function useDishes() {
  return useQuery({ queryKey: ["dishes"], staleTime: 60 * 60_000, queryFn: () => api<Dish[]>("/dishes") });
}

export function useDishNames() {
  const { data } = useDishes();
  const { lang } = useI18n();
  const map = new Map((data ?? []).map((d) => [d.code, lang === "en" ? d.name_en || d.name_vi : d.name_vi]));
  return (code: string | null) => (code ? map.get(code) ?? code : null);
}

export function useProfile() {
  return useQuery({ queryKey: ["profile"], queryFn: () => api<{ profile: Profile | null }>("/profile") });
}

export function useNeeds(enabled = true) {
  return useQuery({
    queryKey: ["needs"], enabled,
    queryFn: () => api<{ needs: Needs; notices: Notice[]; conditions_without_limits: string[] }>("/needs"),
  });
}

export function useHealthLimits() {
  return useQuery({ queryKey: ["health-limits"], queryFn: () => api<HealthLimitRow[]>("/health-limits") });
}

export function useMenu(day: string) {
  return useQuery({ queryKey: ["menu", day], queryFn: () => api<(MenuDay | null)[]>(`/menu?start=${day}`) });
}

const isMenuDay = (x: unknown): x is MenuDay =>
  !!x && typeof x === "object" && "day" in x && "plan" in x;

// Kết quả API sửa thực đơn ⇒ các MenuDay mới: MenuDay, MenuDay[] (generate) hoặc { menu } (áp dụng đề xuất chat).
export function menusFromResult(result: unknown): MenuDay[] {
  const list = Array.isArray(result) ? result
    : result && typeof result === "object" && "menu" in result ? [(result as { menu: unknown }).menu] : [result];
  return list.filter(isMenuDay);
}

// Ghi MenuDay trả về vào cache (không refetch ngày đó); chỉ invalidate các query "menu" khác.
// Không có MenuDay (vd. recipe) ⇒ invalidate toàn bộ "menu" như cũ.
export function applyMenuResult(qc: QueryClient, result: unknown): Promise<void> {
  const menus = menusFromResult(result);
  for (const md of menus) qc.setQueryData(["menu", md.day], [md]);
  const fresh = new Set(menus.map((md) => md.day));
  return qc.invalidateQueries({
    queryKey: ["menu"], predicate: (q) => !(q.queryKey.length === 2 && fresh.has(q.queryKey[1] as string)),
  });
}

export function useMenuMutation<V>(fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: (result) => applyMenuResult(qc, result) });
}

export const generateDay = (day: string) => post<MenuDay[]>("/menu/generate", { start: day, days: 1 });
