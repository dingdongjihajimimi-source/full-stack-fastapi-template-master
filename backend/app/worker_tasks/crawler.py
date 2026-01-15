import uuid
import json
import asyncio
import os
import csv
import httpx
import re
import random
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from pathlib import Path
from sqlmodel import Session
from app.core.db import engine
from app.models import CrawlerTask
from app.core.config import settings
from openai import AsyncOpenAI

# 定义生成文件的根目录
GENERATED_DATA_DIR = Path("generated_data")
CSV_DIR = GENERATED_DATA_DIR / "csv"
SQL_DIR = GENERATED_DATA_DIR / "sql"

# 确保目录存在
CSV_DIR.mkdir(parents=True, exist_ok=True)
SQL_DIR.mkdir(parents=True, exist_ok=True)

# 用于轮换的常见用户代理列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]

def get_random_headers():
    """生成随机请求头以规避反爬虫。"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

def get_next_page_url(current_url: str, html_content: str) -> str | None:
    """
    使用正则启发式或 HTML 解析确定下一页 URL。
    """
    # 策略 A：正则启发式 (例如 page=1, /page/1)
    # 匹配类似 ?page=123 或 /page/123 的模式
    # 第一组：前缀，第二组：页码，第三组：后缀
    page_patterns = [
        r"([?&]page=)(\d+)",
        r"(/page/)(\d+)"
    ]
    
    for pattern in page_patterns:
        match = re.search(pattern, current_url)
        if match:
            current_page_num = int(match.group(2))
            next_page_num = current_page_num + 1
            # 仅替换第一次出现
            next_url = current_url[:match.start(2)] + str(next_page_num) + current_url[match.end(2):]
            return next_url

    # 策略 B：HTML 解析 (BeautifulSoup)
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # 查找带有“Next”、“下一页”、“>”等文本的 <a> 标签
        next_keywords = ["next", "下一页", ">", "more"]
        
        for a in soup.find_all('a', href=True):
            text = a.get_text().strip().lower()
            if any(keyword in text for keyword in next_keywords):
                next_href = a['href']
                return urljoin(current_url, next_href)
    except Exception as e:
        print(f"Error parsing HTML for next page: {e}")
    
    return None

async def process_page(
    page_index: int, 
    url: str, 
    table_name: str, 
    columns: list[str], 
    semaphore: asyncio.Semaphore, 
    csv_lock: asyncio.Lock, 
    sql_lock: asyncio.Lock, 
    client: AsyncOpenAI, 
    task_id: uuid.UUID,
    session_updater
) -> str | None:
    """
    并发处理单个页面/项目。
    管道：爬取 -> 保存 CSV -> AI -> 保存 SQL
    返回：下一页 URL（如果找到）或 None
    """
    async with semaphore:
        try:
            # 步骤 1：爬取 (使用 httpx)
            target_url = url
            next_page_url = None
            
            if "example.com" not in url and "localhost" not in url:
                # 尝试真实抓取
                try:
                    # 反爬虫随机延迟
                    await asyncio.sleep(random.uniform(0.5, 2.0))
                    
                    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=get_random_headers()) as http_client:
                        resp = await http_client.get(target_url)
                        # Detect encoding if needed, httpx handles auto-decoding mostly
                        html_content = resp.text
                        status_code = resp.status_code
                        
                        # 尝试查找下一页
                        next_page_url = get_next_page_url(target_url, html_content)
                        
                        # 增加 AI 上下文限制 (2000 -> 20000)
                        raw_content = html_content[:20000] 
                except Exception as e:
                    raw_content = f"Error fetching {target_url}: {str(e)}"
                    status_code = 500
                    html_content = ""
            else:
                # 模拟数据生成
                await asyncio.sleep(0.5) 
                status_code = 200
                html_content = f"<html><body><p>Mock Content for {url}</p></body></html>"
                raw_content = json.dumps({
                    "title": f"Product {page_index}",
                    "price": 10.5 + page_index,
                    "description": f"This is a description for product {page_index}",
                    "category": "Electronics" if page_index % 2 == 0 else "Clothing",
                    "source_url": url,
                    "page": page_index
                })
                # 模拟分页逻辑：如果 url 有 'page'，则增加它
                next_page_url = get_next_page_url(url, html_content)
                if not next_page_url:
                     # 如果正则失败，回退到模拟启发式 (例如如果 url 没有 page 参数)
                     if "?" not in url:
                         next_page_url = f"{url}?page={page_index + 1}"
                     elif "page=" not in url:
                         next_page_url = f"{url}&page={page_index + 1}"

            # 步骤 2：保存到 CSV (带有元数据的初步保存)
            # 稍后我们将使用 AI 提取的数据更新此行
            csv_row = {
                "page_index": page_index,
                "url": target_url,
                "status": status_code,
            }
            
            # 步骤 3：AI 处理
            columns_str = ", ".join(columns)
            
            # 向 AI 提供元数据，以便在列中请求时可以使用它
            metadata_info = f"Page Index: {page_index}, URL: {target_url}, Status: {status_code}"
            
            prompt = f"""
            You are a data extraction expert. Your task is to extract structured data from the provided HTML/JSON content.
            
            Target Site: {target_url}
            Columns to extract: {columns_str}
            
            Guidelines:
            1. Look for the most prominent data matching the columns.
            2. For 'title' or 'name', look for <h1>, <h2>, <h3> or <a> tags with descriptive text.
            3. For 'price', look for currency symbols ($, £, ¥) or numeric values near 'price' keywords.
            4. If the page is a LISTING page (like a search result or category page), extract the details of the FIRST product/item you see.
            5. If a piece of information (like 'description' or 'category') is NOT present on this specific page, return null for that field.
            6. Use the Metadata for 'url' or 'page_index' if they are requested in the columns.
            
            Return ONLY a valid JSON object. Do not include markdown formatting.
            
            Metadata:
            {metadata_info}
            
            Raw Content (First 20k chars):
            {raw_content}
            
            Response format: {{"column1": "value1", "column2": "value2", ...}}
            """

            extracted_data = {}
            sql_result = ""
            
            try:
                if settings.VOLC_API_KEY and settings.VOLC_DEEPSEEK_MODEL_ID:
                    response = await client.chat.completions.create(
                        model=settings.VOLC_DEEPSEEK_MODEL_ID,
                        messages=[
                            {"role": "system", "content": "You are a precise data extractor that outputs only JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        stream=False,
                        response_format={ "type": "json_object" }
                    )
                    content = response.choices[0].message.content
                    extracted_data = json.loads(content)
                else:
                    await asyncio.sleep(0.5)
                    # 用于演示/测试的模拟提取数据
                    extracted_data = {col: f"Mock {col} {page_index}" for col in columns}
                    if "price" in extracted_data: extracted_data["price"] = 10.5 + page_index
                    if "url" in columns: extracted_data["url"] = target_url

                # 过滤并清理提取的数据
                valid_data = {}
                for col in columns:
                    val = extracted_data.get(col)
                    # 将 None/null 转换为字符串 'NULL' 用于 SQL，或保留为 None 用于 CSV
                    if val is None or val == "None" or val == "null":
                        valid_data[col] = None
                    else:
                        valid_data[col] = val

                # 从提取的数据构造 SQL
                cols = []
                vals = []
                for k, v in valid_data.items():
                    if v is not None:
                        cols.append(k)
                        # 为 SQL 转义单引号
                        escaped_val = str(v).replace("'", "''")
                        vals.append(f"'{escaped_val}'")
                
                if cols:
                    sql_result = f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({', '.join(vals)});"
                else:
                    sql_result = f"-- No data could be extracted for {target_url}"
                
                # 使用提取的数据更新 CSV 行 (缺失值使用 None)
                csv_row.update(valid_data)

            except Exception as e:
                print(f"AI extraction error: {e}")
                sql_result = f"-- Error extracting data for {target_url}: {str(e)}"

            # 最终确定 CSV (使用组合的锁保护写入)
            async with csv_lock:
                csv_file_path = CSV_DIR / f"{task_id}.csv"
                file_exists = csv_file_path.exists()
                
                # 确定所有字段名称 (元数据 + 用户列)
                fieldnames = ["page_index", "url", "status"] + columns
                
                await asyncio.get_running_loop().run_in_executor(
                    None, 
                    lambda: _append_csv(csv_file_path, csv_row, file_exists, fieldnames)
                )

            # 步骤 4：保存到 SQL
            if sql_result:
                async with sql_lock:
                    sql_file_path = SQL_DIR / f"{task_id}.sql"
                    await asyncio.get_running_loop().run_in_executor(
                        None,
                        lambda: _append_sql(sql_file_path, sql_result)
                    )

            # 更新进度
            await session_updater.increment()
            
            return next_page_url

        except Exception as e:
            print(f"Error processing page {page_index}: {e}")
            return None

def _append_csv(path, row, file_exists, fieldnames):
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def _append_sql(path, sql_content):
    with open(path, "a", encoding="utf-8") as f:
        f.write(sql_content + "\n\n")

class ProgressUpdater:
    def __init__(self, task_id, total):
        self.task_id = task_id
        self.total = total
        self.processed = 0
        self.lock = asyncio.Lock()
    
    async def increment(self):
        async with self.lock:
            self.processed += 1
            try:
                with Session(engine) as session:
                    task = session.get(CrawlerTask, self.task_id)
                    if task:
                        task.status = f"processing ({self.processed}/{self.total})"
                        session.add(task)
                        session.commit()
            except Exception as e:
                print(f"Failed to update progress: {e}")

async def generate_sql_from_spider(task_id: uuid.UUID, url: str, table_name: str, columns: list[str], max_pages: int = 1, concurrency: int = 5):
    """
    使用 DeepSeek API 从模拟爬虫数据生成 SQL 的后台任务。
    针对并发、文件存储和分页进行了优化。
    """
    # 初始化锁
    csv_lock = asyncio.Lock()
    sql_lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(concurrency)
    
    # 初始化进度更新器
    updater = ProgressUpdater(task_id, max_pages)

    # 初始化客户端
    client = AsyncOpenAI(
        api_key=settings.VOLC_API_KEY or "sk-placeholder", 
        base_url="https://ark.cn-beijing.volces.com/api/v3"
    )

    # 创建新会话以设置初始状态
    with Session(engine) as session:
        task = session.get(CrawlerTask, task_id)
        if not task:
            return
        task.status = f"processing (0/{max_pages})"
        session.add(task)
        session.commit()

    try:
        # 确定策略：
        # 如果我们能推断 URL（启发式），我们可以生成所有 URL 并并发运行。
        # 否则，我们必须顺序（或混合）运行以发现下一页。
        
        urls_to_crawl = []
        
        # 首先检查启发式
        first_next_url = get_next_page_url(url, "")
        
        if first_next_url and first_next_url != url:
             # 启发式有效！我们可以预生成 URL
             # 例如 url="...page=1", next="...page=2"
             # 我们假设标准递增
             # 我们可以生成最多 max_pages
             print("Heuristic URL generation active")
             base_url = url
             urls_to_crawl.append(base_url)
             
             # 尝试生成后续 URL
             current_sim_url = base_url
             for _ in range(max_pages - 1):
                 next_sim_url = get_next_page_url(current_sim_url, "")
                 if next_sim_url:
                     urls_to_crawl.append(next_sim_url)
                     current_sim_url = next_sim_url
                 else:
                     break
        else:
            # 启发式失败或不适用，我们仅从第一个 URL 开始
            # 并依赖 HTML 解析（这意味着我们无法完全预生成）
            # 但对于请求的“并发”，只有在我们有 URL 时才能并发运行。
            # 如果我们依赖第 N 页来查找第 N+1 页，则发现阶段的并发实际上为 1。
            # 但是，如果我们在模拟模式下或拥有列表，我们可以并发运行。
            urls_to_crawl.append(url)

        # 主循环
        processed_count = 0
        current_batch_urls = urls_to_crawl
        
        # 如果我们动态发现 URL，可能需要基于队列的方法
        # 但为了简单起见，让我们处理初始批次 (启发式)
        # 或者如果启发式失败进入动态循环。
        
        if len(current_batch_urls) >= max_pages or len(current_batch_urls) > 1:
             # 情况 1：我们有足够的 URL（启发式成功），并发运行
             tasks = []
             for i, target_url in enumerate(current_batch_urls[:max_pages]):
                 tasks.append(
                     process_page(
                         page_index=i + 1,
                         url=target_url,
                         table_name=table_name,
                         columns=columns,
                         semaphore=semaphore,
                         csv_lock=csv_lock,
                         sql_lock=sql_lock,
                         client=client,
                         task_id=task_id,
                         session_updater=updater
                     )
                 )
             await asyncio.gather(*tasks)
        else:
             # 情况 2：发现模式（串行或有限并发）
             # 我们抓取第 1 页，看是否得到第 2 页，依此类推。
             current_url = url
             for i in range(max_pages):
                 next_url = await process_page(
                     page_index=i + 1,
                     url=current_url,
                     table_name=table_name,
                     columns=columns,
                     semaphore=semaphore, # 信号量在这里用处不大，因为我们是串行的
                     csv_lock=csv_lock,
                     sql_lock=sql_lock,
                     client=client,
                     task_id=task_id,
                     session_updater=updater
                 )
                 
                 if not next_url:
                     print("No next page found, stopping.")
                     break
                 current_url = next_url

        # 最终状态更新
        with Session(engine) as session:
            task = session.get(CrawlerTask, task_id)
            if task:
                sql_file_path = SQL_DIR / f"{task_id}.sql"
                if sql_file_path.exists():
                    with open(sql_file_path, "r", encoding="utf-8") as f:
                        task.result_sql_content = f.read()
                
                task.status = "completed"
                session.add(task)
                session.commit()

    except Exception as e:
        with Session(engine) as session:
            task = session.get(CrawlerTask, task_id)
            if task:
                task.status = "failed"
                task.result_sql_content = f"Error: {str(e)}"
                session.add(task)
                session.commit()
