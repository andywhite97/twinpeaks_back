from celery import shared_task
from django.core.files.storage import default_storage
from bird import APIError, Bird

from .models import Invoice

def send_invoice_email(self, invoice_id, filename):
    invoice = Invoice.objects.select_related('customer').get(pk=invoice_id)
    if not invoice.invoice_pdf:
        raise ValueError('Invoice PDF path is missing for invoice id %s' % invoice_id)

    with default_storage.open(invoice.invoice_pdf, 'rb') as pdf_file:
        pdf_bytes = pdf_file.read()

    msg = (
        f"Dear {invoice.customer.name},\n\n"
        "Please find your invoice attached.\n\n"
        "Kind regards,\n"
        "TwinPeaks Investments"
    )
    with Bird() as client:
        try:
            message = client.email.send(
                from_={"email": "info@twinpeaksinvestment.com", "name": "TwinPeaks Investments"},
                to=[invoice.customer.email],
                subject=f"Your invoice {invoice.invoice_number}",
                html=f"<p>{msg}</p>",
                attachments= [
                    {
                    "filename": "Invoice.pdf",
                    "content": filename,
                    }
                ]
            )
            print(message.id, message.status)
        except APIError as err:
            print("send failed:", err)
