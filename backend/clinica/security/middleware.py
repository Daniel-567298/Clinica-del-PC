# -*- coding: utf-8 -*-
"""Cabeceras HTTP defensivas OWASP Top 10:2025."""


class OwaspSecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith("/admin"):
            response.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; connect-src 'self' http://127.0.0.1:8000 http://localhost:8000; "
                "frame-ancestors 'none'; object-src 'none';",
            )
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        return response
