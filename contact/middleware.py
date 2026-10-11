class QuotationPrivacyMiddleware:
    """Protect success, validation, authentication and missing-token responses alike."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/api/quotations/'):
            response['Cache-Control'] = 'private, no-store, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Referrer-Policy'] = 'no-referrer'
            response['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
        return response
