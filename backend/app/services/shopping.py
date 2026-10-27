"""Danh sách đi chợ cho N ngày × số người ăn — thuần tính toán từ thực đơn đã lưu (không gọi LLM)."""

import math
import uuid
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.i18n import Lang, name_of, tr
from app.db import foods_repo
from app.db import models as M
from app.planner.solver import CATEGORY_ORDER

# Đơn vị mua đếm được mà catalog chưa có `portion` (khối lượng sống trung bình) — GIẢ ĐỊNH, xem ASSUMPTIONS
COUNT_UNITS = {"egg": 50.0}
SMALL_STEP_CATEGORIES = {"fat"}  # dầu ăn/gia vị: làm tròn 10 g


def _purchase(food, grams: float) -> dict:
    """Quy về đơn vị mua, luôn làm tròn LÊN (không thiếu khi đi chợ)."""
    unit_g = COUNT_UNITS.get(food.code)
    if unit_g:
        n = math.ceil(grams / unit_g - 1e-9)
        return {"kind": "count", "count": n, "unit_key": food.code, "grams": n * unit_g}
    if food.portion:
        n = math.ceil(grams / food.portion.grams - 1e-9)
        return {"kind": "portion", "count": n, "portion": food.portion.description,
                "grams": round(n * food.portion.grams)}
    if food.category in SMALL_STEP_CATEGORIES:
        g = max(10, math.ceil(grams / 10 - 1e-9) * 10)
    else:
        g = max(100, math.ceil(grams / 50 - 1e-9) * 50)
    return {"kind": "weight", "grams": g}


def shopping_list(s: Session, user_id: uuid.UUID, start: date, days: int, servings: int, lang: Lang) -> dict:
    if not 1 <= days <= 7:
        raise AppError(422, "DAYS_RANGE", key="error.DAYS_RANGE.generate")
    if not 1 <= servings <= 10:
        raise AppError(422, "SERVINGS_RANGE")
    catalog = foods_repo.global_catalog(s).with_foods(foods_repo.user_foods(s, user_id))
    end = start + timedelta(days=days - 1)
    need: dict[str, float] = defaultdict(float)
    days_used: dict[str, set[str]] = defaultdict(set)
    missing = []
    for i in range(days):
        day = start + timedelta(days=i)
        md = s.scalar(select(M.MenuDay).where(M.MenuDay.user_id == user_id, M.MenuDay.day == day))
        if md is None:
            missing.append(day.isoformat())
            continue
        for meal in md.meals:
            if not meal.active:
                continue
            for it in meal.items:
                f = catalog.foods.get(it.ingredient_code)
                if f is None or f.user_provided:  # đồ nhập từ nhãn: người dùng tự mua theo sản phẩm
                    continue
                need[f.code] += it.grams  # gồm cả phần lấy từ đồ có sẵn; trừ kho ở dưới
                days_used[f.code].add(day.isoformat())
    # nhân số người ăn rồi trừ đồ có sẵn trong nhà của các ngày đó (không âm)
    total = {code: g * servings for code, g in need.items()}
    for p in s.scalars(select(M.PantryItem).where(M.PantryItem.user_id == user_id, M.PantryItem.day >= start,
                                                  M.PantryItem.day <= end)):
        if p.ingredient_code in total:
            total[p.ingredient_code] = max(0.0, total[p.ingredient_code] - p.grams)
    groups: dict[str, list] = defaultdict(list)
    for code, g in total.items():
        if g <= 0.5:
            continue
        f = catalog.food(code)
        groups[f.category].append({
            "code": code, "name": name_of(f, lang), "grams": round(g), "purchase": _purchase(f, g),
            "days_used": sorted(days_used[code]),
        })
    out = []
    for cat in sorted(groups, key=lambda c: CATEGORY_ORDER.index(c) if c in CATEGORY_ORDER else 99):
        out.append({"category": cat, "label": tr(f"shop.category.{cat}", lang),
                    "items": sorted(groups[cat], key=lambda x: x["name"])})
    return {"start": start.isoformat(), "days": days, "servings": servings, "missing_days": missing, "groups": out}
