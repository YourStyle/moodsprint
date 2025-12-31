"""Telegram Stars payment handlers for marketplace."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from database import get_user_by_telegram_id

router = Router()
logger = logging.getLogger(__name__)


# ============ Pre-checkout Validation ============


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout: PreCheckoutQuery):
    """
    Validate pre-checkout query before payment is processed.

    Telegram sends this before accepting payment.
    We verify the listing/card is still available.
    """
    payload = pre_checkout.invoice_payload

    try:
        if payload.startswith("marketplace_purchase_"):
            # Marketplace card purchase
            parts = payload.split("_")
            listing_id = int(parts[2])
            buyer_id = int(parts[3])

            # Verify listing is still active
            from database import check_listing_available

            is_available = await check_listing_available(listing_id)

            if not is_available:
                await pre_checkout.answer(
                    ok=False,
                    error_message="Эта карта уже продана или снята с продажи",
                )
                return

            # Verify buyer matches
            user = await get_user_by_telegram_id(pre_checkout.from_user.id)
            if not user or user.get("id") != buyer_id:
                await pre_checkout.answer(
                    ok=False,
                    error_message="Ошибка авторизации. Попробуйте ещё раз.",
                )
                return

            await pre_checkout.answer(ok=True)

        elif payload.startswith("skip_cooldown_"):
            # Cooldown skip purchase
            parts = payload.split("_")
            card_id = int(parts[2])
            user_id = int(parts[3])

            # Verify card is still on cooldown
            from database import check_card_on_cooldown

            is_on_cooldown = await check_card_on_cooldown(card_id, user_id)

            if not is_on_cooldown:
                await pre_checkout.answer(
                    ok=False,
                    error_message="Карта уже не на перезарядке",
                )
                return

            # Verify owner matches
            user = await get_user_by_telegram_id(pre_checkout.from_user.id)
            if not user or user.get("id") != user_id:
                await pre_checkout.answer(
                    ok=False,
                    error_message="Ошибка авторизации. Попробуйте ещё раз.",
                )
                return

            await pre_checkout.answer(ok=True)

        elif payload.startswith("sparks_purchase_"):
            # Sparks pack purchase
            parts = payload.split("_")
            _pack_id = parts[2]  # noqa: F841 - used in successful_payment
            user_id = int(parts[3])

            # Verify user matches
            user = await get_user_by_telegram_id(pre_checkout.from_user.id)
            if not user or user.get("id") != user_id:
                await pre_checkout.answer(
                    ok=False,
                    error_message="Ошибка авторизации. Попробуйте ещё раз.",
                )
                return

            await pre_checkout.answer(ok=True)

        else:
            # Unknown payload type
            logger.warning(f"Unknown payment payload: {payload}")
            await pre_checkout.answer(
                ok=False,
                error_message="Неизвестный тип платежа",
            )

    except Exception as e:
        logger.error(f"Pre-checkout error: {e}")
        await pre_checkout.answer(
            ok=False,
            error_message="Произошла ошибка. Попробуйте ещё раз.",
        )


# ============ Successful Payment ============


@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """
    Handle successful Telegram Stars payment.

    Called after user confirms payment in Telegram.
    """
    payment = message.successful_payment
    payload = payment.invoice_payload
    telegram_payment_id = payment.telegram_payment_charge_id

    logger.info(
        f"Successful payment: payload={payload}, "
        f"amount={payment.total_amount}, "
        f"payment_id={telegram_payment_id}"
    )

    try:
        if payload.startswith("marketplace_purchase_"):
            # Complete marketplace purchase
            parts = payload.split("_")
            listing_id = int(parts[2])
            buyer_id = int(parts[3])

            from database import complete_marketplace_purchase

            result = await complete_marketplace_purchase(
                listing_id=listing_id,
                buyer_id=buyer_id,
                telegram_payment_id=telegram_payment_id,
            )

            if result.get("success"):
                card_name = result.get("card", {}).get("name", "Карта")
                await message.answer(
                    f"✅ Покупка завершена!\n\n"
                    f"🃏 Карта «{card_name}» добавлена в вашу коллекцию.\n\n"
                    f"Откройте приложение, чтобы посмотреть!"
                )
            else:
                # This shouldn't happen if pre-checkout passed
                logger.error(f"Purchase failed after payment: {result}")
                await message.answer(
                    "⚠️ Произошла ошибка при передаче карты. " "Свяжитесь с поддержкой."
                )

        elif payload.startswith("skip_cooldown_"):
            # Complete cooldown skip
            parts = payload.split("_")
            card_id = int(parts[2])
            user_id = int(parts[3])
            price = payment.total_amount

            from database import complete_cooldown_skip

            result = await complete_cooldown_skip(
                card_id=card_id,
                user_id=user_id,
                telegram_payment_id=telegram_payment_id,
                price=price,
            )

            if result.get("success"):
                card_name = result.get("card", {}).get("name", "Карта")
                await message.answer(
                    f"✅ Карта восстановлена!\n\n"
                    f"🃏 «{card_name}» снова готова к бою.\n\n"
                    f"Откройте приложение, чтобы использовать её!"
                )
            else:
                logger.error(f"Cooldown skip failed after payment: {result}")
                await message.answer("⚠️ Произошла ошибка. Свяжитесь с поддержкой.")

        elif payload.startswith("sparks_purchase_"):
            # Complete sparks purchase
            parts = payload.split("_")
            pack_id = parts[2]
            user_id = int(parts[3])

            from database import complete_sparks_purchase

            result = await complete_sparks_purchase(
                pack_id=pack_id,
                user_id=user_id,
                telegram_payment_id=telegram_payment_id,
            )

            if result.get("success"):
                sparks_amount = result.get("sparks", 0)
                await message.answer(
                    f"✅ Покупка завершена!\n\n"
                    f"✨ +{sparks_amount} Sparks добавлено на ваш счёт.\n\n"
                    f"Откройте приложение, чтобы использовать их!"
                )
            else:
                logger.error(f"Sparks purchase failed after payment: {result}")
                await message.answer("⚠️ Произошла ошибка. Свяжитесь с поддержкой.")

        else:
            logger.warning(f"Unknown successful payment payload: {payload}")

    except Exception as e:
        logger.error(f"Payment processing error: {e}")
        await message.answer(
            "⚠️ Произошла ошибка при обработке платежа. " "Свяжитесь с поддержкой."
        )


# ============ Invoice Creation (called from webapp) ============


@router.callback_query(F.data.startswith("buy_card:"))
async def create_card_purchase_invoice(callback: CallbackQuery):
    """
    Create invoice for card purchase.

    Callback data format: buy_card:{listing_id}
    """
    listing_id = int(callback.data.split(":")[1])

    from database import get_listing_for_purchase

    listing = await get_listing_for_purchase(listing_id)

    if not listing:
        await callback.answer("Карта уже продана или снята с продажи", show_alert=True)
        return

    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    # Check not buying own card
    if listing.get("seller_id") == user.get("id"):
        await callback.answer("Нельзя купить свою карту", show_alert=True)
        return

    card = listing.get("card", {})
    price = listing.get("price_stars")

    await callback.message.answer_invoice(
        title=f"Карта: {card.get('name', 'Карта')}",
        description=(
            f"Покупка карты {card.get('name')} "
            f"({card.get('rarity', 'rare')}) за {price} ⭐"
        ),
        payload=f"marketplace_purchase_{listing_id}_{user['id']}",
        currency="XTR",  # Telegram Stars currency
        prices=[LabeledPrice(label="Карта", amount=price)],
    )

    await callback.answer()


@router.callback_query(F.data.startswith("skip_cooldown:"))
async def create_cooldown_skip_invoice(callback: CallbackQuery):
    """
    Create invoice for cooldown skip.

    Callback data format: skip_cooldown:{card_id}
    """
    card_id = int(callback.data.split(":")[1])

    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    from database import get_card_cooldown_info

    card_info = await get_card_cooldown_info(card_id, user["id"])

    if not card_info:
        await callback.answer("Карта не найдена", show_alert=True)
        return

    if not card_info.get("is_on_cooldown"):
        await callback.answer("Карта не на перезарядке", show_alert=True)
        return

    # Calculate price: 2 Stars per hour remaining (rounded up)
    remaining_hours = card_info.get("remaining_hours", 1)
    price = remaining_hours * 2

    await callback.message.answer_invoice(
        title="Пропустить перезарядку",
        description=(
            f"Восстановить карту «{card_info.get('name', 'Карта')}» "
            f"сейчас за {price} ⭐"
        ),
        payload=f"skip_cooldown_{card_id}_{user['id']}",
        currency="XTR",
        prices=[LabeledPrice(label="Восстановление", amount=price)],
    )

    await callback.answer()


# ============ Refund handling ============


@router.message(F.refunded_payment)
async def process_refund(message: Message):
    """Handle refunded payments (for logging/tracking)."""
    refund = message.refunded_payment
    logger.info(
        f"Payment refunded: payload={refund.invoice_payload}, "
        f"amount={refund.total_amount}"
    )

    # We could add logic here to revert purchases if needed
    # For now, just log it
