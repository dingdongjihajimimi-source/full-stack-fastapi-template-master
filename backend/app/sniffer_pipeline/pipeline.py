import logging
import asyncio
from typing import Optional, Dict, Any
from .scout import Scout
from .architect import Architect
from .harvester import Harvester
from .refinery import Refinery
from .schemas import ExtractionStrategy

logger = logging.getLogger(__name__)

class SnifferPipeline:
    """
    Autonomous 'Scout-Harvest-Refine' Pipeline.
    Supports pausing, resuming, and status tracking.
    """
    def __init__(self):
        self.scout = Scout()
        self.architect = Architect()
        self.harvester = Harvester()
        self.refinery = Refinery()

    async def run(
        self, 
        url: str, 
        task_id: str, 
        update_callback=None, 
        table_name_hint: Optional[str] = None,
        review_mode: bool = False
    ):
        """
        Executes the pipeline.
        
        Args:
            url: Target URL
            task_id: Unique ID for the task (used for logging/state)
            update_callback: Async function(task_id, phase, state_data) to persist state
            table_name_hint: Optional table name to suggest to AI
            review_mode: If True, pauses after Phase 2 for user confirmation
        """
        
        async def _notify(phase: str, state_data: Dict[str, Any] = None):
            logger.info(f"[{task_id}] Phase Update: {phase}")
            if update_callback:
                await update_callback(task_id, phase, state_data)

        async def _log(message: str, phase: str, level: str = "INFO"):
            """
            Enhanced logging helper.
            """
            log_msg = f"[{task_id}] {message}"
            if level == "ERROR":
                logger.error(log_msg)
            elif level == "WARN":
                logger.warning(log_msg)
            elif level == "DEBUG":
                logger.debug(log_msg)
            else:
                logger.info(log_msg)
                
            if update_callback:
                # Pass plain message to frontend, maybe with a level prefix if needed
                # But frontend usually just displays lines. We can prefix meaningful icons or colors if we want.
                prefix = ""
                if level == "ERROR": prefix = "❌ "
                elif level == "WARN": prefix = "⚠️ "
                
                await update_callback(task_id, phase, {"log_message": f"{prefix}{message}"})

        logger.info(f"🚀 Starting Sniffer Pipeline for target: {url} (Task: {task_id})")
        await _log(f"Starting Sniffer Pipeline for target: {url}", "scout")

        # Phase 1: Scout
        await _notify("scout")
        logger.info("--- Phase 1: Scout (Sampling) ---")
        try:
            candidates = await self.scout.sniff_sample(url, task_id=task_id, log_callback=lambda m, l="INFO": _log(m, "scout", l))
        except Exception as e:
            await _log(f"Scout crashed: {e}", "scout", "ERROR")
            candidates = []

        if not candidates:
            logger.error("Scout found no API candidates. Aborting.")
            await _notify("failed", {"error": "No candidates found"})
            return {"status": "failed", "step": "scout", "message": "No candidates found"}
        
        await _log(f"✅ Scout found {len(candidates)} candidates.", "scout")
        logger.info(f"✅ Scout found {len(candidates)} candidates.")

        # Phase 2: Architect
        await _notify("architect")
        logger.info("--- Phase 2: Architect (Strategy Definition) ---")
        try:
            strategy = await self.architect.define_extraction_strategy(candidates, table_name_hint, task_id=task_id, log_callback=lambda m, l="INFO": _log(m, "architect", l))
            logger.info(f"✅ Strategy defined: {strategy.description}")
            await _log(f"✅ Strategy defined: {strategy.description}", "architect")
        except Exception as e:
            logger.error(f"Architect failed: {e}")
            await _notify("failed", {"error": str(e)})
            return {"status": "failed", "step": "architect", "error": str(e)}

        # Pause for Review if requested
        if review_mode:
            logger.info("⏸ Pausing for Pre-run Review...")
            await _notify("review", {"strategy": strategy.dict()})
            return {"status": "paused", "step": "review", "strategy": strategy.dict()}

        # Continue directly if no review
        return await self.resume(task_id, url, strategy, update_callback)

    async def resume(
        self,
        task_id: str,
        url: str,
        strategy: ExtractionStrategy,
        update_callback=None
    ):
        """
        Resumes the pipeline from Phase 3 (Harvester) with a (potentially modified) strategy.
        """
        async def _notify(phase: str, state_data: Dict[str, Any] = None):
            logger.info(f"[{task_id}] Phase Update: {phase}")
            if update_callback:
                await update_callback(task_id, phase, state_data)

        async def _log(message: str, phase: str, level: str = "INFO"):
            log_msg = f"[{task_id}] {message}"
            if level == "ERROR":
                logger.error(log_msg)
            elif level == "WARN":
                logger.warning(log_msg)
            elif level == "DEBUG":
                logger.debug(log_msg)
            else:
                logger.info(log_msg)
                
            if update_callback:
                prefix = ""
                if level == "ERROR": prefix = "❌ "
                elif level == "WARN": prefix = "⚠️ "
                await update_callback(task_id, phase, {"log_message": f"{prefix}{message}"})

        # Phase 3: Harvester
        await _notify("harvester")
        logger.info("--- Phase 3: Harvester (Execution) ---")
        try:
            raw_data = await self.harvester.run_harvest(url, strategy, task_id=task_id, log_callback=lambda m, l="INFO": _log(m, "harvester", l))
            logger.info(f"✅ Harvester collected {len(raw_data)} chunks.")
            await _log(f"✅ Harvester collected {len(raw_data)} chunks.", "harvester")
        except Exception as e:
            logger.error(f"Harvester failed: {e}")
            await _notify("failed", {"error": str(e)})
            return {"status": "failed", "step": "harvester", "error": str(e)}

        # Phase 4: Refinery
        await _notify("refinery")
        logger.info("--- Phase 4: Refinery (ETL & SQL) ---")
        try:
            items_refined = await self.refinery.process_and_insert(raw_data, strategy, task_id, log_callback=lambda m, l="INFO": _log(m, "refinery", l))
            logger.info("✅ Refinery finished execution.")
            await _log(f"✅ Refinery finished execution. Extracted {items_refined} items.", "refinery")
        except Exception as e:
            logger.error(f"Refinery failed: {e}")
            await _notify("failed", {"error": str(e)})
            return {"status": "failed", "step": "refinery", "error": str(e)}

        await _notify("completed", {"items_harvested": items_refined})
        await _log(f"🎉 Pipeline completed. Harvested {items_refined} items.", "completed")
        logger.info("🎉 Pipeline completed successfully.")
        return {
            "status": "success",
            "strategy": strategy.dict(),
            "items_harvested": items_refined
        }
