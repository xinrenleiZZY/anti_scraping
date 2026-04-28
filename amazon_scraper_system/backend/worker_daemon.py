"""
分布式爬虫 Worker 守护进程
功能：
1. 定时发送心跳到 NAS
2. 从 NAS 领取任务
3. 执行爬取任务
4. 保存结果到 NAS
5. 更新任务状态
"""

import os
import sys
import json
import time
import uuid
import socket
import logging
import threading
from pathlib import Path
from datetime import datetime
from pathlib import Path

WORKER_ID = os.getenv("WORKER_ID", f"worker_{socket.gethostname()}_{uuid.uuid4().hex[:6]}")
NAS_BASE = Path(os.getenv("NAS_SHARE_PATH", "//192.168.40.3/钟正洋/amazon_scraper"))
TASKS_DIR = NAS_BASE / "tasks"
RESULTS_DIR = NAS_BASE / "results"
HEARTBEAT_DIR = NAS_BASE / "heartbeats"
DATA_DIR = Path(os.getenv("INPUT_FOLDER", "/app/amazon_data"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DATA_DIR", "/app/processed_data"))

PROXY_URL = os.getenv("WORKER_PROXY", None)
POLL_INTERVAL = 10
HEARTBEAT_INTERVAL = 30

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def ensure_dirs():
    """确保必要的目录存在"""
    for d in [TASKS_DIR, RESULTS_DIR, HEARTBEAT_DIR, DATA_DIR, PROCESSED_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    logger.info(f"目录初始化完成: NAS={NAS_BASE}")


def send_heartbeat():
    """发送心跳到 NAS"""
    heartbeat_file = HEARTBEAT_DIR / f"{WORKER_ID}.json"
    heartbeat_data = {
        "worker_id": WORKER_ID,
        "ip": socket.gethostbyname(socket.gethostname()),
        "proxy": PROXY_URL,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "timestamp": time.time()
    }
    try:
        with open(heartbeat_file, 'w', encoding='utf-8') as f:
            json.dump(heartbeat_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"心跳发送失败: {e}")


def heartbeat_loop():
    """心跳线程"""
    while True:
        send_heartbeat()
        time.sleep(HEARTBEAT_INTERVAL)


def get_pending_tasks():
    """获取所有待处理任务"""
    tasks = []
    if not TASKS_DIR.exists():
        return tasks

    for task_file in TASKS_DIR.glob("*.json"):
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task = json.load(f)
                if task.get("status") == "pending":
                    tasks.append(task)
        except Exception as e:
            logger.error(f"读取任务文件失败 {task_file}: {e}")
    return tasks


def claim_task(task):
    """声明任务（将状态改为 running）"""
    task_id = task.get("task_id")
    task_file = TASKS_DIR / f"{task_id}.json"

    try:
        with open(task_file, 'r', encoding='utf-8') as f:
            current = json.load(f)

        if current.get("status") != "pending":
            return False

        current["status"] = "running"
        current["assigned_to"] = WORKER_ID
        current["started_at"] = datetime.now().isoformat()

        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=2, ensure_ascii=False)

        logger.info(f"已领取任务: {task_id} - {task.get('keyword')}")
        return True
    except Exception as e:
        logger.error(f"声明任务失败 {task_id}: {e}")
        return False


def complete_task(task, result_file=None, error=None):
    """完成任务"""
    task_id = task.get("task_id")
    task_file = TASKS_DIR / f"{task_id}.json"

    try:
        with open(task_file, 'r', encoding='utf-8') as f:
            current = json.load(f)

        current["status"] = "failed" if error else "completed"
        current["completed_at"] = datetime.now().isoformat()
        if error:
            current["error"] = str(error)
        if result_file:
            current["result_file"] = str(result_file)

        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=2, ensure_ascii=False)

        logger.info(f"任务已完成: {task_id}, 状态: {current['status']}")
    except Exception as e:
        logger.error(f"更新任务状态失败 {task_id}: {e}")


def run_scraper(keyword, pages=None):
    """执行爬取任务"""
    logger.info(f"开始爬取: {keyword}, 页数: {pages or '自动'}")

    sys.path.insert(0, str(Path(__file__).parent))
    from backend.app.scraper.auto_amazon_scraper import SimpleRequestExecutor, AmazonSearchScraper
    from backend.app.scraper.dataprocess import process as preprocess_file

    postal_code = "90060"
    delay_range = (3, 6)
    output_dir = str(DATA_DIR)

    executor = SimpleRequestExecutor(
        delay_range=delay_range,
        postal_code=postal_code,
        proxy_url=PROXY_URL
    )

    scraper = AmazonSearchScraper(
        request_executor=executor,
        delay_range=delay_range,
        output_dir=output_dir,
        postal_code=postal_code
    )

    try:
        items = scraper.scrape_search(keyword, pages=pages, auto_pages=(pages is None))

        if items:
            scraper.save_results(items, keyword)
            raw_file = list(DATA_DIR.glob(f"{keyword.replace(' ', '+')}_*.json"))[-1]
            preprocess_file(str(raw_file))
            processed_file = list(PROCESSED_DIR.glob(f"{raw_file.stem}_processed.json"))[-1]

            result_file = RESULTS_DIR / f"{WORKER_ID}_{processed_file.name}"
            import shutil
            shutil.copy(processed_file, result_file)
            logger.info(f"结果已保存: {result_file}")
            return str(result_file)
        else:
            logger.warning(f"无数据: {keyword}")
            return None

    finally:
        executor.close()


def process_tasks():
    """主循环：处理任务"""
    logger.info("Worker 启动，等待任务...")

    while True:
        try:
            pending = get_pending_tasks()

            if not pending:
                logger.debug(f"暂无任务，{POLL_INTERVAL}秒后再次检查...")
                time.sleep(POLL_INTERVAL)
                continue

            task = pending[0]
            task_id = task.get("task_id")

            if not claim_task(task):
                time.sleep(POLL_INTERVAL)
                continue

            keyword = task.get("keyword")
            pages = task.get("pages")

            try:
                result_file = run_scraper(keyword, pages)
                complete_task(task, result_file=result_file)
            except Exception as e:
                logger.error(f"爬取失败 {keyword}: {e}")
                complete_task(task, error=str(e))

        except Exception as e:
            logger.error(f"处理任务时出错: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    logger.info(f"=" * 50)
    logger.info(f"Worker ID: {WORKER_ID}")
    logger.info(f"Proxy: {PROXY_URL or '无'}")
    logger.info(f"NAS: {NAS_BASE}")
    logger.info(f"=" * 50)

    ensure_dirs()
    send_heartbeat()

    heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    heartbeat_thread.start()

    process_tasks()
