"""Explicit admin-driven campaign sending; no background service required."""
import hashlib
import json
from bird import Bird, APIStatusError
from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from .emails import newsletter_update_email, subscription_url
from .models import Campaign, CampaignDelivery, Subscriber

UNSUBSCRIBE_PLACEHOLDER = 'https://example.invalid/replace-newsletter-unsubscribe'


def audience(campaign):
    query = Subscriber.objects.filter(status='confirmed', confirmed_at__isnull=False)
    interests = list(campaign.interests.values_list('pk', flat=True))
    if interests:
        query = query.filter(interests__in=interests)
    return query.distinct().order_by('pk')


def render_campaign(campaign):
    campaign.clean()
    sample = Subscriber(status='confirmed')
    return newsletter_update_email(sample, campaign.featured,
        [post for post in (campaign.article_two, campaign.article_three) if post],
        subject=campaign.subject, introduction=campaign.introduction,
        unsubscribe_url=UNSUBSCRIBE_PLACEHOLDER)


def review_data(campaign):
    html, text = render_campaign(campaign)
    recipients = list(audience(campaign).values_list('pk', 'token_version'))
    digest = hashlib.sha256(json.dumps([campaign.subject, html, text, recipients], default=str).encode()).hexdigest()
    return html, text, recipients, digest


def review_token(campaign):
    return signing.dumps({'id': campaign.pk, 'digest': review_data(campaign)[3]}, salt='newsletter-campaign-review')


def start_campaign(pk, token):
    with transaction.atomic():
        campaign = Campaign.objects.select_for_update().get(pk=pk)
        if campaign.status != 'draft':
            return campaign
        html, text, recipients, digest = review_data(campaign)
        try:
            signed = signing.loads(token, salt='newsletter-campaign-review', max_age=1800)
        except signing.BadSignature:
            raise ValidationError('This review expired. Review the campaign again.')
        if signed != {'id': pk, 'digest': digest}:
            raise ValidationError('The content or audience changed. Review the campaign again.')
        if not recipients:
            raise ValidationError('No confirmed subscribers match this audience.')
        campaign.html_snapshot, campaign.text_snapshot = html, text
        campaign.status = 'sending'
        campaign.started_at = timezone.now()
        campaign.save()
        CampaignDelivery.objects.bulk_create([
            CampaignDelivery(campaign=campaign, subscriber_id=subscriber_id, token_version=version)
            for subscriber_id, version in recipients])
        return campaign


def send_message(recipient, subject, html, text):
    if settings.NEWSLETTER_EMAIL_PROVIDER == 'bird':
        if not settings.BIRD_API_KEY:
            raise ImproperlyConfigured('Bird is not configured.')
        with Bird(api_key=settings.BIRD_API_KEY, timeout=20, max_retries=0) as client:
            client.email.send(from_={'email': settings.CONTACT_FROM_EMAIL, 'name': settings.CONTACT_FROM_NAME},
                to=[recipient], subject=subject, html=html, text=text, track_clicks=False, track_opens=False)
    elif settings.NEWSLETTER_EMAIL_PROVIDER == 'django':
        if send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, [recipient], html_message=html) != 1:
            raise ImproperlyConfigured('Email backend did not accept the message.')
    else:
        raise ImproperlyConfigured('Unknown newsletter provider.')


def send_next(pk):
    # Persist the claim BEFORE contacting Bird. A crash or timeout must never cause
    # automatic redelivery of a message the provider might already have accepted.
    with transaction.atomic():
        campaign = Campaign.objects.select_for_update().get(pk=pk)
        if campaign.status != 'sending':
            return
        item = campaign.deliveries.filter(status='pending').order_by('pk').first()
        if not item:
            if not campaign.deliveries.filter(status='sending').exists():
                campaign.status = 'complete'
                campaign.save(update_fields=['status'])
            return
        item.status, item.attempted_at = 'sending', timezone.now()
        item.save(update_fields=['status', 'attempted_at'])
    with transaction.atomic():
        subscriber = Subscriber.objects.select_for_update().get(pk=item.subscriber_id)
        if subscriber.status != 'confirmed' or subscriber.token_version != item.token_version:
            item.status, item.detail = 'skipped', 'Subscription changed before sending.'
        else:
            url = subscription_url(subscriber, 'unsubscribe')
            try:
                send_message(subscriber.email, campaign.subject,
                    campaign.html_snapshot.replace(UNSUBSCRIBE_PLACEHOLDER, url),
                    campaign.text_snapshot.replace(UNSUBSCRIBE_PLACEHOLDER, url))
            except ImproperlyConfigured:
                item.status, item.detail = 'failed', 'Email provider configuration needs attention.'
            except APIStatusError as error:
                item.status = 'failed' if error.status_code in (400, 401, 402, 403, 404, 413, 422, 429) else 'unknown'
                item.detail = f'Provider returned HTTP {error.status_code}. Not retried.'
            except Exception:
                item.status, item.detail = 'unknown', 'Provider acceptance could not be verified. Not retried.'
            else:
                item.status, item.sent_at = 'accepted', timezone.now()
                item.detail = 'Accepted by the email provider; inbox delivery is not yet tracked.'
        item.save(update_fields=['status', 'detail', 'sent_at'])


def progress(campaign):
    counts = {key: 0 for key, _ in CampaignDelivery._meta.get_field('status').choices}
    counts.update({row['status']: row['n'] for row in campaign.deliveries.values('status').annotate(n=Count('pk'))})
    return counts
