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
        Phase 1: Navigate, scroll, and capture all JSON candidates.
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

                    # Filter for JSON-like responses
                    is_json = any(t in content_type for t in [
                        "application/json", 
                        "application/vnd.api+json", 
                        "text/json", 
                        "text/javascript",
                        "application/javascript"
                    ])
                    
                    # Also accept text/plain if it looks like JSON
                    if "text/plain" in content_type:
                        try:
                            # We'll peek at the body later to confirm
                            is_json = True
                        except:
                            pass

                    # Relaxed resource type filter
                    # Accept almost anything that isn't obviously media/css
                    is_data_request = resource_type in ["xhr", "fetch", "script", "other", "document"]
                    
                    if is_json and is_data_request:
                        headers = {
                            k: v for k, v in request.headers.items()
                            if k.lower() in ["referer", "authorization", "cookie", "x-requested-with", "accept", "user-agent"]
                        }
                        
                        try:
                            body = await response.text()
                            # Double check content for JSON-like structure if ambiguous
                            if "text/plain" in content_type and not (body.strip().startswith("{") or body.strip().startswith("[")):
                                return
                            
                            preview = body[:5000] # Increased preview size
                        except Exception:
                            # If we can't read the body, skip it
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
                        # Log rejected URLs at DEBUG level only
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
                
                # Final wait for trailing requests
                await asyncio.sleep(3.0)

            except Exception as e:
                await _log(f"Scout navigation error: {e}", "ERROR")
            finally:
                await browser.close()
        
        await _log(f"Scout finished. Found {len(candidates)} raw candidates.")
        return self._deduplicate_candidates(candidates)

    def _deduplicate_candidates(self, candidates: List[Candidate]) -> List[Candidate]:
        """
        Simple deduplication to avoid sending identical API calls to AI.
        Groups by Method + URL Path (ignoring query params mostly, or maybe keeping them?)
        Let's keep unique Method+URL for now.
        """
        unique_map = {}
        for c in candidates:
            # Use full URL to distinguish different pagination calls etc, 
            # but maybe we only need one sample per endpoint pattern?
            # AI needs to see the pattern. 
            # Let's keep one sample per "Endpoint Path".
            from urllib.parse import urlparse
            parsed = urlparse(c.url)
            key = f"{c.method}:{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # Keep the one with the longest preview (most data)
            if key not in unique_map:
                unique_map[key] = c
            else:
                if len(c.response_preview) > len(unique_map[key].response_preview):
                    unique_map[key] = c
        
        return list(unique_map.values())
