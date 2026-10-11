import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, models, transaction
from django.db.models import F
from django.utils import timezone

# Create your models here.
class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.email}"


class QuotationSequence(models.Model):
    year = models.PositiveIntegerField(unique=True)
    next_number = models.PositiveIntegerField(default=1)


class Quotation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REQUESTED = "requested", "Requested"
        UNDER_REVIEW = "under_review", "Under review"
        SENT = "sent", "Sent"
        VIEWED = "viewed", "Viewed"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"
        # Retain this status for historical quotations; new conversions are retired.
        CONVERTED_TO_ORDER = "converted_to_order", "Converted to order (legacy)"
        CANCELLED = "cancelled", "Cancelled"

    # The migration initially assigns UUIDs to legacy records, so leave room for
    # that value as well as the normal TP-Q-YYYY-0001 sequence.
    quote_number = models.CharField(max_length=36, unique=True, editable=False)
    public_access_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=120)
    company_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    message = models.TextField()
    internal_notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.REQUESTED)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, default=settings.SHOP_CURRENCY)
    valid_until = models.DateField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.quote_number

    def save(self, *args, **kwargs):
        if not self.quote_number:
            self.quote_number = self.allocate_number()
        super().save(*args, **kwargs)

    @classmethod
    def allocate_number(cls):
        year = timezone.now().year
        try:
            with transaction.atomic():
                sequence, _ = QuotationSequence.objects.select_for_update().get_or_create(year=year)
                number = sequence.next_number
                QuotationSequence.objects.filter(pk=sequence.pk).update(next_number=F("next_number") + 1)
                return f"TP-Q-{year}-{number:04d}"
        except IntegrityError:
            return cls.allocate_number()

    @property
    def is_expired(self):
        return bool(self.valid_until and self.valid_until < timezone.localdate())

    def refresh_expiry(self):
        if self.is_expired and self.status in {self.Status.SENT, self.Status.VIEWED}:
            self.status = self.Status.EXPIRED
            self.save(update_fields=["status", "updated_at"])
        return self.status == self.Status.EXPIRED

    def recalculate_totals(self):
        subtotal = sum((item.line_total for item in self.items.all()), Decimal("0.00"))
        self.subtotal = subtotal
        self.total = max(Decimal("0.00"), subtotal - self.discount_amount) + self.tax_amount

    def issue(self):
        if not self.items.exists():
            raise ValueError("A quotation needs at least one item before it can be issued.")
        self.recalculate_totals()
        self.valid_until = self.valid_until or timezone.localdate() + timedelta(days=14)
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=["subtotal", "total", "valid_until", "status", "sent_at", "updated_at"])


class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, related_name="items", on_delete=models.CASCADE)
    solution = models.ForeignKey("services.Solution", null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")

    def save(self, *args, **kwargs):
        unit_price = Decimal(self.unit_price)
        discount = Decimal(self.discount_amount)
        tax = Decimal(self.tax_amount)
        self.line_total = max(Decimal("0.00"), unit_price * self.quantity - discount) + tax
        super().save(*args, **kwargs)
