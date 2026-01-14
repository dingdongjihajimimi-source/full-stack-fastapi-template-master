import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel

class CrawlerTask(SQLModel, table=True):
    __tablename__ = "crawler_task"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    status: str = Field(default="pending")  # pending, processing, paused, completed, failed
    result_sql_content: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    
    # New fields for autonomous pipeline
    pipeline_state: str | None = Field(default=None)  # JSON string of the current strategy/state
    current_phase: str | None = Field(default=None)   # scout, architect, review, harvester, refinery
