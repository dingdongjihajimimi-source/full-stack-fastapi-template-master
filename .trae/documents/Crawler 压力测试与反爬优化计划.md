# Crawler 压力测试与反爬优化计划

## 1. 反爬策略优化 (backend/app/worker\_tasks/crawler.py)

为了更好地“躲过”反爬机制，将实施以下优化：

* **随机 User-Agent**: 使用 `fake-useragent` 库（或内置一个常见 UA 列表）为每个请求随机生成 User-Agent。

* **随机延迟**: 在请求之间引入 `random.uniform(0.5, 2.0)` 的随机等待时间，模拟人类行为。

* **请求头优化**: 完善 `httpx` 的 headers，加入 `Accept-Language`, `Referer` 等常见字段。

* 把 `Accept-Language` 设成 `zh-CN,zh;q=0.9，或者其他本地语言`

## 2. 压力测试脚本 (stress\_test\_crawler.py)

将编写一个独立的 Python 脚本，用于对 Crawler 接口进行高并发压力测试。

* **测试目标**: 验证 `concurrency` 参数是否真实生效，以及系统在高负载下的稳定性。

* **测试逻辑**:

  1. **并发发起任务**: 使用 `asyncio` 同时发起多个 `POST /crawl/start` 请求（例如 10 个并发任务）。
  2. **每个任务配置**: 设置 `max_pages=5`, `concurrency=5`。
  3. **监控**: 轮询每个任务的状态接口，记录状态变化和耗时。
  4. **验证**:

     * 检查总耗时是否符合预期（并发应该比串行快）。

     * 检查所有任务是否最终都标记为 `completed`。

     * 检查 `generated_data` 目录下是否生成了相应数量的文件。

## 3. 执行步骤

1. **修改 Crawler 代码**: 注入反爬逻辑（User-Agent, Headers, Delay）。
2. **编写测试脚本**: 创建 `backend/stress_test_crawler.py`。
3. **运行测试**: 在 `backend` 容器内或本地环境运行测试脚本，输出报告。

