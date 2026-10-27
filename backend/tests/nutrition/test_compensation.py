from datetime import date, timedelta

from app.nutrition.compensation import DayEnergy, cheat_day_energy, plan_compensation

D0 = date(2026, 10, 21)


def days(n, target=2000, floor=1500):
    return [DayEnergy(day=D0 + timedelta(days=i + 1), target_kcal=target, floor_kcal=floor) for i in range(n)]


def test_capped_10pct_per_day_max_3_days_rest_forgiven():
    c = plan_compensation(1000, days(5))
    assert [r.kcal for r in c.reductions] == [200, 200, 200]
    assert c.forgiven_kcal == 400


def test_never_below_floor():
    c = plan_compensation(1000, days(3, target=1550, floor=1500))
    assert all(r.kcal <= 50 for r in c.reductions)
    assert all(1550 - r.kcal >= 1500 for r in c.reductions)


def test_small_overflow_single_day():
    c = plan_compensation(120, days(3))
    assert len(c.reductions) == 1 and c.reductions[0].kcal == 120 and c.forgiven_kcal == 0


def test_no_overflow_no_reduction():
    assert plan_compensation(0, days(3)).reductions == []


def test_cheat_day_keeps_half_for_meals():
    assert cheat_day_energy(2000, 1800) == 2800
    assert cheat_day_energy(2000, 500) == 2000
