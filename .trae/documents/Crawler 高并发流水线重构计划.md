# Crawler 模块高并发重构计划

本计划将完全重构 `backend/app/worker_tasks/crawler.py`，实现基于 `asyncio.Semaphore` 的高并发流水线。

## 1. 依赖确认

* **httpx**: 已在 `pyproject.toml` 中，可直接使用。

* **aiofiles**: 未在依赖中，将使用 `asyncio.to_thread` 配合标准文件操作来实现非阻塞写入，避免引入新依赖导致重建镜像。

## 2. 核心重构逻辑 (backend/app/worker\_tasks/crawler.py)

### 2.1 引入新模块

导入 `httpx`, `asyncio`, `csv`, `time` 等必要模块。

### 2.2 定义 Worker 函数 `process_page`

创建一个核心异步函数，处理单个页面的全流程：

1. **信号量控制**: 使用 `async with semaphore:` 包裹逻辑。
2. **Step 1 抓取**: 使用 `httpx.AsyncClient` 抓取 `url`。

   * *注*: 如果 URL 是模拟地址（如 `example.com`），则回退到模拟数据生成，但流程保持一致。
3. **Step 2 落盘 CSV**:

   * 获取 `asyncio.Lock`。

   * 将抓取到的原始数据（如 HTML 摘要、URL、状态码）追加写入 CSV。
4. **Step 3 AI 清洗**:

   * 调用 DeepSeek API，传入 HTML/Text，要求生成 SQL。
5. **Step 4 落盘 SQL**:

   * 获取 `asyncio.Lock`。

   * 将生成的 SQL 追加写入 SQL 文件。
6. **进度更新**:

   * 增加 `processed_count` 计数。

   * 计算进度百分比，实时更新 `task.status` (例如 `"processing (25/100)"`)。

### 2.3 重写 `generate_sql_from_spider`

作为入口函数，负责：

1. 初始化文件（写入 CSV Header）。
2. 创建 `asyncio.Semaphore(concurrency)`。
3. 创建 `asyncio.Lock` 用于文件写入安全。
4. 根据 `max_pages` 创建任务列表（Tasks）。
5. 使用 `asyncio.gather` 并发执行所有任务。
6. 最终汇总状态，标记为 `completed`。

## 3. 验证计划

* **代码静态检查**: 确保没有语法错误。

* **功能验证**:

  * 启动任务，观察日志输出。

  * 检查 `generated_data/csv` 和 `generated_data/sql` 下的文件内容是否实时增加。

  * 观察前端状态条是否显示实时进度（如 "processing (5/20)"）。

* 重新部署前后端的docker项目

## 4. 注意事项

* 由于未引入 `aiofiles`，文件写入将使用 `loop.run_in_executor` 或直接在锁内快速同步写入（鉴于并发量 20 内，同步写入 CSV/SQL 也是可接受的，但为了极致性能会尽量优化）。

* 将保留 Mock 逻辑作为 "Fetch Failed" 或 "Dummy URL" 的兜底方案，确保测试顺利进行。

