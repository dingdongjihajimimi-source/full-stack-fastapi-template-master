# Industrial Collector Performance Optimization Plan

## 1. Problem Analysis
The slowness is caused by:
1.  **Synchronous Blocking**: The collector uses synchronous `Session(engine)` calls inside the asynchronous Playwright event loop. This blocks the loop, causing significant delays.
2.  **Excessive Transactions**: The code commits to the database for *every single* captured resource (N resources = N transactions).
3.  **Missing Async Driver**: The project currently uses `psycopg2` (sync) instead of `asyncpg` (async).

## 2. Solution Strategy

### A. Enable Async Database Support (`backend/app/core/db.py`)
*   Add `async_engine` using `create_async_engine`.
*   This requires the `asyncpg` driver (which is likely already installed via `psycopg[binary]`, but we should ensure the URI is correct).

### B. Refactor Collector to be Fully Async (`backend/app/industrial_pipeline/collector.py`)
*   **Use AsyncSession**: Replace `Session(engine)` with `AsyncSession(async_engine)`.
*   **Batch Processing**:
    *   Introduce an in-memory buffer (`self.buffer = []`).
    *   Flush the buffer to the database only when it reaches a threshold (e.g., 50 items) or when the task completes.
    *   This reduces DB round-trips from N to N/50.

## 3. Implementation Steps

1.  **Modify `app/core/db.py`**: Initialize `async_engine`.
2.  **Update `app/industrial_pipeline/collector.py`**:
    *   Inject `AsyncSession`.
    *   Implement `flush_buffer` method.
    *   Update `handle_response` to append to buffer instead of writing directly.

## 4. Verification
*   Run a new harvest task.
*   Observe logs to confirm batch inserts (e.g., "Flushing 50 items").
*   Check if the UI updates faster and the task completes sooner.
