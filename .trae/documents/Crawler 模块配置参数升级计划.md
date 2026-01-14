# Crawler 模块参数升级计划

本计划旨在为爬虫任务增加 `max_pages`（最大页数）和 `concurrency`（并发数）两个配置参数，从而提供更灵活的控制能力。

## 1. 后端修改 (Backend)

### 1.1 修改 API 请求模型
*   **文件**: `backend/app/api/routes/crawler.py`
*   **动作**: 更新 `CrawlRequest` 类，新增字段：
    *   `max_pages`: `int`，默认值 1，大于 0。
    *   `concurrency`: `int`，默认值 5，建议范围 1-20。
*   **动作**: 更新 `start_crawl` 函数，将新参数透传给后台任务 `generate_sql_from_spider`。

### 1.2 升级后台任务逻辑
*   **文件**: `backend/app/worker_tasks/crawler.py`
*   **动作**: 更新 `generate_sql_from_spider` 函数签名以接收新参数。
*   **逻辑实现**:
    *   **数据量控制**: 使用 `max_pages` 控制模拟数据的生成量。假设每页 20 条数据，总生成 `max_pages * 20` 条数据。
    *   **并发控制**: 使用 `asyncio.Semaphore(concurrency)` 限制同时进行的 DeepSeek API 调用数量，防止触发限流或过载。

## 2. 前端 Client 更新
*   **动作**: 运行 `openapi-typescript-codegen` 重新生成前端 SDK，确保类型定义包含新字段。

## 3. 前端界面修改 (Frontend)

### 3.1 增加配置输入
*   **文件**: `frontend/src/routes/_layout/crawler.tsx`
*   **动作**: 在 Configuration 区域新增两个 Input 组件：
    *   **Max Pages**: 数字输入框，默认 1。
    *   **Concurrency**: 数字输入框，默认 5。
*   **动作**: 更新 `handleStartCrawl` 函数，将表单中的新参数传递给 API。

## 4. 验证计划
*   **构建**: 重新构建前后端 Docker 容器。
*   **测试**: 启动一个任务，设置 `Max Pages = 5` (生成 100 条数据) 和 `Concurrency = 2`。
*   **观察**: 检查后端日志确认并发控制是否生效（是否分批处理），并检查生成的 CSV/SQL 文件数据量是否符合预期。
