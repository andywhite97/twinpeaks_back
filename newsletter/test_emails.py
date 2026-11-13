from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from blog.models import BlogPost
from contact.tasks import render_email
from .emails import confirmation_email, newsletter_update_email
from .models import Subscriber, ConfirmationEmail


@override_settings(PUBLIC_SITE_URL='https://example.invalid')
class NewsletterEmailTests(TestCase):
    def setUp(self):
        self.subscriber = Subscriber.objects.create(email='reader@example.invalid', requested_at=timezone.now(), status='confirmed')
        self.post = BlogPost.objects.create(title='<script>unsafe</script> & useful', slug='useful-guide', body='<p>Guide</p>', excerpt='<img src=x onerror=alert(1)>', status='published', published_at=timezone.now())

    def test_confirmation_contains_both_actions_and_small_logo(self):
        html, text = confirmation_email(self.subscriber)
        for content in (html, text):
            self.assertIn('/newsletter/confirm#token=', content)
            self.assertIn('/newsletter/unsubscribe#token=', content)
            self.assertIn('48 hours', content)
        self.assertIn('width="188"', html)
        self.assertIn('prefers-color-scheme: dark', html)
        self.assertIn('[data-ogsc]', html)
        self.assertNotIn('intended for the recipient only', html)

    def test_digest_escapes_content_and_has_recipient_unsubscribe(self):
        html, text = newsletter_update_email(self.subscriber, self.post, subject='Journal update')
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img src=x', html)
        self.assertIn('<script>unsafe</script>', text)
        self.assertIn('https://example.invalid/blog/useful-guide', html)
        self.assertIn('/newsletter/unsubscribe#token=', html)
        self.assertNotIn('Also in the journal', html)
        self.assertNotIn('None', html + text)

    def test_digest_rejects_drafts_future_articles_and_unconfirmed_recipients(self):
        self.post.status = 'draft'
        with self.assertRaises(ValueError):
            newsletter_update_email(self.subscriber, self.post, subject='Test')
        self.post.status = 'published'
        self.post.published_at = timezone.now() + timedelta(days=1)
        with self.assertRaises(ValueError):
            newsletter_update_email(self.subscriber, self.post, subject='Test')
        self.post.published_at = timezone.now()
        self.subscriber.status = 'unsubscribed'
        with self.assertRaises(ValueError):
            newsletter_update_email(self.subscriber, self.post, subject='Test')

    def test_sender_delivers_multipart_confirmation(self):
        self.subscriber.status = 'pending'
        self.subscriber.save()
        ConfirmationEmail.objects.create(subscriber=self.subscriber, token_version=self.subscriber.token_version)
        call_command('send_newsletter_confirmations', stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].alternatives[0].mimetype, 'text/html')
        self.assertIn('Confirm my subscription', mail.outbox[0].alternatives[0].content)

    def test_zero_accepted_messages_stays_retryable(self):
        self.subscriber.status = 'pending'
        self.subscriber.save()
        item = ConfirmationEmail.objects.create(subscriber=self.subscriber, token_version=self.subscriber.token_version)
        with patch('newsletter.management.commands.send_newsletter_confirmations.send_mail', return_value=0):
            call_command('send_newsletter_confirmations', stdout=StringIO(), stderr=StringIO())
        item.refresh_from_db()
        self.assertTrue(item.failed)
        self.assertIsNone(item.sent_at)

    def test_existing_transactional_branding_remains_unchanged(self):
        html, _ = render_email('general', 'Test', {'company': None, 'name': 'Alex', 'email_content': 'Hello'})
        self.assertIn('width="250"', html)
        self.assertIn('intended for the recipient only', html)

    @override_settings(NEWSLETTER_EMAIL_PROVIDER='bird', BIRD_API_KEY='synthetic-test-key')
    @patch('newsletter.management.commands.send_newsletter_confirmations.Bird')
    def test_bird_delivery_is_recipient_scoped_and_not_repeated(self, bird):
        self.subscriber.status = 'pending'
        self.subscriber.save()
        item = ConfirmationEmail.objects.create(subscriber=self.subscriber, token_version=self.subscriber.token_version)
        other = Subscriber.objects.create(email='other@example.invalid', requested_at=timezone.now())
        untouched = ConfirmationEmail.objects.create(subscriber=other, token_version=other.token_version)
        for _ in range(2):
            call_command('send_newsletter_confirmations', recipient=self.subscriber.email, stdout=StringIO())
        sender = bird.return_value.__enter__.return_value.email.send
        sender.assert_called_once()
        self.assertEqual(sender.call_args.kwargs['to'], [self.subscriber.email])
        self.assertFalse(sender.call_args.kwargs['track_clicks'])
        self.assertIn('Confirm my subscription', sender.call_args.kwargs['html'])
        item.refresh_from_db()
        untouched.refresh_from_db()
        self.assertIsNotNone(item.sent_at)
        self.assertEqual(untouched.attempts, 0)

    @override_settings(NEWSLETTER_EMAIL_PROVIDER='bird', BIRD_API_KEY='')
    @patch('newsletter.management.commands.send_newsletter_confirmations.Bird')
    def test_missing_bird_key_never_uses_process_credentials(self, bird):
        self.subscriber.status = 'pending'
        self.subscriber.save()
        item = ConfirmationEmail.objects.create(subscriber=self.subscriber, token_version=self.subscriber.token_version)
        call_command('send_newsletter_confirmations', stdout=StringIO(), stderr=StringIO())
        bird.assert_not_called()
        item.refresh_from_db()
        self.assertTrue(item.failed)
        self.assertIsNone(item.sent_at)
