"""Local illustrative previews: no database access, subscriptions, or email sends."""
from pathlib import Path
from shutil import copytree
from django.core.management.base import BaseCommand
from django.test import override_settings
from newsletter.emails import CONFIRMATION_SUBJECT, render_newsletter_email


class Command(BaseCommand):
    help = 'Render newsletter confirmation and update previews with synthetic content.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='newsletter-previews')

    def handle(self, *args, **options):
        destination = Path(options['output']).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        context = {
            'company': None,
            'confirmation_url': 'https://example.invalid/newsletter/confirm#token=preview-only-not-a-real-token',
            'unsubscribe_url': 'https://example.invalid/newsletter/unsubscribe#token=preview-only-not-a-real-token',
            'featured': {'title': 'Choosing CCTV for your business', 'category': 'Security', 'reading_minutes': 6,
                'excerpt': 'Start with the coverage, recording and monitoring your premises need.',
                'url': 'https://example.invalid/blog/choosing-cctv', 'image': 'assets/security.jpg',
                'image_alt': 'Security technology illustration'},
            'articles': [
                {'title': 'Why your office Wi-Fi keeps dropping', 'category': 'Networking', 'url': 'https://example.invalid/blog/office-wifi'},
                {'title': 'Choosing your first POS system', 'category': 'POS solutions', 'url': 'https://example.invalid/blog/first-pos'},
            ],
        }
        links = []
        for template, subject in [('confirmation', CONFIRMATION_SUBJECT), ('update', 'Smarter security. Better-connected business.')]:
            with override_settings(EMAIL_ASSET_BASE_URL='assets', PUBLIC_SITE_URL='https://example.invalid'):
                html, text = render_newsletter_email(template, subject, context)
            (destination / f'{template}.html').write_text(html, encoding='utf-8')
            (destination / f'{template}.txt').write_text(text, encoding='utf-8')
            for theme, rule in [('light', '@media not all'), ('dark', '@media all')]:
                (destination / f'{template}-{theme}.html').write_text(html.replace('@media (prefers-color-scheme: dark)', rule), encoding='utf-8')
                links.append(f'<li><a href="{template}-{theme}.html">{template.title()} — {theme}</a></li>')
        assets = Path(__file__).resolve().parents[5] / 'front-v2-publish/public/assets/email'
        copytree(assets, destination / 'assets', dirs_exist_ok=True)
        (destination / 'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Newsletter previews</title><body style="font:18px/1.8 Arial;padding:32px;background:#F6F9FD;color:#082447"><h1>TwinPeaks newsletter emails</h1><p>Illustrative content only. No emails sent. Browser previews simulate the authored palettes; mailbox rendering may differ.</p><ul>' + ''.join(links) + '</ul></body></html>', encoding='utf-8')
        self.stdout.write(f'Rendered newsletter previews: {destination / "index.html"}')
