# backend/app/api/scraping.py
from fastapi import APIRouter, BackgroundTasks, Query, WebSocket, WebSocketDisconnect, Depends, HTTPException,Header
from sqlalchemy.orm import Session
from app.database import get_db
from typing import Optional
import asyncio
import logging
from datetime import datetime
from app.models import ScrapingTask
from app.scraper.pipeline import run_now, run_daily, run_weekly, stop_task as pipeline_stop_task, stop_all_tasks as pipeline_stop_all_tasks, stop_all_completely, is_globally_stopped, reset_global_stop
from pydantic import BaseModel
from typing import List, Optional as OptionalType

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/tasks/running") # ZY 0422
def get_running_tasks():
    """获取正在运行的任务"""
    from app.models import ScrapingTask
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        # 查找状态为 running 或 pending 的任务
        running = db.query(ScrapingTask).filter(
            ScrapingTask.status.in_(['running', 'pending'])
        ).all()
        return running
    finally:
        db.close()

@router.post("/scrape") # ZY 0422 使用使用 asyncio.to_thread 异步
async def start_scraping(
    background_tasks: BackgroundTasks,
    keyword: Optional[str] = Query(None),
    pages: Optional[int] = Query(None)
):
    """启动爬取任务"""
    # 检查全局停止标志
    if is_globally_stopped():
        raise HTTPException(status_code=409, detail="系统已全局停止，请先调用 /api/tasks/stop/reset 重置后再启动")

    # 使用 asyncio.to_thread 避免阻塞主线程
    async def run_in_thread():
        from app.scraper.pipeline import run_now
        # 在线程池中执行同步代码
        result = await asyncio.to_thread(run_now, keyword, pages)
        return result
        # background_tasks.add_task(run_now, keyword, pages)

    # 创建后台任务
    task = asyncio.create_task(run_in_thread())
    return {
        "message": "任务已启动",
        "keyword": keyword or "所有关键词",
        "pages": pages or "自动"
    }


@router.post("/scrape/daily")
def trigger_daily(background_tasks: BackgroundTasks):
    """触发每日任务"""
    from app.scraper.pipeline import run_daily
    
    background_tasks.add_task(run_daily)
    return {"message": "每日任务已启动"}


@router.post("/scrape/weekly")
def trigger_weekly(background_tasks: BackgroundTasks):
    """触发每周任务"""
    from app.scraper.pipeline import run_weekly
    
    background_tasks.add_task(run_weekly)
    return {"message": "每周任务已启动"}


# 在文件末尾添加
@router.post("/tasks/{task_id}/stop")
def stop_single_task(
    task_id: int, 
    password: str = Header(..., alias="X-Password"),
    db: Session = Depends(get_db)
):
    """终止正在运行的任务（需要密码验证）"""
    from app.models import ScrapingTask
    
    # 密码验证
    if password != "HZX123456":
        raise HTTPException(status_code=403, detail="密码错误，无权终止任务")
    
    task = db.query(ScrapingTask).filter(ScrapingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status not in ['running', 'pending']:
        raise HTTPException(status_code=400, detail="只能终止运行中或等待中的任务")
    
    # 调用 pipeline 的 stop_task 函数
    from app.scraper.pipeline import stop_task as pipeline_stop_task
    pipeline_stop_task(task_id)

    # 更新任务状态为失败
    task.status = 'failed'
    task.error_message = '用户手动终止'
    task.completed_at = datetime.now()
    db.commit()
    
    return {"message": "任务已终止", "task_id": task_id}


@router.post("/tasks/stop-all")
def stop_all_tasks(
    password: str = Header(..., alias="X-Password"),
    db: Session = Depends(get_db)
):
    """彻底停止所有爬取任务（需要密码验证）
    
    功能：
    1. 设置全局停止标志，后续关键词不再启动
    2. 标记数据库中所有 running/pending 的任务为 stopped
    3. 正在执行的任务在下一个检查点会自行停止
    """
    # 密码验证
    if password != "HZX123456":
        raise HTTPException(status_code=403, detail="密码错误，无权终止任务")
    
    # 调用全局彻底停止
    result = stop_all_completely()
    
    return {
        "message": f"已彻底停止 {result['stopped_count']} 个任务，后续关键词不再执行",
        "stopped_count": result['stopped_count'],
        "status": "stopped"
    }


@router.post("/tasks/stop/reset")
def reset_stop_flag(
    password: str = Header(..., alias="X-Password")
):
    """重置全局停止标志，允许继续爬取（需要密码验证）"""
    if password != "HZX123456":
        raise HTTPException(status_code=403, detail="密码错误")
    
    result = reset_global_stop()
    return {
        "message": "全局停止标志已清除，可以继续爬取",
        "was_stopped": result['was_stopped']
    }


@router.get("/tasks/stop/status")
def get_stop_status():
    """查看当前全局停止状态"""
    return {
        "globally_stopped": is_globally_stopped(),
        "message": "已全局停止" if is_globally_stopped() else "正常运行中"
    }

# ========== 定时任务管理（Cron表达式） ==========

class ScheduleJobCreate(BaseModel):
    name: str
    cron: str
    keywords: List[str] = []
    pages: OptionalType[int] = None
    enabled: bool = True
    description: str = ""


class ScheduleJobUpdate(BaseModel):
    name: OptionalType[str] = None
    cron: OptionalType[str] = None
    keywords: OptionalType[List[str]] = None
    pages: OptionalType[int] = None
    enabled: OptionalType[bool] = None
    description: OptionalType[str] = None


@router.get("/schedule/jobs")
def get_schedule_jobs():
    """获取所有定时任务"""
    from app.scraper.schedule_config import load_schedule_config
    config = load_schedule_config()
    return config.get('jobs', [])


@router.post("/schedule/jobs")
def create_schedule_job(job: ScheduleJobCreate):
    """创建定时任务"""
    from app.scraper.schedule_config import add_schedule_job
    job_dict = job.model_dump()
    result = add_schedule_job(job_dict)
    return result


@router.put("/schedule/jobs/{job_id}")
def update_schedule_job(job_id: str, job: ScheduleJobUpdate):
    """更新定时任务"""
    from app.scraper.schedule_config import update_schedule_job
    updates = {k: v for k, v in job.model_dump().items() if v is not None}
    result = update_schedule_job(job_id, updates)
    return result


@router.delete("/schedule/jobs/{job_id}")
def delete_schedule_job(job_id: str):
    """删除定时任务"""
    from app.scraper.schedule_config import delete_schedule_job
    success = delete_schedule_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"message": "已删除"}


@router.post("/schedule/reload")
def reload_schedule():
    """重新加载定时任务"""
    from app.main import reload_cron_jobs
    reload_cron_jobs()
    return {"message": "定时任务已重新加载"}


@router.get("/schedule/jobs/{job_id}/runs")
def get_job_runs(job_id: str):
    """获取任务运行记录"""
    from app.scraper.schedule_config import get_job_run_history
    return get_job_run_history(job_id)


@router.post("/schedule/jobs/{job_id}/run-record")
def record_job_run(job_id: str, status: str = "success", note: str = ""):
    """记录任务运行"""
    from app.scraper.schedule_config import record_job_run
    record_job_run(job_id, status, note)
    return {"message": "已记录"}