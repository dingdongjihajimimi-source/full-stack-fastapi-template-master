import logging

from sqlmodel import Session

from app.core.db import engine, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 中文：初始化数据库
def init() -> None:
    with Session(engine) as session:
        init_db(session)

# 中文：创建初始数据
def main() -> None:
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")

# 中文：如果作为主程序运行，则创建初始数据
if __name__ == "__main__":
    main()
