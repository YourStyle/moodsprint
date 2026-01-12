"""Card-related async tasks."""

import structlog

from app.celery_app import celery

logger = structlog.get_logger()


@celery.task(bind=True, max_retries=3, default_retry_delay=120)
def generate_card_image_async(self, card_id: int):
    """Generate card image using AI asynchronously."""
    from app import db
    from app.models import Card
    from app.services.card_service import CardService

    try:
        logger.info("generate_card_image_started", card_id=card_id)

        card = db.session.get(Card, card_id)
        if not card:
            logger.warning("card_not_found", card_id=card_id)
            return {"success": False, "error": "Card not found"}

        service = CardService()
        image_url = service.generate_image_for_card(card)

        if image_url:
            card.image_url = image_url
            db.session.commit()
            logger.info(
                "generate_card_image_completed", card_id=card_id, image_url=image_url
            )
            return {"success": True, "image_url": image_url}
        else:
            logger.warning("generate_card_image_no_result", card_id=card_id)
            return {"success": False, "error": "Image generation returned no result"}

    except Exception as e:
        logger.error("generate_card_image_failed", card_id=card_id, error=str(e))
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=2, default_retry_delay=60)
def regenerate_card_stats_async(self, card_id: int):
    """Regenerate card stats based on template."""
    from app import db
    from app.models import Card

    try:
        logger.info("regenerate_card_stats_started", card_id=card_id)

        card = db.session.get(Card, card_id)
        if not card or not card.template:
            return {"success": False, "error": "Card or template not found"}

        # Regenerate stats from template
        template = card.template
        card.attack = template.base_attack
        card.hp = template.base_hp
        card.max_hp = template.base_hp

        db.session.commit()
        logger.info("regenerate_card_stats_completed", card_id=card_id)

        return {"success": True}

    except Exception as e:
        logger.error("regenerate_card_stats_failed", card_id=card_id, error=str(e))
        raise self.retry(exc=e)
