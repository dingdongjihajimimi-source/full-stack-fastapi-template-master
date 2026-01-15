# 数据库表结构文档 (Database Schema Documentation)

本文档概述了 Industrial Data Flow 项目的数据库表结构。

## 数据表概览

| 表名 (Table Name) | 描述 (Description) |
| :--- | :--- |
| `user` | 存储用户账户信息（认证、个人资料）。 |
| `item` | 存储用户拥有的项目（示例资源）。 |
| `chatmessage` | 存储会话中的单条聊天消息。 |
| `chatsession` | 存储聊天会话的元数据。 |
| `crawler_task` | 追踪爬虫任务的状态和结果。 |
| `crawl_index` | 已爬取内容的索引（防止重复，包含 URL、文件路径、哈希值）。 |
| `industrial_batch` | 追踪工业数据处理的批次信息。 |
| `alembic_version` | 追踪数据库迁移版本。 |

---

## 表结构详情

### `user` (用户表)
存储用户的认证信息和个人资料数据。

| 字段名 | 类型 | 允许为空 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | 否 | 主键 |
| `email` | `varchar(255)` | 否 | 唯一邮箱地址 |
| `hashed_password` | `varchar` | 否 | Bcrypt 哈希加密后的密码 |
| `full_name` | `varchar(255)` | 是 | 用户全名 |
| `is_active` | `boolean` | 否 | 账户是否激活 |
| `is_superuser` | `boolean` | 否 | 是否为超级用户 |

### `item` (项目表)
关联到用户的示例资源表。

| 字段名 | 类型 | 允许为空 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | 否 | 主键 |
| `title` | `varchar(255)` | 否 | 项目标题 |
| `description` | `varchar(255)` | 是 | 项目描述 |
| `owner_id` | `uuid` | 否 | 外键 -> `user.id` |

### `chatmessage` (聊天消息表)
聊天会话中的单条消息记录。

| 字段名 | 类型 | 允许为空 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | 否 | 主键 |
| `session_id` | `uuid` | 否 | 外键 -> `chatsession.id` |
| `owner_id` | `uuid` | 否 | 外键 -> `user.id` |
| `role` | `varchar(50)` | 否 | 角色（'user' 用户 或 'assistant' 助手） |
| `content` | `varchar` | 否 | 消息内容 |
| `created_at` | `timestamp` | 否 | 创建时间 |

### `chatsession` (聊天会话表)
用于将聊天消息分组的会话记录。

| 字段名 | 类型 | 允许为空 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | 否 | 主键 |
| `user_id` | `uuid` | 否 | 外键 -> `user.id` |
| `title` | `varchar(255)` | 否 | 会话标题 |
| `created_at` | `timestamp` | 否 | 创建时间 |
| `updated_at` | `timestamp` | 否 | 最后更新时间 |

### `crawler_task` (爬虫任务表)
管理异步爬虫作业。

| 字段名 | 类型 | 允许为空 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | 否 | 主键 |
| `status` | `varchar` | 否 | 任务状态（例如：'pending' 等待中, 'completed' 已完成） |
| `result_sql_content` | `varchar` | 是 | 爬取结果生成的 SQL 内容 |
| `pipeline_state` | `varchar` | 是 | 管道当前状态 |
| `current_phase` | `varchar` | 是 | 当前执行阶段 |
| `created_at` | `timestamp` | 否 | 创建时间 |

### `crawl_index` (爬取索引表)
所有已爬取文件和 URL 的索引，用于去重。

| 字段名 | 类型 | 允许为空 | 描述 |
| :--- | :--- | :--- | :--- |
| `url_hash` | `varchar(64)` | 否 | 主键 (URL 的 SHA 哈希值) |
| `original_url` | `varchar(2048)` | 否 | 原始 URL |
| `file_path` | `varchar(512)` | 否 | 存储的内容文件路径 |
| `content_md5` | `varchar(64)` | 否 | 内容的 MD5 哈希值 |
| `content_type` | `varchar(128)` | 是 | MIME 类型 |
| `size_bytes` | `integer` | 是 | 文件大小（字节） |
| `created_at` | `timestamp` | 否 | 创建时间 |
| `updated_at` | `timestamp` | 否 | 最后更新时间 |

### `industrial_batch` (工业批次表)
追踪工业数据的批处理信息。

| 字段名 | 类型 | 允许为空 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | 否 | 主键 |
| `url` | `varchar` | 否 | 批次的源 URL |
| `item_count` | `integer` | 否 | 批次内的项目数量 |
| `status` | `varchar` | 否 | 批次状态 |
| `storage_path` | `varchar` | 是 | 批次数据存储路径 |
| `created_at` | `timestamp` | 否 | 创建时间 |
