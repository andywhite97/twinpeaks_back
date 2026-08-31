import logging

from bird import Bird
from django.conf import settings
from django.utils.html import escape

from .models import ContactMessage

logger = logging.getLogger(__name__)


def send_contact_message_notification(message: ContactMessage) -> None:
    """Send acknowledgement and team notification through Bird."""
    contact_message = ContactMessage.objects.get(pk=message.pk)
    try:
        with Bird() as client:
            _send_customer_acknowledgement(client, contact_message)
            _send_internal_notification(client, contact_message)
    except Exception:
        # The enquiry is already persisted. Provider failures must not turn a
        # submitted contact form into an API failure for the customer.
        logger.exception("Unable to send contact emails for message %s", contact_message.pk)


def _send_customer_acknowledgement(client: Bird, message: ContactMessage) -> None:
    subject = "We received your message | TwinPeaks Investment"
    html_body = (
        f"<p>Hello {escape(message.name)},</p>"
        "<p>Thank you for contacting <strong>TwinPeaks Investment</strong>. "
        "We have received your message and a member of our team will contact you "
        "shortly with further support.</p>"
        "<p>Kind regards,<br>TwinPeaks Investment</p>"
    )
    _send(client, subject, html_body, [message.email])


def _send_internal_notification(client: Bird, message: ContactMessage) -> None:
    subject = f"New website contact message from {message.name}"
    html_body = (
        f"<p><strong>Name:</strong> {escape(message.name)}<br>"
        f"<strong>Email:</strong> {escape(message.email)}</p>"
        f"<p><strong>Message:</strong><br>{escape(message.message).replace(chr(10), '<br>')}</p>"
    )
    _send(client, subject, html_body, [settings.CONTACT_NOTIFICATION_EMAIL])


def _send(client: Bird, subject: str, html_body: str, recipients: list[str]) -> None:
    client.email.send(
        from_={"email": settings.CONTACT_FROM_EMAIL, "name": settings.CONTACT_FROM_NAME},
        to=recipients,
        subject=subject,
        html=html_body,
    )
