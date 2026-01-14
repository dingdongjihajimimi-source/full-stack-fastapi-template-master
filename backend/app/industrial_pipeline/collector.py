import json
import logging
import asyncio
import random
import math
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from playwright.async_api import async_playwright, Page, Response, Browser, Playwright
from playwright_stealth import Stealth
from sqlalchemy.orm import Session

from app.core.db import engine
from app.core.config import settings
from app.models.crawl_index import CrawlIndex

logger = logging.getLogger(__name__)

# UA Pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

class GlobalBrowserManager:
    """Singleton manager for a shared Browser instance."""
    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None

    @classmethod
    async def start(cls):
        if not cls._playwright:
            cls._playwright = await async_playwright().start()
            logger.info("Global Playwright Started")
        
        if not cls._browser:
            # Launch standard chromium, headless. 
            # Note: stealth plugin is applied at context/page level.
            cls._browser = await cls._playwright.chromium.launch(headless=True)
            logger.info("Global Browser Instance Launched")

    @classmethod
    async def stop(cls):
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
            logger.info("Global Browser Closed")
        
        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None
            logger.info("Global Playwright Stopped")

    @classmethod
    def get_browser(cls) -> Optional[Browser]:
        return cls._browser

class IndustrialCollector:
    """
    Industrial Harvest Collector (Stealth + Concurrency Edition)
    """

    def __init__(self):
        self.collected_count = 0
        self.html_saved = False  # Track if main HTML is already saved
        self.context_requests = 0  # For memory monitoring
        self.context_recycle_threshold = 200  # Recycle after 200 requests (or 512MB)
        self.storage_root = Path(settings.STORAGE_ROOT_DIR)
        
    def _gaussian_delay(self, mean: float = 1.5, std: float = 0.5) -> float:
        """Generate Gaussian-distributed delay (in seconds)."""
        delay = random.gauss(mean, std)
        # Clamp to reasonable bounds
        return max(0.5, min(delay, 4.0))
    
    def _bezier_curve(self, start: float, end: float, steps: int = 20) -> List[float]:
        """Generate Bezier curve points for natural scrolling."""
        # Cubic Bezier with random control points
        p0, p3 = start, end
        p1 = start + (end - start) * random.uniform(0.2, 0.4)
        p2 = start + (end - start) * random.uniform(0.6, 0.8)
        
        points = []
        for i in range(steps + 1):
            t = i / steps
            # Cubic Bezier formula
            point = (
                (1-t)**3 * p0 +
                3 * (1-t)**2 * t * p1 +
                3 * (1-t) * t**2 * p2 +
                t**3 * p3
            )
            points.append(point)
        return points
        
    def _calculate_md5(self, content: bytes) -> str:
        """Calculate MD5 hash of content."""
        return hashlib.md5(content).hexdigest()
    
    def _get_storage_path(self, content_md5: str, extension: str = ".json") -> Path:
        """Get storage path for content with date-based organization."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = self.storage_root / "raw" / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir / f"{content_md5}{extension}"
    
    def _save_to_hybrid_storage(self, url: str, content: bytes, content_type: str) -> bool:
        """Save content using hybrid file+DB storage with MD5 deduplication."""
        try:
            # Calculate hashes
            url_hash = self._calculate_md5(url.encode())
            content_md5 = self._calculate_md5(content)
            
            # Check for duplicate content
            with Session(engine) as db:
                existing = db.query(CrawlIndex).filter(
                    CrawlIndex.content_md5 == content_md5
                ).first()
                
                if existing:
                    logger.debug(f"Duplicate content detected (MD5: {content_md5[:8]}), skipping write")
                    # Update timestamp only
                    existing.updated_at = datetime.utcnow()
                    db.commit()
                    return False  # Didn't write new file
                
                # Determine extension
                ext = ".json" if "json" in content_type else ".html"
                file_path = self._get_storage_path(content_md5, ext)
                
                # Write file
                file_path.write_bytes(content)
                
                # Create DB index
                index_entry = CrawlIndex(
                    url_hash=url_hash,
                    original_url=url[:2048],  # Truncate if too long
                    file_path=str(file_path.relative_to(self.storage_root)),
                    content_md5=content_md5,
                    content_type=content_type,
                    size_bytes=len(content)
                )
                db.add(index_entry)
                db.commit()
                
                logger.debug(f"Saved to hybrid storage: {file_path.name}")
                return True  # Wrote new file
                
        except Exception as e:
            logger.error(f"Hybrid storage error: {e}")
            return False
            
    async def _detect_captcha_or_block(self, page: Page) -> bool:
        """Detect if page is captcha/login wall/blocked."""
        try:
            # Check page content for blocking keywords
            content = await page.content()
            content_lower = content.lower()
            
            block_keywords = [
                "captcha", "recaptcha", "hcaptcha",
                "verify you are human", "verify you're human",
                "access denied", "blocked", "forbidden",
                "请输入验证码", "人机验证", "滑块验证",
                "cloudflare", "security check"
            ]
            
            for keyword in block_keywords:
                if keyword in content_lower:
                    logger.warning(f"Detected blocking: '{keyword}'")
                    return True
            
            return False
        except Exception:
            return False

    def _is_quality_json(self, json_data: Any, url: str) -> bool:
        """Filter out low-quality/garbage JSON (analytics, config, etc.)."""
        # Convert to string for analysis
        json_str = json.dumps(json_data, ensure_ascii=False)
        
        # Size filter: too small = likely config/metadata
        if len(json_str) < 200:
            logger.debug(f"Skipping small JSON ({len(json_str)} bytes): {url}")
            return False
        
        # Keyword blacklist: analytics, tracking, telemetry
        garbage_keywords = [
            "analytics", "sentry", "tracking", "telemetry", 
            "gtag", "gtm", "pixel", "amplitude", "mixpanel",
            "i18n", "locale", "translation", "__webpack"
        ]
        
        url_lower = url.lower()
        for keyword in garbage_keywords:
            if keyword in url_lower:
                logger.debug(f"Skipping garbage JSON (keyword '{keyword}'): {url}")
                return False
        
        # Heuristic: Check if contains valuable data keys
        # Look for common data structure indicators
        valuable_indicators = ["data", "items", "list", "results", "products", "posts"]
        if isinstance(json_data, dict):
            keys_str = " ".join(str(k).lower() for k in json_data.keys())
            if any(indicator in keys_str for indicator in valuable_indicators):
                return True
        
        # If it's an array with multiple items, likely valuable
        if isinstance(json_data, list) and len(json_data) > 3:
            return True
        
        # Medium-sized dict without blacklisted keywords = likely valuable
        if isinstance(json_data, dict) and len(json_str) >= 500:
            return True
        
        return False

    async def harvest(self, url: str, output_dir: Path, config: Dict[str, Any], progress_callback: Optional[Any] = None) -> int:
        """
        Execute harvest task with stealth tactics and concurrency support.
        Config includes: scroll_count, max_items, wait_until, etc.
        progress_callback: Async function to call with (current_count)
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        self.collected_count = 0
        
        scroll_count = config.get("scroll_count", 5)
        max_items = config.get("max_items", 100)
        wait_until = config.get("wait_until", "networkidle")
        
        browser = GlobalBrowserManager.get_browser()
        local_playwright = None
        should_close_browser = False
        context = None  # Track context for recycling

        if not browser:
            logger.warning("Global browser not found, launching local instance")
            local_playwright = await async_playwright().start()
            browser = await local_playwright.chromium.launch(headless=True)
            should_close_browser = True

        try:
            ua = random.choice(USER_AGENTS)
            viewport = {
                "width": 1920 + random.randint(-100, 100), 
                "height": 1080 + random.randint(-100, 100)
            }
            
            context = await browser.new_context(
                user_agent=ua,
                viewport=viewport,
                locale="en-US",
                timezone_id="America/New_York",
                has_touch=False,
                is_mobile=False
            )
            
            page = await context.new_page()
            
            try:
                await Stealth().apply_stealth_async(page)
                await self._inject_fingerprint_masking(page)
                
                # Setup response handler
                page.on("response", lambda response: asyncio.create_task(
                    self._handle_response(response, output_dir, max_items, progress_callback)
                ))
                
                logger.info(f"Navigating to {url} [Config: {config}]")
                await page.goto(url, wait_until=wait_until, timeout=60000) # type: ignore
                
                # Check for captcha/blocking immediately after load
                if await self._detect_captcha_or_block(page):
                    logger.error("CAPTCHA or Anti-bot block detected! Aborting harvest context.")
                    return 0
                
                for i in range(scroll_count):
                    if self.collected_count >= max_items:
                        logger.info(f"Max items reached ({max_items}), stopping scroll.")
                        break
                    
                    # Check if context needs recycling
                    if self.context_requests >= self.context_recycle_threshold:
                        logger.warning(f"Context request limit reached ({self.context_requests}), recycling context...")
                        await page.close()
                        await context.close()
                        
                        # Create fresh context
                        context = await browser.new_context(
                            user_agent=ua,
                            viewport=viewport,
                            locale="en-US",
                            timezone_id="America/New_York",
                            has_touch=False,
                            is_mobile=False
                        )
                        page = await context.new_page()
                        await Stealth().apply_stealth_async(page)
                        page.on("response", lambda response: asyncio.create_task(
                            self._handle_response(response, output_dir, max_items, progress_callback)
                        ))
                        await page.goto(url, wait_until=wait_until, timeout=60000) # type: ignore
                        self.context_requests = 0
                        logger.info("Context recycled successfully")
                        
                        # Check blocking again
                        if await self._detect_captcha_or_block(page):
                             logger.error("CAPTCHA detected after recycle! Stopping.")
                             break
                        
                    logger.info(f"Intelligent Scrolling {i+1}/{scroll_count}")
                    await self._bezier_scroll(page)
                    
                    # Auto-click "Load More" buttons if detected
                    await self._auto_click_load_more(page)
                    
                    # Wait for network activity to settle after scroll with Gaussian delay
                    await page.wait_for_timeout(int(self._gaussian_delay(1.2, 0.4) * 1000))
                    await self._wait_for_network_idle(page, timeout=5000)
                
                # Final stabilization: wait for any pending requests
                logger.info("Final network stabilization...")
                await self._wait_for_network_idle(page, timeout=3000)
                
            finally:
                await page.close()
                await context.close()
                
        except Exception as e:
            logger.error(f"Harvest error: {e}")
            raise e
            
        finally:
            if should_close_browser and browser:
                await browser.close()
                if local_playwright:
                    await local_playwright.stop()
                logger.info("Local Browser closed")

        # Extract SSR Data before closing
        try:
            await self._extract_ssr_data(page, output_dir, progress_callback)
        except Exception as e:
            logger.warning(f"SSR extraction failed: {e}")

        # Save Metadata
        self._save_metadata(url, output_dir, config)
        return self.collected_count
        
    async def _extract_ssr_data(self, page: Page, output_dir: Path, progress_callback: Optional[Any] = None):
        """Extract SSR (Server-Side Rendered) data from page scripts."""
        ssr_dir = output_dir / "ssr_data"
        ssr_dir.mkdir(exist_ok=True)
        
        # Common SSR patterns
        patterns = [
            "window.__INITIAL_STATE__",
            "window.__PRELOADED_STATE__",
            "window.__NEXT_DATA__",
            "window.__NUXT__",
            "__APOLLO_STATE__",
        ]
        
        for pattern in patterns:
            try:
                result = await page.evaluate(f"typeof {pattern} !== 'undefined' ? JSON.stringify({pattern}) : null")
                if result:
                    self.collected_count += 1
                    pattern_name = pattern.replace("window.", "").replace("__", "")
                    filename = f"ssr_{self.collected_count:04d}_{pattern_name}.json"
                    (ssr_dir / filename).write_text(result)
                    logger.info(f"Extracted SSR data: {pattern}")
                    
                    if self.collected_count % 5 == 0 and progress_callback:
                        try:
                            await progress_callback(self.collected_count)
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"Pattern {pattern} not found or failed: {e}")

    async def _inject_fingerprint_masking(self, page: Page):
        """Inject scripts to mask Canvas and WebGL fingerprints."""
        masking_script = """
        // Canvas fingerprint masking
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            const context = this.getContext('2d');
            if (context) {
                const imageData = context.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] += Math.floor(Math.random() * 3) - 1;  // Tiny random noise
                }
                context.putImageData(imageData, 0, 0);
            }
            return originalToDataURL.apply(this, arguments);
        };
        
        // WebGL fingerprint masking
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(param) {
            if (param === 37445) {  // UNMASKED_VENDOR_WEBGL
                return 'Intel Inc.';
            }
            if (param === 37446) {  // UNMASKED_RENDERER_WEBGL
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter.apply(this, arguments);
        };
        """
        try:
            await page.add_init_script(masking_script)
            logger.debug("Fingerprint masking scripts injected")
        except Exception as e:
            logger.warning(f"Failed to inject masking scripts: {e}")
    
    async def _bezier_scroll(self, page: Page):
        """Scroll using Bezier curve for natural acceleration."""
        try:
            current_scroll = await page.evaluate("window.scrollY")
            viewport_height = await page.evaluate("window.innerHeight")
            
            # Target scroll distance (70-90% of viewport)
            scroll_distance = viewport_height * random.uniform(0.7, 0.9)
            target_scroll = current_scroll + scroll_distance
            
            # Generate Bezier curve points
            curve_points = self._bezier_curve(current_scroll, target_scroll, steps=25)
            
            # Animate scroll along curve
            for i, scroll_pos in enumerate(curve_points):
                await page.evaluate(f"window.scrollTo(0, {scroll_pos})")
                # Variable delay mimicking mouse wheel physics
                delay = random.randint(15, 40) if i < len(curve_points) // 2 else random.randint(20, 60)
                await page.wait_for_timeout(delay)
            
            # Wait for height stabilization
            prev_height = await page.evaluate("document.body.scrollHeight")
            for retry in range(5):
                await page.wait_for_timeout(int(self._gaussian_delay(0.8, 0.2) * 1000))
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height > prev_height:
                    logger.debug(f"Height increased: {prev_height} -> {new_height}")
                    prev_height = new_height
                else:
                    break
                    
        except Exception as e:
            logger.warning(f"Bezier scroll error: {e}")
    
    async def _auto_click_load_more(self, page: Page):
        """Detect and click 'Load More' or similar buttons."""
        try:
            # Common patterns for pagination buttons
            selectors = [
                "text=/load more/i",
                "text=/show more/i",
                "text=/查看更多/i",
                "text=/加载更多/i",
                "button:has-text('More')",
                "a:has-text('Next')",
                "[class*='load']:has-text('more')",
                "[class*='show']:has-text('more')"
            ]
            
            for selector in selectors:
                try:
                    button = page.locator(selector).first
                    if await button.is_visible(timeout=1000):
                        logger.info(f"Auto-clicking: {selector}")
                        await button.click()
                        await page.wait_for_timeout(int(self._gaussian_delay(1.5, 0.5) * 1000))
                        return  # Only click one button per scroll
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Auto-click check failed: {e}")

    async def _intelligent_scroll(self, page: Page):
        """Adaptive scrolling that waits for dynamic content to load."""
        try:
            # Get initial height
            prev_height = await page.evaluate("document.body.scrollHeight")
            
            # Scroll down in smaller, measured steps
            viewport_height = await page.evaluate("window.innerHeight")
            current_scroll = await page.evaluate("window.scrollY")
            
            # Target: scroll about 70-90% of viewport (more conservative)
            scroll_distance = viewport_height * random.uniform(0.7, 0.9)
            target_scroll = current_scroll + scroll_distance
            
            # Smooth scroll in chunks
            steps = random.randint(8, 15)
            step_size = scroll_distance / steps
            
            for step in range(steps):
                current_scroll += step_size * random.uniform(0.9, 1.1)
                await page.evaluate(f"window.scrollTo(0, {current_scroll})")
                await page.wait_for_timeout(random.randint(80, 150))  # Slower, more human-like
            
            # CRITICAL: Wait for height to stabilize (lazy loading indicator)
            max_retries = 5
            for retry in range(max_retries):
                await page.wait_for_timeout(800)  # Give page time to trigger lazy load
                new_height = await page.evaluate("document.body.scrollHeight")
                
                if new_height > prev_height:
                    logger.debug(f"Height increased: {prev_height} -> {new_height}")
                    prev_height = new_height
                    # Content is still loading, keep waiting
                else:
                    # Height stable, likely loaded
                    break
                    
        except Exception as e:
            logger.warning(f"Intelligent scroll error: {e}")
    
    async def _wait_for_network_idle(self, page: Page, timeout: int = 5000):
        """Wait until network is idle (no requests for 500ms)."""
        try:
            # Use Playwright's built-in network idle detection
            await page.wait_for_load_state("networkidle", timeout=timeout)  # type: ignore
            logger.debug("Network idle confirmed")
        except Exception as e:
            # Timeout is acceptable, just log and continue
            logger.debug(f"Network idle timeout (acceptable): {e}")

    async def _human_scroll(self, page: Page):
        """Simulate human scrolling behavior with randomization."""
        try:
            # Random scroll steps
            total_height = await page.evaluate("document.body.scrollHeight")
            current_pos = 0
            step_size = random.randint(150, 400)
            
            while current_pos < total_height:
                current_pos += step_size
                await page.evaluate(f"window.scrollTo(0, {current_pos})")
                
                # Random pause
                await page.wait_for_timeout(random.randint(100, 500))
                
                # Re-calculate height (for infinite scroll)
                total_height = await page.evaluate("document.body.scrollHeight")
                
        except Exception:
            pass # Ignore scroll errors to ensure task continues

    async def _handle_response(self, response: Response, output_dir: Path, max_items: int, progress_callback: Optional[Any] = None):
        """Handle individual network response with heuristic JSON detection."""
        try:
            if self.collected_count >= max_items:
                return

            content_type = response.headers.get("content-type", "")
            resource_type = response.request.resource_type
            self.context_requests += 1
            
            # Heuristic Interception: Check ALL fetch/xhr/script/other for JSON
            if resource_type in ["xhr", "fetch", "script", "other"]:
                try:
                    body = await response.body()
                    if not body:
                        return
                    
                    # Decode and check if starts with { or [
                    try:
                        text = body.decode('utf-8', errors='ignore').strip()
                        if text.startswith(('{', '[')):
                            # Attempt JSON parse regardless of Content-Type
                            try:
                                json_data = json.loads(text)
                                self.collected_count += 1
                                idx = self.collected_count
                                
                                api_dir = output_dir / "api_data"
                                api_dir.mkdir(exist_ok=True)
                                
                                url_seg = response.url.split("?")[0].split("/")[-1]
                                url_seg = "".join([c for c in url_seg if c.isalnum() or c in "._-"])[:30]
                                if not url_seg: url_seg = "data"
                                
                                filename = f"api_{idx:04d}_{url_seg}.json"
                                
                                # Quality filter before saving
                                if not self._is_quality_json(json_data, response.url):
                                    return  # Skip low-quality JSON
                                
                                # Use hybrid storage
                                content_bytes = json.dumps(json_data, indent=2, ensure_ascii=False).encode('utf-8')
                                self._save_to_hybrid_storage(response.url, content_bytes, "application/json")
                                logger.info(f"Heuristic JSON captured: {response.url}")
                                
                                # Non-blocking callback (fire and forget)
                                if self.collected_count % 5 == 0 and progress_callback:
                                    asyncio.create_task(self._safe_callback(progress_callback, self.collected_count))
                                return
                            except json.JSONDecodeError:
                                pass  # Not valid JSON, continue to normal handling
                    except Exception:
                        pass
                except Exception:
                    pass

            # HTML: Save main page only once, don't count it
            if "text/html" in content_type:
                if not self.html_saved:
                    try:
                        body = await response.body()
                        if body:
                            # Use hybrid storage for HTML too
                            self._save_to_hybrid_storage(response.url, body, "text/html")
                            self.html_saved = True
                            logger.info("Saved main HTML page (hybrid storage)")
                    except Exception:
                        pass
                return  # Don't count HTML toward max_items

            # Skip images and other non-data assets
            if any(ct in content_type for ct in ["image/", "video/", "font/", "text/css"]):
                return

        except Exception as e:
            logger.warning(f"Failed to process response {response.url}: {e}")
    
    async def _safe_callback(self, callback, count: int):
        """Execute callback safely without blocking network."""
        try:
            await callback(count)
        except Exception as e:
            logger.error(f"Progress callback failed: {e}")

    def _save_metadata(self, url: str, output_dir: Path, config: Dict[str, Any]):
        metadata = {
            "url": url,
            "config": config,
            "collected_at": datetime.now().isoformat(),
            "resource_count": self.collected_count,
            "mode": "stealth_concurrent_v2"
        }
        (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
