import uuid
from datetime import timedelta
from django.core import signing
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from services.models import Solution
from .models import ConfirmationEmail, Subscriber, SubscriptionEvent

CONSENT = 'I agree to receive TwinPeaks articles and occasional service updates by email. I can unsubscribe at any time.'


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    consent = serializers.BooleanField()
    interests = serializers.PrimaryKeyRelatedField(queryset=Solution.objects.filter(is_active=True), many=True, required=False)
    source = serializers.ChoiceField(choices=['blog', 'article'], default='blog')

    def validate_consent(self, value):
        if value is not True:
            raise serializers.ValidationError('Please agree to receive the newsletter.')
        return value


class NewsletterThrottle(AnonRateThrottle):
    rate = '10/hour'


class PublicNewsletterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [NewsletterThrottle]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        response['Referrer-Policy'] = 'no-referrer'
        return response


class Subscribe(PublicNewsletterView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        now = timezone.now()
        with transaction.atomic():
            subscriber, created = Subscriber.objects.get_or_create(email=data['email'].strip().lower(), defaults={'requested_at': now})
            subscriber = Subscriber.objects.select_for_update().get(pk=subscriber.pk)
            # Generic response; do not expose membership or modify a confirmed subscription.
            if created or (subscriber.status != 'confirmed' and subscriber.requested_at < now - timedelta(days=1)):
                subscriber.status = 'pending'
                subscriber.token_version = uuid.uuid4()
                subscriber.requested_at = now
                subscriber.source = data['source']
                subscriber.save()
                subscriber.interests.set(data.get('interests', []))
                SubscriptionEvent.objects.create(subscriber=subscriber, event='signup_requested')
                ConfirmationEmail.objects.create(subscriber=subscriber, token_version=subscriber.token_version)
        return Response({'message': 'If this address needs confirmation, we will email a confirmation link. Please check your inbox and spam folder.'}, status=202)


def subscription_token(subscriber, action):
    return signing.dumps({'id': subscriber.pk, 'version': str(subscriber.token_version)}, salt=f'newsletter-{action}')


class SubscriptionAction(PublicNewsletterView):
    action = 'confirm'

    def post(self, request):
        token = request.data.get('token')
        if not isinstance(token, str) or len(token) > 1000:
            return Response({'message': 'This link is invalid.'}, status=400)
        try:
            data = signing.loads(token, salt=f'newsletter-{self.action}', max_age=48 * 3600 if self.action == 'confirm' else None)
            with transaction.atomic():
                subscriber = Subscriber.objects.select_for_update().get(pk=data['id'], token_version=data['version'])
                now = timezone.now()
                if self.action == 'confirm':
                    if subscriber.status == 'unsubscribed' or subscriber.requested_at < now - timedelta(hours=48):
                        raise signing.BadSignature()
                    if subscriber.status != 'confirmed':
                        subscriber.status = 'confirmed'
                        subscriber.confirmed_at = now
                        subscriber.unsubscribed_at = None
                        subscriber.save()
                        SubscriptionEvent.objects.create(subscriber=subscriber, event='confirmed')
                    message = 'You’re subscribed. Welcome to the TwinPeaks newsletter.'
                else:
                    if subscriber.status != 'unsubscribed':
                        subscriber.status = 'unsubscribed'
                        subscriber.unsubscribed_at = now
                        subscriber.save()
                        SubscriptionEvent.objects.create(subscriber=subscriber, event='unsubscribed')
                    message = 'You’re unsubscribed. You will no longer receive the newsletter.'
        except (signing.BadSignature, Subscriber.DoesNotExist, KeyError, ValueError, TypeError):
            return Response({'message': 'This link is invalid or expired. Please subscribe again for a new confirmation link.'}, status=400)
        return Response({'message': message})


class Unsubscribe(SubscriptionAction):
    action = 'unsubscribe'
