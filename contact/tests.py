from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import ContactMessage
from .tasks import send_contact_message_notification


class ContactMessageTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('contact.views.send_contact_message_notification')
    def test_contact_message_creation_sends_notification(self, notification):
        payload = {
            'name': 'Jane Doe',
            'email': 'jane@example.com',
            'message': 'Hello, I would like more info.',
        }
        response = self.client.post('/api/contact/', payload, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ContactMessage.objects.count(), 1)
        message = ContactMessage.objects.first()
        self.assertEqual(message.name, 'Jane Doe')
        self.assertEqual(message.email, 'jane@example.com')
        self.assertEqual(message.message, 'Hello, I would like more info.')

        notification.assert_called_once_with(message)

    @patch('contact.views.send_contact_message_notification')
    def test_invalid_contact_message_is_rejected_without_notification(self, notification):
        response = self.client.post(
            '/api/contact/',
            {'name': 'Jane Doe', 'email': 'not-an-email', 'message': 'Hello'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ContactMessage.objects.count(), 0)
        notification.assert_not_called()

    def test_contact_messages_are_not_visible_to_anonymous_visitors(self):
        response = self.client.get('/api/contact/messages/')

        self.assertIn(response.status_code, (401, 403))

    def test_admin_can_view_contact_messages(self):
        ContactMessage.objects.create(name='Jane Doe', email='jane@example.com', message='Hello')
        admin = get_user_model().objects.create_superuser('admin@example.com', 'secure-password')
        self.client.force_authenticate(admin)

        response = self.client.get('/api/contact/messages/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['email'], 'jane@example.com')

    @override_settings(
        CONTACT_FROM_EMAIL='support@twinpeaksinvestment.com',
        CONTACT_FROM_NAME='TwinPeaks Support',
        CONTACT_NOTIFICATION_EMAIL='team@twinpeaksinvestment.com',
    )
    @patch('contact.tasks.Bird')
    def test_contact_message_sends_customer_acknowledgement(self, bird):
        message = ContactMessage.objects.create(
            name='Jane Doe', email='jane@example.com', message='I need help with an order.'
        )

        send_contact_message_notification(message)

        send = bird.return_value.__enter__.return_value.email.send
        self.assertEqual(send.call_count, 2)
        acknowledgement = next(call.kwargs for call in send.call_args_list if call.kwargs['to'] == ['jane@example.com'])
        self.assertEqual(acknowledgement['subject'], 'We received your message | TwinPeaks Investment')
        self.assertEqual(acknowledgement['from_'], {'email': 'support@twinpeaksinvestment.com', 'name': 'TwinPeaks Support'})
        self.assertIn('We have received your message', acknowledgement['html'])
        self.assertIn('contact you shortly', acknowledgement['html'])
