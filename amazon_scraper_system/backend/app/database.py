from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:123456@localhost:5200/amazon_scraper")

def create_engine_with_retry(max_retries=10, delay=3):
    for i in range(max_retries):
        try:
            engine = create_engine(DATABASE_URL)
            engine.connect().close()
            logger.info("数据库连接成功")
            return engine
        except Exception as e:
            logger.warning(f"数据库连接失败 ({i+1}/{max_retries}): {e}")
            if i < max_retries - 1:
                time.sleep(delay)
    raise Exception("数据库连接失败，已达最大重试次数")

engine = create_engine_with_retry()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()