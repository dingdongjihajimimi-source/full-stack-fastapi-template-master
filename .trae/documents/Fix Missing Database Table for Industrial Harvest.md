# Database Migration Plan

## 1. Issue Diagnosis
The "Industrial Harvest" feature is failing to store data because the `raw_data_lake` table does not exist in the database. While the Python model `RawDataLake` was created, the corresponding database schema migration was never generated or applied.

## 2. Remediation Steps
I will execute the following operations in the `backend` container to sync the database schema:

1.  **Generate Migration**: Create a new Alembic revision file that detects the new `RawDataLake` model.
    ```bash
    alembic revision --autogenerate -m "Add RawDataLake table"
    ```
2.  **Apply Migration**: Execute the migration to create the table in the PostgreSQL database.
    ```bash
    alembic upgrade head
    ```

## 3. Verification
After applying the migration, I will:
1.  Verify the command exit code is 0 (success).
2.  Ask you to try the "Start Harvest" button again in the UI.

This will resolve the "No batches found" issue and allow the industrial collector to persist data.
