"""
AI Extractor Module for Deep Data Cleaning

Uses DeepSeek (via Volcengine) to extract structured data from cleaned HTML.
Falls back to None on failure, allowing caller to use light-cleaned HTML instead.
"""
import os
import json
import logging
from typing import Optional, Dict, Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AiExtractor:
    """
    Extracts structured data from HTML using DeepSeek LLM.
    """
    
    def __init__(self):
        self.api_key = settings.VOLC_API_KEY or ""
        self.base_url = settings.VOLC_BASE_URL
        self.model_id = settings.VOLC_DEEPSEEK_MODEL_ID or ""
        
        if not self.api_key or not self.model_id:
            logger.warning("DeepSeek API not configured. AI extraction will fail.")
    
    def extract(self, cleaned_html: str, max_tokens: int = 4096) -> Optional[Dict[str, Any]]:
        """
        Send cleaned HTML to DeepSeek and get structured JSON back.
        
        Args:
            cleaned_html: Pre-cleaned HTML (from HtmlCleaner)
            max_tokens: Max tokens for response
            
        Returns:
            Extracted data as dict, or None if extraction failed
        """
        if not self.api_key or not self.model_id:
            logger.error("DeepSeek API not configured")
            return None
        
        # Construct prompt
        # Construct prompt
        system_prompt = """你是一个数据提取专家。
请忽略HTML中的所有标签结构，直接关注其中的文本内容数据。
请将网页中看起来是完整数据块的内容（例如商品信息、文章段落、评论列表等）完整地提取出来，按顺序组成一个JSON数组。
每个数据块应该是一个独立的JSON对象。

要求：
1. 彻底忽略HTML标签，只关注数据本身
2. 提取出所有有意义的数据块
3. 必须返回合法的JSON数组格式
4. 不要包含任何解释性文字，只返回JSON
"""
        
        user_prompt = f"请把以下HTML内容中的数据提取为JSON数组：\n\n{cleaned_html}"
        
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model_id,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.1  # Low temperature for more deterministic output
                },
                timeout=120.0  # 2 minute timeout for large documents
            )
            
            if response.status_code != 200:
                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            
            # Extract content from response
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not content:
                logger.error("Empty response from DeepSeek")
                return None
            
            # Try to parse as JSON
            # Sometimes the model wraps JSON in markdown code blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            extracted_data = json.loads(content)
            
            # Add metadata
            return {
                "success": True,
                "data": extracted_data,
                "model": self.model_id,
                "tokens_used": result.get("usage", {})
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return {
                "success": False,
                "error": "AI返回的不是有效的JSON格式",
                "raw_content": content if 'content' in locals() else None
            }
        except httpx.TimeoutException:
            logger.error("DeepSeek API timeout")
            return None
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return None
