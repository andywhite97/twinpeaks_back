# Transactional emails

Ten HTML templates and matching plain-text versions cover general correspondence, contact, quote request, quotation delivery, acceptance and decline flows. `contact.tasks` renders the automatic notifications and passes both formats to Bird. The general template is reusable through `render_email` but does not send mail on its own. Templates use Django autoescaping for customer content in HTML; plain-text templates intentionally disable HTML escaping.

`base.html` follows the supplied collection concept: a white logo header, photographic navy banner, pale-blue reference panels, blue buttons and a dark contact footer. The table layout uses a 600px maximum width and an Outlook desktop wrapper, with system fonts. Photos are background decoration; the solid navy heading panel stays readable when backgrounds are unsupported. Actual rendering can vary between email clients.

Footer email addresses come from CONTACT_FROM_EMAIL or QUOTATION_FROM_EMAIL; phone and address come from CompanyProfile when supplied. Website and private quotation links use PUBLIC_SITE_URL; PDF links use PUBLIC_API_URL. Logo and JPEG photo assets are shipped in both v2 public/assets/email directories and use EMAIL_ASSET_BASE_URL. Deploy those frontend assets before enabling the updated emails, or point EMAIL_ASSET_BASE_URL at their public HTTPS host. Subjects, sender identities, recipient routing and provider failure handling remain in `contact.tasks`. Customer templates never expose internal notes. The request acknowledgement contains no draft prices; the issued quotation contains its confirmed total, optional expiry and private link. Enquiry references are derived from the persisted ContactMessage ID, not a new database field.

Generate illustrative previews without sending email or writing database records:

    python manage.py preview_emails --output ../../output/email-previews --settings=twinpeaks.test_settings

Open the resulting index.html in a browser. It shows the five main concept variants alongside links to all ten templates, including team and declined variants. Preview assets are copied locally, and quotation links use example.invalid with no real access tokens. Preview generation does not read CompanyProfile or write database records. No migration is required.

Light/dark colour-scheme metadata, a prefers-color-scheme dark palette and Outlook data-ogsc/data-ogsb overrides keep authored text, links, panels and buttons paired with contrasting backgrounds. The logo sits on a white plate so its navy lettering remains visible. Inline colours and bgcolor attributes supply fallbacks when clients strip head CSS; banner text uses a solid navy background instead of a gradient that could remain dark while a client inverts only the text.

The preview index has light/dark controls and each template has adaptive, forced-light and forced-dark browser previews. These simulate the authored palettes, not Gmail/Outlook colour inversion. Email clients differ in their dark-mode CSS support, so actual mailbox rendering still needs checks in the recipient clients; browser previews cannot guarantee every client’s transformations.
