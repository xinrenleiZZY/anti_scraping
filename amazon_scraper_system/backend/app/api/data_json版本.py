# backend/app/api/data.py
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import csv
import io
import json
from pathlib import Path

from app.database import get_db
from app import crud, schemas
from app.models import RawSearchResult, ScrapingTask

router = APIRouter()

# 配置文件路径
CONFIG_PATH = Path(__file__).parent.parent / "scraper" / "scraper_config.json"


def load_config():
    """加载配置文件"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"keywords": []}


def get_keyword_attributes():
    """获取所有关键词的属性（标签、节日等）"""
    config = load_config()
    return {
        "keyword_tags": config.get("keyword_tags", {}),
        "keyword_festivals": config.get("keyword_festivals", {}),
        "keyword_festival_types": config.get("keyword_festival_types", {}),
        "keyword_hot_seasons": config.get("keyword_hot_seasons", {}),
    }


@router.get("/results")
def get_results(
    keyword: Optional[str] = Query(None),
    keywords: Optional[List[str]] = Query(None),
    asin: Optional[str] = Query(None),
    ad_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    # ========== 新增筛选参数 ==========
    tags: Optional[List[str]] = Query(None),
    festival: Optional[str] = Query(None),
    festival_type: Optional[str] = Query(None),
    hot_season: Optional[str] = Query(None),
    # ================================
    db: Session = Depends(get_db)
):
    """查询爬取结果"""
    query = db.query(RawSearchResult)
    
    # 加载关键词属性
    attrs = get_keyword_attributes()
    keyword_tags = attrs["keyword_tags"]
    keyword_festivals = attrs["keyword_festivals"]
    keyword_festival_types = attrs["keyword_festival_types"]
    keyword_hot_seasons = attrs["keyword_hot_seasons"]

    # ========== 关键词筛选 ==========
    if keyword:
        query = query.filter(RawSearchResult.keyword == keyword)
    elif keywords:
        query = query.filter(RawSearchResult.keyword.in_(keywords))
    
    # ========== 标签筛选 ==========
    if tags:
        matched_keywords = set()
        for kw, kw_tags in keyword_tags.items():
            if any(tag in kw_tags for tag in tags):
                matched_keywords.add(kw)
        if matched_keywords:
            query = query.filter(RawSearchResult.keyword.in_(matched_keywords))
        else:
            return {"data": [], "total": 0, "page": page, "limit": limit, "total_pages": 0}
    
    # ========== 节日筛选 ==========
    if festival:
        matched_keywords = [kw for kw, f in keyword_festivals.items() if f == festival]
        if matched_keywords:
            query = query.filter(RawSearchResult.keyword.in_(matched_keywords))
        else:
            return {"data": [], "total": 0, "page": page, "limit": limit, "total_pages": 0}
    
    # ========== 大/小节日筛选 ==========
    if festival_type:
        matched_keywords = [kw for kw, ft in keyword_festival_types.items() if ft == festival_type]
        if matched_keywords:
            query = query.filter(RawSearchResult.keyword.in_(matched_keywords))
        else:
            return {"data": [], "total": 0, "page": page, "limit": limit, "total_pages": 0}
    
    # ========== 热卖期筛选 ==========
    if hot_season:
        matched_keywords = [kw for kw, hs in keyword_hot_seasons.items() if hs == hot_season]
        if matched_keywords:
            query = query.filter(RawSearchResult.keyword.in_(matched_keywords))
        else:
            return {"data": [], "total": 0, "page": page, "limit": limit, "total_pages": 0}
    
    # ========== 其他筛选 ==========
    if asin:
        query = query.filter(RawSearchResult.asin == asin)
    if ad_type:
        query = query.filter(RawSearchResult.ad_type == ad_type)
    
    # ========== 日期范围筛选 ==========
    if date_from:
        from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        query = query.filter(RawSearchResult.date >= from_date)
    if date_to:
        to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        query = query.filter(RawSearchResult.date <= to_date)
        
    query = query.order_by(RawSearchResult.scraped_at.desc())
    
    
    # ========== 分页 ==========
    total = query.count()
    total_pages = (total + limit - 1) // limit
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()
    
    # ========== 构建返回数据（包含关键词属性） ==========
    data = []
    for item in items:
        kw = item.keyword
        data.append({
            'id': item.id,
            'keyword': kw,
            'asin': item.asin,
            'title': item.title[:100] if item.title else '',
            'price_current': item.price_current,
            'price_list': item.price_list,
            'rating_stars': float(item.rating_stars) if item.rating_stars else None,
            'rating_count': item.rating_count,
            'ad_type': item.ad_type,
            'ad_rank': item.ad_rank,
            'organic_rank': item.organic_rank,
            'page': item.page,
            'scraped_at': item.scraped_at.isoformat() if item.scraped_at else None,
            'date': item.scraped_at.strftime('%Y-%m-%d') if item.scraped_at else None,
            # ========== 从配置文件获取关键词属性 ==========
            'tags': keyword_tags.get(kw, []),
            'festival': keyword_festivals.get(kw, ''),
            'festival_type': keyword_festival_types.get(kw, ''),
            'hot_season': keyword_hot_seasons.get(kw, ''),
        })
    
    return {
        'data': data,
        'total': total,
        'page': page,
        'limit': limit,
        'total_pages': total_pages
    }


@router.get("/tasks")
def get_tasks(
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """查询任务列表"""
    query = db.query(ScrapingTask)
    
    if status:
        query = query.filter(ScrapingTask.status == status)
    if keyword:
        query = query.filter(ScrapingTask.keyword.contains(keyword))
    
    query = query.order_by(ScrapingTask.id.desc())
    
    total = query.count()
    total_pages = (total + limit - 1) // limit
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()
    
    data = []
    for item in items:
        data.append({
            'id': item.id,
            'keyword': item.keyword,
            'status': item.status,
            'total_items': item.total_items,
            'started_at': item.started_at.isoformat() if item.started_at else None,
            'completed_at': item.completed_at.isoformat() if item.completed_at else None,
            'error_message': item.error_message
        })
    
    return {
        'data': data,
        'total': total,
        'page': page,
        'limit': limit,
        'total_pages': total_pages
    }


@router.get("/tasks/{task_id}")
def get_task_detail(task_id: int, db: Session = Depends(get_db)):
    """获取任务详情"""
    task = db.query(ScrapingTask).filter(ScrapingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {
        'id': task.id,
        'keyword': task.keyword,
        'status': task.status,
        'total_items': task.total_items,
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'error_message': task.error_message
    }


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """获取统计数据"""
    # 总关键词数
    try:
        config = load_config()
        total_keywords = len(config.get('keywords', []))
    except:
        total_keywords = 0
    
    total_tasks = db.query(ScrapingTask).count()
    total_products = db.query(RawSearchResult).count()
    
    today = datetime.now().date()
    today_count = db.query(RawSearchResult).filter(
        RawSearchResult.scraped_at >= today
    ).count()
    
    return {
        'total_keywords': total_keywords,
        'total_tasks': total_tasks,
        'total_products': total_products,
        'today_count': today_count
    }


@router.get("/asins")
def get_asins(keyword: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """获取所有不重复的 ASIN 列表"""
    query = db.query(RawSearchResult.asin).filter(RawSearchResult.asin != None)
    if keyword:
        query = query.filter(RawSearchResult.keyword == keyword)
    asins = [row[0] for row in query.distinct().order_by(RawSearchResult.asin).all()]
    return asins


@router.get("/results/export")
def export_results(
    keyword: Optional[str] = Query(None),
    asin: Optional[str] = Query(None),
    ad_type: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    festival: Optional[str] = Query(None),
    festival_type: Optional[str] = Query(None),
    hot_season: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """导出查询结果为 CSV"""
    query = db.query(RawSearchResult)
    
    # 加载关键词属性用于筛选
    attrs = get_keyword_attributes()
    keyword_tags = attrs["keyword_tags"]
    keyword_festivals = attrs["keyword_festivals"]
    keyword_festival_types = attrs["keyword_festival_types"]
    keyword_hot_seasons = attrs["keyword_hot_seasons"]
    
    if keyword:
        query = query.filter(RawSearchResult.keyword == keyword)
    
    # 标签筛选
    if tags:
        matched_keywords = set()
        for kw, kw_tags in keyword_tags.items():
            if any(tag in kw_tags for tag in tags):
                matched_keywords.add(kw)
        if matched_keywords:
            query = query.filter(RawSearchResult.keyword.in_(matched_keywords))
        else:
            return StreamingResponse(iter(['']), media_type='text/csv')
    
    # 节日筛选
    if festival:
        matched_keywords = [kw for kw, f in keyword_festivals.items() if f == festival]
        if matched_keywords:
            query = query.filter(RawSearchResult.keyword.in_(matched_keywords))
        else:
            return StreamingResponse(iter(['']), media_type='text/csv')
    
    if festival_type:
        matched_keywords = [kw for kw, ft in keyword_festival_types.items() if ft == festival_type]
        if matched_keywords:
            query = query.filter(RawSearchResult.keyword.in_(matched_keywords))
        else:
            return StreamingResponse(iter(['']), media_type='text/csv')
    
    if hot_season:
        matched_keywords = [kw for kw, hs in keyword_hot_seasons.items() if hs == hot_season]
        if matched_keywords:
            query = query.filter(RawSearchResult.keyword.in_(matched_keywords))
        else:
            return StreamingResponse(iter(['']), media_type='text/csv')
    
    if asin:
        query = query.filter(RawSearchResult.asin == asin)
    if ad_type:
        query = query.filter(RawSearchResult.ad_type == ad_type)
    
    items = query.order_by(RawSearchResult.scraped_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['date', 'keyword', 'asin', 'title', 'price_current', 'rating_stars', 'rating_count', 'ad_type', 'ad_rank', 'organic_rank', 'page', 'scraped_at'])
    for item in items:
        writer.writerow([
            item.scraped_at.strftime('%Y-%m-%d') if item.scraped_at else '',
            item.keyword, item.asin, item.title,
            item.price_current, item.rating_stars, item.rating_count,
            item.ad_type, item.ad_rank, item.organic_rank, item.page,
            item.scraped_at.isoformat() if item.scraped_at else ''
        ])

    output.seek(0)
    return StreamingResponse(
        iter(['\ufeff' + output.getvalue()]),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="results.csv"'}
    )