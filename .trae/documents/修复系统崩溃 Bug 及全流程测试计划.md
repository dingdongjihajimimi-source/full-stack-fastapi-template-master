## 故障排查与修复计划

### 1. 修复前端运行时崩溃
- **防御性访问**：在 [crawler.tsx](file:///home/pikaqiu/PythonProject/full-stack-fastapi-template-master/frontend/src/routes/_layout/crawler.tsx) 中对 `strategyReview` 及其属性（如 `target_keys`, `sql_schema`）增加可选链（Optional Chaining）或默认值处理，防止 `undefined.join()` 等操作导致页面崩溃。
- **解析优化**：增强 `pipeline_state` JSON 解析的健壮性。

### 2. 后端稳定性检查
- **日志审计**：检查 `docker compose logs backend` 确认是否存在未处理的 Python 异常。
- **数据库校验**：验证 `crawler_task` 表结构是否与 [crawler_task.py](file:///home/pikaqiu/PythonProject/full-stack-fastapi-template-master/backend/app/models/crawler_task.py) 模型一致。

### 3. 全流程功能验证
- 验证“手动模式”与“自主模式”的切换逻辑。
- 测试“策略审查”弹窗在不同网络延迟下的表现。
- 确保爬取结果（CSV/SQL）的生成与下载链路通畅。

## 待办事项 (Todo)
1. 修复 [crawler.tsx](file:///home/pikaqiu/PythonProject/full-stack-fastapi-template-master/frontend/src/routes/_layout/crawler.tsx) 中的空值访问 Bug (高优先级)
2. 检查后端服务健康状态与数据库一致性
3. 重新执行 Docker 构建并部署验证
