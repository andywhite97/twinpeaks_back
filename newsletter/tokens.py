from django.core import signing


def subscription_token(subscriber, action):
    return signing.dumps({'id': subscriber.pk, 'version': str(subscriber.token_version)}, salt=f'newsletter-{action}')
