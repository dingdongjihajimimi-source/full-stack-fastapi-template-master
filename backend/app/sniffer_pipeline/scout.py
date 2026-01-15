import asyncio
import logging
import random
from typing import List, Dict, Any
from fake_useragent import UserAgent
from playwright.async_api import async_playwright, Response
from .schemas import Candidate

logger = logging.getLogger(__name__)

class Scout:
    def __init__(self):
        self.ua = UserAgent()

    async def sniff_sample(self, url: str, scroll_count: int = 2, task_id: str = "Unknown", log_callback=None) -> List[Candidate]:
        """
        第一阶段：导航、滚动并捕获所有 JSON 候选者。
        """
        candidates: List[Candidate] = []
        user_agent = self.ua.random

        async def _log(msg, level="INFO"):
            logger.info(f"[{task_id}] {msg}")
            if log_callback:
                await log_callback(msg, level)

        await _log(f"Scout starting for {url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True
            )
            page = await context.new_page()

            async def handle_response(response: Response):
                try:
                    request = response.request
                    resource_type = request.resource_type
                    content_type = response.headers.get("content-type", "").lower()

                    # 过滤类似 JSON 的响应
                    is_json = any(t in content_type for t in [
                        "application/json", 
                        "application/vnd.api+json", 
                        "text/json", 
                        "text/javascript",
                        "application/javascript"
                    ])
                    
                    # 如果看起来像 JSON，也接受 text/plain
                    if "text/plain" in content_type:
                        try:
                            # 稍后我们会查看正文进行确认
                            is_json = True
                        except:
                            pass

                    # 放宽的资源类型过滤器
                    # 接受几乎任何不是明显媒体/CSS 的内容
                    is_data_request = resource_type in ["xhr", "fetch", "script", "other", "document"]
                    
                    if is_json and is_data_request:
                        headers = {
                            k: v for k, v in request.headers.items()
                            if k.lower() in ["referer", "authorization", "cookie", "x-requested-with", "accept", "user-agent"]
                        }
                        
                        try:
                            body = await response.text()
                            # 如果不明确，仔细检查内容是否有类似 JSON 的结构
                            if "text/plain" in content_type and not (body.strip().startswith("{") or body.strip().startswith("[")):
                                return
                            
                            preview = body[:5000] # 增加预览大小
                        except Exception:
                            # 如果无法读取正文，则跳过
                            return

                        candidate = Candidate(
                            url=request.url,
                            method=request.method,
                            headers=headers,
                            payload=request.post_data,
                            response_preview=preview,
                            resource_type=resource_type
                        )
                        candidates.append(candidate)
                        await _log(f"Captured candidate: {request.method} {request.url} ({resource_type})", "DEBUG")
                    else:
                        # 仅在 DEBUG 级别记录拒绝的 URL
                        # await _log(f"Skipped: {request.url} (Type: {content_type})", "DEBUG")
                        pass

                except Exception as e:
                    logger.error(f"Error in response handler: {e}")

            page.on("response", handle_response)

            try:
                await _log(f"Navigating to {url}...")
                await page.goto(url, wait_until="networkidle", timeout=45000)

                for i in range(scroll_count):
                    await _log(f"Scout scrolling ({i+1}/{scroll_count})...")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(random.uniform(1.5, 3.0))
                
                # 最后等待后续请求
                await asyncio.sleep(3.0)

            except Exception as e:
                await _log(f"Scout navigation error: {e}", "ERROR")
            finally:
                await browser.close()
        
        await _log(f"Scout finished. Found {len(candidates)} raw candidates.")
        return self._deduplicate_candidates(candidates)

    def _deduplicate_candidates(self, candidates: List[Candidate]) -> List[Candidate]:
        """
        简单的去重，以避免向 AI 发送相同的 API 调用。
        按方法 + URL 路径分组（主要忽略查询参数，或者保留它们？）
        目前让我们保持唯一的方法+URL。
        """
        unique_map = {}
        for c in candidates:
            # 使用完整 URL 来区分不同的分页调用等，
            # 但也许每个端点模式只需要一个样本？
            # AI 需要看到模式。
            # 让我们每个“端点路径”保留一个样本。
            from urllib.parse import urlparse
            parsed = urlparse(c.url)
            key = f"{c.method}:{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # 保留预览最长的一个（数据最多）
            if key not in unique_map:
                unique_map[key] = c
            else:
                if len(c.response_preview) > len(unique_map[key].response_preview):
                    unique_map[key] = c
        
        return list(unique_map.values())
