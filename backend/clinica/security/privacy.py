# -*- coding: utf-8 -*-
"""Aislamiento de privacidad de PII conforme a Ley N° 21.719 (Proyección de DTO por rol)."""

from clinica.security.validators import normalize_rut


def mask_rut(rut: str) -> str:
    limpio = normalize_rut(rut)
    if not limpio:
        return "**.***.***-*"
    return f"**.***.***-{limpio[-1]}"


def mask_name(full_name: str) -> str:
    parts = str(full_name or "").strip().split()
    if not parts:
        return "Titular ***"
    return f"{parts[0]} ***"


def project_owner_for_role(owner, role: str) -> dict:
    """
    Si el usuario autenticado es Alumno Técnico, el servidor NUNCA transmite RUT completo,
    correo, teléfono ni domicilio en la respuesta HTTP (Ley 21.719 / OWASP A01).
    """
    if owner.anonimizado:
        return {
            "id": owner.id,
            "rut": "ANONIMIZADO",
            "nombre_completo": "Titular Anonimizado (Ley 21.719)",
            "telefono": "[Eliminado tras 60 días]",
            "correo": "[Eliminado]",
            "comuna_direccion": "[Eliminado]",
            "anonimizado": True,
        }

    if role == "TECNICO":
        return {
            "id": owner.id,
            "rut": mask_rut(owner.rut),
            "nombre_completo": mask_name(owner.nombre_completo),
            "telefono": "[Solo Recepción]",
            "correo": "[Protegido Ley 21.719]",
            "comuna_direccion": "[Oculta por Ley 21.719]",
            "anonimizado": False,
        }

    return {
        "id": owner.id,
        "rut": owner.rut,
        "nombre_completo": owner.nombre_completo,
        "telefono": owner.telefono,
        "correo": owner.correo,
        "comuna_direccion": owner.comuna_direccion,
        "anonimizado": False,
    }
