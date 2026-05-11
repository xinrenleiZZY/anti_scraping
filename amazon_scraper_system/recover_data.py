"""
数据恢复脚本 - 从文件系统重建数据库
恢复来源:
  1. processed_data/*_processed.json → raw_search_results
  2. scraper_config.json → keyword_attributes
  3. amazon_data/*_report.txt → scraping_tasks
"""
import json
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import re
from datetime import datetime
from pathlib import Path

import psycopg2

BASE_DIR = Path(__file__).parent
PROCESSED_DIR = BASE_DIR / "backend" / "app" / "scraper" / "processed_data"
AMAZON_DATA_DIR = BASE_DIR / "backend" / "app" / "scraper" / "amazon_data"
SCRAPER_CONFIG = BASE_DIR / "backend" / "app" / "scraper" / "scraper_config.json"

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:123456@localhost:5200/amazon_scraper")


def parse_db_url(url: str):
    """解析 DATABASE_URL"""
    m = re.match(r"postgresql://(.+?):(.+?)@(.+?):(\d+)/(.+)", url)
    if not m:
        raise ValueError(f"无法解析 DATABASE_URL: {url}")
    user, pwd, host, port, dbname = m.groups()
    return {"user": user, "password": pwd, "host": host, "port": int(port), "dbname": dbname}


def get_conn():
    db = parse_db_url(DATABASE_URL)
    return psycopg2.connect(**db)


def recover_raw_search_results():
    """从 processed_data/*_processed.json 恢复 raw_search_results 表"""
    json_files = sorted(PROCESSED_DIR.glob("*_processed.json"))
    if not json_files:
        print("⚠️ 未找到 processed JSON 文件，跳过 raw_search_results 恢复")
        return

    print(f"\n📦 找到 {len(json_files)} 个 processed JSON 文件")

    conn = get_conn()
    cur = conn.cursor()

    total_rows = 0
    total_failed = 0

    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ❌ 读取失败: {fpath.name} - {e}")
            total_failed += 1
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
                    """
                    INSERT INTO raw_search_results
                        (data_index, page, index_position, ad_type, ad_rank, organic_rank,
                         asin, title, url, price_current, price_list,
                         rating_stars, rating_count, is_prime,
                         image_small, image_large, brand_name,
                         inner_products, inner_products_count,
                         postal_code, keyword, date, scraped_at)
                    VALUES
                        (%s, %s, %s, %s, %s, %s,
                         %s, %s, %s, %s, %s,
                         %s, %s, %s,
                         %s, %s, %s,
                         %s, %s,
                         %s, %s, %s, %s)
                    """,
                    (
                        row.get("data_index"),
                        row.get("page"),
                        row.get("index"),
                        row.get("ad_type"),
                        str(row.get("ad_rank")) if row.get("ad_rank") is not None else None,
                        row.get("organic_rank"),
                        row.get("asin"),
                        row.get("title"),
                        row.get("url"),
                        row.get("price_current"),
                        row.get("price_list"),
                        row.get("rating_stars"),
                        row.get("rating_count"),
                        row.get("is_prime"),
                        row.get("image_small"),
                        row.get("image_large"),
                        row.get("brand_name"),
                        inner,
                        row.get("inner_products_count", 0),
                        postal,
                        row.get("keyword"),
                        date_val,
                        scraped_at,
                    ),
                )
                total_rows += 1
            except Exception as e:
                total_failed += 1
                print(f"  ⚠️ 行插入失败 [{fpath.name}]: {e}")

        print(f"  ✅ {fpath.name} 导入完成")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\n✅ raw_search_results 恢复完成: 成功 {total_rows} 行, 失败 {total_failed}")


def recover_keyword_attributes():
    """从 scraper_config.json 恢复 keyword_attributes 表"""
    if not SCRAPER_CONFIG.exists():
        print("⚠️ 未找到 scraper_config.json，跳过 keyword_attributes 恢复")
        return

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
        print("⚠️ 配置中无关键词属性数据，跳过 keyword_attributes 恢复")
        return

    records = []
    for kw in sorted(all_keywords):
        tags = keyword_tags.get(kw, [])
        festival = keyword_festivals.get(kw, "")
        festival_type = keyword_festival_types.get(kw, "")
        hot_season = keyword_hot_seasons.get(kw, "")
        records.append((kw, json.dumps(tags), festival, festival_type, hot_season))

    print(f"\n📦 从 scraper_config.json 找到 {len(records)} 个关键词的属性")

    conn = get_conn()
    cur = conn.cursor()
    inserted = 0

    for kw, tags, festival, festival_type, hot_season in records:
        try:
            cur.execute(
                """
                INSERT INTO keyword_attributes (keyword, tags, festival, festival_type, hot_season)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (keyword) DO UPDATE SET
                    tags = EXCLUDED.tags,
                    festival = EXCLUDED.festival,
                    festival_type = EXCLUDED.festival_type,
                    hot_season = EXCLUDED.hot_season,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (kw, tags, festival, festival_type, hot_season),
            )
            inserted += 1
        except Exception as e:
            print(f"  ⚠️ 插入失败 [{kw}]: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ keyword_attributes 恢复完成: 成功 {inserted} 行")


def recover_scraping_tasks():
    """从 amazon_data/*_report.txt 重建 scraping_tasks 表"""
    report_files = sorted(AMAZON_DATA_DIR.glob("*_report.txt"))
    if not report_files:
        print("⚠️ 未找到 report.txt 文件，跳过 scraping_tasks 恢复")
        return

    print(f"\n📦 找到 {len(report_files)} 个 report.txt 文件")

    conn = get_conn()
    cur = conn.cursor()
    inserted = 0

    for fpath in report_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"  ❌ 读取失败: {fpath.name} - {e}")
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
            print(f"  ⚠️ 无法解析关键词: {fpath.name}")
            continue

        try:
            cur.execute(
                """
                INSERT INTO scraping_tasks (keyword, total_items, status, started_at, completed_at, source_file)
                VALUES (%s, %s, 'completed', %s, %s, %s)
                """,
                (keyword, total_items, scraped_time, scraped_time, fpath.name),
            )
            inserted += 1
        except Exception as e:
            print(f"  ⚠️ 插入失败 [{keyword}]: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ scraping_tasks 恢复完成: 成功 {inserted} 行")


if __name__ == "__main__":
    print("=" * 60)
    print("  Amazon Scraper 数据恢复脚本")
    print(f"  数据库: {DATABASE_URL}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if len(sys.argv) > 1:
        targets = sys.argv[1:]
    else:
        targets = ["all"]

    if "all" in targets or "raw_search_results" in targets:
        recover_raw_search_results()

    if "all" in targets or "keyword_attributes" in targets:
        recover_keyword_attributes()

    if "all" in targets or "scraping_tasks" in targets:
        recover_scraping_tasks()

    print("\n" + "=" * 60)
    print("  恢复完成！")
    print("=" * 60)
    print("\n⚠️  users 和 user_keywords 表无法从文件恢复，需手动创建。")
