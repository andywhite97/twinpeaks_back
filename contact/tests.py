from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import ContactMessage


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True,
)
class ContactMessageTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_contact_message_creation_sends_notification_email(self):
        response = self.client.post(
            '/api/contact/',
            {
                'name': 'Jane Doe',
                'email': 'jane@example.com',
                'message': 'Hello, I would like more info.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ContactMessage.objects.count(), 1)
        message = ContactMessage.objects.first()
        self.assertEqual(message.name, 'Jane Doe')
        self.assertEqual(message.email, 'jane@example.com')
        self.assertEqual(message.message, 'Hello, I would like more info.')

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, f'New Contact Message from {message.name}')
        self.assertIn(message.message, sent_email.body)
        self.assertEqual(sent_email.to, ['andileblessinghlophe@gmail.com'])
