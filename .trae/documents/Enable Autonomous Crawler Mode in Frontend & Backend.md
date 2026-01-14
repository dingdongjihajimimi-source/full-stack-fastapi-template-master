I will enhance the backend and frontend to support a sophisticated "Autonomous Mode" with real-time visibility and control.

### **1. Backend Enhancements**
*   **Stateful Pipeline & Progress Tracking**:
    *   Update `SnifferPipeline` to broadcast status updates (Phase 1 -> 2 -> 3 -> 4) to Redis or Database.
    *   Add a `task_id` context to the pipeline to associate logs and state.
*   **"Pre-run Review" Pause Mechanism**:
    *   Modify `SnifferPipeline` to accept a `review_mode=True` flag.
    *   If enabled, the pipeline will **pause after Phase 2 (Architect)** and save the proposed `ExtractionStrategy` to the database/Redis with status `paused_for_review`.
    *   Create a new API `POST /api/v1/crawl/resume/{task_id}` that accepts the (potentially modified) strategy and resumes the pipeline (Phase 3 & 4).
*   **Real-time Logging**:
    *   Implement a custom Logger adapter in the pipeline that pushes log lines to a Redis list or channel keyed by `task_id`.
    *   Create a WebSocket endpoint (or polling API) `GET /api/v1/crawl/logs/{task_id}` to stream these logs to the frontend.

### **2. Frontend Enhancements (`crawler.tsx`)**
*   **Visual Progress Tracker**:
    *   Add a stepper component showing: `Scout` -> `Architect` -> `Review (Optional)` -> `Harvester` -> `Refinery`.
    *   Highlight the current active phase.
*   **Pre-run Review UI**:
    *   If "Pre-run Review" is enabled, show a modal/form after Phase 2.
    *   Display the AI-generated `Table Name`, `Columns`, and `SQL Schema`.
    *   Allow the user to edit these fields.
    *   "Confirm & Continue" button to trigger the resume API.
*   **Live Log Console**:
    *   Add a terminal-like window at the bottom.
    *   Stream logs from the backend (e.g., "Scout found 5 candidates...", "Architect defining schema...").

### **3. Execution Steps**
1.  **Backend**:
    *   Modify `CrawlerTask` model to include `pipeline_state` (JSON) and `current_phase`.
    *   Update `SnifferPipeline` to handle pausing and logging.
    *   Implement `start_autonomous_crawl` and `resume_crawl` endpoints.
2.  **Frontend**:
    *   Update `Crawler` component with tabs (Manual/Auto).
    *   Implement the Progress Stepper and Log Window.
    *   Implement the Strategy Review Modal.
3.  **Deployment**:
    *   Restart containers.
