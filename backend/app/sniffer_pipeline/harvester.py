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
        Phase 3: Execute targeted harvesting based on the strategy.
        """
        async def _log(msg, level="INFO"):
            logger.info(f"[{task_id}] {msg}")
            if log_callback:
                await log_callback(msg, level)

        raw_data: List[RawDataBlock] = []
        user_agent = self.ua.random
        
        # Compile regex for performance
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
                # Interceptor logic
                request = response.request
                # Check if URL matches the target pattern
                if pattern.search(request.url):
                    try:
                        # Only care about successful responses
                        if response.ok:
                            content_type = response.headers.get("content-type", "").lower()
                            data = None
                            
                            # Try parsing as JSON first
                            if "application/json" in content_type or "text/json" in content_type:
                                try:
                                    data = await response.json()
                                    await _log(f"Extracted JSON from: {request.url}", "DEBUG")
                                except:
                                    pass
                            
                            # Fallback to Text/HTML
                            if data is None:
                                text_content = await response.text()
                                # Wrap HTML in a structure compatible with Refinery
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
                    # Log ignored URLs at DEBUG level
                    # await _log(f"Ignored: {request.url}", "DEBUG")
                    pass

            page.on("response", handle_response)

            try:
                await page.goto(url, wait_until="networkidle", timeout=45000)
                
                # Active Harvesting Loop (Scroll/Paginate)
                # In a real scenario, this might need to click "Next" buttons too, 
                # but scrolling is a good baseline for infinite scroll APIs.
                for i in range(max_scrolls):
                    await _log(f"Harvester scrolling {i+1}/{max_scrolls}")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    # Dynamic wait could be better, but fixed is safe for now
                    await asyncio.sleep(4) 
                
                await asyncio.sleep(2)
            except Exception as e:
                await _log(f"Harvester navigation error: {e}", "ERROR")
            finally:
                await browser.close()
        
        await _log(f"Harvester finished. Collected {len(raw_data)} data blocks.")
        return raw_data
