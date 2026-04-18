from fastapi import APIRouter, BackgroundTasks
from backend.app.scraper.pipeline import run_now, run_daily

router = APIRouter()

@router.post("/scrape")
def start_scraping(keyword: str = None, pages: int = None, background_tasks: BackgroundTasks):
    """启动爬取任务"""
    background_tasks.add_task(run_now, keyword, pages)
    return {"message": "任务已启动", "keyword": keyword or "all"}

@router.post("/scrape/daily")
def trigger_daily(background_tasks: BackgroundTasks):
    """触发每日任务"""
    background_tasks.add_task(run_daily)
    return {"message": "每日任务已启动"}

@router.post("/scrape/weekly")
def trigger_weekly(background_tasks: BackgroundTasks):
    """触发每周任务"""
    background_tasks.add_task(run_weekly)
    return {"message": "每周任务已启动"}