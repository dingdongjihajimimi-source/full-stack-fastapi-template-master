import time
import requests
import json
import os
import sys

# Configuration
API_URL = "http://localhost:8000/api/v1"
# Assuming authentication is required, we need a superuser token. 
# But the crawler endpoint uses `SessionDep` which usually implies `deps.get_current_active_superuser` or similar IF it was decorated with dependencies.
# Looking at crawler.py, `start_crawl` only takes `SessionDep` and `CrawlRequest`.
# Wait, `SessionDep` is just database session. 
# However, `backend/app/api/main.py` might apply global dependencies or `crawler` router might be included with dependencies.
# Let's assume for now we need a token, as most endpoints do.
EMAIL = "admin@example.com"
PASSWORD = "changethis"

def get_access_token():
    url = f"{API_URL}/login/access-token"
    data = {
        "username": EMAIL,
        "password": PASSWORD
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"Failed to get access token: {e}")
        # If login fails, maybe we can try without token if the endpoint is public (unlikely for this template)
        return None

def test_crawler_flow():
    print("--- 开始测试自动生成 SQL 流程 ---")
    
    token = get_access_token()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        print("✅ 获取 Access Token 成功")
    else:
        print("⚠️ 未能获取 Token，尝试匿名访问...")

    # 1. Start Crawl Task
    start_url = f"{API_URL}/crawl/start"
    payload = {
        "url": "https://www.example.com/products",
        "table_name": "products_test_table",
        "columns": ["title", "price", "description", "category", "source_url"]
    }
    
    print(f"\n1. 发送任务请求: {payload['url']}")
    try:
        response = requests.post(start_url, json=payload, headers=headers)
        response.raise_for_status()
        task_id = response.json() # Direct UUID response based on response_model=uuid.UUID
        # If response is a string "xxxx-xxx", it's good.
        # If it's a dict {"id": "..."} we need to parse.
        # Based on crawler.py: `return crawler_task.id` and `response_model=uuid.UUID`, it should be a string.
        if isinstance(task_id, dict) and "id" in task_id:
            task_id = task_id["id"]
            
        print(f"✅ 任务创建成功! ID: {task_id}")
    except Exception as e:
        print(f"❌ 任务创建失败: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return

    # 2. Poll Status
    status_url = f"{API_URL}/crawl/{task_id}"
    print("\n2. 开始轮询任务状态...")
    
    max_retries = 120 # 120 seconds timeout
    for i in range(max_retries):
        try:
            response = requests.get(status_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            status = data.get("status")
            
            print(f"   [{i+1}s] 状态: {status}")
            
            if status == "completed":
                print("\n✅ 任务完成！")
                print("-" * 40)
                print("生成的 SQL 内容预览 (前 500 字符):")
                sql_content = data.get("result_sql_content", "")
                print(sql_content[:500] + "..." if len(sql_content) > 500 else sql_content)
                print("-" * 40)
                
                # Check for SQL keywords
                if "INSERT INTO" in sql_content:
                    print("✅ SQL 格式验证通过 (包含 INSERT INTO)")
                else:
                    print("⚠️ SQL 格式可能有误")
                break
            
            elif status == "failed":
                print("\n❌ 任务失败！")
                print(f"错误信息: {data.get('result_sql_content')}")
                break
            
            time.sleep(1)
        except Exception as e:
            print(f"轮询出错: {e}")
            time.sleep(1)
    else:
        print("\n❌ 等待超时 (120秒)")

if __name__ == "__main__":
    test_crawler_flow()
