from datetime import datetime
from sqlmodel import SQLModel, Field


class CrawlIndex(SQLModel, table=True):
    """
    Hybrid storage index for crawled data.
    Actual content stored in files, DB only tracks metadata.
    """
    __tablename__ = "crawl_index"

    url_hash: str = Field(max_length=64, primary_key=True, index=True)  # MD5 of URL
    original_url: str = Field(max_length=2048)
    file_path: str = Field(max_length=512)  # Relative path to storage root
    content_md5: str = Field(max_length=64, index=True)  # MD5 of content for deduplication
    content_type: str | None = Field(default=None, max_length=128)  # application/json, text/html, etc.
    size_bytes: int | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
