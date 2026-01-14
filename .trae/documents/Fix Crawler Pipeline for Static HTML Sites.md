# Crawler Pipeline Fix Plan

## Problem Analysis
The user reported that the crawler pipeline completes successfully but produces 0 results ("collected 0 blocks").
- **Logs Analysis**: The "Architect" phase correctly identified that `books.toscrape.com` is a static HTML site and defined a strategy for it.
- **Root Cause**: The `Harvester` component strictly attempts to parse responses as JSON (`response.json()`). When it encounters the HTML pages (as predicted by the Architect), it fails to parse them, resulting in 0 data blocks.
- **Secondary Issue**: The `Architect`'s prompt instructs the AI to expect "JSON items", so the generated transformation code might not be prepared to handle HTML input even if the Harvester passed it.

## Proposed Changes

1.  **Modify `backend/app/sniffer_pipeline/harvester.py`**:
    *   Update `handle_response` to check the `Content-Type` header.
    *   If the response is not JSON (e.g., `text/html`), fallback to `response.text()` and wrap it in a dictionary structure: `{"html": text_content, "url": url}`.
    *   This ensures that HTML pages are captured and passed to the Refinery.

2.  **Modify `backend/app/sniffer_pipeline/architect.py`**:
    *   Update the system prompt to explicitly inform the AI that:
        *   The input `item` might be a dictionary containing `html` and `url` if the target is a static site.
        *   In such cases, the `transform_item` function **MUST** import `bs4` (BeautifulSoup) to parse the HTML.
    *   This ensures the AI generates valid Python code that can handle the HTML data passed by the Harvester.

## Verification
- Run a test crawl against `https://books.toscrape.com/`.
- Verify that "Harvester" collects blocks > 0.
- Verify that "Refinery" extracts items > 0.
- Verify that the CSV/SQL files are generated.
