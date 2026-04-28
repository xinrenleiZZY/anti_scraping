# backend/app/scraper/schedule_config.py

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 配置文件路径
SCHEDULE_CONFIG_PATH = Path(__file__).parent / "schedule_config.json"

# 默认配置
DEFAULT_CONFIG = {
    "jobs": [
        {
            "id": "daily_job",
            "name": "每日爬取",
            "enabled": True,
            "cron": "0 9 * * *",
            "keywords": [],
            "pages": None,
            "description": "每天早上9点自动爬取所有关键词",
            "created_at": None
        },
        {
            "id": "weekly_job",
            "name": "每周爬取",
            "enabled": True,
            "cron": "0 9 * * 1",
            "keywords": [],
            "pages": None,
            "description": "每周一早上9点自动爬取所有关键词",
            "created_at": None
        }
    ]
}


def load_schedule_config() -> Dict:
    """加载定时任务配置"""
    if SCHEDULE_CONFIG_PATH.exists():
        try:
            with open(SCHEDULE_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 确保有 jobs 字段
                if 'jobs' not in config:
                    config['jobs'] = DEFAULT_CONFIG['jobs']
                return config
        except Exception as e:
            logger.error(f"加载定时任务配置失败: {e}")
            return DEFAULT_CONFIG.copy()
    else:
        # 创建默认配置文件
        save_schedule_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_schedule_config(config: Dict):
    """保存定时任务配置"""
    try:
        # 确保目录存在
        SCHEDULE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SCHEDULE_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info("定时任务配置已保存")
    except Exception as e:
        logger.error(f"保存定时任务配置失败: {e}")
        raise


def add_schedule_job(job: Dict) -> Dict:
    """添加定时任务"""
    config = load_schedule_config()
    
    # 生成唯一ID
    if 'id' not in job or not job['id']:
        job['id'] = f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 添加创建时间
    job['created_at'] = datetime.now().isoformat()
    
    config['jobs'].append(job)
    save_schedule_config(config)
    
    logger.info(f"已添加定时任务: {job['name']} (ID: {job['id']})")
    return job


def update_schedule_job(job_id: str, updates: Dict) -> Dict:
    """更新定时任务"""
    config = load_schedule_config()
    
    for job in config['jobs']:
        if job['id'] == job_id:
            # 更新字段，保留 id 和 created_at
            for key, value in updates.items():
                if key not in ['id', 'created_at']:
                    job[key] = value
            job['updated_at'] = datetime.now().isoformat()
            save_schedule_config(config)
            logger.info(f"已更新定时任务: {job['name']} (ID: {job_id})")
            return job
    
    raise ValueError(f"未找到ID为 {job_id} 的任务")


def delete_schedule_job(job_id: str) -> bool:
    """删除定时任务"""
    config = load_schedule_config()
    original_length = len(config['jobs'])
    
    config['jobs'] = [j for j in config['jobs'] if j['id'] != job_id]
    
    if len(config['jobs']) < original_length:
        save_schedule_config(config)
        logger.info(f"已删除定时任务: {job_id}")
        return True
    
    return False


def get_schedule_job(job_id: str) -> Optional[Dict]:
    """获取单个定时任务"""
    config = load_schedule_config()
    for job in config['jobs']:
        if job['id'] == job_id:
            return job
    return None


def toggle_schedule_job(job_id: str, enabled: bool) -> Optional[Dict]:
    """启用/禁用定时任务"""
    return update_schedule_job(job_id, {'enabled': enabled})


# Cron 表达式验证
def validate_cron(cron: str) -> bool:
    """验证 Cron 表达式是否有效"""
    parts = cron.split()
    if len(parts) != 5:
        return False
    
    # 简单验证各字段
    fields = ['minute', 'hour', 'day', 'month', 'day_of_week']
    for i, part in enumerate(parts):
        if part == '*':
            continue
        # 检查是否包含数字、逗号、连字符、斜杠
        import re
        if not re.match(r'^[\d\*,/\-]+$', part):
            return False
    
    return True


# Cron 表达式说明
CRON_HELP = """
Cron 表达式格式：分 时 日 月 周

示例：
- 0 9 * * *    每天 09:00
- 0 18 * * *   每天 18:00
- 0 9 * * 1    每周一 09:00
- 0 9 * * 5    每周五 09:00
- 0 0 1 * *    每月1号 00:00
- */30 * * * * 每30分钟
"""