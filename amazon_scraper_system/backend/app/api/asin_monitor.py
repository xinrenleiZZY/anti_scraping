"""ASIN 重点监控 API"""
import json
import time
import hmac
import hashlib
import base64
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
import requests

from app.database import get_db
from app.models import RawSearchResult

router = APIRouter()
logger = logging.getLogger(__name__)

MONITOR_CONFIG_PATH = Path(__file__).parent.parent.parent / "asin_monitor_config.json"

RANK_TYPES = ["organic_rank", "ad_rank_sp", "ad_rank_sb", "ad_rank_video"]
RANK_LABELS = {
    "organic_rank": "自然排名",
    "ad_rank_sp": "SP广告排名",
    "ad_rank_sb": "SB品牌广告排名",
    "ad_rank_video": "视频广告排名",
}

# ===== 飞书发送 =====
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/6021c485-797a-48eb-91e5-f0b4cf144b3e"
FEISHU_SECRET = "K0MnbNq9KiF6tjgGNnkZ1c"
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/fa4291c6-ff15-4bd0-9e3d-715c412c33d1"
FEISHU_SECRET = "1pO1ZY6eBq0Pe5ohp6XXsg"

def _feishu_sign(timestamp: str, secret: str) -> str:
    s = f"{timestamp}\n{secret}"
    return base64.b64encode(hmac.new(s.encode(), digestmod=hashlib.sha256).digest()).decode()

def send_feishu(text: str):
    ts = str(int(time.time()))
    try:
        requests.post(FEISHU_WEBHOOK, json={
            "timestamp": ts, "sign": _feishu_sign(ts, FEISHU_SECRET),
            "msg_type": "text", "content": {"text": text}
        }, timeout=10)
    except Exception as e:
        logger.error(f"飞书发送失败: {e}")

# ===== 配置存储 =====
def _load() -> List[dict]:
    if MONITOR_CONFIG_PATH.exists():
        return json.loads(MONITOR_CONFIG_PATH.read_text(encoding="utf-8"))
    return []

def _save(tasks: List[dict]):
    MONITOR_CONFIG_PATH.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")

# ===== 数据模型 =====
class MonitorTaskCreate(BaseModel):
    asin: str
    monitor_name: str          # 监控人名称
    rank_types: List[str]      # 选择的排名类型
    interval_hours: float      # 查询间隔（小时，≥2）
    days: int = 30             # 分析天数

class MonitorTaskUpdate(BaseModel):
    monitor_name: Optional[str] = None
    rank_types: Optional[List[str]] = None
    interval_hours: Optional[float] = None
    days: Optional[int] = None
    enabled: Optional[bool] = None

# ===== CRUD =====
@router.get("/asin-monitor/tasks")
def list_tasks():
    return _load()

@router.post("/asin-monitor/tasks")
def create_task(body: MonitorTaskCreate):
    if body.interval_hours < 2:
        raise HTTPException(400, "查询间隔不得少于2小时")
    tasks = _load()
    task = {
        "id": f"am_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "asin": body.asin.strip().upper(),
        "monitor_name": body.monitor_name,
        "rank_types": body.rank_types,
        "interval_hours": body.interval_hours,
        "days": body.days,
        "enabled": True,
        "created_at": datetime.now().isoformat(),
        "last_run": None,
        "next_run": datetime.now().isoformat(),
    }
    tasks.append(task)
    _save(tasks)
    return task

@router.put("/asin-monitor/tasks/{task_id}")
def update_task(task_id: str, body: MonitorTaskUpdate):
    tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            for k, v in body.model_dump(exclude_none=True).items():
                t[k] = v
            if body.interval_hours is not None and body.interval_hours < 2:
                raise HTTPException(400, "查询间隔不得少于2小时")
            _save(tasks)
            return t
    raise HTTPException(404, "任务不存在")

@router.delete("/asin-monitor/tasks/{task_id}")
def delete_task(task_id: str):
    tasks = _load()
    tasks = [t for t in tasks if t["id"] != task_id]
    _save(tasks)
    return {"message": "已删除"}

@router.post("/asin-monitor/tasks/{task_id}/run")
def run_task_now(task_id: str, db: Session = Depends(get_db)):
    tasks = _load()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        raise HTTPException(404, "任务不存在")
    result = _execute_monitor_task(task, db)
    task["last_run"] = datetime.now().isoformat()
    task["next_run"] = (datetime.now() + timedelta(hours=task["interval_hours"])).isoformat()
    _save(tasks)
    return result

# ===== 核心执行逻辑 =====
def _execute_monitor_task(task: dict, db: Session) -> dict:
    asin = task["asin"]
    days = task["days"]
    rank_types = task["rank_types"]
    start_date = datetime.now().date() - timedelta(days=days)

    records = db.query(RawSearchResult).filter(
        RawSearchResult.asin.ilike(f"%{asin}%"),
        RawSearchResult.date >= start_date
    ).order_by(RawSearchResult.scraped_at.asc()).all()

    if not records:
        msg = f"【ASIN监控】{task['monitor_name']} - {asin}\n近{days}天暂无数据"
        send_feishu(msg)
        return {"message": "无数据", "sent": True}

    # 按日期聚合各类排名
    def avg_by_date(recs, rank_field, ad_type_filter=None):
        m = {}
        for r in recs:
            if ad_type_filter and r.ad_type != ad_type_filter:
                continue
            d = r.scraped_at.strftime("%m/%d")
            val = getattr(r, rank_field, None)
            if val and val > 0:
                if d not in m:
                    m[d] = {"sum": 0, "count": 0}
                m[d]["sum"] += val
                m[d]["count"] += 1
        return {d: round(v["sum"] / v["count"], 1) for d, v in m.items()}

    rank_map = {
        "organic_rank": avg_by_date(records, "organic_rank"),
        "ad_rank_sp":   avg_by_date(records, "ad_rank", "SP"),
        "ad_rank_sb":   avg_by_date(records, "ad_rank", "SB"),
        "ad_rank_video": avg_by_date(records, "ad_rank", "SB_Video"),
    }

    # 构建消息
    lines = [f"【ASIN重点监控报告】"]
    lines.append(f"监控人：{task['monitor_name']}  |  ASIN：{asin}  |  近{days}天")
    lines.append(f"查询时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("─" * 40)

    summary = {}
    for rt in rank_types:
        label = RANK_LABELS.get(rt, rt)
        data = rank_map.get(rt, {})
        if not data:
            lines.append(f"▸ {label}：暂无数据")
            continue
        dates = sorted(data.keys())
        vals = [data[d] for d in dates]
        latest = vals[-1]
        prev = vals[-2] if len(vals) >= 2 else None
        change = ""
        if prev:
            diff = latest - prev
            change = f"（较前日 {'↑' if diff > 0 else '↓'}{abs(diff):.1f}）"
        best = min(vals)
        worst = max(vals)
        lines.append(f"▸ {label}：最新 #{latest}{change}  |  最优 #{best}  |  最差 #{worst}")
        summary[rt] = {"latest": latest, "best": best, "worst": worst, "dates": dates, "values": vals}

    lines.append("─" * 40)
    lines.append(f"数据大屏：http://192.168.0.193:8880/dashboard_asin.html?asin={asin}")

    send_feishu("\n".join(lines))
    return {"message": "已发送", "summary": summary}


def run_due_monitor_tasks(db_factory):
    """由调度器调用，检查并执行到期的监控任务"""
    tasks = _load()
    now = datetime.now()
    changed = False
    for task in tasks:
        if not task.get("enabled"):
            continue
        next_run = datetime.fromisoformat(task.get("next_run", now.isoformat()))
        if now >= next_run:
            try:
                db = next(db_factory())
                _execute_monitor_task(task, db)
                db.close()
            except Exception as e:
                logger.error(f"监控任务执行失败 {task['id']}: {e}")
            task["last_run"] = now.isoformat()
            task["next_run"] = (now + timedelta(hours=task["interval_hours"])).isoformat()
            changed = True
    if changed:
        _save(tasks)
