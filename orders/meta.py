import hashlib
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _hash(value):
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest() if value else None


def purchase_payload(payment, request):
    order = payment.order
    user_data = {"em": [_hash(order.email)], "ph": [_hash(order.phone_number)], "client_ip_address": request.META.get("REMOTE_ADDR"), "client_user_agent": request.META.get("HTTP_USER_AGENT")}
    return {"data": [{
        "event_name": "Purchase", "event_time": int(time.time()), "event_id": str(payment.meta_event_id), "action_source": "website", "event_source_url": payment.event_source_url,
        "user_data": {key: value for key, value in user_data.items() if value},
        "custom_data": {"currency": order.currency, "value": float(order.subtotal), "content_type": "product", "content_ids": [item.product_slug for item in order.items.all()], "contents": [{"id": item.product_slug, "quantity": item.quantity, "item_price": float(item.unit_price)} for item in order.items.all()]},
    }], "access_token": settings.META_CONVERSIONS_API_ACCESS_TOKEN}


def send_purchase(payment, request):
    if not (settings.META_PIXEL_ID and settings.META_CONVERSIONS_API_ACCESS_TOKEN and payment.meta_event_id):
        return False
    try:
        response = requests.post(f"https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}/{settings.META_PIXEL_ID}/events", json=purchase_payload(payment, request), timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.warning("Meta CAPI Purchase delivery failed for payment %s", payment.pk)
        return False
