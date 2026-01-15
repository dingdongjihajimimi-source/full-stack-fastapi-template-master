from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import User, UserCreate

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# 确保在初始化数据库之前导入所有 SQLModel 模型 (app.models)
# 否则，SQLModel 可能无法正确初始化关系
# 更多详情: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # 表应使用 Alembic 迁移创建
    # 但如果你不想使用迁移，请
    # 取消通过取消注释以下行来创建表
    # from sqlmodel import SQLModel

    # 这之所以有效，是因为模型已经从 app.models 导入并注册
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)
