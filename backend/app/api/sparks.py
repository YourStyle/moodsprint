"""Sparks currency API endpoints."""

from flask import request

from app import db
from app.api import api_bp
from app.models import SPARKS_PACKS, SparksTransaction, TonDeposit, User
from app.utils.auth import get_current_user
from app.utils.response import error_response, success_response


@api_bp.route("/sparks/balance", methods=["GET"])
@get_current_user
def get_sparks_balance(current_user: User):
    """Get user's sparks balance and recent transactions."""
    # Get recent transactions
    transactions = (
        SparksTransaction.query.filter_by(user_id=current_user.id)
        .order_by(SparksTransaction.created_at.desc())
        .limit(10)
        .all()
    )

    return success_response(
        {
            "sparks": current_user.sparks,
            "recent_transactions": [t.to_dict() for t in transactions],
        }
    )


@api_bp.route("/sparks/packs", methods=["GET"])
@get_current_user
def get_sparks_packs(current_user: User):
    """Get available sparks packs for purchase."""
    packs = []
    for pack_id, pack_data in SPARKS_PACKS.items():
        packs.append(
            {
                "id": pack_id,
                "sparks": pack_data["sparks"],
                "price_stars": pack_data["price_stars"],
                "price_ton": pack_data["price_ton"],
            }
        )

    # Sort by sparks amount
    packs.sort(key=lambda x: x["sparks"])

    return success_response({"packs": packs})


@api_bp.route("/sparks/wallet", methods=["POST"])
@get_current_user
def save_wallet_address(current_user: User):
    """Save user's TON wallet address."""
    data = request.get_json()
    wallet_address = data.get("wallet_address")

    if not wallet_address:
        return error_response("wallet_address is required", 400)

    # Basic validation for TON address format
    if len(wallet_address) < 40 or len(wallet_address) > 50:
        return error_response("Invalid wallet address format", 400)

    current_user.ton_wallet_address = wallet_address
    db.session.commit()

    return success_response(
        {
            "wallet_address": current_user.ton_wallet_address,
            "message": "Wallet address saved",
        }
    )


@api_bp.route("/sparks/wallet", methods=["DELETE"])
@get_current_user
def disconnect_wallet(current_user: User):
    """Disconnect user's TON wallet."""
    current_user.ton_wallet_address = None
    db.session.commit()

    return success_response({"message": "Wallet disconnected"})


@api_bp.route("/sparks/deposit-info", methods=["GET"])
@get_current_user
def get_deposit_info(current_user: User):
    """Get information for making a TON deposit."""
    import os

    deposit_address = os.environ.get("TON_DEPOSIT_ADDRESS")

    if not deposit_address:
        return error_response("TON deposits not configured", 503)

    return success_response(
        {
            "deposit_address": deposit_address,
            "memo": str(current_user.id),  # User should include this as memo
            "instructions": (
                "Отправьте TON на указанный адрес с вашим ID в комментарии. "
                "Sparks будут начислены автоматически в течение нескольких минут."
            ),
            "rates": {pack_id: p["price_ton"] for pack_id, p in SPARKS_PACKS.items()},
        }
    )


@api_bp.route("/sparks/deposits", methods=["GET"])
@get_current_user
def get_deposits(current_user: User):
    """Get user's TON deposit history."""
    deposits = (
        TonDeposit.query.filter_by(user_id=current_user.id)
        .order_by(TonDeposit.created_at.desc())
        .limit(20)
        .all()
    )

    return success_response({"deposits": [d.to_dict() for d in deposits]})


@api_bp.route("/sparks/transactions", methods=["GET"])
@get_current_user
def get_transactions(current_user: User):
    """Get user's sparks transaction history."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)  # Limit max per page

    transactions = (
        SparksTransaction.query.filter_by(user_id=current_user.id)
        .order_by(SparksTransaction.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return success_response(
        {
            "transactions": [t.to_dict() for t in transactions.items],
            "total": transactions.total,
            "pages": transactions.pages,
            "current_page": page,
        }
    )


def credit_sparks(
    user_id: int,
    amount: int,
    transaction_type: str,
    description: str = None,
    reference_type: str = None,
    reference_id: int = None,
) -> SparksTransaction:
    """Helper function to credit sparks to a user."""
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    user.add_sparks(amount)

    transaction = SparksTransaction(
        user_id=user_id,
        amount=amount,
        type=transaction_type,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.session.add(transaction)
    db.session.commit()

    return transaction


def debit_sparks(
    user_id: int,
    amount: int,
    transaction_type: str,
    description: str = None,
    reference_type: str = None,
    reference_id: int = None,
) -> SparksTransaction | None:
    """Helper function to debit sparks from a user. Returns None if insufficient."""
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    if not user.spend_sparks(amount):
        return None

    transaction = SparksTransaction(
        user_id=user_id,
        amount=-amount,  # Negative for spending
        type=transaction_type,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.session.add(transaction)
    db.session.commit()

    return transaction
