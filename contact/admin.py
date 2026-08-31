from django.contrib import admin, messages

from .models import ContactMessage, Quotation, QuotationItem
from .tasks import send_quotation_issued_notification

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at"); list_filter = ("created_at",); search_fields = ("name", "email", "message")
    readonly_fields = ("name", "email", "message", "created_at")
    def has_add_permission(self, request): return False

class QuotationItemInline(admin.TabularInline):
    model = QuotationItem; extra = 0
    fields = ("product", "service", "title", "description", "quantity", "unit_price", "discount_amount", "tax_amount", "line_total", "sort_order")
    readonly_fields = ("line_total",)

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ("quote_number", "name", "email", "status", "total", "currency", "valid_until", "created_at")
    list_filter = ("status", "currency", "created_at", "valid_until"); search_fields = ("quote_number", "name", "email", "phone_number")
    readonly_fields = ("quote_number", "public_access_token", "subtotal", "total", "created_at", "updated_at", "sent_at", "viewed_at", "accepted_at", "declined_at", "converted_order")
    inlines = (QuotationItemInline,); actions = ("issue_quotes", "resend_quotes", "convert_quotes_to_orders")
    @admin.action(description="Issue selected quotations and email customers")
    def issue_quotes(self, request, queryset):
        for quotation in queryset:
            try:
                quotation.issue(); send_quotation_issued_notification(quotation.pk)
            except ValueError as exc: self.message_user(request, f"{quotation.quote_number}: {exc}", messages.ERROR)
    @admin.action(description="Resend selected issued quotations")
    def resend_quotes(self, request, queryset):
        for quotation in queryset.filter(status__in=[Quotation.Status.SENT, Quotation.Status.VIEWED]): send_quotation_issued_notification(quotation.pk)

    @admin.action(description="Convert selected accepted quotations to orders")
    def convert_quotes_to_orders(self, request, queryset):
        for quotation in queryset:
            try:
                order = quotation.convert_to_order()
                self.message_user(request, f"{quotation.quote_number} converted to order #{order.pk}.", messages.SUCCESS)
            except ValueError as exc:
                self.message_user(request, f"{quotation.quote_number}: {exc}", messages.ERROR)
