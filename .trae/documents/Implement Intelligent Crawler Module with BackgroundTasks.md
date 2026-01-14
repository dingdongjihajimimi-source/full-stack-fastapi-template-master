I have analyzed the project structure and identified that **Celery is not currently installed or configured** (no `celery` in dependencies, no worker service in `docker-compose.yml`).

To adhere to the "incremental development" and "reuse existing" principles without introducing significant infrastructure complexity (like adding Redis and a new Worker container), I will use **FastAPI's native `BackgroundTasks`**. This achieves the same goal of asynchronous processing and state management via the database, fitting perfectly into the existing architecture.

### 1. Configuration
- **File**: `.env`
  - Add `DEEPSEEK_API_KEY=sk-...` (placeholder).
- **File**: `backend/app/core/config.py`
  - Add `DEEPSEEK_API_KEY: str | None = None` to the `Settings` class.

### 2. Database Model (Refactoring)
To support the request for `app/models/crawler_task.py` while preserving existing models:
- **Action**: Convert `backend/app/models.py` (file) into a package `backend/app/models/` (directory).
  - Move existing `models.py` content to `backend/app/models/__init__.py`.
- **New File**: `backend/app/models/crawler_task.py`
  - Define `CrawlerTask` with fields: `id` (UUID), `status` (str), `result_sql_content` (str), `created_at` (datetime).
- **Update**: `backend/app/models/__init__.py`
  - Import `CrawlerTask` to expose it to the application.
- **Migration**: Run Alembic commands to update the database schema.

### 3. Worker Logic (Background Task)
- **New Directory**: `backend/app/worker_tasks/`
- **New File**: `backend/app/worker_tasks/crawler.py`
  - Implement `async def generate_sql_from_spider(task_id: UUID)`:
    - Create a fresh DB session.
    - Mock 50+ items of data.
    - Call DeepSeek API (using `openai` client compatibility) to generate SQL.
    - Update `CrawlerTask` status and save the generated SQL.

### 4. API Endpoints
- **New File**: `backend/app/api/routes/crawler.py`
  - `POST /start`: Creates a `CrawlerTask` (pending), triggers the background task, and returns `task_id`.
  - `GET /{task_id}`: Returns the task status and generated SQL.
- **Update**: `backend/app/api/main.py`
  - Register the new router with prefix `/crawl`.

### 5. Execution
I will perform these steps sequentially, ensuring the existing business logic remains untouched.
