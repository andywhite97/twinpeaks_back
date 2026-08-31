import uuid

from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending payment"
        PAID = "paid", "Paid"
        PAYMENT_FAILED = "payment_failed", "Payment failed"
        PAYMENT_REVIEW = "payment_review", "Payment review"
        CANCELLED = "cancelled", "Cancelled"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING_PAYMENT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Order {self.public_id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.PROTECT)
    product = models.ForeignKey("products.Product", null=True, blank=True, on_delete=models.SET_NULL)
    product_name = models.CharField(max_length=150)
    product_slug = models.SlugField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"

    order = models.OneToOneField(Order, related_name="payment", on_delete=models.PROTECT)
    provider = models.CharField(max_length=40, default="mtn_momo")
    reference_id = models.UUIDField(unique=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    provider_status = models.CharField(max_length=40, blank=True)
    provider_transaction_id = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    meta_event_id = models.UUIDField(null=True, blank=True, unique=True)
    event_source_url = models.URLField(blank=True)
    meta_event_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
