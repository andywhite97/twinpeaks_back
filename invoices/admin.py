from django.contrib import admin

from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "customer_name",
        "status",
        "total",
        "invoice_date",
        "due_date",
        "created_at",
    )
    list_filter = ("status", "invoice_date", "created_at")
    search_fields = ("invoice_number", "customer_name", "customer_email", "customer_id")
    readonly_fields = ("subtotal", "tax", "total", "items", "created_at", "updated_at")
