"""Bot handlers."""

from aiogram import Router
from handlers.user import router as user_router
from handlers.notifications import router as notifications_router

main_router = Router()
main_router.include_router(user_router)
main_router.include_router(notifications_router)
