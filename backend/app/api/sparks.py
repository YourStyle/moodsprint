"""Sparks currency API endpoints."""

import os

import requests
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from app.api import api_bp
from app.models import SPARKS_PACKS, SparksTransaction, TonDeposit, User
from app.utils.response import error_response, success_response


def create_invoice_link(
    title: str,
    description: str,
    payload: str,
    price_stars: int,
) -> str | None:
    """Create a Telegram Stars invoice link using Bot API."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return None

    url = f"https://api.telegram.org/bot{bot_token}/createInvoiceLink"
    response = requests.post(
        url,
        json={
            "title": title,
            "description": description,
            "payload": payload,
            "currency": "XTR",  # Telegram Stars
            "prices": [{"label": title, "amount": price_stars}],
        },
        timeout=10,
    )

    if response.ok:
        data = response.json()
        if data.get("ok"):
            return data.get("result")

    return None


@api_bp.route("/sparks/balance", methods=["GET"])
@jwt_required()
def get_user_sparks_balance():
    """Get user's sparks balance and recent transactions."""
    user_id = int(get_jwt_identity())
    current_user = User.query.get(user_id)
    if not current_user:
        return error_response("User not found", 404)

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
@jwt_required()
def get_sparks_packs():
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


@api_bp.route("/sparks/buy", methods=["POST"])
@jwt_required()
def buy_sparks_pack():
    """Create invoice link for buying sparks pack with Telegram Stars."""
    user_id = int(get_jwt_identity())
    current_user = User.query.get(user_id)
    if not current_user:
        return error_response("User not found", 404)

    data = request.get_json() or {}
    pack_id = data.get("pack_id")

    if not pack_id or pack_id not in SPARKS_PACKS:
        return error_response("Invalid pack_id", 400)

    pack = SPARKS_PACKS[pack_id]
    sparks_amount = pack["sparks"]
    price_stars = pack["price_stars"]

    # Create invoice link
    invoice_url = create_invoice_link(
        title=f"{sparks_amount} Sparks",
        description=f"Покупка {sparks_amount} Sparks за {price_stars} Stars",
        payload=f"sparks_purchase_{pack_id}_{user_id}",
        price_stars=price_stars,
    )

    if not invoice_url:
        return error_response("Failed to create invoice", 500)

    return success_response({"invoice_url": invoice_url})


@api_bp.route("/sparks/wallet", methods=["POST"])
@jwt_required()
def save_wallet_address():
    """Save user's TON wallet address."""
    user_id = int(get_jwt_identity())
    current_user = User.query.get(user_id)
    if not current_user:
        return error_response("User not found", 404)

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
@jwt_required()
def disconnect_wallet():
    """Disconnect user's TON wallet."""
    user_id = int(get_jwt_identity())
    current_user = User.query.get(user_id)
    if not current_user:
        return error_response("User not found", 404)

    current_user.ton_wallet_address = None
    db.session.commit()

    return success_response({"message": "Wallet disconnected"})


@api_bp.route("/sparks/deposit-info", methods=["GET"])
@jwt_required()
def get_deposit_info():
    """Get information for making a TON deposit."""
    user_id = int(get_jwt_identity())
    current_user = User.query.get(user_id)
    if not current_user:
        return error_response("User not found", 404)

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
@jwt_required()
def get_deposits():
    """Get user's TON deposit history."""
    user_id = int(get_jwt_identity())
    current_user = User.query.get(user_id)
    if not current_user:
        return error_response("User not found", 404)

    deposits = (
        TonDeposit.query.filter_by(user_id=current_user.id)
        .order_by(TonDeposit.created_at.desc())
        .limit(20)
        .all()
    )

    return success_response({"deposits": [d.to_dict() for d in deposits]})


@api_bp.route("/sparks/transactions", methods=["GET"])
@jwt_required()
def get_sparks_transactions():
    """Get user's sparks transaction history."""
    user_id = int(get_jwt_identity())
    current_user = User.query.get(user_id)
    if not current_user:
        return error_response("User not found", 404)

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
