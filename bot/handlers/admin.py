"""Admin handlers for broadcast and management."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import config
from keyboards import get_admin_keyboard, get_broadcast_confirm_keyboard
from database import get_all_users

router = Router()


class BroadcastStates(StatesGroup):
    """Broadcast FSM states."""
    waiting_for_message = State()
    confirm = State()


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in config.ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Admin panel."""
    if not is_admin(message.from_user.id):
        await message.answer("Access denied.")
        return

    users = await get_all_users()

    text = (
        f"Admin Panel\n"
        f"{'=' * 20}\n\n"
        f"Total users: {len(users)}\n\n"
        "Select an action:"
    )

    await message.answer(text, reply_markup=get_admin_keyboard())


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery):
    """Show admin statistics."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied.")
        return

    users = await get_all_users()

    # Calculate some basic stats
    total_users = len(users)
    total_xp = sum(u.get('xp', 0) for u in users)
    avg_level = sum(u.get('level', 1) for u in users) / max(total_users, 1)

    text = (
        f"Platform Statistics\n"
        f"{'=' * 20}\n\n"
        f"Total users: {total_users}\n"
        f"Total XP earned: {total_xp}\n"
        f"Average level: {avg_level:.1f}\n"
    )

    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Start broadcast flow."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied.")
        return

    await callback.message.edit_text(
        "Send me the message you want to broadcast to all users.\n\n"
        "You can send text, photo, or video.\n"
        "Send /cancel to abort."
    )
    await state.set_state(BroadcastStates.waiting_for_message)
    await callback.answer()


@router.message(Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext):
    """Cancel broadcast."""
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("Broadcast cancelled.", reply_markup=get_admin_keyboard())


@router.message(BroadcastStates.waiting_for_message)
async def receive_broadcast_message(message: Message, state: FSMContext):
    """Receive broadcast message."""
    if not is_admin(message.from_user.id):
        return

    # Store message info
    await state.update_data(
        message_id=message.message_id,
        chat_id=message.chat.id,
        message_type='text' if message.text else 'photo' if message.photo else 'video',
        text=message.text or message.caption,
        photo_id=message.photo[-1].file_id if message.photo else None,
        video_id=message.video.file_id if message.video else None
    )

    users = await get_all_users()

    await message.answer(
        f"Ready to send this message to {len(users)} users.\n"
        "Confirm?",
        reply_markup=get_broadcast_confirm_keyboard()
    )
    await state.set_state(BroadcastStates.confirm)


@router.callback_query(F.data == "broadcast:confirm", BroadcastStates.confirm)
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Confirm and send broadcast."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied.")
        return

    data = await state.get_data()
    users = await get_all_users()

    await callback.message.edit_text("Sending broadcast...")

    sent = 0
    failed = 0

    for user in users:
        try:
            if data['message_type'] == 'text':
                await callback.bot.send_message(
                    user['telegram_id'],
                    data['text']
                )
            elif data['message_type'] == 'photo':
                await callback.bot.send_photo(
                    user['telegram_id'],
                    data['photo_id'],
                    caption=data.get('text')
                )
            elif data['message_type'] == 'video':
                await callback.bot.send_video(
                    user['telegram_id'],
                    data['video_id'],
                    caption=data.get('text')
                )
            sent += 1
        except Exception as e:
            failed += 1

    await state.clear()
    await callback.message.edit_text(
        f"Broadcast complete!\n\n"
        f"Sent: {sent}\n"
        f"Failed: {failed}",
        reply_markup=get_admin_keyboard()
    )


@router.callback_query(F.data == "broadcast:cancel", BroadcastStates.confirm)
async def cancel_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    """Cancel broadcast from callback."""
    await state.clear()
    await callback.message.edit_text(
        "Broadcast cancelled.",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:active_users")
async def show_active_users(callback: CallbackQuery):
    """Show recently active users."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied.")
        return

    users = await get_all_users()

    # Sort by last activity (if available) or creation date
    sorted_users = sorted(
        users,
        key=lambda x: x.get('last_activity_date') or x.get('created_at') or '',
        reverse=True
    )[:10]

    text = "Recently Active Users\n" + "=" * 20 + "\n\n"

    for i, user in enumerate(sorted_users, 1):
        username = user.get('username') or user.get('first_name') or f"User {user['telegram_id']}"
        level = user.get('level', 1)
        xp = user.get('xp', 0)
        streak = user.get('streak_days', 0)
        text += f"{i}. {username} - Lv.{level} ({xp} XP, {streak}d streak)\n"

    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    await callback.answer()
