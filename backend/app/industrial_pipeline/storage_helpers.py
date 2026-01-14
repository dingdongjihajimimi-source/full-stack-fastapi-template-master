"""
Hybrid Storage and Deduplication Helper Methods for Industrial Collector.

These methods should be added to the IndustrialCollector class.
"""

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
            
            logger.debug(f"✅ Saved to hybrid storage: {file_path.name}")
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
                logger.warning(f"🚫 Detected blocking: '{keyword}'")
                return True
        
        return False
    except Exception:
        return False
