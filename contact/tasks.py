import logging

from bird import Bird
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from core.models import CompanyProfile

from .models import ContactMessage, Quotation

logger = logging.getLogger(__name__)


def render_email(template: str, subject: str, context: dict, *, quotation_sender: bool = False) -> tuple[str, str]:
    """Render both formats from one context; Django escapes untrusted HTML."""
    company = context["company"] if "company" in context else CompanyProfile.objects.first()
    context = {
        **context,
        "subject": subject,
        "site_url": settings.PUBLIC_SITE_URL.rstrip("/"),
        "support_email": settings.QUOTATION_FROM_EMAIL if quotation_sender else settings.CONTACT_FROM_EMAIL,
        "year": timezone.localdate().year,
        "assets_url": getattr(settings, "EMAIL_ASSET_BASE_URL", settings.PUBLIC_SITE_URL + "/assets/email").rstrip("/"),
        "company": company,
        "contact_url": settings.PUBLIC_SITE_URL.rstrip("/") + "/contact",
        "banner_image": "technology.jpg" if template in {"quote_issued", "general"} else "security.jpg" if template in {"quote_acknowledgement", "quote_internal"} else "workplace.jpg",
    }
    stem = f"contact/emails/{template}"
    return render_to_string(f"{stem}.html", context), render_to_string(f"{stem}.txt", context).strip()


def _send(client: Bird, subject: str, template: str, context: dict, recipients: list[str], *, quotation_sender: bool = False) -> None:
    sender = (
        {"email": settings.QUOTATION_FROM_EMAIL, "name": settings.QUOTATION_FROM_NAME}
        if quotation_sender else {"email": settings.CONTACT_FROM_EMAIL, "name": settings.CONTACT_FROM_NAME}
    )
    html, text = render_email(template, subject, context, quotation_sender=quotation_sender)
    client.email.send(from_=sender, to=recipients, subject=subject, html=html, text=text)


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
    _send(client, "We received your message | TwinPeaks Investment", "contact_acknowledgement", {"message": message}, [message.email])


def _send_internal_notification(client: Bird, message: ContactMessage) -> None:
    _send(client, f"New website contact message from {message.name}", "contact_internal", {"message": message}, [settings.CONTACT_NOTIFICATION_EMAIL])


def send_quotation_request_notification(quotation_id: int) -> None:
    """Send the quote acknowledgement and team notification through Bird."""
    try:
        quotation = Quotation.objects.prefetch_related("items").get(pk=quotation_id)
        with Bird() as client:
            _send_quote_acknowledgement(client, quotation)
            _send_quote_internal_notification(client, quotation)
    except Exception:
        logger.exception("Unable to send quote emails for quotation %s", quotation_id)


def _send_quote_acknowledgement(client: Bird, quotation: Quotation) -> None:
    _send(client, "We received your quote request | TwinPeaks Investment", "quote_acknowledgement",
          {"quotation": quotation, "items": list(quotation.items.all())}, [quotation.email], quotation_sender=True)


def _send_quote_internal_notification(client: Bird, quotation: Quotation) -> None:
    _send(client, f"New quote request from {quotation.name}", "quote_internal",
          {"quotation": quotation, "items": list(quotation.items.all())}, [settings.QUOTE_NOTIFICATION_EMAIL])


def send_quotation_accepted_notification(quotation_id: int) -> None:
    try:
        quotation = Quotation.objects.get(pk=quotation_id)
        context = {"quotation": quotation}
        with Bird() as client:
            _send(client, f"Quotation {quotation.quote_number} accepted", "quote_accepted", context, [quotation.email], quotation_sender=True)
            _send(client, f"Quotation accepted: {quotation.quote_number}", "quote_accepted_internal", context, [settings.QUOTE_NOTIFICATION_EMAIL])
    except Exception:
        logger.exception("Unable to send acceptance emails for quotation %s", quotation_id)


def send_quotation_issued_notification(quotation_id: int) -> None:
    try:
        quotation = Quotation.objects.get(pk=quotation_id)
        context = {
            "quotation": quotation,
            "quotation_url": f"{settings.PUBLIC_SITE_URL.rstrip('/')}/quotations/{quotation.public_access_token}",
            "quotation_pdf_url": f"{getattr(settings, 'PUBLIC_API_URL', 'https://backend.twinpeaksinvestment.com').rstrip('/')}/api/quotations/public/{quotation.public_access_token}/pdf/",
        }
        with Bird() as client:
            _send(client, f"Your quotation {quotation.quote_number} | TwinPeaks Investment", "quote_issued", context, [quotation.email], quotation_sender=True)
    except Exception:
        logger.exception("Unable to send issued quotation email for %s", quotation_id)


def send_quotation_declined_notification(quotation_id: int) -> None:
    try:
        quotation = Quotation.objects.get(pk=quotation_id)
        context = {"quotation": quotation}
        with Bird() as client:
            _send(client, f"Quotation {quotation.quote_number} — response received", "quote_declined", context, [quotation.email], quotation_sender=True)
            _send(client, f"Quotation declined: {quotation.quote_number}", "quote_declined_internal", context, [settings.QUOTE_NOTIFICATION_EMAIL])
    except Exception:
        logger.exception("Unable to send decline emails for quotation %s", quotation_id)
