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
from app.utils import not_found, success_response, validation_error

# Healing requirements: tasks needed per heal
# First heal = 3 tasks, second = 5 tasks (cumulative)
HEAL_REQUIREMENTS = [3, 5]  # tasks required for 1st, 2nd heal

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

    return success_response(
        {
            "cards": [c.to_dict() for c in cards],
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

    return success_response({"card": card.to_dict()})


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


@api_bp.route("/deck", methods=["GET"])
@jwt_required()
def get_deck():
    """Get user's active battle deck."""
    user_id = int(get_jwt_identity())

    service = CardService()
    deck = service.get_user_deck(user_id)

    # Calculate deck stats
    total_hp = sum(c.hp for c in deck)
    total_attack = sum(c.attack for c in deck)
    genres = list(set(c.genre for c in deck))

    return success_response(
        {
            "deck": [c.to_dict() for c in deck],
            "size": len(deck),
            "max_size": 5,
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

    service = CardService()
    result = service.add_to_deck(user_id, card_id)

    if not result["success"]:
        error_messages = {
            "card_not_found": "Карта не найдена",
            "card_destroyed": "Карта уничтожена",
            "already_in_deck": "Карта уже в колоде",
            "deck_full": f"Колода полная (максимум {result.get('max_size', 5)} карт)",
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
    result = service.heal_card(card_id, user_id)

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
    genre = request.args.get("genre")

    query = CardTemplate.query.filter_by(is_active=True)
    if genre:
        query = query.filter_by(genre=genre)

    templates = query.all()

    return success_response(
        {
            "templates": [t.to_dict() for t in templates],
            "total": len(templates),
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

        # Give bonus card to the inviter (referrer)
        referrer_card = service.generate_referral_reward(referrer_id)
        if referrer_card:
            rewards["referrer_card"] = referrer_card.to_dict()

        # Give bonus card to the invitee (current user)
        invitee_card = service.generate_referral_reward(user_id)
        if invitee_card:
            rewards["invitee_card"] = invitee_card.to_dict()
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
    Create a trade offer.

    Request body:
    {
        "receiver_id": 123,
        "sender_card_id": 1,
        "receiver_card_id": 2,  // optional, for exchange
        "message": "Trade message"  // optional
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    receiver_id = data.get("receiver_id")
    sender_card_id = data.get("sender_card_id")
    receiver_card_id = data.get("receiver_card_id")
    message = data.get("message")

    if not receiver_id or not sender_card_id:
        return validation_error(
            {"error": "receiver_id and sender_card_id are required"}
        )

    service = CardService()
    result = service.create_trade_offer(
        user_id, receiver_id, sender_card_id, receiver_card_id, message
    )

    if not result["success"]:
        error_messages = {
            "not_friends": "Вы можете обмениваться только с друзьями",
            "sender_card_invalid": "Ваша карта недоступна для обмена",
            "receiver_card_invalid": "Карта получателя недоступна для обмена",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

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

    return success_response(
        {
            "cards": [c.to_dict() for c in cards],
            "total": len(cards),
        }
    )


@api_bp.route("/admin/remove-friend", methods=["POST"])
@jwt_required()
def admin_remove_friend():
    """
    Remove a friendship between two users (admin only for testing).
    Required JSON: {"user_id": 1, "friend_id": 2}
    """
    get_jwt_identity()  # Verify authenticated
    data = request.get_json()

    user_id = data.get("user_id")
    friend_id = data.get("friend_id")

    if not user_id or not friend_id:
        return validation_error("user_id и friend_id обязательны")

    # For testing: allow any authenticated user (in production, add admin check)
    service = CardService()
    result = service.remove_friend(user_id, friend_id)

    if "error" in result:
        return not_found("Дружба не найдена")

    return success_response({"message": "Дружба удалена"})
