import logging

from sqlalchemy import Engine
from sqlmodel import Session, select
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

from app.core.db import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

max_tries = 60 * 5  # 5 分钟
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
def init(db_engine: Engine) -> None:
    try:
        with Session(db_engine) as session:
            # 尝试创建会话以检查数据库是否唤醒
            session.exec(select(1))
    except Exception as e:
        # 中文：如果创建会话失败，则记录错误并抛出异常
        logger.error(e)
        raise e

# 中文：如果创建会话成功，则记录成功信息
def main() -> None:
    # 中文：初始化服务
    logger.info("Initializing service")
    init(engine)
    # 中文：服务初始化完成
    logger.info("Service finished initializing")


if __name__ == "__main__":
    main()
