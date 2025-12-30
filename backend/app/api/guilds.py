"""Guild system API endpoints."""

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api import api_bp
from app.services.guild_service import GuildService
from app.utils import not_found, success_response, validation_error

# ============ Guild Management ============


@api_bp.route("/guilds", methods=["GET"])
@jwt_required()
def get_guilds():
    """
    Get list of guilds.

    Query params:
    - page: page number (default 1)
    - per_page: items per page (default 20)
    - search: search by name (optional)
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search")

    service = GuildService()
    result = service.get_public_guilds(page=page, per_page=per_page, search=search)

    return success_response(result)


@api_bp.route("/guilds", methods=["POST"])
@jwt_required()
def create_guild():
    """
    Create a new guild.

    Request body:
    {
        "name": "Guild Name",
        "description": "Description",
        "emoji": "⚔️",
        "is_public": true
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    name = data.get("name")
    if not name:
        return validation_error({"name": "Название гильдии обязательно"})

    service = GuildService()
    result = service.create_guild(
        leader_id=user_id,
        name=name,
        description=data.get("description"),
        emoji=data.get("emoji"),
        is_public=data.get("is_public", True),
    )

    if "error" in result:
        error_messages = {
            "name_taken": "Гильдия с таким названием уже существует",
            "already_in_guild": "Вы уже состоите в гильдии",
            "invalid_name_length": "Название должно быть от 3 до 50 символов",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response(result)


@api_bp.route("/guilds/<int:guild_id>", methods=["GET"])
@jwt_required()
def get_guild(guild_id: int):
    """Get guild details."""
    user_id = int(get_jwt_identity())

    service = GuildService()
    result = service.get_guild_details(guild_id, user_id)

    if "error" in result:
        return not_found("Гильдия не найдена")

    return success_response(result)


@api_bp.route("/guilds/<int:guild_id>", methods=["PUT"])
@jwt_required()
def update_guild(guild_id: int):
    """
    Update guild settings (leader/officer only).

    Request body:
    {
        "name": "New Name",
        "description": "New description",
        "emoji": "🏰",
        "is_public": false
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    service = GuildService()
    result = service.update_guild(guild_id, user_id, data)

    if "error" in result:
        error_messages = {
            "guild_not_found": "Гильдия не найдена",
            "not_authorized": "Недостаточно прав",
            "name_taken": "Гильдия с таким названием уже существует",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response(result)


@api_bp.route("/guilds/my", methods=["GET"])
@jwt_required()
def get_my_guild():
    """Get current user's guild."""
    user_id = int(get_jwt_identity())

    service = GuildService()
    result = service.get_user_guild(user_id)

    if "error" in result:
        return success_response({"guild": None, "membership": None})

    return success_response(result)


# ============ Membership ============


@api_bp.route("/guilds/<int:guild_id>/join", methods=["POST"])
@jwt_required()
def join_guild(guild_id: int):
    """Join a public guild."""
    user_id = int(get_jwt_identity())

    service = GuildService()
    result = service.join_guild(user_id, guild_id)

    if "error" in result:
        error_messages = {
            "guild_not_found": "Гильдия не найдена",
            "already_in_guild": "Вы уже состоите в гильдии",
            "guild_full": "Гильдия переполнена",
            "not_public": "Гильдия закрыта для вступления",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response({"message": "Вы вступили в гильдию!", **result})


@api_bp.route("/guilds/leave", methods=["POST"])
@jwt_required()
def leave_guild():
    """Leave current guild."""
    user_id = int(get_jwt_identity())

    service = GuildService()
    result = service.leave_guild(user_id)

    if "error" in result:
        error_messages = {
            "not_in_guild": "Вы не состоите в гильдии",
            "leader_cannot_leave": (
                "Лидер не может покинуть гильдию. "
                "Передайте лидерство или распустите гильдию."
            ),
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response({"message": "Вы покинули гильдию"})


@api_bp.route("/guilds/<int:guild_id>/kick/<int:member_id>", methods=["POST"])
@jwt_required()
def kick_member(guild_id: int, member_id: int):
    """Kick a member from guild (leader/officer only)."""
    user_id = int(get_jwt_identity())

    service = GuildService()
    result = service.kick_member(guild_id, user_id, member_id)

    if "error" in result:
        error_messages = {
            "guild_not_found": "Гильдия не найдена",
            "not_authorized": "Недостаточно прав",
            "member_not_found": "Участник не найден",
            "cannot_kick_leader": "Нельзя исключить лидера",
            "cannot_kick_self": "Нельзя исключить себя",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response({"message": "Участник исключён"})


@api_bp.route("/guilds/<int:guild_id>/promote/<int:member_id>", methods=["POST"])
@jwt_required()
def promote_member(guild_id: int, member_id: int):
    """
    Promote a member (leader only).

    Request body:
    {
        "role": "officer"  // or "leader" to transfer leadership
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    role = data.get("role", "officer")

    service = GuildService()
    result = service.promote_member(guild_id, user_id, member_id, role)

    if "error" in result:
        error_messages = {
            "guild_not_found": "Гильдия не найдена",
            "not_authorized": "Недостаточно прав",
            "member_not_found": "Участник не найден",
            "invalid_role": "Некорректная роль",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response({"message": "Роль изменена", **result})


# ============ Invites ============


@api_bp.route("/guilds/<int:guild_id>/invite", methods=["POST"])
@jwt_required()
def invite_to_guild(guild_id: int):
    """
    Invite a user to guild (officer/leader only).

    Request body:
    {
        "user_id": 123
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    target_user_id = data.get("user_id")
    if not target_user_id:
        return validation_error({"user_id": "ID пользователя обязателен"})

    service = GuildService()
    result = service.invite_to_guild(guild_id, user_id, target_user_id)

    if "error" in result:
        error_messages = {
            "guild_not_found": "Гильдия не найдена",
            "not_authorized": "Недостаточно прав",
            "user_not_found": "Пользователь не найден",
            "already_in_guild": "Пользователь уже в гильдии",
            "invite_pending": "Приглашение уже отправлено",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response({"message": "Приглашение отправлено", **result})


@api_bp.route("/guilds/invites", methods=["GET"])
@jwt_required()
def get_invites():
    """Get pending guild invites for current user."""
    user_id = int(get_jwt_identity())

    service = GuildService()
    invites = service.get_pending_invites(user_id)

    return success_response({"invites": invites})


@api_bp.route("/guilds/invites/<int:invite_id>/accept", methods=["POST"])
@jwt_required()
def accept_invite(invite_id: int):
    """Accept a guild invite."""
    user_id = int(get_jwt_identity())

    service = GuildService()
    result = service.respond_to_invite(invite_id, user_id, accept=True)

    if "error" in result:
        error_messages = {
            "invite_not_found": "Приглашение не найдено",
            "already_in_guild": "Вы уже состоите в гильдии",
            "guild_full": "Гильдия переполнена",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response({"message": "Вы вступили в гильдию!", **result})


@api_bp.route("/guilds/invites/<int:invite_id>/reject", methods=["POST"])
@jwt_required()
def reject_invite(invite_id: int):
    """Reject a guild invite."""
    user_id = int(get_jwt_identity())

    service = GuildService()
    result = service.respond_to_invite(invite_id, user_id, accept=False)

    if "error" in result:
        return not_found("Приглашение не найдено")

    return success_response({"message": "Приглашение отклонено"})


# ============ Raids ============


@api_bp.route("/guilds/<int:guild_id>/raids", methods=["GET"])
@jwt_required()
def get_guild_raids(guild_id: int):
    """Get guild's raids (active and recent completed)."""
    user_id = int(get_jwt_identity())

    service = GuildService()
    result = service.get_guild_raids(guild_id, user_id)

    if "error" in result:
        error_messages = {
            "guild_not_found": "Гильдия не найдена",
            "not_member": "Вы не являетесь членом гильдии",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response(result)


@api_bp.route("/guilds/<int:guild_id>/raids", methods=["POST"])
@jwt_required()
def start_raid(guild_id: int):
    """
    Start a new raid (leader/officer only).

    Request body (optional):
    {
        "monster_id": 1  // Use specific monster, or auto-select
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    monster_id = data.get("monster_id")

    service = GuildService()
    result = service.start_raid(guild_id, user_id, monster_id)

    if "error" in result:
        error_messages = {
            "guild_not_found": "Гильдия не найдена",
            "not_authorized": "Недостаточно прав",
            "raid_active": "Уже есть активный рейд",
            "monster_not_found": "Монстр не найден",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response({"message": "Рейд начат!", **result})


@api_bp.route("/raids/<int:raid_id>", methods=["GET"])
@jwt_required()
def get_raid(raid_id: int):
    """Get raid details with leaderboard."""
    user_id = int(get_jwt_identity())

    service = GuildService()
    result = service.get_raid_details(raid_id, user_id)

    if "error" in result:
        return not_found("Рейд не найден")

    return success_response(result)


@api_bp.route("/raids/<int:raid_id>/attack", methods=["POST"])
@jwt_required()
def attack_raid(raid_id: int):
    """
    Attack raid boss.

    Uses player's deck to calculate damage.
    Limited to 3 attacks per day per player.
    """
    user_id = int(get_jwt_identity())

    service = GuildService()
    result = service.attack_raid(raid_id, user_id)

    if "error" in result:
        error_messages = {
            "raid_not_found": "Рейд не найден",
            "raid_not_active": "Рейд неактивен",
            "not_member": "Вы не являетесь членом гильдии",
            "no_deck": "У вас нет карт в колоде",
            "daily_limit": "Достигнут дневной лимит атак (3/день)",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response(result)


# ============ Leaderboard ============


@api_bp.route("/guilds/leaderboard", methods=["GET"])
@jwt_required()
def get_guild_leaderboard():
    """
    Get guild leaderboard.

    Query params:
    - sort_by: "level" (default) or "raids_won"
    - page: page number
    - per_page: items per page
    """
    sort_by = request.args.get("sort_by", "level")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    service = GuildService()
    result = service.get_leaderboard(sort_by=sort_by, page=page, per_page=per_page)

    return success_response(result)
