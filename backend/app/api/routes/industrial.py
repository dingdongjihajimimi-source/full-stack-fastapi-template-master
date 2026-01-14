"""
工业收割模式后端接口

提供批量数据收割功能，通过 Playwright 模拟浏览器滚动加载内容，
并将收集到的资源（图片、文件等）存储到本地文件系统。
"""
import uuid
import json
import shutil
import zipfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import select

from app.api.deps import SessionDep
from app.models import IndustrialBatch, IndustrialBatchPublic, IndustrialFileInfo
from app.core.paths import INDUSTRIAL_DIR

router = APIRouter()
logger = logging.getLogger(__name__)


class CollectRequest(BaseModel):
    """收集请求参数"""
    url: str
    scroll_count: int = 5
    max_items: int = 100
    wait_until: str = "networkidle"  # networkidle, commit, domcontentloaded, load


async def run_industrial_harvest(batch_id: str, url: str, config: dict):
    """
    执行工业收割任务（后台任务）
    使用 IndustrialCollector 滚动页面并收集资源
    """
    from app.core.db import engine
    from sqlmodel import Session
    from app.industrial_pipeline.collector import IndustrialCollector
    
    batch_dir = INDUSTRIAL_DIR / batch_id
    
    # 更新状态为处理中
    with Session(engine) as db:
        batch = db.get(IndustrialBatch, uuid.UUID(batch_id))
        if batch:
            batch.status = "processing"
            batch.storage_path = str(batch_dir)
            db.add(batch)
            db.commit()
    
    async def update_progress(current_count: int):
        """Callback to update item count in DB"""
        with Session(engine) as db:
            b = db.get(IndustrialBatch, uuid.UUID(batch_id))
            if b:
                b.item_count = current_count
                db.add(b)
                db.commit()

    try:
        collector = IndustrialCollector()
        # 执行收割任务 - 传入整套配置和回调
        collected_count = await collector.harvest(url, batch_dir, config, progress_callback=update_progress)
        
        # 更新批次状态 - 成功
        with Session(engine) as db:
            batch = db.get(IndustrialBatch, uuid.UUID(batch_id))
            if batch:
                batch.status = "completed"
                batch.item_count = collected_count
                db.add(batch)
                db.commit()
                
    except Exception as e:
        logger.error(f"Industrial harvest failed: {e}")
        # 更新批次状态 - 失败
        with Session(engine) as db:
            batch = db.get(IndustrialBatch, uuid.UUID(batch_id))
            if batch:
                batch.status = "failed"
                db.add(batch)
                db.commit()


@router.get("/batches", response_model=List[IndustrialBatchPublic])
def get_batches(session: SessionDep) -> Any:
    """
    获取所有工业收割批次列表
    """
    statement = select(IndustrialBatch).order_by(IndustrialBatch.created_at.desc())
    batches = session.exec(statement).all()
    
    return [
        IndustrialBatchPublic(
            id=str(batch.id),
            created_at=batch.created_at.isoformat(),
            url=batch.url,
            item_count=batch.item_count,
            status=batch.status,
            storage_path=batch.storage_path,
        )
        for batch in batches
    ]


@router.post("/collect")
def start_collect(
    request: CollectRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> str:
    """
    启动工业收割任务
    """
    # 创建批次记录
    batch = IndustrialBatch(
        url=request.url,
        status="pending",
    )
    session.add(batch)
    session.commit()
    session.refresh(batch)
    
    # 准备配置字典
    config = request.model_dump()
    
    # 添加后台任务
    background_tasks.add_task(
        run_industrial_harvest,
        str(batch.id),
        request.url,
        config,
    )
    
    return str(batch.id)


@router.get("/batch/{batch_id}/files", response_model=List[IndustrialFileInfo])
def get_batch_files(batch_id: uuid.UUID, session: SessionDep) -> Any:
    """
    获取批次中的所有文件列表
    """
    batch = session.get(IndustrialBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    if not batch.storage_path:
        return []
    
    batch_dir = Path(batch.storage_path)
    if not batch_dir.exists():
        return []
    
    files = []
    for filepath in batch_dir.iterdir():
        if filepath.is_file():
            stat = filepath.stat()
            content_type = "application/octet-stream"
            if filepath.suffix in [".jpg", ".jpeg"]:
                content_type = "image/jpeg"
            elif filepath.suffix == ".png":
                content_type = "image/png"
            elif filepath.suffix == ".gif":
                content_type = "image/gif"
            elif filepath.suffix == ".webp":
                content_type = "image/webp"
            elif filepath.suffix == ".json":
                content_type = "application/json"
            elif filepath.suffix == ".html":
                content_type = "text/html"
            
            files.append(IndustrialFileInfo(
                name=filepath.name,
                size=stat.st_size,
                url=f"/api/v1/industrial/batch/{batch_id}/file/{filepath.name}",
                content_type=content_type,
                timestamp=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            ))
    
    return files


@router.get("/batch/{batch_id}/file/{filename}")
def download_file(batch_id: uuid.UUID, filename: str, session: SessionDep) -> Any:
    """
    下载批次中的单个文件
    """
    batch = session.get(IndustrialBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    if not batch.storage_path:
        raise HTTPException(status_code=404, detail="Batch has no storage")
    
    filepath = Path(batch.storage_path) / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/octet-stream",
    )


@router.get("/download/{batch_id}")
def download_batch_zip(batch_id: uuid.UUID, session: SessionDep) -> Any:
    """
    将批次所有文件打包为 ZIP 下载
    """
    batch = session.get(IndustrialBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    if not batch.storage_path:
        raise HTTPException(status_code=404, detail="Batch has no storage")
    
    batch_dir = Path(batch.storage_path)
    if not batch_dir.exists():
        raise HTTPException(status_code=404, detail="Batch directory not found")
    
    # 创建 ZIP 文件
    zip_path = INDUSTRIAL_DIR / f"{batch_id}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filepath in batch_dir.iterdir():
            if filepath.is_file():
                zipf.write(filepath, filepath.name)
    
    return FileResponse(
        path=zip_path,
        filename=f"industrial_batch_{str(batch_id)[:8]}.zip",
        media_type="application/zip",
    )


@router.delete("/batch/{batch_id}")
def delete_batch(batch_id: uuid.UUID, session: SessionDep) -> dict:
    """
    删除批次及其所有文件
    """
    batch = session.get(IndustrialBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # 删除存储目录
    if batch.storage_path:
        batch_dir = Path(batch.storage_path)
        if batch_dir.exists():
            shutil.rmtree(batch_dir)
    
    # 删除可能存在的 ZIP 文件
    zip_path = INDUSTRIAL_DIR / f"{batch_id}.zip"
    if zip_path.exists():
        zip_path.unlink()
    
    # 删除数据库记录
    session.delete(batch)
    session.commit()
    
    return {"status": "deleted"}
