from django.contrib import admin

from .models import Order, OrderItem, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "product_slug", "unit_price", "quantity", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("public_id", "customer_name", "subtotal", "currency", "status", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("public_id", "customer_name", "email", "phone_number")
    readonly_fields = ("public_id", "subtotal", "currency", "created_at", "updated_at")
    inlines = (OrderItemInline,)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference_id", "order", "provider", "status", "amount", "currency", "updated_at")
    readonly_fields = ("reference_id", "order", "provider", "status", "provider_status", "provider_transaction_id", "amount", "currency", "created_at", "updated_at")
