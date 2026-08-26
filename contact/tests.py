from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import ContactMessage


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
