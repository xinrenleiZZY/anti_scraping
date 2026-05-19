"""网站访客记录 API"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.database import get_db
from app.models import VisitorLog

router = APIRouter()


class PageView(BaseModel):
    page: str
    referrer: Optional[str] = None


@router.post("/visitor/track")
def track_pageview(body: PageView, request: Request, db: Session = Depends(get_db)):
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    log = VisitorLog(
        page=body.page,
        ip=client_ip,
        user_agent=request.headers.get("User-Agent", ""),
        referrer=body.referrer or request.headers.get("Referer", ""),
    )
    db.add(log)
    db.commit()
    return {"status": "ok"}


@router.get("/visitor/stats")
def get_stats(days: int = Query(7, ge=1, le=365), db: Session = Depends(get_db)):
    now = datetime.now()
    today = now.date()
    week_start = today - timedelta(days=7)

    today_count = db.query(VisitorLog).filter(
        func.date(VisitorLog.visited_at) == today
    ).count()

    week_count = db.query(VisitorLog).filter(
        func.date(VisitorLog.visited_at) >= week_start
    ).count()

    total_count = db.query(VisitorLog).count()

    top_pages = db.query(
        VisitorLog.page, func.count(VisitorLog.id).label("cnt")
    ).filter(
        func.date(VisitorLog.visited_at) >= week_start
    ).group_by(VisitorLog.page).order_by(func.count(VisitorLog.id).desc()).limit(10).all()

    daily_trend = db.query(
        func.date(VisitorLog.visited_at).label("d"),
        func.count(VisitorLog.id).label("cnt")
    ).filter(
        func.date(VisitorLog.visited_at) >= now.date() - timedelta(days=days)
    ).group_by(func.date(VisitorLog.visited_at)).order_by(func.date(VisitorLog.visited_at).asc()).all()

    return {
        "today": today_count,
        "week": week_count,
        "total": total_count,
        "top_pages": [{"page": p, "count": c} for p, c in top_pages],
        "daily_trend": [{"date": str(d), "count": c} for d, c in daily_trend],
    }


@router.get("/visitor/recent")
def get_recent(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    logs = db.query(VisitorLog).order_by(VisitorLog.visited_at.desc()).limit(limit).all()
    return [{
        "id": l.id,
        "page": l.page,
        "ip": l.ip,
        "user_agent": (l.user_agent or "")[:120],
        "referrer": l.referrer or "",
        "visited_at": l.visited_at.isoformat() if l.visited_at else "",
    } for l in logs]
