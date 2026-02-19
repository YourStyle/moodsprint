"""Card system API endpoints."""

from datetime import date

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from app.api import api_bp
from app.models.card import (
    CardTemplate,
    CardTrade,
    Friendship,
    PendingReferralReward,
    UserCard,
)
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.models.user_profile import UserProfile
from app.services.card_service import CardService
from app.utils import get_lang, not_found, success_response, validation_error
from app.utils.auth import admin_required
from app.utils.notifications import notify_trade_received

# Healing requirements: tasks needed per heal
# First heal = 3 tasks, second = 5 tasks (cumulative)
HEAL_REQUIREMENTS = [0, 3]  # tasks required for 1st (free), 2nd heal

# ============ Card Collection ============


@api_bp.route("/cards", methods=["GET"])
@jwt_required()
def get_user_cards():
    """
    Get user's card collection.

    Query params:
    - genre: filter by genre (optional)
    - in_deck: filter by deck status (optional, "true" or "false")
    """
    user_id = int(get_jwt_identity())
    genre = request.args.get("genre")
    in_deck = request.args.get("in_deck")

    service = CardService()
    cards = service.get_user_cards(user_id, genre=genre)

    if in_deck is not None:
        in_deck_bool = in_deck.lower() == "true"
        cards = [c for c in cards if c.is_in_deck == in_deck_bool]

    # Group by rarity for stats
    rarity_counts = {}
    for card in cards:
        rarity_counts[card.rarity] = rarity_counts.get(card.rarity, 0) + 1

    lang = get_lang()
    return success_response(
        {
            "cards": [c.to_dict(lang) for c in cards],
            "total": len(cards),
            "rarity_counts": rarity_counts,
        }
    )


@api_bp.route("/cards/<int:card_id>", methods=["GET"])
@jwt_required()
def get_card_details(card_id: int):
    """Get details of a specific card."""
    user_id = int(get_jwt_identity())

    card = UserCard.query.filter_by(id=card_id, user_id=user_id).first()
    if not card:
        return not_found("Card not found")

    return success_response({"card": card.to_dict(get_lang())})


@api_bp.route("/cards/<int:card_id>/generate-image", methods=["POST"])
@jwt_required()
def generate_card_image(card_id: int):
    """Generate image for a card (async, called after card is shown to user)."""
    user_id = int(get_jwt_identity())

    service = CardService()
    result = service.generate_card_image_async(card_id, user_id)

    if result.get("success"):
        return success_response(result)
    else:
        return validation_error(result.get("error", "Unknown error"))


# ============ Deck Management ============


def get_max_deck_size(user_level: int) -> int:
    """Dynamic deck size: base 5, +1 at level 10, +1 at level 15."""
    base = 5
    if user_level >= 10:
        base += 1
    if user_level >= 15:
        base += 1
    return base


@api_bp.route("/deck", methods=["GET"])
@jwt_required()
def get_deck():
    """Get user's active battle deck."""
    user_id = int(get_jwt_identity())

    user = User.query.get(user_id)
    max_size = get_max_deck_size(user.level if user else 1)

    service = CardService()
    deck = service.get_user_deck(user_id)

    # Calculate deck stats
    total_hp = sum(c.hp for c in deck)
    total_attack = sum(c.attack for c in deck)
    genres = list(set(c.genre for c in deck))

    lang = get_lang()
    return success_response(
        {
            "deck": [c.to_dict(lang) for c in deck],
            "size": len(deck),
            "max_size": max_size,
            "stats": {
                "total_hp": total_hp,
                "total_attack": total_attack,
                "genres": genres,
            },
        }
    )


@api_bp.route("/deck/add", methods=["POST"])
@jwt_required()
def add_to_deck():
    """
    Add a card to battle deck.

    Request body:
    {
        "card_id": 1
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    card_id = data.get("card_id")
    if not card_id:
        return validation_error({"card_id": "Card ID is required"})

    user = User.query.get(user_id)
    max_size = get_max_deck_size(user.level if user else 1)

    service = CardService()
    result = service.add_to_deck(
        user_id, card_id, max_deck_size=max_size, lang=get_lang()
    )

    if not result["success"]:
        error_messages = {
            "card_not_found": "Карта не найдена",
            "card_destroyed": "Карта уничтожена",
            "already_in_deck": "Карта уже в колоде",
            "deck_full": f"Колода полная (максимум {result.get('max_size', max_size)} карт)",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response(result)


@api_bp.route("/deck/remove", methods=["POST"])
@jwt_required()
def remove_from_deck():
    """
    Remove a card from battle deck.

    Request body:
    {
        "card_id": 1
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    card_id = data.get("card_id")
    if not card_id:
        return validation_error({"card_id": "Card ID is required"})

    service = CardService()
    result = service.remove_from_deck(user_id, card_id)

    if not result["success"]:
        return validation_error({"error": result["error"]})

    return success_response({"message": "Карта убрана из колоды"})


# ============ Card Healing ============


@api_bp.route("/cards/heal-status", methods=["GET"])
@jwt_required()
def get_heal_status():
    """Get healing status - tasks needed for next heal."""
    user_id = int(get_jwt_identity())

    # Get or create profile
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)
        db.session.commit()

    heals_today = profile.get_heals_today()
    required_tasks = get_heal_requirement(heals_today)
    tasks_completed = get_tasks_completed_today(user_id)

    can_heal = required_tasks == 0 or tasks_completed >= required_tasks

    return success_response(
        {
            "heals_today": heals_today,
            "required_tasks": required_tasks,
            "completed_tasks": tasks_completed,
            "can_heal": can_heal,
            "heal_requirements": HEAL_REQUIREMENTS,
        }
    )


def get_tasks_completed_today(user_id: int) -> int:
    """Count tasks completed today."""
    today = date.today()
    return Task.query.filter(
        Task.user_id == user_id,
        Task.status == TaskStatus.COMPLETED.value,
        db.func.date(Task.updated_at) == today,
    ).count()


def get_heal_requirement(heals_today: int) -> int:
    """Get the number of tasks required for the next heal."""
    if heals_today >= len(HEAL_REQUIREMENTS):
        # After defined limits, allow free heals
        return 0
    return HEAL_REQUIREMENTS[heals_today]


@api_bp.route("/cards/<int:card_id>/heal", methods=["POST"])
@jwt_required()
def heal_card(card_id: int):
    """Heal a specific card to full HP."""
    user_id = int(get_jwt_identity())

    # Get or create profile to track heals
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)
        db.session.flush()

    # Check healing requirements
    heals_today = profile.get_heals_today()
    required_tasks = get_heal_requirement(heals_today)

    if required_tasks > 0:
        tasks_completed = get_tasks_completed_today(user_id)
        if tasks_completed < required_tasks:
            heal_number = heals_today + 1
            return validation_error(
                {
                    "error": "not_enough_tasks",
                    "message": f"Для {heal_number}-го лечения за сегодня нужно "
                    f"закрыть {required_tasks} задач. Выполнено: {tasks_completed}.",
                    "required_tasks": required_tasks,
                    "completed_tasks": tasks_completed,
                    "heals_today": heals_today,
                }
            )

    service = CardService()
    result = service.heal_card(card_id, user_id, lang=get_lang())

    if not result["success"]:
        error_messages = {
            "card_not_found": "Карта не найдена",
            "card_destroyed": "Карта уничтожена и не может быть вылечена",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    # Record successful heal
    profile.record_heal()
    db.session.commit()

    return success_response(
        {
            "card": result["card"],
            "message": "Карта вылечена!",
            "heals_today": profile.heals_today,
        }
    )


@api_bp.route("/cards/heal-all", methods=["POST"])
@jwt_required()
def heal_all_cards():
    """Heal all user's cards (counts as one heal action)."""
    user_id = int(get_jwt_identity())

    # Get or create profile to track heals
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)
        db.session.flush()

    # Check healing requirements
    heals_today = profile.get_heals_today()
    required_tasks = get_heal_requirement(heals_today)

    if required_tasks > 0:
        tasks_completed = get_tasks_completed_today(user_id)
        if tasks_completed < required_tasks:
            heal_number = heals_today + 1
            return validation_error(
                {
                    "error": "not_enough_tasks",
                    "message": f"Для {heal_number}-го лечения за сегодня нужно "
                    f"закрыть {required_tasks} задач. Выполнено: {tasks_completed}.",
                    "required_tasks": required_tasks,
                    "completed_tasks": tasks_completed,
                    "heals_today": heals_today,
                }
            )

    service = CardService()
    healed_count = service.heal_all_cards(user_id)

    if healed_count > 0:
        # Record successful heal (counts as one heal action)
        profile.record_heal()
        db.session.commit()

    return success_response(
        {
            "healed_count": healed_count,
            "message": f"Вылечено карт: {healed_count}",
            "heals_today": profile.heals_today,
        }
    )


# ============ Pending Referral Rewards ============


@api_bp.route("/cards/pending-rewards", methods=["GET"])
@jwt_required()
def get_pending_rewards():
    """
    Get pending referral rewards for the current user.
    These are rewards the user should see in a modal when they log in.
    """
    user_id = int(get_jwt_identity())

    pending = PendingReferralReward.query.filter_by(
        user_id=user_id, is_claimed=False
    ).all()

    # Group rewards by friend (in case of multiple invites)
    rewards = []
    for p in pending:
        rewards.append(p.to_dict())

    return success_response(
        {
            "rewards": rewards,
            "total": len(rewards),
        }
    )


@api_bp.route("/cards/pending-rewards/count", methods=["GET"])
@jwt_required()
def get_pending_rewards_count():
    """
    Get count of unclaimed referral rewards.
    Used to show notification bubble in the UI.
    """
    user_id = int(get_jwt_identity())

    count = PendingReferralReward.query.filter_by(
        user_id=user_id, is_claimed=False
    ).count()

    return success_response({"count": count})


@api_bp.route("/cards/pending-rewards/claim", methods=["POST"])
@jwt_required()
def claim_pending_rewards():
    """
    Mark all pending referral rewards as claimed.
    Called after user has seen the rewards modal.
    """
    user_id = int(get_jwt_identity())

    pending = PendingReferralReward.query.filter_by(
        user_id=user_id, is_claimed=False
    ).all()

    claimed_count = 0
    for p in pending:
        p.is_claimed = True
        claimed_count += 1

    db.session.commit()

    return success_response(
        {
            "claimed": claimed_count,
            "message": f"Получено {claimed_count} наград!",
        }
    )


# ============ Card Templates ============


@api_bp.route("/card-templates", methods=["GET"])
@jwt_required()
def get_card_templates():
    """
    Get available card templates.

    Query params:
    - genre: filter by genre (optional)
    """
    user_id = get_jwt_identity()
    genre = request.args.get("genre")
    lang = get_lang()

    query = CardTemplate.query.filter_by(is_active=True)
    if genre:
        query = query.filter_by(genre=genre)

    templates = query.all()

    # Get all template IDs the user has ever owned (including destroyed/merged)
    collected_rows = (
        db.session.query(UserCard.template_id)
        .filter(
            UserCard.user_id == user_id,
            UserCard.template_id.isnot(None),
        )
        .distinct()
        .all()
    )
    collected_template_ids = [r[0] for r in collected_rows]

    # Include unlocked genres for card status classification
    card_service = CardService()
    unlocked_genres = card_service.get_unlocked_genres(user_id)

    return success_response(
        {
            "templates": [t.to_dict(lang) for t in templates],
            "total": len(templates),
            "collected_template_ids": collected_template_ids,
            "unlocked_genres": unlocked_genres,
        }
    )


# ============ Friends System ============


@api_bp.route("/friends", methods=["GET"])
@jwt_required()
def get_friends():
    """Get user's friends list."""
    user_id = int(get_jwt_identity())

    service = CardService()
    friends = service.get_friends(user_id)

    # Enrich with user info
    for friend in friends:
        user = User.query.get(friend["friend_id"])
        if user:
            friend["username"] = user.username
            friend["first_name"] = user.first_name
            friend["level"] = user.level

    return success_response(
        {
            "friends": friends,
            "total": len(friends),
        }
    )


@api_bp.route("/friends/requests", methods=["GET"])
@jwt_required()
def get_friend_requests():
    """Get pending friend requests."""
    user_id = int(get_jwt_identity())

    service = CardService()
    requests = service.get_pending_requests(user_id)

    result = []
    for req in requests:
        user = User.query.get(req.user_id)
        result.append(
            {
                "id": req.id,
                "from_user_id": req.user_id,
                "username": user.username if user else None,
                "first_name": user.first_name if user else None,
                "created_at": req.created_at.isoformat() if req.created_at else None,
            }
        )

    return success_response(
        {
            "requests": result,
            "total": len(result),
        }
    )


@api_bp.route("/friends/request", methods=["POST"])
@jwt_required()
def send_friend_request():
    """
    Send a friend request.

    Request body:
    {
        "user_id": 123  // or
        "username": "friend_username"
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    friend_id = data.get("user_id")
    username = data.get("username")

    if not friend_id and not username:
        return validation_error({"error": "user_id or username is required"})

    # Find friend by username if needed
    if not friend_id and username:
        friend = User.query.filter_by(username=username).first()
        if not friend:
            return not_found("Пользователь не найден")
        friend_id = friend.id

    service = CardService()
    result = service.send_friend_request(user_id, friend_id)

    if not result["success"]:
        error_messages = {
            "cannot_friend_self": "Нельзя добавить себя в друзья",
            "already_friends": "Вы уже друзья",
            "request_pending": "Запрос уже отправлен",
            "blocked": "Пользователь заблокирован",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response(
        {
            "message": "Запрос в друзья отправлен!",
            "friendship": result["friendship"],
        }
    )


@api_bp.route("/friends/accept/<int:request_id>", methods=["POST"])
@jwt_required()
def accept_friend_request(request_id: int):
    """Accept a friend request."""
    user_id = int(get_jwt_identity())

    service = CardService()
    result = service.accept_friend_request(user_id, request_id)

    if not result["success"]:
        return not_found("Запрос не найден")

    return success_response(
        {
            "message": "Запрос принят! Теперь вы друзья.",
            "friendship": result["friendship"],
        }
    )


@api_bp.route("/friends/reject/<int:request_id>", methods=["POST"])
@jwt_required()
def reject_friend_request(request_id: int):
    """Reject a friend request."""
    user_id = int(get_jwt_identity())

    friendship = Friendship.query.filter_by(
        id=request_id, friend_id=user_id, status="pending"
    ).first()

    if not friendship:
        return not_found("Запрос не найден")

    db.session.delete(friendship)
    db.session.commit()

    return success_response({"message": "Запрос отклонён"})


@api_bp.route("/friends/connect-referral", methods=["POST"])
@jwt_required()
def connect_referral():
    """
    Connect with referrer (auto-accept friendship).
    Used when existing user clicks invite link.
    Both users get bonus cards.

    Request body:
    {
        "referrer_id": 123
    }
    """
    from datetime import datetime

    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    referrer_id = data.get("referrer_id")
    if not referrer_id:
        return validation_error({"error": "referrer_id is required"})

    if user_id == referrer_id:
        return validation_error({"error": "Нельзя добавить себя в друзья"})

    # Check if referrer exists
    referrer = User.query.get(referrer_id)
    if not referrer:
        return not_found("Пользователь не найден")

    # Check if friendship already exists
    existing = Friendship.query.filter(
        ((Friendship.user_id == user_id) & (Friendship.friend_id == referrer_id))
        | ((Friendship.user_id == referrer_id) & (Friendship.friend_id == user_id))
    ).first()

    if existing:
        if existing.status == "accepted":
            return success_response(
                {
                    "message": "Вы уже друзья!",
                    "friendship": existing.to_dict(),
                    "already_friends": True,
                }
            )
        elif existing.status == "pending":
            # Auto-accept pending request
            existing.status = "accepted"
            existing.accepted_at = datetime.utcnow()
            db.session.commit()
            return success_response(
                {
                    "message": "Запрос принят! Теперь вы друзья.",
                    "friendship": existing.to_dict(),
                }
            )

    # Create new accepted friendship
    friendship = Friendship(
        user_id=referrer_id,
        friend_id=user_id,
        status="accepted",
        accepted_at=datetime.utcnow(),
    )
    db.session.add(friendship)

    # Give bonus cards to both users
    rewards = {}
    try:
        service = CardService()
        current_user = User.query.get(user_id)
        invitee_name = current_user.first_name or current_user.username or "друг"
        referrer_name = referrer.first_name or referrer.username or "друг"

        # Give bonus card to the inviter (referrer)
        referrer_card = service.generate_referral_reward(referrer_id)
        if referrer_card:
            rewards["referrer_card"] = referrer_card.to_dict(get_lang())
            # Create pending reward for referrer
            pending_referrer = PendingReferralReward(
                user_id=referrer_id,
                friend_id=user_id,
                friend_name=invitee_name,
                card_id=referrer_card.id,
                is_referrer=True,
            )
            db.session.add(pending_referrer)

        # Give bonus card to the invitee (current user)
        invitee_card = service.generate_referral_reward(user_id)
        if invitee_card:
            rewards["invitee_card"] = invitee_card.to_dict(get_lang())
            # Create pending reward for invitee
            pending_invitee = PendingReferralReward(
                user_id=user_id,
                friend_id=referrer_id,
                friend_name=referrer_name,
                card_id=invitee_card.id,
                is_referrer=False,
            )
            db.session.add(pending_invitee)
    except Exception as e:
        # Don't fail the friendship creation if card generation fails
        import logging

        logging.error(f"Failed to generate referral reward cards: {e}")

    db.session.commit()

    response = {
        "message": "Теперь вы друзья!",
        "friendship": friendship.to_dict(),
    }
    if rewards:
        response["rewards"] = rewards

    return success_response(response)


# ============ Card Trading ============


@api_bp.route("/trades", methods=["GET"])
@jwt_required()
def get_trades():
    """Get user's pending trades (sent and received)."""
    user_id = int(get_jwt_identity())

    service = CardService()
    trades = service.get_pending_trades(user_id)

    sent = []
    received = []

    for trade in trades:
        trade_dict = trade.to_dict()

        # Add user info
        sender = User.query.get(trade.sender_id)
        receiver = User.query.get(trade.receiver_id)
        trade_dict["sender_name"] = sender.first_name if sender else None
        trade_dict["receiver_name"] = receiver.first_name if receiver else None

        if trade.sender_id == user_id:
            sent.append(trade_dict)
        else:
            received.append(trade_dict)

    return success_response(
        {
            "sent": sent,
            "received": received,
        }
    )


@api_bp.route("/trades/create", methods=["POST"])
@jwt_required()
def create_trade():
    """
    Create a trade offer (supports single or multiple cards).

    Request body:
    {
        "receiver_id": 123,
        // Single card (backward compatible):
        "sender_card_id": 1,
        "receiver_card_id": 2,  // optional, for exchange
        // OR Multiple cards:
        "sender_card_ids": [1, 2, 3],
        "receiver_card_ids": [4, 5],  // optional, for exchange
        "message": "Trade message"  // optional
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    receiver_id = data.get("receiver_id")
    # Single card support (backward compatible)
    sender_card_id = data.get("sender_card_id")
    receiver_card_id = data.get("receiver_card_id")
    # Multi-card support
    sender_card_ids = data.get("sender_card_ids")
    receiver_card_ids = data.get("receiver_card_ids")
    message = data.get("message")

    # Validate: need either sender_card_id or sender_card_ids
    if not receiver_id or (not sender_card_id and not sender_card_ids):
        return validation_error(
            {"error": "receiver_id and sender_card_id(s) are required"}
        )

    service = CardService()
    result = service.create_trade_offer(
        sender_id=user_id,
        receiver_id=receiver_id,
        sender_card_id=sender_card_id,
        receiver_card_id=receiver_card_id,
        message=message,
        sender_card_ids=sender_card_ids,
        receiver_card_ids=receiver_card_ids,
    )

    if not result["success"]:
        error_messages = {
            "not_friends": "Вы можете обмениваться только с друзьями",
            "sender_card_invalid": "Одна или несколько ваших карт недоступны для обмена",
            "receiver_card_invalid": "Одна или несколько карт получателя недоступны",
            "no_sender_cards": "Не выбрано ни одной карты для обмена",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    # Send notification to receiver
    try:
        sender = User.query.get(user_id)
        receiver = User.query.get(receiver_id)
        if sender and receiver and receiver.telegram_id:
            sender_name = sender.first_name or sender.username or "Пользователь"
            # Count sender cards
            cards_count = len(sender_card_ids) if sender_card_ids else 1
            # Is gift if no receiver cards requested
            is_gift = not receiver_card_id and not receiver_card_ids

            notify_trade_received(
                receiver_telegram_id=receiver.telegram_id,
                sender_name=sender_name,
                cards_count=cards_count,
                is_gift=is_gift,
            )
    except Exception as e:
        # Don't fail the trade if notification fails
        import logging

        logging.getLogger(__name__).warning(f"Failed to send trade notification: {e}")

    return success_response(
        {
            "message": "Предложение обмена отправлено!",
            "trade": result["trade"],
        }
    )


@api_bp.route("/trades/<int:trade_id>/accept", methods=["POST"])
@jwt_required()
def accept_trade(trade_id: int):
    """Accept a trade offer."""
    user_id = int(get_jwt_identity())

    service = CardService()
    result = service.accept_trade(user_id, trade_id)

    if not result["success"]:
        return not_found("Предложение не найдено")

    return success_response(
        {
            "message": "Обмен завершён!",
            "trade": result["trade"],
        }
    )


@api_bp.route("/trades/<int:trade_id>/reject", methods=["POST"])
@jwt_required()
def reject_trade(trade_id: int):
    """Reject a trade offer."""
    user_id = int(get_jwt_identity())

    service = CardService()
    result = service.reject_trade(user_id, trade_id)

    if not result["success"]:
        return not_found("Предложение не найдено")

    return success_response({"message": "Предложение отклонено"})


@api_bp.route("/trades/<int:trade_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_trade(trade_id: int):
    """Cancel a trade offer (sender only)."""
    user_id = int(get_jwt_identity())

    trade = CardTrade.query.filter_by(
        id=trade_id, sender_id=user_id, status="pending"
    ).first()

    if not trade:
        return not_found("Предложение не найдено")

    trade.status = "cancelled"
    db.session.commit()

    return success_response({"message": "Предложение отменено"})


# ============ Friend's Cards (for trading) ============


@api_bp.route("/friends/<int:friend_id>/cards", methods=["GET"])
@jwt_required()
def get_friend_cards(friend_id: int):
    """Get friend's tradeable cards."""
    user_id = int(get_jwt_identity())

    # Check if they are friends
    is_friend = Friendship.query.filter(
        (
            (Friendship.user_id == user_id) & (Friendship.friend_id == friend_id)
            | (Friendship.user_id == friend_id) & (Friendship.friend_id == user_id)
        )
        & (Friendship.status == "accepted")
    ).first()

    if not is_friend:
        return validation_error({"error": "Вы не являетесь друзьями"})

    # Get friend's tradeable cards
    cards = UserCard.query.filter_by(
        user_id=friend_id,
        is_tradeable=True,
        is_destroyed=False,
    ).all()

    lang = get_lang()
    return success_response(
        {
            "cards": [c.to_dict(lang) for c in cards],
            "total": len(cards),
        }
    )


# ============ Genre Unlocking ============


@api_bp.route("/genres/unlocked", methods=["GET"])
@jwt_required()
def get_unlocked_genres():
    """Get user's unlocked genres and unlock availability."""
    user_id = int(get_jwt_identity())

    service = CardService()
    unlocked = service.get_unlocked_genres(user_id)
    unlock_info = service.check_genre_unlock(user_id)

    return success_response(
        {
            "unlocked_genres": unlocked,
            "unlock_available": unlock_info,
        }
    )


@api_bp.route("/genres/select", methods=["POST"])
@jwt_required()
def select_genre_unlock():
    """
    Unlock a new genre.

    Request body:
    {
        "genre": "scifi"
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    genre = data.get("genre")
    if not genre:
        return validation_error({"genre": "Genre is required"})

    service = CardService()
    result = service.unlock_genre(user_id, genre)

    if not result["success"]:
        error_messages = {
            "invalid_genre": "Неизвестный жанр",
            "already_unlocked": "Жанр уже разблокирован",
            "max_genres_reached": "Достигнут максимум жанров для вашего уровня",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response(result)


# ============ Card Leveling ============


@api_bp.route("/cards/<int:card_id>/add-xp", methods=["POST"])
@jwt_required()
def add_card_xp(card_id: int):
    """
    Add XP to a card (admin/testing endpoint).

    Request body:
    {
        "amount": 50
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    amount = data.get("amount", 10)
    if amount <= 0:
        return validation_error({"amount": "Amount must be positive"})

    service = CardService()
    result = service.add_card_xp(card_id, user_id, amount, lang=get_lang())

    if not result["success"]:
        return validation_error({"error": result["error"]})

    return success_response(result)


# ============ Companion System ============


@api_bp.route("/cards/<int:card_id>/companion", methods=["POST"])
@jwt_required()
def set_companion(card_id: int):
    """Set a card as the active companion."""
    user_id = int(get_jwt_identity())

    service = CardService()
    result = service.set_companion(user_id, card_id, lang=get_lang())

    if not result["success"]:
        error_messages = {
            "card_not_found": "Карта не найдена",
            "card_destroyed": "Карта уничтожена",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response(result)


@api_bp.route("/companion", methods=["GET"])
@jwt_required()
def get_companion():
    """Get the user's active companion card."""
    user_id = int(get_jwt_identity())

    service = CardService()
    companion = service.get_companion(user_id)

    if not companion:
        return success_response({"companion": None})

    return success_response({"companion": companion.to_dict(get_lang())})


@api_bp.route("/companion/remove", methods=["POST"])
@jwt_required()
def remove_companion():
    """Remove the active companion."""
    user_id = int(get_jwt_identity())

    service = CardService()
    result = service.remove_companion(user_id)

    return success_response(result)


# ============ Showcase System ============


@api_bp.route("/cards/<int:card_id>/showcase", methods=["POST"])
@jwt_required()
def set_showcase(card_id: int):
    """
    Set a card in a showcase slot.

    Request body:
    {
        "slot": 1  // 1, 2, or 3
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    slot = data.get("slot")
    if slot not in (1, 2, 3):
        return validation_error({"slot": "Slot must be 1, 2, or 3"})

    service = CardService()
    result = service.set_showcase(user_id, card_id, slot, lang=get_lang())

    if not result["success"]:
        return validation_error({"error": result["error"]})

    return success_response(result)


@api_bp.route("/showcase", methods=["GET"])
@jwt_required()
def get_showcase():
    """Get user's showcase cards (3 slots)."""
    user_id = int(get_jwt_identity())

    service = CardService()
    slots = service.get_showcase_cards(user_id, lang=get_lang())

    return success_response({"slots": slots})


@api_bp.route("/showcase/remove", methods=["POST"])
@jwt_required()
def remove_showcase():
    """
    Remove a card from a showcase slot.

    Request body:
    {
        "slot": 1
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    slot = data.get("slot")
    if slot not in (1, 2, 3):
        return validation_error({"slot": "Slot must be 1, 2, or 3"})

    service = CardService()
    result = service.remove_showcase(user_id, slot)

    return success_response(result)


# ============ Campaign Energy ============


@api_bp.route("/energy", methods=["GET"])
@jwt_required()
def get_energy():
    """Get user's campaign energy."""
    user_id = int(get_jwt_identity())

    service = CardService()
    energy = service.get_energy(user_id)

    return success_response(energy)


# ============ Friend Profile & Ranking ============


@api_bp.route("/friends/<int:friend_id>/profile", methods=["GET"])
@jwt_required()
def get_friend_profile(friend_id: int):
    """Get friend's profile with showcase, level, and deck power."""
    user_id = int(get_jwt_identity())

    # Verify friendship
    is_friend = Friendship.query.filter(
        (
            (Friendship.user_id == user_id) & (Friendship.friend_id == friend_id)
            | (Friendship.user_id == friend_id) & (Friendship.friend_id == user_id)
        )
        & (Friendship.status == "accepted")
    ).first()

    if not is_friend:
        return validation_error({"error": "not_friends"})

    friend = User.query.get(friend_id)
    if not friend:
        return not_found("User not found")

    service = CardService()

    # Get friend's deck for power calculation
    deck = service.get_user_deck(friend_id)
    deck_power = sum(c.hp + c.attack for c in deck)

    # Get showcase
    lang = get_lang()
    showcase = service.get_showcase_cards(friend_id, lang=lang)
    return success_response(
        {
            "user_id": friend_id,
            "username": friend.username,
            "first_name": friend.first_name,
            "level": friend.level,
            "deck_power": deck_power,
            "showcase": showcase,
            "deck": [c.to_dict(lang) for c in deck],
        }
    )


@api_bp.route("/friends/ranking", methods=["GET"])
@jwt_required()
def get_friends_ranking():
    """Get friends sorted by total deck power."""
    user_id = int(get_jwt_identity())

    service = CardService()
    friends = service.get_friends(user_id)

    # Calculate deck power for each friend
    ranking = []
    for friend_info in friends:
        fid = friend_info["friend_id"]
        friend_user = User.query.get(fid)
        if not friend_user:
            continue

        deck = service.get_user_deck(fid)
        deck_power = sum(c.hp + c.attack for c in deck)

        ranking.append(
            {
                "user_id": fid,
                "username": friend_user.username,
                "first_name": friend_user.first_name,
                "level": friend_user.level,
                "deck_power": deck_power,
                "cards_count": UserCard.query.filter_by(
                    user_id=fid, is_destroyed=False
                ).count(),
            }
        )

    # Add current user
    current_user = User.query.get(user_id)
    if current_user:
        my_deck = service.get_user_deck(user_id)
        my_power = sum(c.hp + c.attack for c in my_deck)
        ranking.append(
            {
                "user_id": user_id,
                "username": current_user.username,
                "first_name": current_user.first_name,
                "level": current_user.level,
                "deck_power": my_power,
                "cards_count": UserCard.query.filter_by(
                    user_id=user_id, is_destroyed=False
                ).count(),
                "is_me": True,
            }
        )

    # Sort by deck power descending
    ranking.sort(key=lambda x: x["deck_power"], reverse=True)

    # Add rank
    for i, entry in enumerate(ranking):
        entry["rank"] = i + 1

    return success_response({"ranking": ranking})


@api_bp.route("/admin/remove-friend", methods=["POST"])
@admin_required
def admin_remove_friend():
    """
    Remove a friendship between two users (admin only).
    Required JSON: {"user_id": 1, "friend_id": 2}
    """
    data = request.get_json()

    user_id = data.get("user_id")
    friend_id = data.get("friend_id")

    if not user_id or not friend_id:
        return validation_error("user_id и friend_id обязательны")

    service = CardService()
    result = service.remove_friend(user_id, friend_id)

    if "error" in result:
        return not_found("Дружба не найдена")

    return success_response({"message": "Дружба удалена"})
