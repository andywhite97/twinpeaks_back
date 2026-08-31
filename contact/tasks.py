import logging

from bird import Bird
from django.conf import settings
from django.utils.html import escape

from .models import ContactMessage, Quotation

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


def _send(client: Bird, subject: str, html_body: str, recipients: list[str], *, quotation_sender: bool = False) -> None:
    sender = (
        {"email": settings.QUOTATION_FROM_EMAIL, "name": settings.QUOTATION_FROM_NAME}
        if quotation_sender else {"email": settings.CONTACT_FROM_EMAIL, "name": settings.CONTACT_FROM_NAME}
    )
    client.email.send(
        from_=sender,
        to=recipients,
        subject=subject,
        html=html_body,
    )


def send_quotation_request_notification(quotation_id: int) -> None:
    """Send the quote acknowledgement and team notification through Bird."""
    try:
        quotation = Quotation.objects.prefetch_related("items").get(pk=quotation_id)
        with Bird() as client:
            _send_quote_acknowledgement(client, quotation)
            _send_quote_internal_notification(client, quotation)
    except Exception:
        logger.exception("Unable to send quote emails for quotation %s", quotation_id)


def _send_quote_acknowledgement(client: Bird, quote_request: Quotation) -> None:
    subject = "We received your quote request | TwinPeaks Investment"
    requested_items = ", ".join(escape(item.title) for item in quote_request.items.all())
    html_body = (
        f"<p>Hello {escape(quote_request.name)},</p>"
        f"<p>Thank you for requesting a quote{f' for <strong>{requested_items}</strong>' if requested_items else ''}. We have received your request "
        "and a member of our team will contact you shortly with further support.</p>"
        "<p>Kind regards,<br>TwinPeaks Investment</p>"
    )
    _send(client, subject, html_body, [quote_request.email], quotation_sender=True)


def _send_quote_internal_notification(client: Bird, quote_request: Quotation) -> None:
    subject = f"New quote request from {quote_request.name}"
    product = ", ".join(escape(item.title) for item in quote_request.items.all())
    html_body = (
        f"<p><strong>Quote for:</strong> {product}<br>"
        f"<strong>Name:</strong> {escape(quote_request.name)}<br>"
        f"<strong>Email:</strong> {escape(quote_request.email)}<br>"
        f"<strong>Phone:</strong> {escape(quote_request.phone_number)}</p>"
        f"<p><strong>Requirements:</strong><br>{escape(quote_request.message).replace(chr(10), '<br>')}</p>"
    )
    _send(client, subject, html_body, [settings.QUOTE_NOTIFICATION_EMAIL])


def send_quotation_accepted_notification(quotation_id: int) -> None:
    try:
        quotation = Quotation.objects.get(pk=quotation_id)
        with Bird() as client:
            _send(client, f"Quotation {quotation.quote_number} accepted", f"<p>Hello {escape(quotation.name)},</p><p>Thank you for accepting quotation <strong>{quotation.quote_number}</strong>. Our team will contact you about the next steps.</p>", [quotation.email], quotation_sender=True)
            _send(client, f"Quotation accepted: {quotation.quote_number}", f"<p>{escape(quotation.name)} accepted quotation <strong>{quotation.quote_number}</strong>.</p>", [settings.QUOTE_NOTIFICATION_EMAIL])
    except Exception:
        logger.exception("Unable to send acceptance emails for quotation %s", quotation_id)


def send_quotation_issued_notification(quotation_id: int) -> None:
    try:
        quotation = Quotation.objects.get(pk=quotation_id)
        quote_url = f"{settings.PUBLIC_SITE_URL}/quotations/{quotation.public_access_token}"
        with Bird() as client:
            _send(client, f"Your quotation {quotation.quote_number} | TwinPeaks Investment", f"<p>Hello {escape(quotation.name)},</p><p>Your quotation <strong>{quotation.quote_number}</strong> is ready.</p><p><a href=\"{quote_url}\">View your quotation securely</a></p><p>This quotation is valid until {quotation.valid_until}.</p>", [quotation.email], quotation_sender=True)
    except Exception:
        logger.exception("Unable to send issued quotation email for %s", quotation_id)
