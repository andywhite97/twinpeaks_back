import logging

from bird import Bird
from django.conf import settings
from django.utils.html import escape

from .models import Order

logger = logging.getLogger(__name__)


def send_order_placement_notification(order_id: int) -> None:
    """Acknowledge a newly placed, pending-payment order through Bird."""
    order = Order.objects.prefetch_related("items").get(pk=order_id)
    try:
        with Bird() as client:
            _send_customer_acknowledgement(client, order)
            _send_internal_notification(client, order)
    except Exception:
        # The order and payment request are already persisted. Email delivery
        # must not alter the outcome returned to the checkout customer.
        logger.exception("Unable to send order emails for order %s", order.public_id)


def _send_customer_acknowledgement(client: Bird, order: Order) -> None:
    subject = f"We received your order | TwinPeaks Investment"
    html_body = (
        f"<p>Hello {escape(order.customer_name)},</p>"
        "<p>Thank you for your order with <strong>TwinPeaks Investment</strong>. "
        "We have received your order and sent a payment request to your mobile phone.</p>"
        f"<p><strong>Order reference:</strong> {order.public_id}<br>"
        f"<strong>Total:</strong> {order.subtotal:.2f} {escape(order.currency)}</p>"
        "<p>Please approve the payment request to complete your order. Our team will contact you with any further support.</p>"
        "<p>Kind regards,<br>TwinPeaks Investment</p>"
    )
    _send(client, subject, html_body, [order.email])


def _send_internal_notification(client: Bird, order: Order) -> None:
    subject = f"New website order {order.public_id}"
    items = "".join(
        f"<li>{escape(item.product_name)} &times; {item.quantity} &mdash; {item.line_total:.2f} {escape(order.currency)}</li>"
        for item in order.items.all()
    )
    html_body = (
        f"<p><strong>Order reference:</strong> {order.public_id}<br>"
        f"<strong>Customer:</strong> {escape(order.customer_name)}<br>"
        f"<strong>Email:</strong> {escape(order.email)}<br>"
        f"<strong>Phone:</strong> {escape(order.phone_number)}<br>"
        f"<strong>Status:</strong> {escape(order.get_status_display())}<br>"
        f"<strong>Total:</strong> {order.subtotal:.2f} {escape(order.currency)}</p>"
        f"<p><strong>Items:</strong></p><ul>{items}</ul>"
    )
    _send(client, subject, html_body, [settings.ORDER_NOTIFICATION_EMAIL])


def _send(client: Bird, subject: str, html_body: str, recipients: list[str]) -> None:
    client.email.send(
        from_={"email": settings.CONTACT_FROM_EMAIL, "name": settings.CONTACT_FROM_NAME},
        to=recipients,
        subject=subject,
        html=html_body,
    )
