"""
backup.py — 数据备份脚本
备份范围:
  1. 数据库 → SQL 导出（users / user_keywords / scraping_tasks / raw_search_results / keyword_attributes）
  2. DB 关键表 → JSON 文件（users / user_keywords）
  3. 配置文件（scraper_config / schedule_config / asin_monitor_config）
  4. 爬虫数据目录（amazon_data / processed_data）
  5. 日志文件（4 个 .log）
目标路径: \\192.168.40.3\钟正洋\amazon_scraper_system
支持 Windows 定时任务调用
"""

import json
import os
import re
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import sys
_here = Path(__file__).resolve().parent
_root = _here.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from data_control.config import (
    BACKUP_TARGET, TIMESTAMP_FILE, DATABASE_URL,
    SCRAPER_CONFIG, SCHEDULE_CONFIG, ASIN_MONITOR_CONFIG,
    AMAZON_DATA_DIR, PROCESSED_DATA_DIR, POSTGRES_DATA_DIR,
    LOG_FILES, CONFIG_FILES, USERS_JSON, USER_KEYWORDS_JSON,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("backup")


def parse_db_url(url: str) -> dict:
    m = re.match(r"postgresql://(.+?):(.+?)@(.+?):(\d+)/(.+)", url)
    if not m:
        raise ValueError(f"无法解析 DATABASE_URL: {url}")
    user, pwd, host, port, dbname = m.groups()
    return {"user": user, "password": pwd, "host": host, "port": int(port), "dbname": dbname}


def ensure_target() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUP_TARGET / f"backup_{ts}"
    target.mkdir(parents=True, exist_ok=True)
    logger.info(f"备份目录: {target}")
    return target


def backup_sync_json(target: Path) -> bool:
    """调用 sync.py 导出 DB 数据到 JSON，再复制到备份目录"""
    try:
        from data_control.sync import sync_all
        result = sync_all()
        logger.info(f"  JSON 同步结果: {result}")
    except Exception as e:
        logger.warning(f"  同步 JSON 失败（将复制现有文件）: {e}")

    copied = 0
    for src in [USERS_JSON, USER_KEYWORDS_JSON]:
        if src.exists():
            shutil.copy2(src, target / src.name)
            copied += 1
            logger.info(f"  OK  {src.name}")
        else:
            logger.warning(f"  跳过 {src.name}（文件不存在）")
    return copied > 0


def backup_pg_dump(target: Path) -> bool:
    """docker exec pg_dump 导出全部表"""
    try:
        db = parse_db_url(DATABASE_URL)
    except Exception as e:
        logger.error(f"  解析 DATABASE_URL 失败: {e}")
        return False

    out_file = target / "database_dump.sql"
    cmd = (
        f"docker exec amazon_postgres pg_dump"
        f" -U {db['user']} -d {db['dbname']}"
        f" --no-owner --no-acl"
    )
    logger.info(f"  执行: {cmd}")
    result = os.popen(cmd).read()
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(result)
    size_kb = out_file.stat().st_size / 1024
    logger.info(f"  OK  database_dump.sql ({size_kb:.0f} KB)")
    return True


def backup_config_files(target: Path) -> int:
    config_target = target / "config"
    config_target.mkdir(exist_ok=True)
    count = 0
    for src in CONFIG_FILES:
        if src.exists():
            shutil.copy2(src, config_target / src.name)
            count += 1
            logger.info(f"  OK  config/{src.name}")
        else:
            logger.warning(f"  跳过 config/{src.name}（不存在）")
    return count


def backup_dirs(target: Path) -> dict:
    results = {}
    dir_target = target / "data"
    dir_target.mkdir(exist_ok=True)

    for label, src in [
        ("processed_data", PROCESSED_DATA_DIR),
        ("amazon_data", AMAZON_DATA_DIR),
    ]:
        dest = dir_target / label
        if src.exists():
            try:
                shutil.copytree(src, dest, dirs_exist_ok=True)
                file_count = sum(1 for _ in dest.rglob("*") if _.is_file())
                size_mb = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file()) / 1024 / 1024
                logger.info(f"  OK  data/{label} ({file_count} 文件, {size_mb:.1f} MB)")
                results[label] = "ok"
            except Exception as e:
                logger.error(f"  失败 data/{label}: {e}")
                results[label] = f"error: {e}"
        else:
            logger.warning(f"  跳过 data/{label}（目录不存在）")
            results[label] = "skipped"
    return results


def backup_logs(target: Path) -> int:
    log_target = target / "logs"
    log_target.mkdir(exist_ok=True)
    count = 0
    for src in LOG_FILES:
        if src.exists():
            shutil.copy2(src, log_target / src.name)
            count += 1
            logger.info(f"  OK  logs/{src.name}")
    return count


def write_manifest(target: Path, results: dict) -> None:
    manifest = {
        "backup_time": datetime.now().isoformat(),
        "source": str(Path(__file__).resolve().parents[1]),
        "results": results,
    }
    with open(target / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    logger.info("  OK  manifest.json")


def write_timestamp() -> None:
    TIMESTAMP_FILE.write_text(datetime.now().isoformat(), encoding="utf-8")


def run_backup() -> dict:
    logger.info("=" * 60)
    logger.info("  数据备份开始")
    logger.info(f"  目标: {BACKUP_TARGET}")
    logger.info("=" * 60)

    target = ensure_target()
    results = {}

    logger.info("\n[1/6] 导出 DB 关键表到 JSON ...")
    results["json_sync"] = backup_sync_json(target)

    logger.info("\n[2/6] pg_dump 全库 SQL ...")
    results["pg_dump"] = backup_pg_dump(target)

    logger.info("\n[3/6] 配置文件 ...")
    results["config_files"] = backup_config_files(target)

    logger.info("\n[4/6] 爬虫数据目录 ...")
    results["data_dirs"] = backup_dirs(target)

    logger.info("\n[5/6] 日志文件 ...")
    results["logs"] = backup_logs(target)

    logger.info("\n[6/6] 写入 manifest ...")
    write_manifest(target, results)

    write_timestamp()

    logger.info("\n" + "=" * 60)
    logger.info("  备份完成！")
    logger.info(f"  路径: {target}")
    logger.info("=" * 60)
    return results


if __name__ == "__main__":
    run_backup()
