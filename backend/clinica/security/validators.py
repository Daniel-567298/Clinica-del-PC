# -*- coding: utf-8 -*-
"""Validadores de dominio, integridad y prevención de inyección (OWASP A05 / A08)."""

import hashlib
import re
from django.core.exceptions import ValidationError


def normalize_rut(rut: str) -> str:
    return re.sub(r"[^0-9kK]", "", str(rut or "")).upper()


def calc_rut_dv(cuerpo: str) -> str:
    suma = 0
    multiplo = 2
    for ch in reversed(cuerpo):
        suma += multiplo * int(ch)
        multiplo = multiplo + 1 if multiplo < 7 else 2
    dv_esp = 11 - (suma % 11)
    if dv_esp == 11:
        return "0"
    if dv_esp == 10:
        return "K"
    return str(dv_esp)


def validar_rut_chileno(rut_completo: str) -> bool:
    limpio = normalize_rut(rut_completo)
    if len(limpio) < 8 or len(limpio) > 9:
        return False
    cuerpo, dv = limpio[:-1], limpio[-1]
    if not cuerpo.isdigit():
        return False
    return dv == calc_rut_dv(cuerpo)


def validate_rut_field(value: str) -> None:
    if not validar_rut_chileno(value):
        raise ValidationError("El RUT ingresado no supera la validación Módulo 11.")


def format_rut_chileno(rut_completo: str) -> str:
    limpio = normalize_rut(rut_completo)
    if len(limpio) < 2:
        return str(rut_completo or "").strip()
    cuerpo, dv = limpio[:-1], limpio[-1]
    rev = cuerpo[::-1]
    grupos = [rev[i : i + 3][::-1] for i in range(0, len(rev), 3)]
    return f"{'.'.join(reversed(grupos))}-{dv}"


def sanitize_csv_cell(value: str) -> str:
    """Neutraliza CSV / Formula Injection (OWASP A05)."""
    s = str(value or "").strip().strip('"').strip("'")
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def compute_consent_sha256(
    ticket_id: str,
    owner_rut_norm: str,
    damage: str,
    accessories: str,
    consent_iso: str,
) -> str:
    """Hash criptográfico SHA-256 determinístico en servidor (OWASP A08 / Ley 19.799)."""
    payload = f"{ticket_id}|{owner_rut_norm}|{damage.strip()}|{accessories.strip()}|{consent_iso}"
    return "SHA256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
