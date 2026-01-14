# Industrial Harvest CSV Download Plan

## 1. Backend Implementation (`backend/app/api/routes/industrial.py`)

*   **Add Endpoint**: `GET /download/{batch_id}`
*   **Logic**:
    1.  Query `RawDataLake` table for all records matching `batch_id`.
    2.  Use Python's `csv` module (or `pandas` if available/preferred, but `csv` is lighter) to write data to an in-memory string buffer (`io.StringIO`).
    3.  Columns to export: `id`, `url`, `status`, `content_type`, `created_at`, `content` (truncated to first 1000 chars to avoid massive CSVs, or full content if preferred—user said "unintuitive in DB", so full content might be useful, but let's stick to standard CSV practices. I'll export full content but handle newlines).
    4.  Return `StreamingResponse` with `media_type="text/csv"` and `Content-Disposition` header.

## 2. Frontend Implementation (`frontend/src/routes/_layout/crawler.tsx`)

*   **Add "Download CSV" Button**:
    *   In the "Raw Data Lake (Batch List)" table, add a new button next to "Refine".
    *   Icon: `FileDown` or similar from `lucide-react`.
*   **Implement Handler**:
    *   Function `handleDownloadBatch(batchId: string)`.
    *   Fetch blob from `/api/v1/industrial/download/{batchId}`.
    *   Create object URL and trigger download (similar to existing `handleDownload`).

## 3. Verification

*   Start a harvest to generate data.
*   Click the download button.
*   Verify the downloaded CSV file contains the correct data rows.
