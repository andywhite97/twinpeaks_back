from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from products.models import Product

from .models import ContactMessage, Quotation
from .tasks import send_contact_message_notification, send_quotation_request_notification


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

    @patch('contact.views.send_quotation_request_notification')
    def test_product_quote_request_is_saved_and_notified(self, notification):
        product = Product.objects.create(name='Camera', slug='camera', description='', price='25.00', stock_quantity=2)
        payload = {
            'name': 'Jane Doe',
            'email': 'jane@example.com',
            'phone_number': '26876123456',
            'message': 'Please quote for branding and installation.',
        }

        payload['items'] = [{'product_id': product.id, 'quantity': 1}]
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post('/api/quotations/', payload, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Quotation.objects.count(), 1)
        quote_request = Quotation.objects.get()
        self.assertEqual(quote_request.items.first().product, product)
        notification.assert_called_once_with(quote_request.pk)

    @override_settings(
        CONTACT_FROM_EMAIL='support@twinpeaksinvestment.com',
        CONTACT_FROM_NAME='TwinPeaks Support',
        QUOTE_NOTIFICATION_EMAIL='quotes@twinpeaksinvestment.com',
        QUOTATION_FROM_EMAIL='quotations@twinpeaksinvest.com',
        QUOTATION_FROM_NAME='TwinPeaks Quotations',
    )
    @patch('contact.tasks.Bird')
    def test_quote_request_sends_customer_and_team_emails_through_bird(self, bird):
        product = Product.objects.create(name='Camera', slug='camera', description='', price='25.00', stock_quantity=2)
        quote_request = Quotation.objects.create(name='Jane Doe', email='jane@example.com', phone_number='26876123456', message='Please quote for branding and installation.')
        quote_request.items.create(product=product, title=product.name, description='', quantity=1, unit_price='25.00')

        send_quotation_request_notification(quote_request.pk)

        send = bird.return_value.__enter__.return_value.email.send
        self.assertEqual(send.call_count, 2)
        customer_email = next(call.kwargs for call in send.call_args_list if call.kwargs['to'] == ['jane@example.com'])
        team_email = next(call.kwargs for call in send.call_args_list if call.kwargs['to'] == ['quotes@twinpeaksinvestment.com'])
        self.assertEqual(customer_email['from_'], {'email': 'quotations@twinpeaksinvest.com', 'name': 'TwinPeaks Quotations'})
        self.assertIn('Camera', customer_email['html'])
        self.assertIn('26876123456', team_email['html'])

    @patch('contact.views.send_quotation_accepted_notification')
    def test_issued_quote_can_be_viewed_accepted_and_converted_once(self, notification):
        product = Product.objects.create(name='Camera', slug='camera', description='', price='25.00', stock_quantity=2)
        quotation = Quotation.objects.create(name='Jane Doe', email='jane@example.com', phone_number='26876123456', message='Please quote.')
        quotation.items.create(product=product, title=product.name, quantity=2, unit_price='25.00')
        quotation.issue()

        response = self.client.get(f'/api/quotations/public/{quotation.public_access_token}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['items'][0]['title'], 'Camera')
        self.assertEqual(response.data['currency'], 'SZL')
        quotation.refresh_from_db()
        self.assertEqual(quotation.status, Quotation.Status.VIEWED)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(f'/api/quotations/public/{quotation.public_access_token}/accept/', {}, format='json')
        self.assertEqual(response.status_code, 200)
        quotation.refresh_from_db()
        self.assertEqual(quotation.status, Quotation.Status.ACCEPTED)
        notification.assert_called_once_with(quotation.pk)

        order = quotation.convert_to_order()
        quotation.refresh_from_db()
        self.assertEqual(quotation.status, Quotation.Status.CONVERTED_TO_ORDER)
        self.assertEqual(order.items.count(), 1)
        with self.assertRaises(ValueError):
            quotation.convert_to_order()

    def test_public_pdf_route_is_not_handled_as_a_decision(self):
        quotation = Quotation.objects.create(name='Jane Doe', email='jane@example.com', phone_number='26876123456', message='Please quote.')
        quotation.items.create(title='Custom requirement', quantity=1)
        quotation.issue()

        response = self.client.get(f'/api/quotations/public/{quotation.public_access_token}/pdf/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
