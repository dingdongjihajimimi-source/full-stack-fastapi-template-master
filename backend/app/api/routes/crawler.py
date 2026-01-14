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
    mode: str = "manual"  # "manual" or "auto"
    review_mode: bool = False # Pause for review in auto mode

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
    Start a crawler task (Manual or Autonomous).
    """
    crawler_task = CrawlerTask(status="pending")
    session.add(crawler_task)
    session.commit()
    session.refresh(crawler_task)

    if request.mode == "auto":
        # Initialize pipeline_state with starting log
        initial_logs = [f"[{datetime.now().strftime('%H:%M:%S')}] Task initialized. Queued for execution..."]
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
        # Fallback to manual mode defaults if not provided
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
    Resume a paused autonomous crawl with the confirmed strategy.
    """
    task = session.get(CrawlerTask, request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "paused":
        raise HTTPException(status_code=400, detail="Task is not paused")

    # Update status to processing
    task.status = "processing"
    session.add(task)
    session.commit()

    # Re-instantiate strategy from dict
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
    Wrapper to run the pipeline and update DB state.
    We need a fresh session here ideally if running in background?
    FastAPI BackgroundTasks shares session context usually, but better be safe.
    Actually `session` passed here might be closed when request ends. 
    We should create a new session or use the passed one if safe. 
    FastAPI docs say BackgroundTasks runs AFTER response, so dependency session might be closed.
    We should use a new session factory.
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
                
                # Update logs
                logs = existing.get("logs", [])
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Check if there is a specific log message in data
                log_message = f"Phase: {phase}"
                if data and "log_message" in data:
                    log_message = data["log_message"]
                    # If it's a pure log update, we might not want to change phase in DB if it's just "log"
                    # But current_phase is useful for UI progress bar. 
                    # If phase is "log", we keep the previous phase?
                    # Let's assume phase is always passed correctly.
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
                    # Add URL if not present (hack for resume)
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

    # Run Pipeline
    await pipeline.run(url, task_id, update_callback=update_state, table_name_hint=table_name_hint, review_mode=review_mode)

async def resume_autonomous_pipeline_task(
    task_id: str,
    strategy: ExtractionStrategy
):
    from app.core.db import engine
    from sqlmodel import Session
    
    logger.info(f"🔄 Resuming autonomous pipeline task: {task_id}")

    # Retrieve URL from saved state
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
    Get crawler task status.
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
    Download generated CSV or SQL file.
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
    Get recent logs/events for a task from its pipeline_state.
    """
    task = session.get(CrawlerTask, task_id)
    if not task or not task.pipeline_state:
        return {"logs": []}
    
    state = json.loads(task.pipeline_state)
    # We could store a 'logs' list in state
    logs = state.get("logs", [])
    return {"logs": logs}
