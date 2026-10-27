import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Dish, Food, MenuDay, Needs, Notice, Profile } from "../types";
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

export function useDishNames() {
  const { data } = useQuery({
    queryKey: ["dishes"], staleTime: 60 * 60_000,
    queryFn: () => api<Dish[]>("/dishes"),
  });
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
    queryFn: () => api<{ needs: Needs; notices: Notice[]; expert_confirmation_required: string[] }>("/needs"),
  });
}

export function useMenu(day: string) {
  return useQuery({ queryKey: ["menu", day], queryFn: () => api<(MenuDay | null)[]>(`/menu?start=${day}`) });
}

export function useMenuMutation<V>(fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries({ queryKey: ["menu"] }) });
}

export const generateDay = (day: string) => post<MenuDay[]>("/menu/generate", { start: day, days: 1 });
