from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils.dateparse import parse_date
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

    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
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
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    invoice_pdf = models.CharField(max_length=255, blank=True)
    invoice_workbook = models.CharField(max_length=255, blank=True)
    items = models.ManyToManyField(
        "InvoiceItem",
        related_name="invoices",
        blank=True,
    )
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

    NUMBER_PREFIXES = {
        Status.QUOTE: "QT",
        Status.INVOICE: "INV",
        Status.PAID: "RCPT",
    }

    def save(self, *args, **kwargs):
        previous_status = None
        if self.pk:
            previous_status = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )

        should_generate_number = not self.invoice_number or (
            previous_status is not None
            and previous_status != self.status
            and self.status in self.NUMBER_PREFIXES
        )
        if should_generate_number:
            self.invoice_number = self._generate_invoice_number()
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"invoice_number"}

        super().save(*args, **kwargs)

    def _generate_invoice_number(self):
        prefix = self.NUMBER_PREFIXES.get(self.status, "INV")
        invoice_date = self.invoice_date
        if isinstance(invoice_date, str):
            invoice_date = parse_date(invoice_date)
        date_part = invoice_date.strftime("%Y%m%d")
        base_number = f"{prefix}-{date_part}"
        sequence = (
            type(self)
            .objects.filter(invoice_number__startswith=f"{base_number}-")
            .count()
            + 1
        )

        while True:
            invoice_number = f"{base_number}-{sequence:04d}"
            query = type(self).objects.filter(invoice_number=invoice_number)
            if self.pk:
                query = query.exclude(pk=self.pk)
            if not query.exists():
                return invoice_number
            sequence += 1

    def recalculate_totals(self, save=True):
        subtotal = self.items.aggregate(total=Sum("line_total"))["total"] or Decimal("0")
        subtotal = Decimal(subtotal).quantize(Decimal("0.01"))
        tax = (subtotal * Decimal(self.tax_rate)).quantize(Decimal("0.01"))
        total = (subtotal + tax).quantize(Decimal("0.01"))

        self.subtotal = subtotal
        self.tax = tax
        self.total = total

        if save:
            type(self).objects.filter(pk=self.pk).update(
                subtotal=subtotal,
                tax=tax,
                total=total,
            )

        return subtotal, tax, total

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name}"


class InvoiceItem(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="invoice_items",
    )
    product_name = models.CharField(max_length=150, null=True, blank=True)
    product_description = models.TextField(blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        # Capture product details at time of creation
        if self.product:
            if not self.product_name:
                self.product_name = self.product.name
            if not self.product_description:
                self.product_description = self.product.description or ""
            if not self.unit_price:
                self.unit_price = self.product.price
        
        # Calculate line total
        if self.unit_price is not None and self.quantity is not None:
            self.line_total = Decimal(str(self.unit_price)) * Decimal(str(self.quantity))
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"line_total"}
        
        super().save(*args, **kwargs)
        for invoice in self.invoices.all():
            invoice.recalculate_totals()

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


@receiver(m2m_changed, sender=Invoice.items.through)
def recalculate_invoice_totals_on_items_change(sender, instance, action, reverse, **kwargs):
    if reverse and action == "pre_clear":
        instance._invoice_totals_clear_ids = list(
            instance.invoices.values_list("pk", flat=True)
        )
        return

    if action not in {"post_add", "post_remove", "post_clear"}:
        return

    if reverse:
        invoice_ids = kwargs.get("pk_set") or getattr(
            instance, "_invoice_totals_clear_ids", []
        )
        for invoice in Invoice.objects.filter(pk__in=invoice_ids):
            invoice.recalculate_totals()
        if hasattr(instance, "_invoice_totals_clear_ids"):
            del instance._invoice_totals_clear_ids
    else:
        instance.recalculate_totals()
