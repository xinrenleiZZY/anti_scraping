"""
recover.py — 数据库 / 文件恢复脚本

恢复目标:
  db_raw       → raw_search_results 表（processed_data/*_processed.json）
  db_tasks     → scraping_tasks 表（amazon_data/*_report.txt）
  db_kwattrs   → keyword_attributes 表（scraper_config.json）
  db_users     → users + user_keywords 表（users.json + user_keywords.json）
  config       → 配置文件（scraper_config / schedule_config / asin_monitor_config）
  data         → 爬虫数据目录（processed_data / amazon_data）
  logs         → 日志文件

用法:
  python data_control/recover.py                          # 全部恢复
  python data_control/recover.py db_users                 # 只恢复用户
  python data_control/recover.py config data              # 恢复配置 + 数据目录
  python data_control/recover.py --list-backups           # 列出可用备份
  python data_control/recover.py --source backup_20260511_120000 db_raw
"""

import argparse
import json
import sys
import io
import re
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import psycopg2

_here = Path(__file__).resolve().parent
_root = _here.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from data_control.config import (
    BACKUP_TARGET, DATABASE_URL,
    PROCESSED_DATA_DIR, AMAZON_DATA_DIR, SCRAPER_CONFIG,
    USERS_JSON, USER_KEYWORDS_JSON,
    SCHEDULE_CONFIG, ASIN_MONITOR_CONFIG, CONFIG_FILES,
    LOG_FILES, SCRAPER_DIR, BACKEND_DIR,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("recover")


def parse_db_url(url: str) -> dict:
    m = re.match(r"postgresql://(.+?):(.+?)@(.+?):(\d+)/(.+)", url)
    if not m:
        raise ValueError(f"无法解析 DATABASE_URL: {url}")
    user, pwd, host, port, dbname = m.groups()
    return {"user": user, "password": pwd, "host": host, "port": int(port), "dbname": dbname}


def get_conn():
    db = parse_db_url(DATABASE_URL)
    return psycopg2.connect(**db)


def list_backups() -> List[Path]:
    if not BACKUP_TARGET.exists():
        print("⚠️ NAS 备份目录不可访问")
        return []
    backups = sorted(
        [d for d in BACKUP_TARGET.iterdir() if d.is_dir() and d.name.startswith("backup_")],
        reverse=True,
    )
    if not backups:
        print("⚠️ 无备份记录")
        return []
    print(f"可用备份 ({len(backups)} 个):")
    for b in backups:
        manifest = b / "manifest.json"
        note = ""
        if manifest.exists():
            try:
                m = json.loads(manifest.read_text(encoding="utf-8"))
                note = f"  --  {m.get('backup_time', '')}"
            except Exception:
                pass
        print(f"  {b.name}{note}")
    return backups


def find_backup(source: str = None) -> Optional[Path]:
    if not BACKUP_TARGET.exists():
        return None
    if source:
        candidate = BACKUP_TARGET / source
        if candidate.is_dir():
            return candidate
        print(f"⚠️ 指定备份不存在: {source}")
        return None
    backups = sorted(
        [d for d in BACKUP_TARGET.iterdir() if d.is_dir() and d.name.startswith("backup_")],
        reverse=True,
    )
    return backups[0] if backups else None


# ========== DB 恢复 ==========

def recover_raw_search_results() -> dict:
    json_files = sorted(PROCESSED_DATA_DIR.glob("*_processed.json"))
    if not json_files:
        return {"status": "skipped", "reason": "无 processed JSON 文件"}

    print(f"\n📦 raw_search_results: 找到 {len(json_files)} 个文件")

    conn = get_conn()
    cur = conn.cursor()
    total = 0
    failed = 0

    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            failed += 1
            print(f"  ❌ 读取 {fpath.name}: {e}")
            continue

        if not isinstance(data, list):
            data = [data]

        for row in data:
            try:
                inner = row.get("inner_products")
                if inner is not None:
                    inner = json.dumps(inner)
                postal = row.get("postal_code")
                if postal is not None:
                    postal = str(postal)
                scraped_at = row.get("scraped_at")
                if scraped_at and isinstance(scraped_at, str):
                    try:
                        scraped_at = datetime.fromisoformat(scraped_at)
                    except ValueError:
                        scraped_at = None
                date_val = row.get("date")
                if date_val and isinstance(date_val, str):
                    try:
                        date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
                    except ValueError:
                        date_val = None

                cur.execute(
                    """INSERT INTO raw_search_results
                    (data_index, page, index_position, ad_type, ad_rank, organic_rank,
                     asin, title, url, price_current, price_list,
                     rating_stars, rating_count, is_prime,
                     image_small, image_large, brand_name,
                     inner_products, inner_products_count,
                     postal_code, keyword, date, scraped_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        row.get("data_index"), row.get("page"), row.get("index"),
                        row.get("ad_type"), str(row.get("ad_rank")) if row.get("ad_rank") is not None else None,
                        row.get("organic_rank"), row.get("asin"), row.get("title"),
                        row.get("url"), row.get("price_current"), row.get("price_list"),
                        row.get("rating_stars"), row.get("rating_count"), row.get("is_prime"),
                        row.get("image_small"), row.get("image_large"), row.get("brand_name"),
                        inner, row.get("inner_products_count", 0),
                        postal, row.get("keyword"), date_val, scraped_at,
                    ),
                )
                total += 1
            except Exception as e:
                failed += 1

        print(f"  ✅ {fpath.name}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ raw_search_results: {total} 行, 失败 {failed}")
    return {"status": "ok", "inserted": total, "failed": failed}


def recover_scraping_tasks() -> dict:
    report_files = sorted(AMAZON_DATA_DIR.glob("*_report.txt"))
    if not report_files:
        return {"status": "skipped", "reason": "无 report.txt 文件"}

    print(f"\n📦 scraping_tasks: 找到 {len(report_files)} 个报告文件")

    conn = get_conn()
    cur = conn.cursor()
    inserted = 0

    for fpath in report_files:
        try:
            content = fpath.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  ❌ 读取 {fpath.name}: {e}")
            continue

        keyword = ""
        scraped_time = None
        total_items = 0

        for line in content.split("\n"):
            kw_match = re.match(r"关键词:\s*(.+)", line)
            if kw_match:
                keyword = kw_match.group(1).strip()
            time_match = re.match(r"时间:\s*(.+)", line)
            if time_match:
                try:
                    scraped_time = datetime.strptime(time_match.group(1).strip(), "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
            total_match = re.match(r"总元素数:\s*(\d+)", line)
            if total_match:
                total_items = int(total_match.group(1))

        if not keyword:
            print(f"  ⚠️  {fpath.name} 无法解析关键词")
            continue

        try:
            cur.execute(
                """INSERT INTO scraping_tasks (keyword, total_items, status, started_at, completed_at, source_file)
                VALUES (%s, %s, 'completed', %s, %s, %s)""",
                (keyword, total_items, scraped_time, scraped_time, fpath.name),
            )
            inserted += 1
        except Exception as e:
            print(f"  ⚠️  {keyword}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ scraping_tasks: {inserted} 行")
    return {"status": "ok", "inserted": inserted}


def recover_keyword_attributes() -> dict:
    if not SCRAPER_CONFIG.exists():
        return {"status": "skipped", "reason": "scraper_config.json 不存在"}

    with open(SCRAPER_CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)

    keyword_tags = config.get("keyword_tags", {})
    keyword_festivals = config.get("keyword_festivals", {})
    keyword_festival_types = config.get("keyword_festival_types", {})
    keyword_hot_seasons = config.get("keyword_hot_seasons", {})

    all_keywords = set()
    all_keywords.update(keyword_tags.keys())
    all_keywords.update(keyword_festivals.keys())
    all_keywords.update(keyword_festival_types.keys())
    all_keywords.update(keyword_hot_seasons.keys())

    if not all_keywords:
        return {"status": "skipped", "reason": "配置中无属性数据"}

    print(f"\n📦 keyword_attributes: {len(all_keywords)} 个关键词属性")

    conn = get_conn()
    cur = conn.cursor()
    inserted = 0

    for kw in sorted(all_keywords):
        try:
            cur.execute(
                """INSERT INTO keyword_attributes (keyword, tags, festival, festival_type, hot_season)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (keyword) DO UPDATE SET
                    tags = EXCLUDED.tags, festival = EXCLUDED.festival,
                    festival_type = EXCLUDED.festival_type, hot_season = EXCLUDED.hot_season,
                    updated_at = CURRENT_TIMESTAMP""",
                (
                    kw,
                    json.dumps(keyword_tags.get(kw, [])),
                    keyword_festivals.get(kw, ""),
                    keyword_festival_types.get(kw, ""),
                    keyword_hot_seasons.get(kw, ""),
                ),
            )
            inserted += 1
        except Exception as e:
            print(f"  ⚠️  {kw}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ keyword_attributes: {inserted} 行")
    return {"status": "ok", "inserted": inserted}


def recover_users(backup_dir: Path = None) -> dict:
    """从 users.json 恢复 users 和 user_keywords 表"""
    users_src = None

    if backup_dir:
        candidate = backup_dir / USERS_JSON.name
        if candidate.exists():
            users_src = candidate
    if not users_src and USERS_JSON.exists():
        users_src = USERS_JSON

    if not users_src:
        return {"status": "skipped", "reason": "users.json 不存在"}

    print(f"\n📦 users: 从 {users_src}")

    with open(users_src, "r", encoding="utf-8") as f:
        wrapper = json.load(f)

    users_data = wrapper.get("users", [])
    if not users_data:
        print("  ⚠️  users.json 中没有用户数据")
        return {"status": "empty"}

    conn = get_conn()
    cur = conn.cursor()
    user_count = 0
    kw_count = 0

    for u in users_data:
        try:
            cur.execute(
                "INSERT INTO users (id, name, created_at) VALUES (%s, %s, CURRENT_TIMESTAMP) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
                (u["id"], u["name"]),
            )
            user_count += 1
            for kw in u.get("keywords", []):
                cur.execute(
                    "INSERT INTO user_keywords (user_id, keyword) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (u["id"], kw),
                )
                kw_count += 1
        except Exception as e:
            print(f"  ⚠️  {u.get('name')}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ users: {user_count} 人, user_keywords: {kw_count} 条关联")
    return {"status": "ok", "users": user_count, "user_keywords": kw_count}


def recover_user_keywords_only(backup_dir: Path = None) -> dict:
    """从 user_keywords.json 恢复（仅关联）"""
    src = None

    if backup_dir:
        candidate = backup_dir / USER_KEYWORDS_JSON.name
        if candidate.exists():
            src = candidate
    if not src and USER_KEYWORDS_JSON.exists():
        src = USER_KEYWORDS_JSON

    if not src:
        return {"status": "skipped", "reason": "user_keywords.json 不存在"}

    print(f"\n📦 user_keywords: 从 {src}")

    with open(src, "r", encoding="utf-8") as f:
        wrapper = json.load(f)

    relations = wrapper.get("relations", [])
    if not relations:
        return {"status": "empty"}

    conn = get_conn()
    cur = conn.cursor()
    inserted = 0

    for r in relations:
        try:
            cur.execute(
                "INSERT INTO user_keywords (user_id, keyword) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (r["user_id"], r["keyword"]),
            )
            inserted += 1
        except Exception as e:
            print(f"  ⚠️  {r}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ user_keywords: {inserted} 条")
    return {"status": "ok", "inserted": inserted}


# ========== 文件恢复 ==========

def recover_config_files(backup_dir: Path) -> dict:
    """从备份目录恢复配置文件到原位置"""
    config_src = backup_dir / "config"
    if not config_src.exists():
        return {"status": "skipped", "reason": "备份中无 config 目录"}

    print("\n📦 恢复配置文件...")
    count = 0
    for fname in ["scraper_config.json", "schedule_config.json", "asin_monitor_config.json"]:
        src = config_src / fname
        if src.exists():
            dst_map = {
                "scraper_config.json": SCRAPER_CONFIG,
                "schedule_config.json": SCHEDULE_CONFIG,
                "asin_monitor_config.json": ASIN_MONITOR_CONFIG,
            }
            dst = dst_map.get(fname)
            if dst:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                print(f"  ✅ {fname}")
                count += 1
        else:
            print(f"  ⚠️  跳过 {fname}（备份中不存在）")
    print(f"✅ 配置文件: {count} 个")
    return {"status": "ok", "restored": count}


def recover_data_dirs(backup_dir: Path) -> dict:
    """从备份恢复 processed_data/ 和 amazon_data/ 目录"""
    data_src = backup_dir / "data"
    if not data_src.exists():
        return {"status": "skipped", "reason": "备份中无 data 目录"}

    results = {}
    targets = [
        ("processed_data", PROCESSED_DATA_DIR),
        ("amazon_data", AMAZON_DATA_DIR),
    ]

    for label, dst in targets:
        src = data_src / label
        if src.exists():
            print(f"\n📦 恢复 {label}/ ...")
            try:
                shutil.copytree(src, dst, dirs_exist_ok=True)
                file_count = sum(1 for _ in dst.rglob("*") if _.is_file())
                print(f"  ✅ {label}: {file_count} 个文件")
                results[label] = "ok"
            except Exception as e:
                print(f"  ❌ {label}: {e}")
                results[label] = f"error: {e}"
        else:
            print(f"  ⚠️  {label}: 备份中不存在")
            results[label] = "skipped"
    return results


def recover_logs(backup_dir: Path) -> dict:
    """从备份恢复日志文件"""
    log_src = backup_dir / "logs"
    if not log_src.exists():
        return {"status": "skipped", "reason": "备份中无 logs 目录"}

    print("\n📦 恢复日志文件...")
    count = 0
    for log_file in LOG_FILES:
        src = log_src / log_file.name
        if src.exists():
            shutil.copy2(src, log_file)
            print(f"  ✅ {log_file.name}")
            count += 1
    return {"status": "ok", "restored": count}


# ============================================================

DB_RECOVERY_TARGETS = {
    "db_raw":       ("raw_search_results 表",      recover_raw_search_results),
    "db_tasks":     ("scraping_tasks 表",           recover_scraping_tasks),
    "db_kwattrs":   ("keyword_attributes 表",       recover_keyword_attributes),
    "db_users":     ("users + user_keywords 表",    recover_users),
    "db_user_kw":   ("仅 user_keywords 表",         recover_user_keywords_only),
}

FILE_RECOVERY_TARGETS = ["config", "data", "logs"]

ALIAS_MAP = {
    "all":          list(DB_RECOVERY_TARGETS.keys()),
    "db":           list(DB_RECOVERY_TARGETS.keys()),
    "db_all":       list(DB_RECOVERY_TARGETS.keys()),
    "files":        FILE_RECOVERY_TARGETS,
}


def run_recover(targets: List[str], backup_dir: Path = None) -> dict:
    db_targets = []
    file_targets = []

    for t in targets:
        if t in ALIAS_MAP:
            expanded = ALIAS_MAP[t]
            for e in expanded:
                if e in DB_RECOVERY_TARGETS:
                    db_targets.append(e)
                elif e in FILE_RECOVERY_TARGETS:
                    file_targets.append(e)
        elif t in DB_RECOVERY_TARGETS:
            db_targets.append(t)
        elif t in FILE_RECOVERY_TARGETS:
            file_targets.append(t)
        else:
            print(f"⚠️ 未知目标: {t}（有效: {sorted(list(DB_RECOVERY_TARGETS.keys()) + FILE_RECOVERY_TARGETS)}）")

    if not db_targets and not file_targets:
        print("⚠️ 无有效恢复目标")
        return {}

    print("=" * 60)
    print("  Amazon Scraper 数据恢复")
    print(f"  数据库: {DATABASE_URL}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if backup_dir:
        print(f"  备份源: {backup_dir}")
    print("=" * 60)

    results = {}

    for name in db_targets:
        label, func = DB_RECOVERY_TARGETS[name]
        print(f"\n--- {label} ---")
        try:
            if name in ("db_users", "db_user_kw"):
                results[name] = func(backup_dir)
            else:
                results[name] = func()
        except Exception as e:
            print(f"  ❌ {e}")
            results[name] = {"status": "error", "error": str(e)}

    if file_targets and backup_dir:
        if "config" in file_targets:
            results["config"] = recover_config_files(backup_dir)
        if "data" in file_targets:
            results["data"] = recover_data_dirs(backup_dir)
        if "logs" in file_targets:
            results["logs"] = recover_logs(backup_dir)
    elif file_targets and not backup_dir:
        print("\n⚠️ 文件恢复需要指定备份源 (--source)")

    print("\n" + "=" * 60)
    print("  恢复汇总:")
    for name, r in results.items():
        status = r.get("status", "unknown")
        detail = ""
        if "inserted" in r:
            detail = f"({r['inserted']} 行)"
        elif "users" in r:
            detail = f"({r['users']} 用户, {r['user_keywords']} 关联)"
        elif "restored" in r:
            detail = f"({r['restored']} 个)"
        print(f"  {name}: {status} {detail}")
    print("=" * 60)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amazon Scraper 数据恢复")
    parser.add_argument(
        "targets", nargs="*", default=["all"],
        help="恢复目标: all / db / files / db_raw / db_tasks / db_kwattrs / db_users / db_user_kw / config / data / logs",
    )
    parser.add_argument(
        "--source", "-s", metavar="BACKUP_NAME",
        help="指定备份目录名，如 backup_20260511_120000（默认最新）",
    )
    parser.add_argument(
        "--list-backups", action="store_true",
        help="列出可用备份",
    )
    args = parser.parse_args()

    if args.list_backups:
        list_backups()
        sys.exit(0)

    backup_dir = find_backup(args.source)
    if backup_dir:
        print(f"使用备份: {backup_dir}")
    else:
        print("⚠️ NAS 无备份，使用本地文件")

    run_recover(args.targets, backup_dir)
