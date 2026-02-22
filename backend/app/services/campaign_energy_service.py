"""Campaign energy service — extracted from card_service.py."""

import logging

from app import db
from app.models.user_profile import UserProfile

logger = logging.getLogger(__name__)


class CampaignEnergyService:
    def get_energy(self, user_id: int) -> dict:
        """Get user's campaign energy."""
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            return {"energy": 3, "max_energy": 5}

        return {
            "energy": (
                profile.campaign_energy if profile.campaign_energy is not None else 3
            ),
            "max_energy": (
                profile.max_campaign_energy
                if profile.max_campaign_energy is not None
                else 5
            ),
        }

    def add_energy(self, user_id: int, amount: int = 1) -> dict:
        """Add campaign energy (capped at max)."""
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            return {"success": False, "error": "profile_not_found"}

        current = profile.campaign_energy if profile.campaign_energy is not None else 3
        max_e = (
            profile.max_campaign_energy
            if profile.max_campaign_energy is not None
            else 5
        )
        profile.campaign_energy = min(current + amount, max_e)
        db.session.commit()

        return {
            "success": True,
            "energy": profile.campaign_energy,
            "max_energy": max_e,
        }

    def increase_max_energy(self, user_id: int, amount: int = 1) -> dict:
        """Increase max campaign energy limit and fill current to new max."""
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            return {"success": False, "error": "profile_not_found"}

        old_max = profile.max_campaign_energy or 5
        new_max = old_max + amount
        profile.max_campaign_energy = new_max
        profile.campaign_energy = new_max
        db.session.commit()

        return {
            "success": True,
            "old_max": old_max,
            "new_max": new_max,
            "energy": new_max,
        }

    def spend_energy(self, user_id: int) -> dict:
        """Spend 1 campaign energy. Returns success/fail."""
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            return {"success": False, "error": "no_energy"}

        current = profile.campaign_energy if profile.campaign_energy is not None else 3
        if current <= 0:
            max_e = (
                profile.max_campaign_energy
                if profile.max_campaign_energy is not None
                else 5
            )
            return {
                "success": False,
                "error": "no_energy",
                "energy": 0,
                "max_energy": max_e,
            }

        profile.campaign_energy = current - 1
        db.session.commit()

        logger.info(
            f"Energy spent: user={user_id}, "
            f"energy={profile.campaign_energy}/{profile.max_campaign_energy or 5}"
        )

        return {
            "success": True,
            "energy": profile.campaign_energy,
            "max_energy": profile.max_campaign_energy or 5,
        }
