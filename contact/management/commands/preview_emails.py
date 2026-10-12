"""Render illustrative emails locally without writing records or sending mail."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from shutil import copytree

from django.core.management.base import BaseCommand
from django.test import override_settings
from django.utils import timezone

from contact.tasks import render_email


class Command(BaseCommand):
    help = "Write sample HTML/text emails and a preview index. No emails are sent."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="email-previews")

    def handle(self, *args, **options):
        destination = Path(options["output"]).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        quotation = SimpleNamespace(
            name="Alex Dlamini", quote_number="TP-Q-DEMO-0001", email="alex@example.invalid",
            phone_number="+268 7600 0000", company_name="Example Business",
            address="Mbabane, Eswatini", message="We need reliable office Wi-Fi and structured cabling.\nPlease include installation and handover.",
            currency="SZL", total=Decimal("12500.00"), valid_until=date(2026, 11, 12),
            created_at=timezone.now(), accepted_at=timezone.now(), declined_at=timezone.now(), decline_reason="We would like to revisit this scope next quarter.",
        )
        context = {
            "message": SimpleNamespace(pk=42, created_at=timezone.now(), name=quotation.name, email=quotation.email, message="We would like to discuss security for our premises.\nPlease contact us about a site assessment."),
            "quotation": quotation,
            "items": [SimpleNamespace(title="Network Infrastructure", quantity=1), SimpleNamespace(title="IT Support & Maintenance", quantity=1)],
            "quotation_url": "https://example.invalid/quotations/demo-preview-only",
            "quotation_pdf_url": "https://example.invalid/quotations/demo-preview-only/pdf/",
            "company": SimpleNamespace(phone="", address="Eswatini"),
            "name": quotation.name,
            "email_content": "I hope this email finds you well.\n\nLet’s discuss the right technology for your workspace. Please let us know if you have any questions or need further information.",
        }
        templates = [
            ("general", "Built on Vision, Driven by Progress", False),
            ("contact_acknowledgement", "We received your message", False),
            ("contact_internal", "New website enquiry", False),
            ("quote_acknowledgement", "We received your quote request", True),
            ("quote_internal", "New quote request", False),
            ("quote_issued", "Your quotation is ready", True),
            ("quote_accepted", "Quotation accepted", True),
            ("quote_accepted_internal", "Quotation accepted — team notification", False),
            ("quote_declined", "Quotation decision received — declined", True),
            ("quote_declined_internal", "Quotation declined — team notification", False),
        ]
        links = []
        for template, subject, customer in templates:
            with override_settings(EMAIL_ASSET_BASE_URL="assets"):
                html, text = render_email(template, subject, context, quotation_sender=customer)
            (destination / f"{template}.html").write_text(html, encoding="utf-8")
            (destination / f"{template}-light.html").write_text(html.replace('@media (prefers-color-scheme: dark)', '@media not all'), encoding="utf-8")
            (destination / f"{template}-dark.html").write_text(html.replace('@media (prefers-color-scheme: dark)', '@media all'), encoding="utf-8")
            (destination / f"{template}.txt").write_text(text, encoding="utf-8")
            links.append(f'<li style="margin:16px 0;">{subject}: <a href="{template}.html">Adaptive</a> · <a href="{template}-light.html">Light</a> · <a href="{template}-dark.html">Dark</a> · <a href="{template}.txt">Plain text</a></li>')
        featured = [("general", "General / branded"), ("contact_acknowledgement", "Enquiry acknowledgement"), ("quote_acknowledgement", "Quotation request"), ("quote_issued", "Quotation issued"), ("quote_accepted", "Quotation decision")]
        gallery = ''.join(f'<article><h2 style="font-size:15px;">{label}</h2><iframe title="{label}" data-template="{template}" src="{template}-light.html" style="width:100%;height:1250px;border:1px solid #DCE7F2;border-radius:10px;background:white;"></iframe></article>' for template, label in featured)
        index = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TwinPeaks email previews</title><body style="font-family:Arial,sans-serif;margin:24px;padding:12px;background:#F6F9FD;color:#07152D;"><h1>TwinPeaks email collection</h1><p>Illustrative content only. No emails sent.</p><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;">' + gallery + '</div><h2>All previews</h2><ul>' + "".join(links) + '</ul></body></html>'
        controls = '<p>Browser simulations of the authored themes; email apps may also apply their own colour changes.</p><p><button type="button" onclick="setTheme(\'light\')">Light preview</button> <button type="button" onclick="setTheme(\'dark\')">Dark preview</button></p><script>function setTheme(theme){document.querySelectorAll(\"iframe[data-template]\").forEach(frame=>{frame.src=frame.dataset.template+\"-\"+theme+\".html\";});}</script>'
        index = index.replace('<div style="display:grid;', controls + '<div style="display:grid;', 1)
        (destination / "index.html").write_text(index, encoding="utf-8")
        assets = Path(__file__).resolve().parents[5] / "front-v2-publish/public/assets/email"
        if assets.exists():
            copytree(assets, destination / "assets", dirs_exist_ok=True)
        self.stdout.write(self.style.SUCCESS(f"Rendered {len(templates)} previews: {destination / 'index.html'}"))
