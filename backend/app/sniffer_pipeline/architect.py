from typing import Optional, Dict, List
import logging
import json
import re
from openai import AsyncOpenAI
from app.core.config import settings
from .schemas import Candidate, ExtractionStrategy

logger = logging.getLogger(__name__)

class Architect:
    """
    Phase 2: Data Architect (AI)
    Analyzes API response samples and defines an extraction strategy.
    """
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.VOLC_API_KEY, 
            base_url=settings.VOLC_BASE_URL
        )
        self.model = settings.VOLC_DEEPSEEK_MODEL_ID

    async def define_extraction_strategy(self, candidates: List[Candidate], table_name_hint: Optional[str] = None, task_id: str = "Unknown", log_callback=None) -> ExtractionStrategy:
        """
        Phase 2: Analyze candidates and define the extraction strategy.
        """
        async def _log(msg, level="INFO"):
            logger.info(f"[{task_id}] {msg}")
            if log_callback:
                await log_callback(msg, level)

        if not candidates:
            raise ValueError("No candidates provided to Architect.")

        await _log(f"Architect analyzing {len(candidates)} candidates...")

        # Prepare summary for AI (limit token usage)
        summary = []
        for c in candidates:
            summary.append({
                "url": c.url,
                "method": c.method,
                "preview": c.response_preview[:1000] 
            })
        
        await _log(f"Prepared summary for AI ({len(json.dumps(summary))} bytes).", "DEBUG")

        # --- 修正点：构建一个完整的 Prompt 字符串 ---
        prompt = f"""
        You are an AI Data Architect. Analyze these captured API response samples.
        
        Goal: Identify the most valuable data stream and define a robust extraction strategy using Python Code.
        
        Candidates:
        {json.dumps(summary, indent=2)}
        
        Requirements:
        1. **URL Pattern**: Identify the URL pattern for the most important data API. Create a Python Regex that matches this URL (handle pagination params).

        2. **SQL Schema**: Generate a SQL `CREATE TABLE` statement suitable for SQLite/PostgreSQL.
        3. **Transformation Logic**: Write a COMPLETE Python function definition named `transform_item(item)` that takes a single item (dict) and returns a flat dictionary matching the SQL columns. 
           - **Input Handling**: The `item` is usually a JSON dictionary. However, if the target is a static website (HTML), `item` will be `{{'html': '<html>...', 'url': '...'}}`. 
           - **HTML Parsing**: If you suspect the data is in HTML, your code MUST import `bs4` (BeautifulSoup) inside the function and parse `item['html']`.
           - **MUST** include `def transform_item(item):` signature.
           - Handle data types (str -> float/int).
           - Handle missing fields safely (use .get()).
           - Return `None` or empty dict if item is invalid.
           - You may import standard libraries (re, json, datetime) inside the function if needed.

        """

        if table_name_hint:
             prompt += f"\nNote: The user requested the table name to be `{table_name_hint}`. Please use this table name in the SQL schema."

        prompt += """
        Output JSON Format (Strict JSON Only):
        {
            "target_api_url_pattern": "regex_string",
            "sql_schema": "CREATE TABLE table_name (id TEXT, price REAL, ...)",
            "transform_code": "def transform_item(item):\\n    import re\\n    return {\\n        'id': item.get('id'),\\n        'price': float(item.get('price', 0))\\n    }",
            "description": "Explanation of choice"
        }
        """

        try:
            await _log("Sending prompt to AI Architect...", "DEBUG")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise Data Architect. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                stream=False,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            await _log(f"AI Response received ({len(content)} chars). Parsing JSON...", "DEBUG")
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                await _log(f"Failed to parse AI response as JSON: {e}", "ERROR")
                await _log(f"Raw content: {content[:500]}...", "DEBUG")
                raise

            # 注意：这里需要确保 schemas.py 里的 ExtractionStrategy 已经加了 transform_code 字段
            strategy = ExtractionStrategy(**data)
            await _log(f"Strategy defined: {strategy.description}")
            await _log(f"Regex Pattern: {strategy.target_api_url_pattern}", "DEBUG")
            await _log(f"SQL Schema: {strategy.sql_schema.split('(')[0]}...", "DEBUG")
            return strategy

        except Exception as e:
            await _log(f"Architect failed to define strategy: {e}", "ERROR")
            raise