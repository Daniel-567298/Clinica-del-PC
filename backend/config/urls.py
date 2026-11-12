# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("clinica.urls")),
    # Sirve los activos del frontend desacoplado (CSS/JS) y la SPA principal en /
    re_path(r"^css/(?P<path>.*)$", serve, {"document_root": settings.FRONTEND_DIR / "css"}),
    re_path(r"^js/(?P<path>.*)$", serve, {"document_root": settings.FRONTEND_DIR / "js"}),
    path("", TemplateView.as_view(template_name="index.html"), name="frontend-home"),
]
