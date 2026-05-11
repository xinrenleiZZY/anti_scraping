"""
data_control API 路由
提供备份触发、恢复操作、完整性校验的 HTTP 接口
不修改任何现有页面，纯 API 调用
"""

import logging
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class RecoverRequest(BaseModel):
    targets: List[str] = ["all"]
    source: Optional[str] = None


class VerifyResponse(BaseModel):
    checks: list
    ok: int
    warn: int
    err: int


@router.post("/backup/run")
def api_run_backup(background_tasks: BackgroundTasks):
    try:
        from data_control.backup import run_backup
        background_tasks.add_task(run_backup)
        return {"status": "started", "message": "备份任务已提交到后台"}
    except Exception as e:
        logger.error(f"备份启动失败: {e}")
        raise HTTPException(status_code=500, detail=f"备份启动失败: {e}")


@router.post("/backup/run-sync")
def api_run_backup_sync():
    try:
        from data_control.backup import run_backup
        result = run_backup()
        return {"status": "completed", "result": {k: str(v) for k, v in result.items()}}
    except Exception as e:
        logger.error(f"备份执行失败: {e}")
        raise HTTPException(status_code=500, detail=f"备份执行失败: {e}")


@router.get("/backup/status")
def api_backup_status():
    from data_control.config import TIMESTAMP_FILE
    if TIMESTAMP_FILE.exists():
        ts = TIMESTAMP_FILE.read_text(encoding="utf-8").strip()
        from data_control.recover import list_backups, find_backup
        backups = list_backups()
        return {
            "last_backup": ts,
            "backup_count": len(backups),
            "backups": [b.name for b in backups[:5]],
        }
    return {"last_backup": None, "backup_count": 0, "backups": []}


@router.post("/recover/run")
def api_run_recover(body: RecoverRequest):
    try:
        from data_control.recover import run_recover, find_backup
        backup_dir = find_backup(body.source) if body.source else find_backup()
        result = run_recover(body.targets, backup_dir)
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"恢复失败: {e}")
        raise HTTPException(status_code=500, detail=f"恢复失败: {e}")


@router.get("/recover/backups")
def api_list_backups():
    from data_control.recover import list_backups
    backups = list_backups()
    return {"backups": [b.name for b in backups]}


@router.get("/verify")
def api_verify():
    from data_control.verify import run_verify
    return run_verify(json_output=True)


@router.post("/sync/run")
def api_run_sync():
    try:
        from data_control.sync import sync_all
        result = sync_all()
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"同步失败: {e}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")
