"""Bot handlers."""

from aiogram import Router
from handlers.admin import router as admin_router
from handlers.notifications import router as notifications_router
from handlers.payments import router as payments_router
from handlers.user import router as user_router

main_router = Router()
main_router.include_router(user_router)
main_router.include_router(notifications_router)
main_router.include_router(admin_router)
main_router.include_router(payments_router)
