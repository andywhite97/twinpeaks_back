import uuid
from django.core.exceptions import ValidationError
from django.db import models


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    status = models.CharField(max_length=16, choices=[('pending', 'Pending confirmation'), ('confirmed', 'Confirmed'), ('unsubscribed', 'Unsubscribed')], default='pending')
    interests = models.ManyToManyField('services.Solution', blank=True)
    source = models.CharField(max_length=30, default='blog')
    consent_version = models.CharField(max_length=30, default='newsletter-v1')
    token_version = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    requested_at = models.DateTimeField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.email


class SubscriptionEvent(models.Model):
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE, related_name='events')
    event = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    consent_version = models.CharField(max_length=30, default='newsletter-v1')


class ConfirmationEmail(models.Model):
    """Transactional outbox; only confirmation emails, never marketing campaigns."""
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE)
    token_version = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    failed = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['subscriber', 'token_version'], name='unique_newsletter_confirmation')]


class Campaign(models.Model):
    name = models.CharField(max_length=160, help_text='Internal name for this newsletter.')
    subject = models.CharField(max_length=200)
    introduction = models.TextField(max_length=2000, blank=True)
    featured = models.ForeignKey('blog.BlogPost', on_delete=models.PROTECT, related_name='+')
    article_two = models.ForeignKey('blog.BlogPost', on_delete=models.PROTECT, related_name='+', blank=True, null=True)
    article_three = models.ForeignKey('blog.BlogPost', on_delete=models.PROTECT, related_name='+', blank=True, null=True)
    interests = models.ManyToManyField('services.Solution', blank=True,
        help_text='Leave empty for all confirmed subscribers. Otherwise match any selected interest.')
    status = models.CharField(max_length=16, default='draft', choices=[('draft', 'Draft'), ('sending', 'Sending'), ('complete', 'Complete')])
    html_snapshot = models.TextField(blank=True, editable=False)
    text_snapshot = models.TextField(blank=True, editable=False)
    started_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        permissions = [('send_campaign', 'Can send newsletter campaigns')]

    def __str__(self):
        return self.name

    def clean(self):
        if '\n' in self.subject or '\r' in self.subject:
            raise ValidationError({'subject': 'Use a single line for the subject.'})
        ids = [pk for pk in (self.featured_id, self.article_two_id, self.article_three_id) if pk]
        if len(ids) != len(set(ids)):
            raise ValidationError('Choose each article only once.')
        from blog.models import BlogPost
        if BlogPost.published().filter(pk__in=ids).count() != len(ids):
            raise ValidationError('Only articles that are published now can be sent.')


class CampaignDelivery(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.PROTECT, related_name='deliveries')
    subscriber = models.ForeignKey(Subscriber, on_delete=models.PROTECT)
    token_version = models.UUIDField()
    status = models.CharField(max_length=16, default='pending', choices=[
        ('pending', 'Pending'), ('sending', 'Sending / outcome unverified'),
        ('accepted', 'Accepted by provider'), ('failed', 'Rejected'),
        ('unknown', 'Outcome unknown'), ('skipped', 'Skipped')])
    attempted_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    detail = models.CharField(max_length=160, blank=True)

    class Meta:
        verbose_name_plural = 'Campaign deliveries'
        constraints = [models.UniqueConstraint(fields=['campaign', 'subscriber'], name='unique_campaign_subscriber')]

    def __str__(self):
        return f'{self.campaign}: {self.subscriber}'
