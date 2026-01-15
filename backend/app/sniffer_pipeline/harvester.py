import asyncio
import logging
import re
import json
import time
from typing import List
from playwright.async_api import async_playwright, Response
from fake_useragent import UserAgent
from .schemas import ExtractionStrategy, RawDataBlock

logger = logging.getLogger(__name__)

class Harvester:
    def __init__(self):
        self.ua = UserAgent()

    async def run_harvest(self, url: str, strategy: ExtractionStrategy, max_scrolls: int = 5, task_id: str = "Unknown", log_callback=None) -> List[RawDataBlock]:
        """
        第三阶段：根据策略执行目标收割。
        """
        async def _log(msg, level="INFO"):
            logger.info(f"[{task_id}] {msg}")
            if log_callback:
                await log_callback(msg, level)

        raw_data: List[RawDataBlock] = []
        user_agent = self.ua.random
        
        # 编译正则表达式以提高性能
        try:
            pattern = re.compile(strategy.target_api_url_pattern)
        except re.error as e:
            await _log(f"Invalid regex pattern in strategy: {e}", "ERROR")
            raise

        await _log(f"Harvester starting for {url} with pattern: {strategy.target_api_url_pattern}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True
            )
            page = await context.new_page()

            async def handle_response(response: Response):
                # 拦截器逻辑
                request = response.request
                # 检查 URL 是否匹配目标模式
                if pattern.search(request.url):
                    try:
                        # 只关注成功的响应
                        if response.ok:
                            content_type = response.headers.get("content-type", "").lower()
                            data = None
                            
                            # 尝试先解析为 JSON
                            if "application/json" in content_type or "text/json" in content_type:
                                try:
                                    data = await response.json()
                                    await _log(f"Extracted JSON from: {request.url}", "DEBUG")
                                except:
                                    pass
                            
                            # 回退到 Text/HTML
                            if data is None:
                                text_content = await response.text()
                                # 将 HTML 包装在与 Refinery 兼容的结构中
                                data = {"html": text_content, "url": request.url, "content_type": content_type}
                                await _log(f"Extracted HTML/Text ({len(text_content)} chars) from: {request.url}", "DEBUG")

                            if data:
                                raw_data.append(RawDataBlock(
                                    url=request.url,
                                    data=data,
                                    timestamp=time.time()
                                ))
                                await _log(f"Harvested data chunk from {request.url}")
                        else:
                            await _log(f"Response not OK ({response.status}) for target: {request.url}", "WARN")
                    except Exception as e:
                        await _log(f"Failed to process response from target {request.url}: {e}", "WARN")
                else:
                    # 在 DEBUG 级别记录忽略的 URL
                    # await _log(f"Ignored: {request.url}", "DEBUG")
                    pass

            page.on("response", handle_response)

            try:
                await page.goto(url, wait_until="networkidle", timeout=45000)
                
                # 主动收割循环（滚动/分页）
                # 在真实场景中，这可能也需要点击“下一页”按钮，但滚动是无限滚动 API 的良好基准。
                for i in range(max_scrolls):
                    await _log(f"Harvester scrolling {i+1}/{max_scrolls}")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    # 动态等待可能更好，目前固定等待是安全的
                    await asyncio.sleep(4) 
                
                await asyncio.sleep(2)
            except Exception as e:
                await _log(f"Harvester navigation error: {e}", "ERROR")
            finally:
                await browser.close()
        
        await _log(f"Harvester finished. Collected {len(raw_data)} data blocks.")
        return raw_data
