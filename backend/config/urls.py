# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from django.views.decorators.cache import never_cache
from config.frontend import FrontendView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("clinica.urls")),
    # Sirve los activos del frontend desacoplado (CSS/JS) y la SPA principal en /
    re_path(r"^css/(?P<path>.*)$", never_cache(serve), {"document_root": settings.FRONTEND_DIR / "css"}),
    re_path(r"^js/(?P<path>.*)$", never_cache(serve), {"document_root": settings.FRONTEND_DIR / "js"}),
    path("", never_cache(FrontendView.as_view()), name="frontend-home"),
]
