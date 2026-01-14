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

# Common User-Agents list for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]

def get_random_headers():
    """Generate random headers for anti-crawling evasion."""
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
    Determine the next page URL using regex heuristics or HTML parsing.
    """
    # Strategy A: Regex Heuristics (e.g. page=1, /page/1)
    # Match patterns like ?page=123 or /page/123
    # Group 1: prefix, Group 2: page number, Group 3: suffix
    page_patterns = [
        r"([?&]page=)(\d+)",
        r"(/page/)(\d+)"
    ]
    
    for pattern in page_patterns:
        match = re.search(pattern, current_url)
        if match:
            current_page_num = int(match.group(2))
            next_page_num = current_page_num + 1
            # Replace only the first occurrence
            next_url = current_url[:match.start(2)] + str(next_page_num) + current_url[match.end(2):]
            return next_url

    # Strategy B: HTML Parsing (BeautifulSoup)
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Look for <a> tags with text like "Next", "下一页", ">"
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
    Process a single page/item concurrently.
    Pipeline: Crawl -> Save CSV -> AI -> Save SQL
    Returns: Next Page URL (if found) or None
    """
    async with semaphore:
        try:
            # Step 1: Crawl (Using httpx)
            target_url = url
            next_page_url = None
            
            if "example.com" not in url and "localhost" not in url:
                # Try real fetch
                try:
                    # Random delay for anti-crawling
                    await asyncio.sleep(random.uniform(0.5, 2.0))
                    
                    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=get_random_headers()) as http_client:
                        resp = await http_client.get(target_url)
                        # Detect encoding if needed, httpx handles auto-decoding mostly
                        html_content = resp.text
                        status_code = resp.status_code
                        
                        # Try to find next page
                        next_page_url = get_next_page_url(target_url, html_content)
                        
                        # Increase limit for AI context (2000 -> 20000)
                        raw_content = html_content[:20000] 
                except Exception as e:
                    raw_content = f"Error fetching {target_url}: {str(e)}"
                    status_code = 500
                    html_content = ""
            else:
                # Mock Data Generation
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
                # Mock pagination logic: if url has 'page', increment it
                next_page_url = get_next_page_url(url, html_content)
                if not next_page_url:
                     # Fallback mock heuristic if regex failed (e.g. if url has no page param)
                     if "?" not in url:
                         next_page_url = f"{url}?page={page_index + 1}"
                     elif "page=" not in url:
                         next_page_url = f"{url}&page={page_index + 1}"

            # Step 2: Save to CSV (Preliminary with metadata)
            # We will update this row later with AI extracted data
            csv_row = {
                "page_index": page_index,
                "url": target_url,
                "status": status_code,
            }
            
            # Step 3: AI Processing
            columns_str = ", ".join(columns)
            
            # Provide metadata to AI so it can use it if requested in columns
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
                    # Mock extracted data for demo/testing
                    extracted_data = {col: f"Mock {col} {page_index}" for col in columns}
                    if "price" in extracted_data: extracted_data["price"] = 10.5 + page_index
                    if "url" in columns: extracted_data["url"] = target_url

                # Filter and clean extracted data
                valid_data = {}
                for col in columns:
                    val = extracted_data.get(col)
                    # Convert None/null to string 'NULL' for SQL or keep as None for CSV
                    if val is None or val == "None" or val == "null":
                        valid_data[col] = None
                    else:
                        valid_data[col] = val

                # Construct SQL from extracted data
                cols = []
                vals = []
                for k, v in valid_data.items():
                    if v is not None:
                        cols.append(k)
                        # Escape single quotes for SQL
                        escaped_val = str(v).replace("'", "''")
                        vals.append(f"'{escaped_val}'")
                
                if cols:
                    sql_result = f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({', '.join(vals)});"
                else:
                    sql_result = f"-- No data could be extracted for {target_url}"
                
                # Update CSV row with extracted data (using None for missing values)
                csv_row.update(valid_data)

            except Exception as e:
                print(f"AI extraction error: {e}")
                sql_result = f"-- Error extracting data for {target_url}: {str(e)}"

            # Finalize CSV (using a combined lock-protected write)
            async with csv_lock:
                csv_file_path = CSV_DIR / f"{task_id}.csv"
                file_exists = csv_file_path.exists()
                
                # Determine all fieldnames (metadata + user columns)
                fieldnames = ["page_index", "url", "status"] + columns
                
                await asyncio.get_running_loop().run_in_executor(
                    None, 
                    lambda: _append_csv(csv_file_path, csv_row, file_exists, fieldnames)
                )

            # Step 4: Save to SQL
            if sql_result:
                async with sql_lock:
                    sql_file_path = SQL_DIR / f"{task_id}.sql"
                    await asyncio.get_running_loop().run_in_executor(
                        None,
                        lambda: _append_sql(sql_file_path, sql_result)
                    )

            # Update Progress
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
    Background task to generate SQL from mock spider data using DeepSeek API.
    Optimized for concurrency, file storage, and pagination.
    """
    # Initialize locks
    csv_lock = asyncio.Lock()
    sql_lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(concurrency)
    
    # Initialize Progress Updater
    updater = ProgressUpdater(task_id, max_pages)

    # Initialize Client
    client = AsyncOpenAI(
        api_key=settings.VOLC_API_KEY or "sk-placeholder", 
        base_url="https://ark.cn-beijing.volces.com/api/v3"
    )

    # Create a new session to set initial status
    with Session(engine) as session:
        task = session.get(CrawlerTask, task_id)
        if not task:
            return
        task.status = f"processing (0/{max_pages})"
        session.add(task)
        session.commit()

    try:
        # Determine strategy:
        # If we can infer URLs (heuristic), we can generate them all and run concurrently.
        # If not, we must run sequentially (or hybrid) to discover next pages.
        
        urls_to_crawl = []
        
        # Check heuristic first
        first_next_url = get_next_page_url(url, "")
        
        if first_next_url and first_next_url != url:
             # Heuristic worked! We can pre-generate URLs
             # E.g. url="...page=1", next="...page=2"
             # We assume standard incrementing
             # We can generate up to max_pages
             print("Heuristic URL generation active")
             base_url = url
             urls_to_crawl.append(base_url)
             
             # Try to generate subsequent URLs
             current_sim_url = base_url
             for _ in range(max_pages - 1):
                 next_sim_url = get_next_page_url(current_sim_url, "")
                 if next_sim_url:
                     urls_to_crawl.append(next_sim_url)
                     current_sim_url = next_sim_url
                 else:
                     break
        else:
            # Heuristic failed or not applicable, we start with just the first URL
            # and rely on HTML parsing (which means we can't fully pre-generate)
            # But for the requested "concurrency", we can only run concurrent if we have URLs.
            # If we depend on page N to find page N+1, concurrency is effectively 1 for discovery.
            # However, if we are in Mock mode or have a list, we can run concurrent.
            urls_to_crawl.append(url)

        # Main Loop
        processed_count = 0
        current_batch_urls = urls_to_crawl
        
        # We might need a queue-based approach if we discover URLs dynamically
        # But for simplicity, let's process the initial batch (heuristic) 
        # OR enter a dynamic loop if heuristic failed.
        
        if len(current_batch_urls) >= max_pages or len(current_batch_urls) > 1:
             # Case 1: We have enough URLs (Heuristic success), run concurrently
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
             # Case 2: Discovery Mode (Serial or Limited Concurrency)
             # We fetch page 1, see if we get page 2, etc.
             current_url = url
             for i in range(max_pages):
                 next_url = await process_page(
                     page_index=i + 1,
                     url=current_url,
                     table_name=table_name,
                     columns=columns,
                     semaphore=semaphore, # Semaphore less useful here as we are serial
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

        # Final Status Update
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
