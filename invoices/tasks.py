from celery import shared_task
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.conf import settings

from .models import Invoice


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 30})
def send_invoice_email(self, invoice_id, filename):
    invoice = Invoice.objects.select_related('customer').get(pk=invoice_id)
    if not invoice.invoice_pdf:
        raise ValueError('Invoice PDF path is missing for invoice id %s' % invoice_id)

    with default_storage.open(invoice.invoice_pdf, 'rb') as pdf_file:
        pdf_bytes = pdf_file.read()

    subject = f"Your invoice {invoice.invoice_number}"
    message = (
        f"Dear {invoice.customer.name},\n\n"
        "Please find your invoice attached.\n\n"
        "Kind regards,\n"
        "TwinPeaks Investments"
    )
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[invoice.customer.email],
    )
    email.attach(filename, pdf_bytes, "application/pdf")
    email.send(fail_silently=False)
