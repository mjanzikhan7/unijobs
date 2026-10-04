"""Background scoring.

Re-scoring runs in the background because its work grows with the number of jobs. Done inside
the request, one profile save would hold a web worker for a long time.
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="screening.tasks.rescore_for_user")
def rescore_for_user(user_id: int, *, force: bool = False) -> dict[str, int]:
    """Recompute one candidate's fitness scores across the corpus."""
    from django.contrib.auth.models import User

    from screening.services import score_fitness_for

    user = User.objects.filter(pk=user_id).first()
    if user is None:
        logger.info("rescore skipped: user %s no longer exists", user_id)
        return {"scored": 0, "changed": 0}

    return score_fitness_for(user, force=force)
