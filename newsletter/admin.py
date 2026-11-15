from django.contrib import admin
from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.views.decorators.clickjacking import xframe_options_sameorigin
from .models import ConfirmationEmail, Subscriber, SubscriptionEvent, Campaign, CampaignDelivery
from . import campaigns


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


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from blog.models import BlogPost
        for name in ('featured', 'article_two', 'article_three'):
            if name in self.fields:
                self.fields[name].queryset = BlogPost.published()


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    form = CampaignForm
    list_display = ('name', 'subject', 'status', 'created_at', 'campaign_tools')
    list_filter = ('status',)
    search_fields = ('name', 'subject')
    filter_horizontal = ('interests',)
    fields = ('name', 'subject', 'introduction', 'featured', 'article_two', 'article_three',
              'interests', 'status', 'campaign_tools', 'created_at', 'started_at')
    readonly_fields = ('status', 'campaign_tools', 'created_at', 'started_at')
    actions = None

    def get_readonly_fields(self, request, obj=None):
        return self.fields if obj and obj.status != 'draft' else self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        return bool(obj and obj.status == 'draft' and super().has_delete_permission(request, obj))

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        # Serialize draft edits with the final send review, including M2M changes.
        with transaction.atomic():
            if request.method == 'POST' and object_id:
                Campaign.objects.select_for_update().filter(pk=object_id).first()
            return super().changeform_view(request, object_id, form_url, extra_context)

    @admin.display(description='Campaign tools')
    def campaign_tools(self, obj):
        if not obj or not obj.pk:
            return 'Save your draft to preview, test and send.'
        return format_html('<a href="{}">Preview, test and send / delivery results</a>',
                           reverse('admin:newsletter_campaign_review', args=[obj.pk]))

    def get_urls(self):
        return [
            path('<int:pk>/review/', self.admin_site.admin_view(self.review), name='newsletter_campaign_review'),
            path('<int:pk>/preview/', self.admin_site.admin_view(self.preview), name='newsletter_campaign_preview'),
            path('<int:pk>/next/', self.admin_site.admin_view(self.next_delivery), name='newsletter_campaign_next'),
        ] + super().get_urls()

    def checked_campaign(self, request, pk, sending=False):
        campaign = get_object_or_404(Campaign, pk=pk)
        if not self.has_view_or_change_permission(request, campaign):
            raise PermissionDenied
        if sending and not (self.has_change_permission(request, campaign) and request.user.has_perm('newsletter.send_campaign')):
            raise PermissionDenied
        return campaign

    @xframe_options_sameorigin
    def preview(self, request, pk):
        campaign = self.checked_campaign(request, pk)
        try:
            html = campaign.html_snapshot or campaigns.render_campaign(campaign)[0]
        except ValidationError as error:
            return HttpResponse('; '.join(error.messages), status=400, content_type='text/plain')
        response = HttpResponse(html)
        response['Content-Security-Policy'] = "default-src 'none'; img-src https: data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
        response['Cache-Control'] = 'no-store'
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response

    def review(self, request, pk):
        campaign = self.checked_campaign(request, pk, sending=request.method == 'POST')
        error = ''
        auto_start = False
        test_form = forms.Form(request.POST if request.method == 'POST' and request.POST.get('action') == 'test' else None)
        test_form.fields['recipient'] = forms.EmailField(label='Test email address', initial=request.user.email)
        if request.method == 'POST':
            try:
                if request.POST.get('action') == 'start':
                    campaign = campaigns.start_campaign(pk, request.POST.get('review_token', ''))
                    auto_start = True
                elif request.POST.get('action') == 'test' and test_form.is_valid():
                    html, text = (campaign.html_snapshot, campaign.text_snapshot) if campaign.html_snapshot else campaigns.render_campaign(campaign)
                    campaigns.send_message(test_form.cleaned_data['recipient'], '[TEST] ' + campaign.subject, html, text)
                    self.message_user(request, 'Test accepted by the email provider. The sample unsubscribe link is inactive.')
                    return redirect('admin:newsletter_campaign_review', pk)
            except ValidationError as exc:
                error = '; '.join(exc.messages)
            except Exception:
                error = 'The test could not be verified as accepted. Check your inbox and provider before trying again.'
        token, count = '', 0
        if campaign.status == 'draft':
            try:
                token = campaigns.review_token(campaign)
                count = campaigns.audience(campaign).count()
            except ValidationError as exc:
                error = '; '.join(exc.messages)
        counts = campaigns.progress(campaign)
        context = {**self.admin_site.each_context(request), 'opts': self.model._meta,
            'title': 'Review newsletter', 'campaign': campaign, 'test_form': test_form,
            'error': error, 'recipient_count': count, 'review_token': token, 'auto_start': auto_start,
            'counts': counts, 'can_send': request.user.has_perm('newsletter.send_campaign') and self.has_change_permission(request, campaign),
            'deliveries': campaign.deliveries.select_related('subscriber').order_by('pk')[:100],
            'results_url': reverse('admin:newsletter_campaigndelivery_changelist') + f'?campaign__id__exact={pk}',
            'next_url': reverse('admin:newsletter_campaign_next', args=[pk])}
        return render(request, 'admin/newsletter/campaign_review.html', context)

    def next_delivery(self, request, pk):
        if request.method != 'POST':
            return HttpResponse(status=405)
        self.checked_campaign(request, pk, sending=True)
        campaigns.send_next(pk)
        campaign = Campaign.objects.get(pk=pk)
        return JsonResponse({'status': campaign.status, 'counts': campaigns.progress(campaign)})


@admin.register(CampaignDelivery)
class CampaignDeliveryAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'subscriber', 'status', 'attempted_at', 'sent_at', 'detail')
    list_filter = ('campaign', 'status')
    search_fields = ('subscriber__email', 'campaign__name')
    readonly_fields = ('campaign', 'subscriber', 'status', 'attempted_at', 'sent_at', 'detail')
    fields = readonly_fields
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
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
