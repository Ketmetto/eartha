class AdminCSPMiddleware:
    """django-unfold's admin theme is built on Alpine.js, which evaluates
    its x-data/x-on directives via a mechanism CSP's script-src treats as
    eval — needs 'unsafe-eval' to function, unlike the rest of the site.
    Scoped to /admin/ only (staff-only) rather than loosening script-src
    site-wide. Must sit after CSPMiddleware in MIDDLEWARE — setting
    response._csp_update here is the same mechanism csp.decorators.
    csp_update uses on a response, and CSPMiddleware's own process_response
    (which runs after this one, since response processing unwinds in
    reverse middleware order) is what actually reads it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/admin/"):
            response._csp_update = {"script-src": ["'unsafe-eval'"]}
        return response
