import uuid
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
