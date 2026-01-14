I will update the system to allow customizing the crawler task and support distinct models for Chat (Doubao) and SQL Generation (DeepSeek).

**Backend Changes:**

1. **Configuration**:

   * Update `backend/app/core/config.py` to add `VOLC_DEEPSEEK_MODEL_ID` for the SQL generation task.

   * Update `.env` to include a placeholder for `VOLC_DEEPSEEK_MODEL_ID`.
2. **API & Worker**:

   * Modify `backend/app/api/routes/crawler.py` to accept a request body with `url`, `table_name`, and `columns`.

   * Update `backend/app/worker_tasks/crawler.py` to:

     * Accept these new parameters.

     * Use `settings.VOLC_DEEPSEEK_MODEL_ID` for the AI call.

     * Dynamically construct the SQL generation prompt using the provided `table_name` and `columns`.

**Frontend Changes:**

1. **Client SDK**:

   * Regenerate the frontend API client (`npm run generate-client`) to reflect the new API signature.
2. **UI Implementation**:

   * Update `frontend/src/routes/_layout/crawler.tsx` to add input fields for:

     * **Target URL**

     * **Table Name**

     * **Column Names** (comma-separated)

   * Pass these values when starting the crawler task.

**Execution Steps:**

1. Modify backend configuration and code.
2. Restart the backend service to apply changes.
3. Regenerate frontend client.
4. Update frontend UI.

