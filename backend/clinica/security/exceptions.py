# -*- coding: utf-8 -*-
"""Manejador de excepciones OWASP A10 (fail-safe sin filtrar stack traces ni SQL)."""

import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("clinica.security")


def owasp_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        return response

    request = context.get("request")
    logger.exception("Error interno no controlado en %s", getattr(request, "path", "?"))
    return Response(
        {
            "detail": "Error interno procesando la solicitud (OWASP A10: detalle omitido por seguridad)."
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
