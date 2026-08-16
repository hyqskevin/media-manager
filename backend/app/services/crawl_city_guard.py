"""入库硬校验：city_code 必须存在于 cities 表。

设计目标：阻止历史脏数据（如中文字面量、过期 code、空字符串）再次入库。
调用方在写入 Activity/Note 之前调用本函数；不通过则跳过并记 ERROR 日志。
"""

from sqlalchemy.orm import Session

from app.models.config import City


def assert_city_code_exists(db: Session, city_code: str) -> bool:
    """检查 city_code 是否在 cities 表中存在且非空。

    返回 True 表示安全可入库；返回 False 表示应当跳过该活动。
    """
    if not city_code:
        return False
    return db.query(City.id).filter(City.code == city_code).first() is not None