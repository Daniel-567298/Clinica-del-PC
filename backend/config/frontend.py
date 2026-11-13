"""Entrega la página y renueva las referencias a sus archivos cuando cambian."""
from hashlib import sha256
from django.conf import settings
from django.views.generic import TemplateView


class FrontendView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['frontend_versions'] = {
            name: sha256((settings.FRONTEND_DIR / path).read_bytes()).hexdigest()[:16]
            for name, path in {
                'styles': 'css/app.css', 'validators': 'js/validators.js',
                'api': 'js/api.js', 'app': 'js/app.js',
            }.items()
        }
        return context
