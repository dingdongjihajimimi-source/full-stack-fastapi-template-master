# 前端 UI 优化计划：增强下载区域体验

用户反馈当前下载页面（区域）不够醒目，建议优化。我计划对 `frontend/src/routes/_layout/crawler.tsx` 进行界面重构。

## 1. 界面布局重构

### 1.1 引入 Card 组件
项目已包含标准的 `shadcn/ui` Card 组件 (`components/ui/card.tsx`)，将使用它来替换当前硬编码的 `div` 样式，使代码更整洁且风格更统一。

### 1.2 状态与结果分离
目前状态条和下载按钮挤在一起。我将把它们拆分为两个独立的状态视图：
*   **处理中 (Processing)**：展示大尺寸的进度条和动态状态文本，告知用户正在生成中。
*   **完成 (Completed)**：展示一个全新的**结果面板**。

## 2. 结果面板 (Result Panel) 设计

当任务完成后，右侧区域将变为一个醒目的“生成成功”面板，包含以下内容：

### 2.1 顶部：成功提示
*   显示绿色对勾图标 ✅ 和 "Generation Complete" 标题。
*   显示生成耗时（可选，如果数据支持）或简单的成功祝贺语。

### 2.2 核心：大尺寸下载区
将原来的两个小按钮改为两个**大卡片块 (Block)**，并排排列（Grid Layout）：

*   **📄 CSV 数据卡片**
    *   图标：`FileSpreadsheet` (Lucide React)
    *   标题：Raw Data (CSV)
    *   描述：包含爬取的原始字段数据。
    *   按钮：大尺寸绿色按钮 "Download CSV"

*   **🗄️ SQL 脚本卡片**
    *   图标：`Database` (Lucide React)
    *   标题：SQL Script
    *   描述：标准 `INSERT INTO` 建表语句。
    *   按钮：大尺寸蓝色按钮 "Download SQL"

### 2.3 底部：SQL 预览
*   保留代码预览区域，但将其放在下载卡片下方，作为次要信息展示。
*   增加 "Copy" 复制按钮。

## 3. 具体代码变更

*   **文件**：`frontend/src/routes/_layout/crawler.tsx`
*   **导入**：引入 `Card, CardHeader, CardTitle, CardContent` 等组件。
*   **逻辑**：
    *   根据 `taskStatus.status` 条件渲染不同的 Card。
    *   使用 `grid-cols-2` 布局下载区域。

## 4. 预期效果
右侧不再是一个单调的黑色方框，而是一个交互性强、重点突出的结果仪表盘，用户一眼就能看到下载入口，且点击操作更方便。
