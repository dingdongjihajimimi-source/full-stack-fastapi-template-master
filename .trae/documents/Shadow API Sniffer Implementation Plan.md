# Shadow API Sniffer Module Implementation Plan

## 1. Directory Restructuring (Safe Migration)

To support the requested file structure `backend/app/utils/sniffer.py` while preserving existing functionality:

*   **Action**: Move the existing content of `backend/app/utils.py` to `backend/app/utils/__init__.py`.
*   **Result**: This transforms `utils` from a single file module into a Python package. Existing imports like `from app.utils import send_email` will continue to work without any changes to other files.

## 2. Dependency Management

*   **Action**: Update `backend/pyproject.toml` to add:
    *   `playwright>=1.40.0`
    *   `fake-useragent>=1.4.0`
*   **Action**: Update `backend/Dockerfile` to:
    *   Install system dependencies required by Playwright (browsers).
    *   Add a build step to install Playwright browsers (`RUN playwright install chromium --with-deps`).

## 3. Implement Sniffer Module (`backend/app/utils/sniffer.py`)

Create the new module with the following core components:

### A. Initialization & Browser Setup
*   Function: `sniff_api(url: str, scroll_count: int = 3)`
*   Logic:
    *   Use `fake-useragent` to generate a random UA.
    *   Launch Playwright in headless mode.
    *   Setup `page.on("response", handler)` to intercept network traffic.

### B. Traffic Filtering (The Handler)
*   Criteria:
    *   `content-type` includes `application/json`.
    *   `resource_type` is `xhr` or `fetch`.
*   Data Capture:
    *   URL, Method (GET/POST).
    *   Headers (Referer, Authorization, Cookie).
    *   Payload (for POST requests).
    *   Response Preview (first 500 chars).

### C. Simulation (Human Behavior)
*   Logic:
    *   Wait for page load.
    *   Loop `scroll_count` times:
        *   Scroll to bottom.
        *   Wait 1-2 seconds (randomized) for network requests to trigger.

### D. AI Analysis (The Judge)
*   Function: `analyze_candidates_with_ai(candidates_list)`
*   Logic:
    *   Construct a prompt for DeepSeek containing the captured API candidates.
    *   Request: Identify the core data API and extraction rules.
    *   Output: Return a structured dict (URL, headers, params) ready for `httpx`.

## 4. Verification

*   **Rebuild Container**: Rebuild the backend Docker container to install new dependencies and browsers.
*   **Test**: Since this is a utility module, I will create a small test script (or use `fastapi shell`) to invoke `sniff_api` against a target site (e.g., a known SPA site) to verify it captures JSON traffic.
