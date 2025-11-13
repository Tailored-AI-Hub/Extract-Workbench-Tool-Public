from .tasks import celery_app

# Celery autodiscovery happens here
__all__ = ["celery_app"]