import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel

class CrawlerTask(SQLModel, table=True):
    __tablename__ = "crawler_task"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    status: str = Field(default="pending")  # 待处理、处理中、已暂停、已完成、失败
    result_sql_content: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 自主管道的新字段
    pipeline_state: str | None = Field(default=None)  # JSON 格式的当前策略/状态
    current_phase: str | None = Field(default=None)   # 侦察、架构、审核、收割、精炼
