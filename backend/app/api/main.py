from fastapi import APIRouter

from app.api.routes import (
    chat,
    crawler,
    fireworks,
    industrial,
    items,
    login,
    private,
    users,
    utils,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(chat.router)
api_router.include_router(fireworks.router)
api_router.include_router(crawler.router, prefix="/crawl", tags=["crawler"])
api_router.include_router(industrial.router, prefix="/industrial", tags=["industrial"])


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
