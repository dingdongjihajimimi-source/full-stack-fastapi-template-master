import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class IndustrialBatch(SQLModel, table=True):
    """工业收割批次模型"""
    __tablename__ = "industrial_batch"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    url: str = Field(default="")
    item_count: int = Field(default=0)
    status: str = Field(default="pending")  # pending, processing, completed, failed
    storage_path: Optional[str] = Field(default=None)


class IndustrialBatchPublic(SQLModel):
    """返回给前端的批次信息"""
    id: str
    created_at: str
    url: str
    item_count: int
    status: str
    storage_path: Optional[str] = None


class IndustrialFileInfo(SQLModel):
    """批次中单个文件的信息"""
    name: str
    size: int
    url: str
    content_type: str
    timestamp: str
