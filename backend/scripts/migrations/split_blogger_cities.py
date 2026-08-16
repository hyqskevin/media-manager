"""一次性迁移：建 blogger_cities 表 + 把 Blogger.city_code 拆分过去。

执行入口：`python -m scripts.migrations.split_blogger_cities`
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.models.blogger_city import BloggerCity
from app.models.config import Blogger, City


def run_migration(db: Session) -> int:
    """执行迁移。返回新建的 BloggerCity 行数。"""
    # 1. 确保表存在（脚本可独立运行；ORM 启动时也会跑 create_all）
    Base.metadata.create_all(engine, tables=[BloggerCity.__table__])

    # 2. 搬数据
    moved = 0
    bloggers = (
        db.query(Blogger)
        .filter(Blogger.city_code.isnot(None))
        .filter(Blogger.city_code != "")
        .all()
    )
    for b in bloggers:
        exists = db.scalar(
            select(BloggerCity).where(
                BloggerCity.blogger_id == b.id,
                BloggerCity.city_code == b.city_code,
            )
        )
        if exists:
            continue
        db.add(
            BloggerCity(
                blogger_id=b.id,
                city_code=b.city_code,
                enabled=b.enabled,
            )
        )
        moved += 1
    db.commit()
    return moved


def main() -> None:
    db = SessionLocal()
    try:
        total = db.query(Blogger).count()
        moved = run_migration(db)
        print(f"扫描博主 {total} / 已迁移 {moved}")
    finally:
        db.close()


if __name__ == "__main__":
    main()