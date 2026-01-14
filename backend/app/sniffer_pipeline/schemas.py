from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class Candidate(BaseModel):
    url: str
    method: str
    headers: Dict[str, str]
    payload: Optional[str] = None
    response_preview: str
    resource_type: str = "xhr"

class ExtractionStrategy(BaseModel):
    target_api_url_pattern: str
    sql_schema: str
    # 新增：让 LLM 给你写一个 Python 函数体，输入 raw_json，输出 dict
    transform_code: str 
    description: Optional[str] = None

class RawDataBlock(BaseModel):
    url: str
    data: Any  # The JSON object or list
    timestamp: float
