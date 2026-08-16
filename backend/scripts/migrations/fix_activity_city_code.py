"""一次性数据迁移：把脏数据的 activities.city_code 修正为 City.code。

脏数据表现：city_code 字段存的是中文字面量（如 '上海'）而非 cities.code（如 'city-99f1e469'），
导致前端按 cities.code 筛选时命中 0 条。

修复规则：
- city_code 已经是 cities.code → 保留。
- city_code 等于某 cities.name → 改为该城市的 cities.code。
- 其他情况不在本脚本处理，由入库硬校验在抓取阶段拦截。
"""

from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.config import City


def run_migration(db: Session) -> int:
    """执行迁移，返回修正的活动数量。"""
    code_by_name = {c.name: c.code for c in db.query(City).all()}
    codes = set(code_by_name.values())
    fixed = 0
    activities = (
        db.query(Activity)
        .filter(Activity.deleted_at.is_(None))
        .all()
    )
    for activity in activities:
        if activity.city_code in codes:
            continue
        if activity.city_code in code_by_name:
            activity.city_code = code_by_name[activity.city_code]
            fixed += 1
    db.commit()
    return fixed


def main() -> None:
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        total = db.query(Activity).filter(Activity.deleted_at.is_(None)).count()
        fixed = run_migration(db)
        print(f"扫描 {total} / 已修正 {fixed}")
    finally:
        db.close()


if __name__ == "__main__":
    main()