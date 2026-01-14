import logging
from app.sniffer_pipeline import SnifferPipeline

logger = logging.getLogger(__name__)

async def sniff_api(url: str, scroll_count: int = 3):
    """
    Refactored to use the autonomous SnifferPipeline.
    This function triggers the full Scout-Harvest-Refine process.
    
    Legacy wrapper for the new autonomous pipeline.
    """
    logger.info(f"Using new SnifferPipeline for {url}")
    pipeline = SnifferPipeline()
    # Note: run() handles the full flow including DB insertion.
    result = await pipeline.run(url)
    return result
