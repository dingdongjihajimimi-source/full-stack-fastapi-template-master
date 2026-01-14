I will refactor the existing sniffer into a modular `sniffer_pipeline` package.

### **1. Proposed Folder Structure**
I will create a new package `backend/app/sniffer_pipeline/` to house the decoupled components.

```text
backend/app/sniffer_pipeline/
├── __init__.py           # Exposes the main pipeline
├── schemas.py            # Pydantic models (Strategy, Candidate)
├── scout.py              # Phase 1: Traffic Sampling (Refactored from sniffer.py)
├── architect.py          # Phase 2: AI Schema Definition
├── harvester.py          # Phase 3: Targeted Data Collection
├── refinery.py           # Phase 4: AI ETL & SQL Execution
└── pipeline.py           # Orchestrator (Main Entry Point)
```

### **2. Component Implementation Details**

#### **Phase 1: The Scout (`scout.py`)**
- **Function**: `sniff_sample(url: str)`
- **Logic**: 
  - Uses `playwright` to navigate and scroll.
  - Captures **all** JSON (XHR/Fetch) responses into a list of candidates.
  - Returns `List[Candidate]`.

#### **Phase 2: The Architect (`architect.py`)**
- **Function**: `define_extraction_strategy(candidates: List[Candidate])`
- **Logic**:
  - Sends candidate samples to DeepSeek.
  - **Prompt**: "Analyze JSONs... Identify valuable data... Define Schema."
  - **Output**: `ExtractionStrategy` object containing:
    - `target_api_url_pattern`: Regex for the API.
    - `target_keys`: Fields to extract.
    - `sql_schema`: `CREATE TABLE` statement.

#### **Phase 3: The Harvester (`harvester.py`)**
- **Function**: `run_harvest(url: str, strategy: ExtractionStrategy)`
- **Logic**:
  - Re-navigates to the target URL.
  - Sets up a strict network interceptor using `strategy.target_api_url_pattern`.
  - Scrolls/Paginate to collect data chunks.
  - Returns `List[Dict]` (Raw Data Blocks).

#### **Phase 4: The Refinery (`refinery.py`)**
- **Function**: `process_and_insert(raw_data: List[Dict], strategy: ExtractionStrategy)`
- **Logic**:
  - Executes `strategy.sql_schema` to ensure the table exists.
  - Sends raw data chunks to DeepSeek.
  - **Prompt**: "Clean data... Return valid SQL INSERT statements."
  - Executes the generated SQL against the database using `app.core.db.engine`.

#### **Orchestrator (`pipeline.py`)**
- Ties everything together: `Scout -> Architect -> Harvester -> Refinery`.

### **3. Execution Plan**
1.  **Create Directory**: `backend/app/sniffer_pipeline/`.
2.  **Define Models**: Create `schemas.py` with Pydantic models.
3.  **Implement Components**: Create `scout.py`, `architect.py`, `harvester.py`, `refinery.py`.
4.  **Implement Pipeline**: Create `pipeline.py`.
5.  **Update `sniffer.py`**: Refactor `backend/app/utils/sniffer.py` to be a compatibility wrapper or remove it (depending on preference, I will likely deprecate it or make it use the pipeline). *I will assume replacing it with a facade is best to keep existing imports working if any.*
