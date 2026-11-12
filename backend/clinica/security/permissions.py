# -*- coding: utf-8 -*-
"""Control de Acceso Basado en Roles estricto (OWASP A01 - Deny by Default)."""

from rest_framework.permissions import BasePermission


ROLE_RECEPCIONISTA = "RECEPCIONISTA"
ROLE_TECNICO = "TECNICO"
ROLE_DOCENTE_PO = "DOCENTE_PO"


def get_user_role(user) -> str:
    if not user or not user.is_authenticated:
        return "ANON"
    if user.is_superuser:
        return ROLE_DOCENTE_PO
    perfil = getattr(user, "perfil", None)
    if perfil and perfil.habilitado_jornada:
        return perfil.rol
    return "DISABLED"


class _BaseRolePermission(BasePermission):
    allowed_roles: tuple[str, ...] = ()
    message = "HTTP 403 Forbidden (OWASP A01): Rol sin permisos para este módulo."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        role = get_user_role(user)
        if role in self.allowed_roles:
            return True

        # Registra denegación RBAC 403 en PostgreSQL (OWASP A09)
        from clinica.patterns.observer import ClinicEventBus

        ClinicEventBus.get_instance().publish(
            "RBAC_403_FORBIDDEN",
            {
                "nivel": "WARN",
                "usuario": user,
                "actor": f"{user.username} ({role})",
                "ruta": request.path,
                "ip": request.META.get("REMOTE_ADDR"),
                "detalle": f"Acceso denegado a {request.method} {request.path} para rol {role}.",
            },
        )
        return False


class IsRecepcionOrDocente(_BaseRolePermission):
    allowed_roles = (ROLE_RECEPCIONISTA, ROLE_DOCENTE_PO)


class IsTecnicoOrDocente(_BaseRolePermission):
    allowed_roles = (ROLE_TECNICO, ROLE_DOCENTE_PO)


class IsAnyInternalRole(_BaseRolePermission):
    allowed_roles = (ROLE_RECEPCIONISTA, ROLE_TECNICO, ROLE_DOCENTE_PO)


class IsDocentePO(_BaseRolePermission):
    allowed_roles = (ROLE_DOCENTE_PO,)
