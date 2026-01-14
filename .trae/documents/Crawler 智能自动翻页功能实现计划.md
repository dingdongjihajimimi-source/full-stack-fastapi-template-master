# Crawler 智能自动翻页功能实现计划

本计划旨在为爬虫模块增加自动发现下一页 URL 的能力，从而实现连续爬取。

## 1. 依赖管理
*   **动作**: 检查 `pyproject.toml`，发现缺少 `beautifulsoup4`。
*   **计划**: 将 `beautifulsoup4` 添加到 `backend/pyproject.toml` 的 `dependencies` 中。

## 2. 核心逻辑实现 (backend/app/worker\_tasks/crawler.py)

### 2.1 新增辅助函数 `get_next_page_url`
*   **输入**: `current_url` (str), `html_content` (str)
*   **输出**: `next_url` (str | None)
*   **逻辑**:
    1.  **策略 A - URL 模式推测**:
        *   使用正则匹配 URL 中的页码参数（如 `page=1`, `/page/1`）。
        *   如果匹配成功，将页码 +1 并构造新 URL。
    2.  **策略 B - HTML 解析 (BeautifulSoup)**:
        *   初始化 `BeautifulSoup(html_content, 'html.parser')`。
        *   查找所有 `<a>` 标签。
        *   遍历检查 `a.text` 是否包含关键词（"Next", "下一页", ">", "next", "More"）。
        *   提取 `href` 属性，并使用 `urllib.parse.urljoin` 转换为绝对路径。
    3.  **返回**: 优先返回策略 A 的结果（通常更准确），若失败则返回策略 B 的结果。

### 2.2 改造主循环 `generate_sql_from_spider`
*   **当前逻辑**: 固定循环 `range(max_pages)`，每次 `page_index` 自增。
*   **新逻辑**: 改为 `while` 循环模式。
    *   维护一个 `urls_to_visit` 队列（初始为 `[start_url]`）。
    *   维护 `processed_count` 计数器。
    *   **循环条件**: `processed_count < max_pages` 且 `urls_to_visit` 不为空。
    *   **并发控制**: 依然使用 `semaphore` 控制并发，但由于翻页通常依赖上一页的结果（或者是线性的），**严格的自动翻页通常是串行或有限并发的**。
        *   *修正*: 用户之前要求了并发 `concurrency`。对于翻页场景，如果通过 URL 推测出后续 5 页（如 page=2,3,4,5,6），则可以并发。但如果是基于 HTML 解析，必须爬完第 1 页才知道第 2 页。
        *   *折中方案*: 
            1.  **优先尝试 URL 推测**: 如果能推测出规律，一次性生成 `min(concurrency, remaining_pages)` 个后续 URL 并发爬取。
            2.  **HTML 解析兜底**: 如果推测失败，则退化为串行（爬取 -> 解析下一页 -> 爬取）。
            3.  **简化实现**: 为保持代码清晰，我们将采用**“预判模式”**。在第一页爬取时，尝试推测 URL 模式。如果成功，直接生成后续所有 URL 放入任务列表。如果失败，则仅依赖 HTML 解析（此时并发度受限于发现新 URL 的速度，可能退化为近似串行）。

    *   **更稳健的实现**: 
        *   保持当前的 `process_page` 函数基本不变，但让它**返回**发现的 `next_url`。
        *   主函数维护一个 `Task` 列表。初始放入 `page 1`。
        *   当一个任务完成时，检查其返回的 `next_url`。如果是新 URL 且未访问过，且未达到 `max_pages`，则创建新任务加入队列。
        *   由于 `asyncio.gather` 等待所有任务完成，这不适合动态添加任务。我们将改用 `asyncio.create_task` 配合 `while` 循环检测任务状态。

    *   **本次任务简化路径**: 鉴于用户主要需要“智能翻页”，且之前的代码结构是 `asyncio.gather`。
        *   **修改 `process_page`**: 增加 HTML 解析逻辑，返回 `next_url`。
        *   **修改主流程**: 
            *   如果是 **Mock 模式** (example.com) 或 **URL 推测成功**: 直接生成所有 URL，并发执行（保持高效率）。
            *   如果是 **真实抓取且无法推测**: 只能串行（上一页抓完 -> 解析出下一页 -> 抓下一页）。
            *   **逻辑合并**: 
                1. 尝试 URL 推测。如果成功，生成列表 `[url_p1, url_p2, ...]`，直接并发。
                2. 如果推测失败，进入 `while` 循环：
                   `current_url = start_url`
                   `for i in range(max_pages)`:
                       `next_url = await process_page(...)`
                       `if not next_url: break`
                       `current_url = next_url`

## 3. 验证计划
*   **安装依赖**: 运行 `uv sync` 或重新构建容器。
*   **测试**: 使用一个真实的分页 URL（或模拟的支持翻页的 URL）进行测试。

