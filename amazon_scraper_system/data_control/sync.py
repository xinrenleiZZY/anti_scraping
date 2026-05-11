"""
数据同步 - 数据库 ↔ JSON 文件双向同步
供 API 路由调用，每次写操作后自动同步
"""

import json
import logging
from pathlib import Path
from datetime import datetime

import sys
_backend = str(Path(__file__).resolve().parents[1] / "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from data_control.config import (
    USERS_JSON, USER_KEYWORDS_JSON, SCRAPER_CONFIG,
)

logger = logging.getLogger(__name__)


def _get_db():
    from app.database import SessionLocal
    return SessionLocal()


def _load_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def sync_users() -> None:
    """导出 users 表全量到 users.json"""
    db = _get_db()
    try:
        from app.models import User, UserKeyword
        users = db.query(User).all()
        data = []
        for u in users:
            keywords = db.query(UserKeyword).filter(
                UserKeyword.user_id == u.id
            ).all()
            data.append({
                "id": u.id,
                "name": u.name,
                "keywords": [k.keyword for k in keywords],
            })
        _save_json(USERS_JSON, {
            "synced_at": datetime.now().isoformat(),
            "total": len(data),
            "users": data,
        })
        logger.info(f"users.json 已同步: {len(data)} 个用户")
    except Exception as e:
        logger.error(f"同步 users.json 失败: {e}")
    finally:
        db.close()


def sync_user_keywords() -> None:
    """导出 user_keywords 表全量到 user_keywords.json"""
    db = _get_db()
    try:
        from app.models import UserKeyword, User
        records = (
            db.query(UserKeyword, User.name)
            .join(User, User.id == UserKeyword.user_id)
            .all()
        )
        data = []
        for uk, uname in records:
            data.append({
                "id": uk.id,
                "user_id": uk.user_id,
                "user_name": uname,
                "keyword": uk.keyword,
            })
        _save_json(USER_KEYWORDS_JSON, {
            "synced_at": datetime.now().isoformat(),
            "total": len(data),
            "relations": data,
        })
        logger.info(f"user_keywords.json 已同步: {len(data)} 条关联")
    except Exception as e:
        logger.error(f"同步 user_keywords.json 失败: {e}")
    finally:
        db.close()


def sync_keyword_attributes_to_config() -> None:
    """
    从数据库 keyword_attributes 表同步到 scraper_config.json
    更新 keyword_tags / keyword_festivals / keyword_festival_types / keyword_hot_seasons 字段
    """
    config = _load_json(SCRAPER_CONFIG)
    if not config:
        logger.warning("scraper_config.json 不存在，跳过同步")
        return

    db = _get_db()
    try:
        from app.models import KeywordAttribute
        attrs = db.query(KeywordAttribute).all()

        config["keyword_tags"] = {}
        config["keyword_festivals"] = {}
        config["keyword_festival_types"] = {}
        config["keyword_hot_seasons"] = {}

        for a in attrs:
            if a.tags:
                config["keyword_tags"][a.keyword] = a.tags
            if a.festival:
                config["keyword_festivals"][a.keyword] = a.festival
            if a.festival_type:
                config["keyword_festival_types"][a.keyword] = a.festival_type
            if a.hot_season:
                config["keyword_hot_seasons"][a.keyword] = a.hot_season

        _save_json(SCRAPER_CONFIG, config)
        logger.info(f"scraper_config.json 已同步: {len(attrs)} 个关键词属性")
    except Exception as e:
        logger.error(f"同步 scraper_config.json 失败: {e}")
    finally:
        db.close()


def sync_all() -> dict:
    """一键同步所有数据到 JSON 备份"""
    results = {}
    funcs = [
        ("users", sync_users),
        ("user_keywords", sync_user_keywords),
        ("keyword_attributes", sync_keyword_attributes_to_config),
    ]
    for name, func in funcs:
        try:
            func()
            results[name] = "ok"
        except Exception as e:
            results[name] = f"error: {e}"
    return results


if __name__ == "__main__":
    print(sync_all())
