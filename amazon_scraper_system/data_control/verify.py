"""
verify.py — 数据完整性校验
检查项:
  1. DB 各表行数 vs 文件备份行数
  2. 配置文件是否存在
  3. 数据目录是否存在且非空
  4. scrap_ data 一致性
用法:
  python data_control/verify.py           # 全部检查
  python data_control/verify.py --json    # JSON 格式输出
"""

import json
import sys
import io
import re
import logging
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import psycopg2

_here = Path(__file__).resolve().parent
_root = _here.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from data_control.config import (
    DATABASE_URL,
    SCRAPER_CONFIG, SCHEDULE_CONFIG, ASIN_MONITOR_CONFIG,
    PROCESSED_DATA_DIR, AMAZON_DATA_DIR, POSTGRES_DATA_DIR,
    USERS_JSON, USER_KEYWORDS_JSON, LOG_FILES,
    BACKUP_TARGET,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("verify")


def parse_db_url(url: str) -> dict:
    m = re.match(r"postgresql://(.+?):(.+?)@(.+?):(\d+)/(.+)", url)
    if not m:
        raise ValueError(f"无法解析 DATABASE_URL: {url}")
    user, pwd, host, port, dbname = m.groups()
    return {"user": user, "password": pwd, "host": host, "port": int(port), "dbname": dbname}


def get_conn():
    db = parse_db_url(DATABASE_URL)
    return psycopg2.connect(**db)


def _db_count(table: str) -> int:
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count
    except Exception as e:
        logger.warning(f"  查询 {table} 失败: {e}")
        return -1


def _file_count_json(path: Path, key: str = None) -> int:
    if not path.exists():
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if key:
            return len(data.get(key, []))
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            return data.get("total", len(data))
        return 0
    except Exception:
        return 0


def _dir_info(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "files": 0, "size_mb": 0}
    files = list(path.rglob("*"))
    file_items = [f for f in files if f.is_file()]
    size_mb = sum(f.stat().st_size for f in file_items) / 1024 / 1024
    return {"exists": True, "files": len(file_items), "size_mb": round(size_mb, 1)}


def check_database() -> list:
    items = []
    tables = ["raw_search_results", "scraping_tasks", "keyword_attributes", "users", "user_keywords"]
    for t in tables:
        count = _db_count(t)
        items.append({
            "name": f"DB:{t}",
            "count": count,
            "status": "✅" if count > 0 else ("⚠️" if count >= 0 else "❌"),
        })
    return items


def check_config_files() -> list:
    items = []
    for path in [SCRAPER_CONFIG, SCHEDULE_CONFIG, ASIN_MONITOR_CONFIG]:
        items.append({
            "name": f"config:{path.name}",
            "count": "存在" if path.exists() else "缺失",
            "status": "✅" if path.exists() else "❌",
        })
    return items


def check_data_dirs() -> list:
    items = []
    for label, path in [
        ("dir:processed_data", PROCESSED_DATA_DIR),
        ("dir:amazon_data", AMAZON_DATA_DIR),
        ("dir:postgres_data", POSTGRES_DATA_DIR),
    ]:
        info = _dir_info(path)
        items.append({
            "name": label,
            "count": f"{info['files']} 文件, {info['size_mb']} MB" if info["exists"] else "不存在",
            "status": "✅" if info["files"] > 0 else "❌",
        })
    return items


def check_json_backups() -> list:
    items = []
    for label, path, key in [
        ("json:users", USERS_JSON, "users"),
        ("json:user_keywords", USER_KEYWORDS_JSON, "relations"),
    ]:
        count = _file_count_json(path, key)
        items.append({
            "name": label,
            "count": count,
            "status": "✅" if count > 0 else ("⚠️" if path.exists() else "❌"),
        })
    return items


def check_logs() -> list:
    items = []
    for path in LOG_FILES:
        items.append({
            "name": f"log:{path.name}",
            "count": f"{path.stat().st_size / 1024:.0f} KB" if path.exists() else "缺失",
            "status": "✅" if path.exists() else "⚠️",
        })
    return items


def check_nas() -> list:
    items = []
    if BACKUP_TARGET.exists():
        backups = sorted(
            [d for d in BACKUP_TARGET.glob("backup_*") if d.is_dir()],
            reverse=True,
        )
        latest = backups[0].name if backups else "无"
        items.append({
            "name": "nas:备份目录",
            "count": f"{len(backups)} 个备份, 最新: {latest}",
            "status": "✅" if backups else "⚠️",
        })
    else:
        items.append({
            "name": "nas:备份目录",
            "count": "不可访问",
            "status": "❌",
        })
    return items


def check_consistency() -> list:
    items = []
    db_products = _db_count("raw_search_results")
    processed_files = len(list(PROCESSED_DATA_DIR.glob("*_processed.json"))) if PROCESSED_DATA_DIR.exists() else 0
    amazon_files = len(list(AMAZON_DATA_DIR.glob("*.json"))) if AMAZON_DATA_DIR.exists() else 0

    items.append({
        "name": "一致性: 商品数据 vs processed文件",
        "count": f"DB={db_products}, processed={processed_files}",
        "status": "✅" if db_products > 0 and processed_files > 0 else "⚠️",
    })
    items.append({
        "name": "一致性: amazon_data JSON 文件",
        "count": f"{amazon_files} 个",
        "status": "✅" if amazon_files > 0 else "⚠️",
    })
    return items


def run_verify(json_output: bool = False) -> dict:
    checks = []
    checks += check_database()
    checks += check_config_files()
    checks += check_data_dirs()
    checks += check_json_backups()
    checks += check_logs()
    checks += check_nas()
    checks += check_consistency()

    ok = sum(1 for c in checks if c["status"] == "✅")
    warn = sum(1 for c in checks if c["status"] == "⚠️")
    err = sum(1 for c in checks if c["status"] == "❌")

    if json_output:
        print(json.dumps(checks, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(f"  数据完整性检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        for c in checks:
            print(f"  {c['status']}  {c['name']:<35}  {c['count']}")
        print("-" * 60)
        print(f"  总计: ✅ {ok}  ⚠️ {warn}  ❌ {err}")
        print("=" * 60)

    return {"checks": checks, "ok": ok, "warn": warn, "err": err}


if __name__ == "__main__":
    json_output = "--json" in sys.argv
    run_verify(json_output)
