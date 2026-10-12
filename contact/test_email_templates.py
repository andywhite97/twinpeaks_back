from datetime import date
from unittest.mock import patch

from django.test import TestCase, override_settings

from .models import ContactMessage, Quotation
from .tasks import (
    render_email, send_contact_message_notification,
    send_quotation_request_notification, send_quotation_issued_notification,
    send_quotation_accepted_notification,
    send_quotation_declined_notification,
)


@override_settings(PUBLIC_SITE_URL="https://example.invalid/", QUOTATION_FROM_EMAIL="quotes@example.invalid")
class EmailTemplateTests(TestCase):
    def setUp(self):
        self.message = ContactMessage.objects.create(name='<script>alert("name")</script>', email="customer@example.invalid", message='<img src=x onerror=alert(1)>\nSecond line')
        self.quote = Quotation.objects.create(name=self.message.name, email=self.message.email,
            phone_number="26876123456", message=self.message.message,
            internal_notes="SECRET INTERNAL NOTES", total="1200.50", valid_until=date(2026, 11, 12))
        self.quote.items.create(title="Network & cabling", quantity=2)

    @patch("contact.tasks.Bird")
    def test_all_notifications_send_branded_html_and_plain_text_without_leaking_notes(self, bird):
        send_contact_message_notification(self.message)
        send_quotation_request_notification(self.quote.pk)
        send_quotation_issued_notification(self.quote.pk)
        send_quotation_accepted_notification(self.quote.pk)
        calls = bird.return_value.__enter__.return_value.email.send.call_args_list
        self.assertEqual(len(calls), 7)
        for call in calls:
            payload = call.kwargs
            self.assertIn('<!doctype html>', payload["html"])
            self.assertIn('#0B3D91', payload["html"])
            self.assertIn("TwinPeaks Investment", payload["text"])
            self.assertIn('&lt;script&gt;', payload["html"])
            self.assertNotIn('<script>', payload["html"])
            self.assertNotIn('<img src=x', payload["html"])
            self.assertNotIn('SECRET INTERNAL NOTES', payload["html"] + payload["text"])
        internal = calls[1].kwargs
        self.assertIn('&lt;img', internal["html"])
        self.assertIn('<br>Second line', internal["html"])
        self.assertIn('<img src=x', internal["text"])
        issued = calls[4].kwargs
        url = f"https://example.invalid/quotations/{self.quote.public_access_token}"
        self.assertIn(f'href="{url}"', issued["html"])
        self.assertIn(url, issued["text"])
        self.assertIn('SZL 1200.50', issued["text"])
        self.assertIn('12 November 2026', issued["html"])
        self.assertIn('quotes@example.invalid', issued["html"])
        self.assertIn(f'/api/quotations/public/{self.quote.public_access_token}/pdf/', issued["html"])
        self.assertNotIn(str(self.quote.public_access_token), calls[3].kwargs["html"])

    def test_optional_expiry_and_company_fields_do_not_render_placeholder_values(self):
        self.quote.valid_until = None
        html, text = render_email("quote_issued", "Your quotation", {"quotation": self.quote, "quotation_url": "https://example.invalid/quotations/test"})
        self.assertNotIn('Valid until', html + text)
        self.assertNotIn('None', html + text)
        html, text = render_email("quote_internal", "New request", {"quotation": self.quote, "items": []})
        self.assertNotIn('Company:', html + text)

    @patch("contact.tasks.Bird")
    def test_decline_confirmation_and_team_notification_are_distinct(self, bird):
        self.quote.status = Quotation.Status.DECLINED
        self.quote.decline_reason = '<script>private customer reason</script>'
        self.quote.save()
        send_quotation_declined_notification(self.quote.pk)
        calls = bird.return_value.__enter__.return_value.email.send.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertIn('Declined', calls[0].kwargs['html'])
        self.assertNotIn('next steps.', calls[0].kwargs['html'])
        self.assertNotIn('private customer reason', calls[0].kwargs['html'])
        self.assertIn('&lt;script&gt;private customer reason', calls[1].kwargs['html'])

    def test_general_template_escapes_message_and_has_brand_assets(self):
        html, text = render_email('general', 'Hello', {'name': 'Alex', 'email_content': '<script>Example</script>\nNext line'})
        self.assertIn('&lt;script&gt;Example', html)
        self.assertIn('<script>Example</script>', text)
        self.assertIn('/assets/email/logo.png', html)

    def test_email_palettes_keep_normal_text_contrast_in_both_modes(self):
        def luminance(hex_color):
            channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
            return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

        pairs = [
            ('#082447', '#FFFFFF'), ('#5B7191', '#FFFFFF'), ('#405670', '#EEF5FD'),
            ('#FFFFFF', '#032744'), ('#FFFFFF', '#006BEF'), ('#FFFFFF', '#0B3D91'),
            ('#E5F2FF', '#10263F'), ('#E5F2FF', '#18344F'), ('#85C9FF', '#18344F'),
            ('#B9C9DB', '#10263F'), ('#BFF2DC', '#103D32'), ('#087A4E', '#E5F6EF'),
        ]
        for foreground, background in pairs:
            light, dark = sorted([luminance(foreground), luminance(background)], reverse=True)
            with self.subTest(foreground=foreground, background=background):
                self.assertGreaterEqual((light + 0.05) / (dark + 0.05), 4.5)
        html, _ = render_email('general', 'Test', {'name': 'Alex', 'email_content': 'Message'})
        self.assertIn('name="color-scheme" content="light dark"', html)
        self.assertIn('@media (prefers-color-scheme: dark)', html)
        self.assertIn('[data-ogsc]', html)
        self.assertIn('class="email-content"', html)
        self.assertIn('class="logo-plate"', html)

    @patch('contact.views.send_quotation_declined_notification')
    def test_decline_endpoint_notifies_once_after_commit(self, notification):
        self.quote.items.create(title='Installation', quantity=1)
        self.quote.issue()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(f'/api/quotations/public/{self.quote.public_access_token}/decline/', data={})
        self.assertEqual(response.status_code, 200)
        notification.assert_called_once_with(self.quote.pk)
