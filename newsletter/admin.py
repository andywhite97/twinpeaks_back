from django.contrib import admin
from .models import ConfirmationEmail, Subscriber, SubscriptionEvent


class EventInline(admin.TabularInline):
    model = SubscriptionEvent
    extra = 0
    fields = ('event', 'consent_version', 'created_at')
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'status', 'source', 'confirmed_at', 'unsubscribed_at')
    list_filter = ('status', 'interests')
    search_fields = ('email',)
    readonly_fields = ('email', 'status', 'interests', 'source', 'consent_version', 'created_at', 'requested_at', 'confirmed_at', 'unsubscribed_at')
    exclude = ('token_version',)
    inlines = (EventInline,)

    def has_add_permission(self, request):
        return False


@admin.register(ConfirmationEmail)
class ConfirmationAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscriber', 'created_at', 'sent_at', 'attempts', 'failed')
    list_filter = ('failed',)
    readonly_fields = ('subscriber', 'created_at', 'sent_at', 'attempts', 'failed', 'token_version')
    actions = ('retry_failed',)

    @admin.action(description='Requeue failed confirmation emails (does not send immediately)')
    def retry_failed(self, request, queryset):
        count = queryset.filter(sent_at=None, failed=True).update(attempts=0, failed=False)
        self.message_user(request, f'{count} confirmation email(s) requeued. Expired requests still require a fresh signup.')

    def has_add_permission(self, request):
        return False
