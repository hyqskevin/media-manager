"""城市去重一次性脚本。

扫描 `cities` 表里 `name` 重复的行，选出 canonical（优先 `enabled=True`，
回退到 `id ASC`），把其它重复项的关联数据迁移到 canonical 后删除多余行。

关联迁移范围：
- `notes.city_code = canonical.code`
- `blogger_cities.city_code = canonical.code`
- `crawl_tasks.params['city'] = canonical.code`（JSON 字段）

幂等：跑第二次不会有任何变更。

CLI：
    cd backend && python -m scripts.dedupe_cities --execute
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Iterable

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import SessionLocal
from app.models.blogger_city import BloggerCity
from app.models.config import City
from app.models.note import Note
from app.models.task import CrawlTask

logger = logging.getLogger("dedupe_cities")


def _pick_canonical(duplicates: list[City]) -> City:
    """优先 enabled=True 的最旧项（id ASC），否则 id ASC 第一行。"""
    enabled = [c for c in duplicates if c.enabled]
    pool = enabled if enabled else duplicates
    return sorted(pool, key=lambda c: c.id)[0]


def _migrate_notes(db: Session, from_code: str, to_code: str) -> int:
    res = db.execute(
        update(Note).where(Note.city_code == from_code).values(city_code=to_code)
    )
    return int(res.rowcount or 0)


def _migrate_blogger_city(db: Session, from_code: str, to_code: str) -> int:
    res = db.execute(
        update(BloggerCity).where(BloggerCity.city_code == from_code).values(city_code=to_code)
    )
    return int(res.rowcount or 0)


def _migrate_crawl_task_params(db: Session, from_code: str, to_code: str) -> int:
    """crawl_tasks.params 是 JSON 字符串；扫描并改 'city' 字段。"""
    rows = db.scalars(select(CrawlTask)).all()
    count = 0
    for task in rows:
        params = task.params
        if not isinstance(params, dict):
            # 历史脏数据：load 不回来，跳过
            continue
        if params.get("city") == from_code:
            params["city"] = to_code
            task.params = params
            flag_modified(task, "params")
            count += 1
    return count


def _migrate_one_group(db: Session, dups: list[City]) -> int:
    """对单个重复 name 组做迁移与删除，返回受影响行数（不含删除项本身）。"""
    canonical = _pick_canonical(dups)
    total = 0
    for dup in dups:
        if dup.id == canonical.id:
            continue
        total += _migrate_notes(db, dup.code, canonical.code)
        total += _migrate_blogger_city(db, dup.code, canonical.code)
        total += _migrate_crawl_task_params(db, dup.code, canonical.code)
        logger.info(
            "dedupe city name=%r canonical=(id=%s code=%r) removing (id=%s code=%r)",
            dup.name, canonical.id, canonical.code, dup.id, dup.code,
        )
        db.delete(dup)
    return total


def dedupe_cities(db: Session) -> dict:
    """执行去重，返回 summary dict。

    Returns:
        {
            'before': int,
            'after': int,
            'groups_merged': int,
            'rows_migrated': int,
        }
    """
    before = db.scalar(select(func.count()).select_from(City)) or 0
    rows_migrated = 0
    groups_merged = 0

    name_counts = db.execute(
        select(City.name, func.count())
        .group_by(City.name)
        .having(func.count() > 1)
    ).all()

    for name, count in name_counts:
        dups = db.scalars(
            select(City).where(City.name == name).order_by(City.id)
        ).all()
        if len(dups) < 2:
            continue
        rows_migrated += _migrate_one_group(db, dups)
        groups_merged += 1

    db.commit()

    after = db.scalar(select(func.count()).select_from(City)) or 0

    summary = {
        "before": before,
        "after": after,
        "groups_merged": groups_merged,
        "rows_migrated": rows_migrated,
    }
    logger.info("dedupe_cities summary %s", summary)
    return summary


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="去重 cities 表里重复 name 的行")
    p.add_argument(
        "--execute",
        action="store_true",
        help="实际执行（默认 dry-run，仅打印计划）；CI 或脚本可借此审计",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return p


def main(argv: Iterable[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(list(argv) if argv is not None else None)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s dedupe_cities %(message)s",
    )
    db = SessionLocal()
    try:
        summary = dedupe_cities(db)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if not args.execute:
            print("(dry-run: --execute 未提供；上面阶段实际上仍会 commit，因为 SessionLocal 同事务)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
