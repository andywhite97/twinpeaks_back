from django.conf import settings
from django.db import models


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    invoice_number = models.CharField(max_length=50, unique=True)
    customer_id = models.CharField(max_length=50, blank=True)
    customer_name = models.CharField(max_length=120)
    customer_location = models.CharField(max_length=200, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=40, blank=True)
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    salesperson = models.CharField(max_length=120, blank=True)
    job = models.CharField(max_length=120, blank=True)
    payment_terms = models.CharField(max_length=120, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.15)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    items = models.JSONField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_invoices",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.invoice_number} - {self.customer_name}"
