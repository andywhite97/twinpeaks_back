from django.contrib import admin

from .models import Customer, Invoice, InvoiceItem


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("customer_id", "name", "email", "phone", "created_at")
    search_fields = ("customer_id", "name", "email", "phone")
    readonly_fields = ("customer_id", "created_at", "updated_at")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "customer",
        "status",
        "total",
        "invoice_date",
        "due_date",
        "created_at",
    )
    list_filter = ("status", "invoice_date", "created_at")
    search_fields = (
        "invoice_number",
        "customer__customer_id",
        "customer__name",
        "customer__email",
    )
    readonly_fields = ("subtotal", "tax", "total", "items", "created_at", "updated_at")
    list_editable = ("status",)


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = (
        "product_name",
        "quantity",
        "unit_price",
        "line_total",
        "invoice_numbers",
    )
    search_fields = ("invoices__invoice_number", "product_name", "product__name")
    readonly_fields = (
        "product_name",
        "product_description",
        "unit_price",
        "line_total",
        "created_at",
    )

    def invoice_numbers(self, item):
        return ", ".join(item.invoices.values_list("invoice_number", flat=True))
