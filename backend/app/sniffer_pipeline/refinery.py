# app/sniffer_pipeline/refinery.py

import logging
import csv
import json
import re
from typing import List, Any
from sqlalchemy import text
from app.core.db import engine
from app.sniffer_pipeline.schemas import ExtractionStrategy, RawDataBlock
from app.core.paths import SQL_DIR, CSV_DIR  # 引入统一路径

logger = logging.getLogger(__name__)

class Refinery:
    def __init__(self):
        # 彻底移除 LLM 客户端，纯 Python 处理
        pass

    async def process_and_insert(self, raw_data_list: List[RawDataBlock], strategy: ExtractionStrategy, task_id: str, log_callback=None) -> int:
        """
        执行转换代码，生成 CSV/SQL 文件，并入库。
        """
        async def _log(msg, level="INFO"):
            logger.info(f"[{task_id}] {msg}")
            if log_callback:
                await log_callback(msg, level)

        if not raw_data_list:
            await _log("No raw data blocks to refine.", "WARN")
            return 0

        await _log(f"Refinery started. Processing {len(raw_data_list)} raw data blocks...")

        # 1. 编译转换函数 (Code Execution)
        try:
            local_scope = {}
            # 执行 LLM 生成的 Python 代码
            exec(strategy.transform_code, {}, local_scope)
            transform_func = local_scope.get("transform_item")
            
            if not callable(transform_func):
                raise ValueError("Generated code missing 'transform_item' function")
            await _log("Transformation code compiled successfully.", "DEBUG")
        except Exception as e:
            await _log(f"Failed to compile transformation code: {e}", "ERROR")
            return 0

        # 2. 准备数据库表
        # 从 CREATE TABLE 语句中提取表名
        table_name_match = re.search(r"CREATE TABLE\s+([^\s\(]+)", strategy.sql_schema, re.IGNORECASE)
        table_name = table_name_match.group(1) if table_name_match else "scraped_data"
        await _log(f"Target table name identified: {table_name}", "DEBUG")

        try:
            with engine.connect() as connection:
                connection.execute(text(strategy.sql_schema))
                connection.commit()
            await _log("SQL Schema applied (Table created/verified).", "DEBUG")
        except Exception as e:
            await _log(f"Table creation failed (might already exist): {e}", "WARN")
            # 继续尝试处理，也许表已经存在

        # 3. 处理数据循环
        total_items = 0
        batch_size = 500  # 每 500 条写一次文件和数据库
        buffer = []

        async with engine.connect() as connection:
            for i, block in enumerate(raw_data_list):
                # 兼容处理: data 可能是 list 也可能是 dict
                raw_items = block.data
                if isinstance(raw_items, dict):
                    raw_items = raw_items.get('data', raw_items.get('list', [raw_items]))
                if not isinstance(raw_items, list):
                    raw_items = [raw_items]

                await _log(f"Processing block {i+1}/{len(raw_data_list)} ({len(raw_items)} items)", "DEBUG")

                for item in raw_items:
                    try:
                        # === 核心转换 ===
                        row_dict = transform_func(item)
                        if row_dict:
                            buffer.append(row_dict)
                    except Exception as e:
                        await _log(f"Transform error on item: {e}", "WARN")

                    # === 缓冲区满，刷盘 ===
                    if len(buffer) >= batch_size:
                        await self._flush_buffer(connection, buffer, table_name, task_id)
                        total_items += len(buffer)
                        buffer = [] # 清空缓冲

            # === 处理剩余数据 ===
            if buffer:
                await self._flush_buffer(connection, buffer, table_name, task_id)
                total_items += len(buffer)

        await _log(f"Refinery complete. Processed {total_items} items.")
        return total_items

    async def _flush_buffer(self, connection, buffer: List[dict], table_name: str, task_id: str):
        """
        将缓冲区数据写入 CSV, SQL 文件并插入数据库
        """
        if not buffer:
            return

        keys = list(buffer[0].keys())

        # --- 1. 写入 CSV 文件 ---
        csv_path = CSV_DIR / f"{task_id}.csv"
        file_exists = csv_path.exists()
        try:
            with open(csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(buffer)
        except Exception as e:
            logger.error(f"Failed to write CSV: {e}")

        # --- 2. 写入 SQL 文件 (用于下载) ---
        sql_path = SQL_DIR / f"{task_id}.sql"
        try:
            with open(sql_path, "a", encoding="utf-8") as f:
                for row in buffer:
                    # 简单的 SQL 生成逻辑 (注意：生产环境要注意转义，这里做基础处理)
                    cols = ", ".join(keys)
                    vals = []
                    for k in keys:
                        v = row.get(k)
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        else:
                            # 转义单引号
                            safe_v = str(v).replace("'", "''")
                            vals.append(f"'{safe_v}'")
                    
                    val_str = ", ".join(vals)
                    f.write(f"INSERT INTO {table_name} ({cols}) VALUES ({val_str});\n")
        except Exception as e:
            logger.error(f"Failed to write SQL file: {e}")

        # --- 3. 插入数据库 (真实存储) ---
        try:
            # 使用 SQLAlchemy 的 bind params 方式防止注入
            # 构造 :key 格式的 value 占位符
            bind_vals = ", ".join([f":{k}" for k in keys])
            cols = ", ".join(keys)
            stmt = text(f"INSERT INTO {table_name} ({cols}) VALUES ({bind_vals})")
            
            await connection.execute(stmt, buffer)
            await connection.commit()
            logger.info(f"✅ Flushed {len(buffer)} items to DB/CSV/SQL")
        except Exception as e:
            logger.error(f"DB Insert failed: {e}")
            await connection.rollback()