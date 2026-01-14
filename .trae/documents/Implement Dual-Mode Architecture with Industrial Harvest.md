# Crawler Logging Optimization Plan

## 1. Goal

Enhance the logging system to provide granular visibility into every step of the "Scout-Harvest-Refine" pipeline, enabling easier debugging and performance monitoring.

## 2. Changes Overview

### A. `SnifferPipeline` (pipeline.py)

* **Improve** **`_log`** **helper**: Support log levels (INFO, DEBUG, WARN, ERROR) and pass them to the update callback so the frontend can color-code them eventually (though backend logs are the priority).

* **Log Task Context**: Ensure every log message includes `[TaskID]`.

### B. `Scout` (scout.py)

* **Log URL Visits**: Log every URL navigation with status.

* **Log Candidates**: Log details of every candidate found (URL, method, content-type) at DEBUG level.

* **Log Filter Decisions**: Log why a response was accepted or rejected (e.g., "Skipped: Image resource", "Accepted: JSON content-type").

### C. `Architect` (architect.py)

* **Log AI Interaction**: Log the size of the summary sent to AI.

* **Log Strategy**: Log the generated regex pattern and SQL schema (truncated).

* **Log Errors**: Detailed exception logging if AI call fails.

### D. `Harvester` (harvester.py)

* **Log Interception**: Log every intercepted request URL.

* **Log Matching**: Log "Matched pattern" vs "Ignored" for each request.

* **Log Extraction**: Log success/failure of JSON parsing or HTML fallback for each matched response.

* **Log Progress**: Log scroll progress (e.g., "Scrolling 1/5").

### E. `Refinery` (refinery.py)

* **Log Compilation**: Log success/failure of compiling the Python transform code.

* **Log Data Processing**: Log how many items were extracted from each block.

* **Log Transformation Errors**: Log specific errors during `transform_item` execution (e.g., "KeyError: 'price'", "ValueError: invalid literal for float()").

* **Log DB Operations**: Log the number of rows inserted and any SQL errors.

## 3. Implementation Details

* Use `logger.info` for high-level progress (visible in standard logs).

* Use `logger.debug` for high-volume details (requiring verbose mode to see).

* Pass critical logs to `update_callback` so they appear in the UI terminal.

## 4. Execution Steps

1. Update `backend/app/sniffer_pipeline/pipeline.py` to support enhanced logging helper.
2. Update `backend/app/sniffer_pipeline/scout.py` with detailed navigation and filtering logs.
3. Update `backend/app/sniffer_pipeline/architect.py` with AI prompt/response logs.
4. Update `backend/app/sniffer_pipeline/harvester.py` with request interception and matching logs.
5. Update `backend/app/sniffer_pipeline/refinery.py` with transformation and DB insertion logs.

