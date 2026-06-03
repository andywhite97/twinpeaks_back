from django.conf import settings
from django.db import models
from products.models import Product
import uuid


class Customer(models.Model):
    email = models.EmailField(primary_key=True)
    customer_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "email"]

    def save(self, *args, **kwargs):
        if not self.customer_id:
            self.customer_id = self._generate_customer_id()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_customer_id(cls):
        while True:
            customer_id = f"CUST-{uuid.uuid4().hex[:8].upper()}"
            if not cls.objects.filter(customer_id=customer_id).exists():
                return customer_id

    def __str__(self):
        return f"{self.name} - {self.email}"


class Invoice(models.Model):
    class Status(models.TextChoices):
        QUOTE = "quote", "Quote"
        INVOICE = "invoice", "Invoice"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="invoices",
    )
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
        default=Status.QUOTE,
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
        return f"{self.invoice_number} - {self.customer.name}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="line_items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="invoice_items",
    )
    product_name = models.CharField(max_length=150)
    product_description = models.TextField(blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
