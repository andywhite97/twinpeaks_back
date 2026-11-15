"""Branded newsletter rendering. Rendering never sends a campaign."""
from urllib.parse import quote, urlsplit

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from core.models import CompanyProfile
from .tokens import subscription_token

CONFIRMATION_SUBJECT = 'Confirm your TwinPeaks newsletter subscription'


def render_newsletter_email(template, subject, context):
    if template not in {'confirmation', 'update'}:
        raise ValueError('Unknown newsletter email template')
    site = settings.PUBLIC_SITE_URL.rstrip('/')
    values = {
        'company': context.get('company') if 'company' in context else CompanyProfile.objects.first(),
        'site_url': site,
        'solutions_url': site + '/solutions',
        'support_email': settings.CONTACT_FROM_EMAIL,
        'year': timezone.localdate().year,
        'assets_url': getattr(settings, 'EMAIL_ASSET_BASE_URL', site + '/assets/email').rstrip('/'),
        'banner_image': 'technology.jpg',
        'logo_width': 188,
        **context,
        'subject': subject,
    }
    stem = f'newsletter/emails/{template}'
    return render_to_string(stem + '.html', values), render_to_string(stem + '.txt', values).strip()


def subscription_url(subscriber, action):
    return f'{settings.PUBLIC_SITE_URL.rstrip("/")}/newsletter/{action}#token={quote(subscription_token(subscriber, action))}'


def confirmation_email(subscriber):
    return render_newsletter_email('confirmation', CONFIRMATION_SUBJECT, {
        'confirmation_url': subscription_url(subscriber, 'confirm'),
        'unsubscribe_url': subscription_url(subscriber, 'unsubscribe'),
    })


def newsletter_update_email(subscriber, featured, articles=(), *, subject):
    """Prepare a recipient-specific digest for the future campaign sender."""
    if subscriber.status != 'confirmed':
        raise ValueError('Newsletter updates require a confirmed subscription')
    selected = [featured, *articles]
    now = timezone.now()
    if len({post.pk for post in selected}) != len(selected):
        raise ValueError('Select each article only once')
    if len(selected) > 3:
        raise ValueError('Choose one featured article and up to two additional articles')
    cards = []
    for post in selected:
        if not post.pk or post.status != 'published' or not post.published_at or post.published_at > now:
            raise ValueError('Only published articles may appear in a newsletter')
        image = post.cover_image.url if post.cover_image else ''
        # Production email assets must be absolute HTTPS URLs.
        if image and (urlsplit(image).scheme != 'https' or not urlsplit(image).netloc):
            image = ''
        cards.append({
            'title': post.title, 'excerpt': post.excerpt,
            'url': settings.PUBLIC_SITE_URL.rstrip('/') + '/blog/' + quote(post.slug, safe=''),
            'image': image, 'image_alt': post.cover_alt,
            'category': post.category.name if post.category else 'Insights',
            'reading_minutes': post.reading_minutes,
        })
    return render_newsletter_email('update', subject, {
        'featured': cards[0], 'articles': cards[1:],
        'unsubscribe_url': subscription_url(subscriber, 'unsubscribe'),
    })
