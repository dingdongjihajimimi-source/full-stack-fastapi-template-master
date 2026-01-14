# app/core/paths.py
from pathlib import Path
import os

# 获取项目根目录 (假设 app 在根目录下)
# 这种写法比较稳，不管你在哪运行 docker，都能定位到 backend 根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent 

GENERATED_DATA_DIR = BASE_DIR / "generated_data"
SQL_DIR = GENERATED_DATA_DIR / "sql"
CSV_DIR = GENERATED_DATA_DIR / "csv"
INDUSTRIAL_DIR = GENERATED_DATA_DIR / "industrial"

# 确保目录存在
SQL_DIR.mkdir(parents=True, exist_ok=True)
CSV_DIR.mkdir(parents=True, exist_ok=True)
INDUSTRIAL_DIR.mkdir(parents=True, exist_ok=True)