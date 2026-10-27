"""Nạp dữ liệu nguyên liệu/món vào DB: `python -m app.seed` (idempotent)."""

from app.db import foods_repo
from app.db import session as dbs


def main() -> None:
    dbs.init_engine()
    with dbs._SessionLocal() as s:
        n = foods_repo.seed(s)
    print(f"Seeded {n} ingredients")


if __name__ == "__main__":
    main()
