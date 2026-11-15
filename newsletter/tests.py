from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.db import transaction
from django.utils import timezone
from services.models import Solution
from .models import ConfirmationEmail, Subscriber, SubscriptionEvent
from .views import subscription_token


class NewsletterTests(TestCase):
    def setUp(self):
        cache.clear()

    def signup(self, email='reader@example.com', **kwargs):
        return self.client.post('/api/newsletter/subscribe/', {'email': email, 'consent': True, **kwargs}, content_type='application/json')

    def action(self, action, token):
        return self.client.post(f'/api/newsletter/{action}/', {'token': token}, content_type='application/json')

    def test_consent_required(self):
        self.assertEqual(self.signup(consent=False).status_code, 400)
        self.assertFalse(Subscriber.objects.exists())

    @override_settings(NEWSLETTER_EMAIL_PROVIDER='bird', BIRD_API_KEY='synthetic-test-key')
    @patch('newsletter.delivery.Bird')
    def test_signup_sends_immediately_through_bird_once(self, bird):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.signup()
        self.assertEqual(response.status_code, 202)
        item = ConfirmationEmail.objects.get()
        self.assertIsNotNone(item.sent_at)
        with self.captureOnCommitCallbacks(execute=True):
            self.signup()
        sender = bird.return_value.__enter__.return_value.email.send
        sender.assert_called_once()
        self.assertEqual(sender.call_args.kwargs['to'], ['reader@example.com'])
        self.assertIn('Confirm my subscription', sender.call_args.kwargs['html'])

    def test_existing_unsent_signup_sends_on_resubmission(self):
        self.signup()  # Simulate a record from the previous queue-only deployment.
        with self.captureOnCommitCallbacks(execute=True):
            self.signup()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(ConfirmationEmail.objects.count(), 1)

    def test_immediate_failure_is_recorded_and_resubmission_retries(self):
        with patch('newsletter.delivery.send_mail', side_effect=RuntimeError('Synthetic failure')):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.signup()
        self.assertEqual(response.status_code, 202)
        self.assertTrue(ConfirmationEmail.objects.get().failed)
        with self.captureOnCommitCallbacks(execute=True):
            self.signup()
        item = ConfirmationEmail.objects.get()
        self.assertIsNotNone(item.sent_at)
        self.assertFalse(item.failed)
        self.assertEqual(item.attempts, 2)

    def test_immediate_retries_are_bounded(self):
        with patch('newsletter.delivery.send_mail', side_effect=RuntimeError('Synthetic failure')) as send:
            for _ in range(4):
                with self.captureOnCommitCallbacks(execute=True):
                    self.signup()
        self.assertEqual(send.call_count, 3)
        self.assertEqual(ConfirmationEmail.objects.get().attempts, 3)

    def test_rollback_never_sends_confirmation(self):
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    self.signup()
                    raise RuntimeError('Rollback')
        self.assertFalse(Subscriber.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_confirmed_resubmission_never_sends(self):
        self.signup()
        Subscriber.objects.update(status='confirmed')
        with self.captureOnCommitCallbacks(execute=True):
            self.signup()
        self.assertEqual(len(mail.outbox), 0)

    def test_duplicate_signup_does_not_duplicate_mail_or_reveal_status(self):
        first = self.signup('Reader@Example.com')
        second = self.signup()
        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(Subscriber.objects.count(), 1)
        self.assertEqual(ConfirmationEmail.objects.count(), 1)
        self.assertEqual(Subscriber.objects.get().status, 'pending')

    def test_confirm_unsubscribe_and_no_get_mutation(self):
        self.signup()
        subscriber = Subscriber.objects.get()
        confirm = subscription_token(subscriber, 'confirm')
        unsubscribe = subscription_token(subscriber, 'unsubscribe')
        self.assertEqual(self.client.get('/api/newsletter/confirm/').status_code, 405)
        self.assertEqual(self.action('confirm', confirm).status_code, 200)
        self.assertEqual(self.action('confirm', confirm).status_code, 200)
        self.assertEqual(SubscriptionEvent.objects.filter(event='confirmed').count(), 1)
        self.assertEqual(self.action('unsubscribe', confirm).status_code, 400)
        self.assertEqual(self.action('unsubscribe', unsubscribe).status_code, 200)
        self.assertEqual(self.action('unsubscribe', unsubscribe).status_code, 200)
        self.assertEqual(self.action('confirm', confirm).status_code, 400)
        subscriber.refresh_from_db()
        self.assertEqual(subscriber.status, 'unsubscribed')

    def test_expired_and_tampered_confirmation(self):
        self.signup()
        subscriber = Subscriber.objects.get()
        token = subscription_token(subscriber, 'confirm')
        self.assertEqual(self.action('confirm', token + 'x').status_code, 400)
        Subscriber.objects.update(requested_at=timezone.now()-timedelta(days=3))
        self.assertEqual(self.action('confirm', token).status_code, 400)

    def test_confirmed_interests_cannot_be_changed_by_anonymous_signup(self):
        interest = Solution.objects.create(title='Networking')
        self.signup(interests=[interest.pk])
        subscriber = Subscriber.objects.get()
        self.action('confirm', subscription_token(subscriber, 'confirm'))
        self.signup(interests=[])
        self.assertEqual(list(subscriber.interests.values_list('pk', flat=True)), [interest.pk])

    def test_outbox_sends_once_and_no_marketing(self):
        self.signup()
        call_command('send_newsletter_confirmations', stdout=StringIO())
        call_command('send_newsletter_confirmations', stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/newsletter/confirm#token=', mail.outbox[0].body)
        self.assertIn('/newsletter/unsubscribe#token=', mail.outbox[0].body)
        self.assertIsNotNone(ConfirmationEmail.objects.get().sent_at)

    def test_failed_email_remains_retryable(self):
        self.signup()
        with patch('newsletter.delivery.send_mail', side_effect=RuntimeError('Synthetic failure')):
            call_command('send_newsletter_confirmations', stdout=StringIO(), stderr=StringIO())
        self.assertTrue(ConfirmationEmail.objects.get().failed)
        call_command('send_newsletter_confirmations', stdout=StringIO())
        self.assertIsNotNone(ConfirmationEmail.objects.get().sent_at)

    def test_unsubscribed_request_is_not_emailed(self):
        self.signup()
        subscriber = Subscriber.objects.get()
        self.action('unsubscribe', subscription_token(subscriber, 'unsubscribe'))
        call_command('send_newsletter_confirmations', stdout=StringIO())
        self.assertEqual(len(mail.outbox), 0)
