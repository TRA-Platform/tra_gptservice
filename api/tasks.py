import logging
import traceback

from celery import current_app
from django.db import transaction
from django.utils import timezone

import api
from api.models import Request

app = current_app._get_current_object()
logger = logging.getLogger(__name__)


@app.task
def request_resolve(request_id):
    try:
        logger.error(f"request: {request_id}")
        request_object = Request.objects.get(pk=request_id)
        request_object.resolve()
    except Request.DoesNotExist:
        pass
