I will update the crawler background task to use the Volcengine API (DeepSeek hosted on Volcengine) instead of the official DeepSeek API.

**Plan:**
1.  **Update `backend/app/worker_tasks/crawler.py`**:
    *   Change the API client initialization to use `settings.VOLC_API_KEY` and the Volcengine Base URL (`https://ark.cn-beijing.volces.com/api/v3`), matching the logic already present in `chat.py`.
    *   Update the model parameter to use `settings.VOLC_MODEL_ID`.
    *   Update the condition to check if `VOLC_API_KEY` is set instead of `DEEPSEEK_API_KEY`.

This will ensure the "Smart Crawler" feature uses your correct Volcengine credentials.