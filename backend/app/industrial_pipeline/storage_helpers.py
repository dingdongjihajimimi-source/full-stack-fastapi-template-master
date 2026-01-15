"""
工业采集器的混合存储和去重辅助方法。

这些方法应添加到 IndustrialCollector 类中。
"""

def _calculate_md5(self, content: bytes) -> str:
    """计算内容的 MD5 哈希值。"""
    return hashlib.md5(content).hexdigest()

def _get_storage_path(self, content_md5: str, extension: str = ".json") -> Path:
    """获取基于日期组织的内容存储路径。"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    date_dir = self.storage_root / "raw" / date_str
    date_dir.mkdir(parents=True, exist_ok=True)
    return date_dir / f"{content_md5}{extension}"

def _save_to_hybrid_storage(self, url: str, content: bytes, content_type: str) -> bool:
    """使用混合文件+数据库存储保存内容，并进行 MD5 去重。"""
    try:
        # 计算哈希值
        url_hash = self._calculate_md5(url.encode())
        content_md5 = self._calculate_md5(content)
        
        # 检查重复内容
        with Session(engine) as db:
            existing = db.query(CrawlIndex).filter(
                CrawlIndex.content_md5 == content_md5
            ).first()
            
            if existing:
                logger.debug(f"Duplicate content detected (MD5: {content_md5[:8]}), skipping write")
                # 仅更新时间戳
                existing.updated_at = datetime.utcnow()
                db.commit()
                return False  # Didn't write new file
            
            # 确定扩展名
            ext = ".json" if "json" in content_type else ".html"
            file_path = self._get_storage_path(content_md5, ext)
            
            # 写入文件
            file_path.write_bytes(content)
            
            # 创建数据库索引
            index_entry = CrawlIndex(
                url_hash=url_hash,
                original_url=url[:2048],  # 如果太长则截断
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
    """检测页面是否被验证码/登录墙/阻止。"""
    try:
        # 检查页面内容中的阻止关键字
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
