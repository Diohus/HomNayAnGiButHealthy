"""Ràng buộc lặp món: một món chính không xuất hiện quá MAX_RUN ngày liên tiếp."""

from datetime import date, timedelta

MAX_RUN = 3


def _run_length(dish: str, day: date, mains_by_date: dict[date, set[str]]) -> int:
    """Độ dài chuỗi ngày liên tiếp chứa `dish` nếu đặt nó vào `day`."""
    n = 1
    d = day - timedelta(days=1)
    while dish in mains_by_date.get(d, set()):
        n += 1
        d -= timedelta(days=1)
    d = day + timedelta(days=1)
    while dish in mains_by_date.get(d, set()):
        n += 1
        d += timedelta(days=1)
    return n


def forbidden_mains(day: date, mains_by_date: dict[date, set[str]], candidates) -> set[str]:
    """Món chính bị cấm ở `day` (xét cả ngày trước và sau — an toàn khi sinh lại ngày giữa tuần)."""
    others = {d: s for d, s in mains_by_date.items() if d != day}
    return {c for c in candidates if _run_length(c, day, others) > MAX_RUN}


def max_consecutive_run(mains_by_date: dict[date, set[str]]) -> int:
    best = 0
    for day, dishes in mains_by_date.items():
        for dish in dishes:
            if dish in mains_by_date.get(day - timedelta(days=1), set()):
                continue  # chỉ đếm từ đầu chuỗi
            n, d = 0, day
            while dish in mains_by_date.get(d, set()):
                n += 1
                d += timedelta(days=1)
            best = max(best, n)
    return best
