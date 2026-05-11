"""
数据管控 - 公共路径配置
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_CONTROL_DIR = PROJECT_ROOT / "data_control"

BACKEND_DIR = PROJECT_ROOT / "backend"
SCRAPER_DIR = BACKEND_DIR / "app" / "scraper"

SCRAPER_CONFIG = SCRAPER_DIR / "scraper_config.json"
SCHEDULE_CONFIG = SCRAPER_DIR / "schedule_config.json"
ASIN_MONITOR_CONFIG = BACKEND_DIR / "asin_monitor_config.json"

AMAZON_DATA_DIR = SCRAPER_DIR / "amazon_data"
PROCESSED_DATA_DIR = SCRAPER_DIR / "processed_data"
POSTGRES_DATA_DIR = PROJECT_ROOT / "postgres_data"

USERS_JSON = DATA_CONTROL_DIR / "users.json"
USER_KEYWORDS_JSON = DATA_CONTROL_DIR / "user_keywords.json"

LOG_FILES = [
    BACKEND_DIR / "amazon_scraper.log",
    BACKEND_DIR / "amazon_scraper_old.log",
    SCRAPER_DIR / "amazon_scraper.log",
    PROJECT_ROOT / "amazon_scraper_old.log",
]

CONFIG_FILES = [
    SCRAPER_CONFIG,
    SCHEDULE_CONFIG,
    ASIN_MONITOR_CONFIG,
]

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:123456@localhost:5200/amazon_scraper",
)

BACKUP_TARGET = Path("//192.168.40.3/钟正洋/amazon_scraper_system")

TIMESTAMP_FILE = DATA_CONTROL_DIR / ".last_backup"
