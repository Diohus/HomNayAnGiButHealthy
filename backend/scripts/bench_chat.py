"""Đo độ trễ hiểu câu chat với LLM THẬT (không thuộc pytest). Chạy từ thư mục backend:

    python scripts/bench_chat.py

Đọc cấu hình LLM từ .env (không sửa .env). 10 câu cố định × 2 lượt (lượt 2 trúng cache), so sánh:
  - before: đường 2 bước cũ (parse ⇒ resolve), tương đương CHAT_SINGLE_PASS=false
  - after : 1 lượt LLM gộp (N1)
In p50/p90 (ms) của phần LLM (hiểu câu) và của toàn bộ câu trả lời (gồm bộ tối ưu thực đơn).
Không in nội dung trả lời của LLM; chỉ in loại câu trả lời và mã món nhận được.
"""

import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:  # Windows/proxy công ty: dùng kho chứng chỉ hệ điều hành nếu có
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

from app.ai.providers import get_provider
from app.chat import parser as P
from app.chat import understand as U
from app.chat.engine import ChatContext, handle
from app.core.config import get_settings
from app.foods import load_seed_catalog
from app.foods import resolve as RS
from app.nutrition import HealthProfileIn, compute_needs
from app.planner import PlanRequest, solve_day
from app.services.targets import planner_targets

SENTENCES = [
    "toi muon an ga ran", "trứg luộc", "trưa nay ăn bún bò huế", "cho tôi ít trái thơm", "tôi không ăn được hành",
    "I don't like fish", "tôi vừa ăn 1 tô phở bò", "tối nay ăn canh chua cá lóc", "toi muon an bun cha",
    "hôm nay cheat day, ăn pizza",
]
NOW = datetime.now().replace(hour=9, minute=0)


def make_ctx(catalog, resolve_fn):
    p = HealthProfileIn(sex="female", age=30, height_cm=160, weight_kg=55, activity_level="moderate")
    n = compute_needs(p)
    cat = catalog.filtered(p.allergies, p.diets)

    def plan_fn(day, required, snacks, e, min_meal, extra=()):
        return solve_day(PlanRequest(day=day, slots=n.meal_slots, targets=planner_targets(n, e), required=required,
                                     locked=[*snacks, *extra], min_meal_energy_kcal=min_meal), cat)

    return ChatContext(now=NOW, slots=n.meal_slots, allergies=[], diets=[], catalog_full=catalog, catalog=cat,
                       energy_target=lambda d: n.get("energy_kcal").value, energy_floor=n.energy_floor_kcal,
                       plan_fn=plan_fn, resolve_fn=resolve_fn)


class Counting:
    def __init__(self, inner):
        self.inner, self.calls, self.name = inner, 0, inner.name

    def complete_json(self, *a):
        self.calls += 1
        return self.inner.complete_json(*a)


def run(mode: str, provider, catalog, retries: int) -> dict:
    llm_ms, total_ms, lines = [], [], []
    for pass_no in (1, 2):
        for text in SENTENCES:
            t0 = time.perf_counter()
            llm = 0.0
            pre = {}
            one = U.understand(text, provider, catalog, "vi", NOW, retries) if mode == "after" else None
            if one is not None:
                parsed, pre = one
                name = "llm"
            else:
                parsed, name = P.parse(text, provider, retries, "vi", NOW)
            llm += time.perf_counter() - t0

            def resolve_fn(ms, pre=pre):
                nonlocal llm
                t = time.perf_counter()
                out = {m: pre[m] for m in ms if m in pre and pre[m].kind != "unknown"}
                todo = [m for m in ms if m not in out]
                if todo:
                    out.update(RS.resolve_mentions(provider, todo, catalog, "vi", retries))
                llm += time.perf_counter() - t
                return out

            reply = handle(text, parsed, make_ctx(catalog, resolve_fn), name)
            total = time.perf_counter() - t0
            llm_ms.append(llm * 1000)
            total_ms.append(total * 1000)
            dishes = sorted({d.dish_code or d.food_code for d in reply.detected})
            lines.append(f"  [{mode} #{pass_no}] {llm * 1000:6.0f} ms LLM {total * 1000:6.0f} ms total  "
                         f"{reply.parser:5} {parsed.intent:9} {reply.kind:10} {text!r} ⇒ {dishes}")
    return {"llm": llm_ms, "total": total_ms, "lines": lines}


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, round(q * (len(xs) - 1)))]


def summary(name: str, xs: list[float]) -> str:
    return f"{name}: p50={statistics.median(xs):.0f} ms  p90={pct(xs, 0.9):.0f} ms"


def main():
    s = get_settings()
    inner = get_provider(s)
    if inner is None:
        sys.exit("LLM chưa cấu hình (LLM_API_KEY trong .env) — benchmark cần LLM thật.")
    catalog = load_seed_catalog()
    for mode in ("before", "after"):
        for c in (U.cache, P._cache, RS.cache):
            c.clear()
        provider = Counting(inner)
        r = run(mode, provider, catalog, s.llm_max_retries)
        print(f"\n== {mode} ({'2 bước: parse ⇒ resolve' if mode == 'before' else '1 lượt gộp'}), "
              f"{provider.calls} lượt gọi LLM ==")
        print("\n".join(r["lines"]))
        for p in (1, 2):
            part = slice(0, 10) if p == 1 else slice(10, 20)
            print(f"  lượt {p}: " + summary("LLM", r["llm"][part]) + " | " + summary("tổng", r["total"][part]))


if __name__ == "__main__":
    main()
