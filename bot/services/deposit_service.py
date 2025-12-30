"""TON deposit monitoring service."""

import logging
from dataclasses import dataclass
from decimal import Decimal

import httpx
from config import config
from database import async_session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Sparks packs configuration (must match backend)
SPARKS_PACKS = {
    "starter": {"sparks": 100, "price_ton": 0.1},
    "basic": {"sparks": 500, "price_ton": 0.45},
    "standard": {"sparks": 1000, "price_ton": 0.8},
    "premium": {"sparks": 2500, "price_ton": 1.75},
    "elite": {"sparks": 5000, "price_ton": 3.0},
    "ultimate": {"sparks": 10000, "price_ton": 5.0},
}


def get_sparks_for_ton(ton_amount: float) -> int:
    """Calculate sparks to credit for TON deposit amount."""
    selected_pack = None
    for pack in sorted(SPARKS_PACKS.values(), key=lambda x: x["price_ton"]):
        if pack["price_ton"] <= ton_amount:
            selected_pack = pack
        else:
            break

    if selected_pack:
        return selected_pack["sparks"]

    # If less than minimum pack, give proportional amount
    # Base rate: 1000 sparks per 0.8 TON = 1250 sparks per TON
    return int(ton_amount * 1250)


@dataclass
class Transaction:
    """Parsed TON transaction."""

    hash: str
    sender_address: str
    amount_nano: int
    memo: str | None


class DepositService:
    """Service for monitoring TON deposits."""

    def __init__(self):
        self.deposit_address = config.TON_DEPOSIT_ADDRESS
        self.tonapi_key = config.TONAPI_KEY

    async def get_transactions(self, limit: int = 100) -> list[dict] | None:
        """Fetch transactions from TONAPI."""
        if not self.tonapi_key:
            logger.warning("TONAPI_KEY not configured, skipping deposit check")
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://tonapi.io/v2/blockchain/accounts/{self.deposit_address}/transactions",
                    params={"limit": limit},
                    headers={"Authorization": f"Bearer {self.tonapi_key}"},
                    timeout=30.0,
                )

            if response.status_code != 200:
                logger.error(f"TONAPI error: {response.status_code} - {response.text}")
                return None

            data = response.json()
            return data.get("transactions", [])

        except Exception as e:
            logger.error(f"Error fetching transactions: {e}")
            return None

    async def is_deposit_processed(self, tx_hash: str) -> bool:
        """Check if a deposit was already processed."""
        async with async_session() as session:
            result = await session.execute(
                text("SELECT id FROM ton_deposits WHERE tx_hash = :tx_hash"),
                {"tx_hash": tx_hash},
            )
            return result.fetchone() is not None

    async def record_deposit(
        self,
        tx_hash: str,
        sender_address: str,
        amount_nano: int,
        user_id: int | None,
        sparks_credited: int | None,
        memo: str | None,
        status: str = "pending",
    ):
        """Record a TON deposit in database."""
        amount_ton = Decimal(amount_nano) / Decimal(10**9)

        async with async_session() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO ton_deposits
                        (user_id, tx_hash, sender_address, amount_nano, amount_ton,
                         memo, status, sparks_credited, created_at, processed_at)
                    VALUES
                        (:user_id, :tx_hash, :sender_address, :amount_nano, :amount_ton,
                         :memo, :status, :sparks_credited, NOW(),
                         CASE WHEN :status = 'processed' THEN NOW() ELSE NULL END)
                    ON CONFLICT (tx_hash) DO NOTHING
                """
                ),
                {
                    "user_id": user_id,
                    "tx_hash": tx_hash,
                    "sender_address": sender_address,
                    "amount_nano": amount_nano,
                    "amount_ton": amount_ton,
                    "memo": memo,
                    "status": status,
                    "sparks_credited": sparks_credited,
                },
            )
            await session.commit()

    async def credit_user_sparks(self, user_id: int, amount: int, tx_hash: str) -> bool:
        """Credit Sparks to user and record transaction."""
        async with async_session() as session:
            # Update user's Sparks balance
            await session.execute(
                text(
                    """
                    UPDATE users
                    SET sparks = sparks + :amount
                    WHERE id = :user_id
                """
                ),
                {"user_id": user_id, "amount": amount},
            )

            # Record Sparks transaction
            await session.execute(
                text(
                    """
                    INSERT INTO sparks_transactions
                        (user_id, amount, type, reference_type, reference_id,
                         description, created_at)
                    VALUES
                        (:user_id, :amount, 'ton_deposit', 'ton_deposit', NULL,
                         :description, NOW())
                """
                ),
                {
                    "user_id": user_id,
                    "amount": amount,
                    "description": f"Пополнение TON: +{amount} Sparks",
                },
            )

            await session.commit()
            return True

    async def get_user_by_id(self, user_id: int) -> dict | None:
        """Get user by ID."""
        async with async_session() as session:
            result = await session.execute(
                text("SELECT id, telegram_id, first_name FROM users WHERE id = :uid"),
                {"uid": user_id},
            )
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None

    def parse_transaction(self, tx: dict) -> Transaction | None:
        """Parse a transaction from TONAPI response."""
        if not tx.get("in_msg"):
            return None

        if not tx.get("success"):
            return None

        action = tx["in_msg"]
        if not action:
            return None

        # Check if it's a text comment transaction
        if action.get("decoded_op_name") != "text_comment":
            return None

        if not action.get("destination"):
            return None

        if not action.get("decoded_body"):
            return None

        memo = action["decoded_body"].get("text")
        if not memo:
            return None

        return Transaction(
            hash=tx["hash"],
            sender_address=action["source"]["address"],
            amount_nano=int(action["value"]),
            memo=memo.strip(),
        )

    async def process_deposits(self) -> int:
        """
        Check for new deposits and process them.

        Returns number of processed deposits.
        """
        transactions = await self.get_transactions()
        if not transactions:
            return 0

        processed = 0

        for tx_data in transactions:
            tx = self.parse_transaction(tx_data)
            if not tx:
                continue

            # Skip if already processed
            if await self.is_deposit_processed(tx.hash):
                continue

            # Minimum deposit: 0.01 TON
            min_amount_nano = int(0.01 * 10**9)
            if tx.amount_nano < min_amount_nano:
                await self.record_deposit(
                    tx_hash=tx.hash,
                    sender_address=tx.sender_address,
                    amount_nano=tx.amount_nano,
                    user_id=None,
                    sparks_credited=None,
                    memo=tx.memo,
                    status="failed",
                )
                logger.info(f"Deposit too small: {tx.hash}")
                continue

            # Try to parse user ID from memo
            try:
                user_id = int(tx.memo)
            except (ValueError, TypeError):
                await self.record_deposit(
                    tx_hash=tx.hash,
                    sender_address=tx.sender_address,
                    amount_nano=tx.amount_nano,
                    user_id=None,
                    sparks_credited=None,
                    memo=tx.memo,
                    status="failed",
                )
                logger.info(f"Invalid memo (not user ID): {tx.hash} - {tx.memo}")
                continue

            # Check if user exists
            user = await self.get_user_by_id(user_id)
            if not user:
                await self.record_deposit(
                    tx_hash=tx.hash,
                    sender_address=tx.sender_address,
                    amount_nano=tx.amount_nano,
                    user_id=None,
                    sparks_credited=None,
                    memo=tx.memo,
                    status="failed",
                )
                logger.info(f"User not found: {tx.hash} - user_id={user_id}")
                continue

            # Calculate Sparks to credit
            ton_amount = tx.amount_nano / 10**9
            sparks = get_sparks_for_ton(ton_amount)

            # Credit user
            await self.credit_user_sparks(user["id"], sparks, tx.hash)

            # Record successful deposit
            await self.record_deposit(
                tx_hash=tx.hash,
                sender_address=tx.sender_address,
                amount_nano=tx.amount_nano,
                user_id=user["id"],
                sparks_credited=sparks,
                memo=tx.memo,
                status="processed",
            )

            logger.info(
                f"Deposit processed: {tx.hash} - "
                f"user={user['id']}, ton={ton_amount:.2f}, sparks={sparks}"
            )
            processed += 1

        return processed


# Singleton instance
deposit_service = DepositService()


async def check_deposits():
    """Scheduled job to check for new deposits."""
    try:
        processed = await deposit_service.process_deposits()
        if processed > 0:
            logger.info(f"Processed {processed} new deposits")
    except Exception as e:
        logger.error(f"Error checking deposits: {e}")
