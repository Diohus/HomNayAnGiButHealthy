"""Fixture dùng chung cho test chatbot (tiếng Việt và tiếng Anh)."""

from datetime import datetime

import pytest

from app.chat.engine import ChatContext, handle
from app.chat.parser import parse
from app.nutrition import HealthProfileIn, compute_needs
from app.planner import PlanRequest, solve_day
from app.services.targets import planner_targets

NOW = datetime(2026, 10, 21, 9, 0)


@pytest.fixture()
def make_ctx(catalog):
    def _make(**profile_kw):
        p = HealthProfileIn(**{"sex": "female", "age": 30, "height_cm": 160, "weight_kg": 55,
                               "activity_level": "moderate", **profile_kw})
        n = compute_needs(p)
        cat = catalog.filtered(p.allergies, p.diets)

        def plan_fn(day, required, snacks, e, min_meal, extra=()):
            return solve_day(PlanRequest(day=day, slots=n.meal_slots, targets=planner_targets(n, e),
                                         required=required, locked=[*snacks, *extra], min_meal_energy_kcal=min_meal),
                             cat)

        return ChatContext(now=NOW, slots=n.meal_slots, allergies=p.allergies, diets=p.diets, catalog_full=catalog,
                           catalog=cat, energy_target=lambda d: n.get("energy_kcal").value,
                           energy_floor=n.energy_floor_kcal, plan_fn=plan_fn), n
    return _make


def ask(ctx, text):
    parsed, src = parse(text, None)
    return handle(text, parsed, ctx, src)
