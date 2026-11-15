from datetime import timedelta
from unittest.mock import patch
from bird import APIStatusError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from blog.models import BlogPost
from services.models import Solution
from .models import Campaign, CampaignDelivery, Subscriber
from .campaigns import audience, render_campaign, review_token, start_campaign, send_next, send_message


class CampaignTests(TestCase):
    def setUp(self):
        self.post = BlogPost.objects.create(title='Useful guide', slug='guide', excerpt='Advice', body='<p>Content</p>', status='published', published_at=timezone.now())
        self.campaign = Campaign.objects.create(name='Launch', subject='Latest insights', introduction='<script>hello</script>', featured=self.post)
        self.reader = Subscriber.objects.create(email='reader@example.invalid', status='confirmed', requested_at=timezone.now(), confirmed_at=timezone.now())
        self.admin = get_user_model().objects.create_superuser('admin@example.invalid', 'test-only')
        self.client.force_login(self.admin)
        self.review_url = f'/admin/newsletter/campaign/{self.campaign.pk}/review/'
        self.next_url = f'/admin/newsletter/campaign/{self.campaign.pk}/next/'

    def start(self):
        return start_campaign(self.campaign.pk, review_token(self.campaign))

    def test_audience_requires_confirmation_and_matches_any_interest_once(self):
        Subscriber.objects.create(email='pending@example.invalid', requested_at=timezone.now())
        Subscriber.objects.create(email='out@example.invalid', requested_at=timezone.now(), status='unsubscribed', confirmed_at=timezone.now())
        a = Solution.objects.create(title='Security')
        b = Solution.objects.create(title='Networking')
        self.reader.interests.add(a, b)
        self.campaign.interests.add(a, b)
        self.assertEqual(list(audience(self.campaign)), [self.reader])

    def test_preview_escapes_introduction_and_never_sends(self):
        response = self.client.get(f'/admin/newsletter/campaign/{self.campaign.pk}/preview/')
        self.assertContains(response, '&lt;script&gt;hello&lt;/script&gt;')
        self.assertNotContains(response, '<script>hello</script>')
        self.assertEqual(response['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_articles_and_duplicate_articles_rejected(self):
        self.campaign.article_two = self.post
        with self.assertRaises(ValidationError):
            render_campaign(self.campaign)
        self.campaign.article_two = None
        self.post.published_at = timezone.now() + timedelta(days=1)
        self.post.save()
        with self.assertRaises(ValidationError):
            render_campaign(self.campaign)

    def test_changed_audience_invalidates_review(self):
        token = review_token(self.campaign)
        Subscriber.objects.create(email='new@example.invalid', requested_at=timezone.now(), status='confirmed', confirmed_at=timezone.now())
        with self.assertRaises(ValidationError):
            start_campaign(self.campaign.pk, token)
        self.assertFalse(CampaignDelivery.objects.exists())

    def test_snapshot_and_duplicate_start_send_only_once(self):
        token = review_token(self.campaign)
        self.start()
        start_campaign(self.campaign.pk, token)
        self.post.title = 'Changed later'
        self.post.save()
        for _ in range(3):
            send_next(self.campaign.pk)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Useful guide', mail.outbox[0].body)
        self.assertNotIn('Changed later', mail.outbox[0].body)
        self.assertIn('/newsletter/unsubscribe#token=', mail.outbox[0].body)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'complete')
        self.assertEqual(CampaignDelivery.objects.get().status, 'accepted')

    def test_unsubscribe_before_delivery_skips_recipient(self):
        self.start()
        Subscriber.objects.filter(pk=self.reader.pk).update(status='unsubscribed')
        send_next(self.campaign.pk)
        self.assertEqual(CampaignDelivery.objects.get().status, 'skipped')
        self.assertEqual(len(mail.outbox), 0)

    def test_resume_sends_remaining_recipient_with_own_link(self):
        Subscriber.objects.create(email='second@example.invalid', requested_at=timezone.now(), status='confirmed', confirmed_at=timezone.now())
        self.start()
        send_next(self.campaign.pk)
        self.assertEqual(CampaignDelivery.objects.filter(status='pending').count(), 1)
        send_next(self.campaign.pk)
        self.assertEqual(len(mail.outbox), 2)
        self.assertNotEqual(mail.outbox[0].body, mail.outbox[1].body)
        self.assertEqual(mail.outbox[0].to, ['reader@example.invalid'])
        self.assertEqual(mail.outbox[1].to, ['second@example.invalid'])

    def test_empty_audience_cannot_start(self):
        self.reader.status = 'pending'
        self.reader.save()
        with self.assertRaises(ValidationError):
            self.start()
        self.assertFalse(CampaignDelivery.objects.exists())

    def test_started_campaign_cannot_be_edited_through_admin(self):
        self.start()
        self.client.post(f'/admin/newsletter/campaign/{self.campaign.pk}/change/', {
            'name':'Changed', 'subject':'Forged subject', 'status':'draft', 'featured':self.post.pk, '_save':'Save'})
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.subject, 'Latest insights')
        self.assertEqual(self.campaign.status, 'sending')

    def test_timeout_is_not_retried(self):
        self.start()
        with patch('newsletter.campaigns.send_message', side_effect=TimeoutError) as send:
            send_next(self.campaign.pk)
            send_next(self.campaign.pk)
        send.assert_called_once()
        self.assertEqual(CampaignDelivery.objects.get().status, 'unknown')

    def test_interrupted_claim_is_not_retried(self):
        self.start()
        CampaignDelivery.objects.update(status='sending')
        send_next(self.campaign.pk)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(CampaignDelivery.objects.get().status, 'sending')

    def test_provider_rejection_is_visible(self):
        self.start()
        with patch('newsletter.campaigns.send_message', side_effect=APIStatusError('private', status_code=422, type='validation_error')):
            send_next(self.campaign.pk)
        item = CampaignDelivery.objects.get()
        self.assertEqual(item.status, 'failed')
        self.assertNotIn('private', item.detail)

    def test_test_send_has_no_campaign_deliveries(self):
        response = self.client.post(self.review_url, {'action':'test', 'recipient':'test@example.invalid'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(mail.outbox[0].to, ['test@example.invalid'])
        self.assertTrue(mail.outbox[0].subject.startswith('[TEST]'))
        self.assertFalse(CampaignDelivery.objects.exists())

    def test_gets_do_not_send_and_send_requires_permission(self):
        self.assertEqual(self.client.get(self.next_url).status_code, 405)
        self.assertEqual(self.client.get(self.review_url).status_code, 200)
        staff = get_user_model().objects.create_user('viewer@example.invalid', is_staff=True)
        staff.user_permissions.add(Permission.objects.get(codename='view_campaign'), Permission.objects.get(codename='change_campaign'))
        self.client.force_login(staff)
        self.assertEqual(self.client.post(self.review_url, {'action':'start','review_token':review_token(self.campaign)}).status_code, 403)
        self.assertEqual(self.client.post(self.next_url).status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(self.review_url, {'action':'start','review_token':review_token(self.campaign)}).status_code, 403)

    def test_admin_start_then_progress(self):
        response = self.client.post(self.review_url, {'action':'start','review_token':review_token(self.campaign)})
        self.assertContains(response, 'data-auto-start="yes"')
        response = self.client.post(self.next_url)
        self.assertEqual(response.json()['counts']['accepted'], 1)
        self.assertEqual(self.client.post(self.next_url).json()['status'], 'complete')

    @override_settings(NEWSLETTER_EMAIL_PROVIDER='bird', BIRD_API_KEY='synthetic')
    @patch('newsletter.campaigns.Bird')
    def test_bird_send_uses_one_recipient_and_no_sdk_retries(self, bird):
        send_message('reader@example.invalid', 'Subject', '<p>HTML</p>', 'Text')
        bird.assert_called_once_with(api_key='synthetic', timeout=20, max_retries=0)
        sender = bird.return_value.__enter__.return_value.email.send
        self.assertEqual(sender.call_args.kwargs['to'], ['reader@example.invalid'])
        self.assertFalse(sender.call_args.kwargs['track_clicks'])
