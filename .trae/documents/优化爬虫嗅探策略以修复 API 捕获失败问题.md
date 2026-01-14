## 故障分析与解决方案

您遇到的“流水线执行失败”问题，核心原因是**后端爬虫的嗅探策略过于严格**，导致在某些目标网站上无法捕获到 API 请求。

### 问题根源
代码 `backend/app/sniffer_pipeline/scout.py` 中的过滤器只允许：
1.  `content-type` 必须包含 `application/json`
2.  `resource-type` 必须是 `xhr` 或 `fetch`

如果目标网站是**服务端渲染 (SSR)**，或者 API 返回的 `content-type` 不规范（例如 `text/plain`），或者数据通过 HTML 内联脚本加载，当前的嗅探器就会“两眼一抹黑”，报告找不到 API。

### 修复计划

我将优化后端的嗅探逻辑，使其更加健壮：

1.  **放宽 Content-Type 过滤**：
    *   允许 `application/json`, `application/vnd.api+json`, `text/json`, `text/javascript`, 甚至包含 `{` 开头的 `text/plain`。
2.  **增加数据源**：
    *   除了 XHR/Fetch，尝试捕获 HTML 中的内联 JSON 数据（如 Next.js 的 `__NEXT_DATA__`）。
3.  **前端验证**：
    *   提供一个真实的测试 URL（如 `https://dummyjson.com/products`），确保系统在正常情况下能跑通。

### 待办事项 (Todo)

1.  [后端] 修改 `backend/app/sniffer_pipeline/scout.py`，放宽响应过滤条件。
2.  [后端] 重启后端服务以应用更改。
3.  [前端] 建议您使用 `https://dummyjson.com/products` 作为目标 URL 进行测试（这是一个真实的 JSON API 示例站）。

请确认此计划，我将立即开始修改代码。
