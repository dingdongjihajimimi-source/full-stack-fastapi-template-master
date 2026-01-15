import uuid
import json
import logging
from datetime import datetime
from typing import Any, Optional, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import select
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.models import CrawlerTask
from app.worker_tasks.crawler import generate_sql_from_spider, CSV_DIR, SQL_DIR
from app.sniffer_pipeline.pipeline import SnifferPipeline
from app.sniffer_pipeline.schemas import ExtractionStrategy
from app.core.paths import CSV_DIR, SQL_DIR
router = APIRouter()
logger = logging.getLogger(__name__)

class CrawlRequest(BaseModel):
    url: str
    table_name: Optional[str] = None
    columns: list[str] = []
    max_pages: int = 1
    concurrency: int = 5
    mode: str = "manual"  # "manual" 或 "auto"
    review_mode: bool = False # 自动模式下暂停等待审核

class ResumeRequest(BaseModel):
    task_id: uuid.UUID
    strategy: dict # The confirmed/edited strategy

@router.post("/start", response_model=uuid.UUID)
def start_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> Any:
    """
    启动爬虫任务（手动或自主）。
    """
    crawler_task = CrawlerTask(status="pending")
    session.add(crawler_task)
    session.commit()
    session.refresh(crawler_task)

    if request.mode == "auto":
        # 初始化管道状态并记录启动日志
        initial_logs = [f"[{datetime.now().strftime('%H:%M:%S')}] 任务初始化。已排队等待执行..."]
        crawler_task.pipeline_state = json.dumps({"logs": initial_logs})
        session.add(crawler_task)
        session.commit()

        background_tasks.add_task(
            run_autonomous_pipeline_task,
            str(crawler_task.id),
            request.url,
            request.table_name,
            request.review_mode
        )
    else:
        # 如果未提供，则回退到手动模式默认值
        table_name = request.table_name or "scraped_data"
        columns = request.columns or ["content"]
        
        background_tasks.add_task(
            generate_sql_from_spider, 
            crawler_task.id, 
            request.url, 
            table_name, 
            columns,
            request.max_pages,
            request.concurrency
        )

    return crawler_task.id

@router.post("/resume", response_model=Dict[str, str])
def resume_crawl(
    request: ResumeRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> Any:
    """
    使用确认的策略恢复暂停的自主爬取。
    """
    task = session.get(CrawlerTask, request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "paused":
        raise HTTPException(status_code=400, detail="Task is not paused")

    # 更新状态为处理中
    task.status = "processing"
    session.add(task)
    session.commit()

    # 从字典重新实例化策略
    try:
        strategy = ExtractionStrategy(**request.strategy)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {e}")

    background_tasks.add_task(
        resume_autonomous_pipeline_task,
        str(task.id),
        strategy
    )

    return {"status": "resumed"}

async def run_autonomous_pipeline_task(
    task_id: str, 
    url: str, 
    table_name_hint: Optional[str],
    review_mode: bool
):
    """
    运行管道并更新数据库状态的包装器。
    我们在这里需要一个新的会话，因为如果在后台运行，
    FastAPI BackgroundTasks 通常会共享会话上下文，但为了安全起见。
    实际上，这里传递的 `session` 可能会在请求结束时关闭。
    我们应该创建一个新的会话或在安全的情况下使用传递的会话。
    FastAPI 文档称 BackgroundTasks 在响应后运行，因此依赖会话可能会关闭。
    我们应该使用新的会话工厂。
    """
    from app.core.db import engine
    from sqlmodel import Session
    
    pipeline = SnifferPipeline()

    async def update_state(tid, phase, data):
        with Session(engine) as db_session:
            task = db_session.get(CrawlerTask, uuid.UUID(tid))
            if task:
                task.current_phase = phase
                existing = json.loads(task.pipeline_state) if task.pipeline_state else {}
                
                # 更新日志
                logs = existing.get("logs", [])
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # 检查数据中是否有特定的日志消息
                log_message = f"Phase: {phase}"
                if data and "log_message" in data:
                    log_message = data["log_message"]
                    # 如果是纯日志更新，我们可能不想更改数据库中的阶段
                    # 但 current_phase 对 UI 进度条很有用。
                    # 如果阶段是“日志”，我们保留上一个阶段？
                    # 让我们假设阶段总是正确传递的。
                elif phase == "scout":
                     log_message = "阶段：侦察（采样）"
                elif phase == "architect":
                     log_message = "阶段：架构师（策略定义）"
                elif phase == "review":
                     log_message = "阶段：审核（等待用户）"
                elif phase == "harvester":
                     log_message = "阶段：收获者（执行）"
                elif phase == "refinery":
                     log_message = "阶段：精炼厂（ETL & SQL）"
                elif phase == "completed":
                     log_message = "阶段：已完成"
                elif phase == "failed":
                     error_msg = data.get("error", "未知错误") if data else "未知错误"
                     log_message = f"阶段：失败 - {error_msg}"

                logs.append(f"[{timestamp}] {log_message}")
                existing["logs"] = logs
                
                if data:
                    # 如果不存在 URL 则添加（用于恢复的临时处理）
                    if "url" not in existing:
                        existing["url"] = url
                    existing.update(data)
                
                task.pipeline_state = json.dumps(existing)
                
                if phase == "completed":
                    task.status = "completed"
                    if data and "items_harvested" in data:
                        existing["items_harvested"] = data["items_harvested"]
                elif phase == "failed":
                    task.status = "failed"
                elif phase == "review":
                    task.status = "paused"
                else:
                    task.status = "processing"
                
                db_session.add(task)
                db_session.commit()

    # 运行管道
    await pipeline.run(url, task_id, update_callback=update_state, table_name_hint=table_name_hint, review_mode=review_mode)

async def resume_autonomous_pipeline_task(
    task_id: str,
    strategy: ExtractionStrategy
):
    from app.core.db import engine
    from sqlmodel import Session
    
    logger.info(f"🔄 Resuming autonomous pipeline task: {task_id}")

    # Retrieve URL from saved state
    # 从保存的状态中检索 URL
    url = ""
    with Session(engine) as db_session:
        task = db_session.get(CrawlerTask, uuid.UUID(task_id))
        if task and task.pipeline_state:
            state = json.loads(task.pipeline_state)
            url = state.get("url", "")
    
    if not url:
        logger.error(f"Could not find URL for resuming task {task_id}")
        return

    pipeline = SnifferPipeline()

    async def update_state(tid, phase, data):
        with Session(engine) as db_session:
            task = db_session.get(CrawlerTask, uuid.UUID(tid))
            if task:
                task.current_phase = phase
                existing = json.loads(task.pipeline_state) if task.pipeline_state else {}
                
                # Update logs
                logs = existing.get("logs", [])
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Check if there is a specific log message in data
                log_message = f"Phase: {phase}"
                if data and "log_message" in data:
                    log_message = data["log_message"]
                elif phase == "scout":
                     log_message = "Phase: Scout (Sampling)"
                elif phase == "architect":
                     log_message = "Phase: Architect (Strategy Definition)"
                elif phase == "review":
                     log_message = "Phase: Review (Waiting for user)"
                elif phase == "harvester":
                     log_message = "Phase: Harvester (Execution)"
                elif phase == "refinery":
                     log_message = "Phase: Refinery (ETL & SQL)"
                elif phase == "completed":
                     log_message = "Phase: Completed"
                elif phase == "failed":
                     error_msg = data.get("error", "Unknown error") if data else "Unknown error"
                     log_message = f"Phase: Failed - {error_msg}"

                logs.append(f"[{timestamp}] {log_message}")
                existing["logs"] = logs

                if data:
                    existing.update(data)
                
                task.pipeline_state = json.dumps(existing)
                
                if phase == "completed":
                    task.status = "completed"
                elif phase == "failed":
                    task.status = "failed"
                else:
                    task.status = "processing"
                
                db_session.add(task)
                db_session.commit()

    await pipeline.resume(task_id, url, strategy, update_callback=update_state)


@router.get("/{task_id}", response_model=CrawlerTask)
def get_crawl_status(
    task_id: uuid.UUID,
    session: SessionDep,
) -> Any:
    """
    获取爬虫任务状态。
    """
    task = session.get(CrawlerTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/download/{task_id}/{file_type}")
def download_crawl_file(
    task_id: uuid.UUID,
    file_type: str,
    session: SessionDep,
) -> Any:
    """
    下载生成的 CSV 或 SQL 文件。
    """
    task = session.get(CrawlerTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if file_type == "csv":
        file_path = CSV_DIR / f"{task_id}.csv"
        filename = f"crawler_data_{task_id}.csv"
        media_type = "text/csv"
    elif file_type == "sql":
        file_path = SQL_DIR / f"{task_id}.sql"
        filename = f"generated_sql_{task_id}.sql"
        media_type = "application/sql"
    else:
        raise HTTPException(status_code=400, detail="Invalid file type. Must be 'csv' or 'sql'.")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found. Please ensure the task is completed.")

    return FileResponse(
        path=file_path, 
        filename=filename, 
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/logs/{task_id}")
def get_task_logs(task_id: uuid.UUID, session: SessionDep):
    """
    从 pipeline_state 获取任务的最近日志/事件。
    """
    task = session.get(CrawlerTask, task_id)
    if not task or not task.pipeline_state:
        return {"logs": []}
    
    state = json.loads(task.pipeline_state)
    # 我们可以在状态中存储“日志”列表
    logs = state.get("logs", [])
    return {"logs": logs}
