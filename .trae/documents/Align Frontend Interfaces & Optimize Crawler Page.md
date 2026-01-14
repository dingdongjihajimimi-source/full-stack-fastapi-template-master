# Frontend-Backend Interface Alignment & Page Optimization Plan

## 1. Interface Alignment
The goal is to strictly align the Frontend TypeScript definitions with the Backend Pydantic models to ensure type safety and prevent runtime errors.

- **Update `frontend/src/client/types.gen.ts`**:
  - Sync `CrawlRequest` with backend `crawler.py`:
    - Change `table_name` from `string` to `string | null | undefined` (Backend allows `None`).
    - Change `columns` from `Array<string>` to `Array<string> | undefined` (Backend defaults to `[]`).
  - Verify `mode` and `review_mode` are correctly defined (already present but need to ensure optionality matches backend).

## 2. Code Refactoring & Type Safety
- **Remove `any` casts in `crawler.tsx`**:
  - Refactor `startMutation` to use the strictly typed `CrawlerService.startCrawl` without bypassing TypeScript checks.
- **Form Logic Update**:
  - Update `handleStartCrawl` to correctly construct the payload based on "Manual" vs "Auto" mode, omitting optional fields when not needed.

## 3. UI/UX Optimization
- **Terminal Enhancements**:
  - Add a **"Clear Logs"** button to the terminal header.
  - Add a **"Refresh Status"** button to manually sync state if polling is slow.
- **Review Dialog Improvements**:
  - Increase the height of `transform_code` and `sql_schema` editors.
  - Ensure the "Confirm & Continue" button clearly indicates it will resume the pipeline.
- **Status Visualization**:
  - Improve the "Pipeline Progress" stepper to handle "Failed" or "Paused" states more visually (e.g., amber for paused).
