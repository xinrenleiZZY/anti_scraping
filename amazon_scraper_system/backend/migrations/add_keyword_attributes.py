"""
迁移脚本：将关键词属性从 JSON 文件迁移到数据库
运行方式：在 backend 目录下执行 python -m migrations.add_keyword_attributes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path
from app.database import SessionLocal, engine
from app.models import Base, KeywordAttribute

# 配置文件路径
CONFIG_PATH = Path(__file__).parent.parent / "app" / "scraper" / "scraper_config.json"


def create_table():
    """创建 keyword_attributes 表"""
    print("📦 创建 keyword_attributes 表...")
    Base.metadata.create_all(bind=engine, tables=[KeywordAttribute.__table__])
    print("✅ 表创建完成")


def migrate_data():
    """将 JSON 文件数据迁移到数据库"""
    print("📖 读取 JSON 配置文件...")
    
    if not CONFIG_PATH.exists():
        print("⚠️ 配置文件不存在，跳过数据迁移")
        return
    
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    db = SessionLocal()
    try:
        keyword_tags = config.get("keyword_tags", {})
        keyword_festivals = config.get("keyword_festivals", {})
        keyword_festival_types = config.get("keyword_festival_types", {})
        keyword_hot_seasons = config.get("keyword_hot_seasons", {})
        
        # 获取所有关键词
        all_keywords = set()
        all_keywords.update(keyword_tags.keys())
        all_keywords.update(keyword_festivals.keys())
        all_keywords.update(keyword_festival_types.keys())
        all_keywords.update(keyword_hot_seasons.keys())
        
        print(f"📊 找到 {len(all_keywords)} 个有关键词属性的关键词")
        
        migrated_count = 0
        for keyword in all_keywords:
            attrs = db.query(KeywordAttribute).filter(KeywordAttribute.keyword == keyword).first()
            if not attrs:
                attrs = KeywordAttribute(keyword=keyword)
                db.add(attrs)
            
            attrs.tags = keyword_tags.get(keyword, [])
            attrs.festival = keyword_festivals.get(keyword, "")
            attrs.festival_type = keyword_festival_types.get(keyword, "")
            attrs.hot_season = keyword_hot_seasons.get(keyword, "")
            migrated_count += 1
        
        db.commit()
        print(f"✅ 成功迁移 {migrated_count} 条记录到数据库")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        db.close()


def verify_migration():
    """验证迁移结果"""
    db = SessionLocal()
    try:
        count = db.query(KeywordAttribute).count()
        print(f"📊 数据库中共有 {count} 条关键词属性记录")
        
        # 显示前5条作为示例
        sample = db.query(KeywordAttribute).limit(5).all()
        for attrs in sample:
            print(f"  - {attrs.keyword}: tags={attrs.tags}, festival={attrs.festival}, type={attrs.festival_type}, hot={attrs.hot_season}")
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("开始迁移关键词属性数据")
    print("=" * 50)
    
    create_table()
    migrate_data()
    verify_migration()
    
    print("\n✅ 迁移完成！")
    print("💡 提示：现在可以重启后端服务了")