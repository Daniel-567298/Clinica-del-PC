# -*- coding: utf-8 -*-
"""
Patrón GoF 4 (Arquitectónico / Creacional): Repository + Singleton — ClinicaRepository.
Centraliza las consultas optimizadas PostgreSQL evitando N+1 y midiendo latencia (RNF07 <= 2.0s).
"""

import time
from threading import Lock
from django.db.models import Count, Q
from rest_framework.exceptions import ValidationError

from clinica.models import Dispositivo, FichaAtencion, Propietario
from clinica.security.validators import format_rut_chileno, normalize_rut


class ClinicaRepository:
    _instance = None
    _lock = Lock()

    @classmethod
    def get_instance(cls) -> "ClinicaRepository":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @staticmethod
    def base_ficha_queryset():
        return FichaAtencion.objects.select_related(
            "propietario", "dispositivo", "tecnico_asignado"
        ).prefetch_related(
            "servicios", "checklist_items__servicio", "notas", "transiciones"
        )

    @staticmethod
    def upsert_owner(
        rut: str,
        nombre_completo: str,
        telefono: str,
        correo: str,
        comuna_direccion: str,
    ) -> Propietario:
        rut_norm = normalize_rut(rut)
        rut_fmt = format_rut_chileno(rut)
        declared = dict(nombre_completo=nombre_completo, telefono=telefono,
                        correo=correo, comuna_direccion=comuna_direccion)
        owner, created = Propietario.objects.get_or_create(
            rut_normalizado=rut_norm, defaults={"rut": rut_fmt, **declared}
        )
        if not created:
            # El formulario público nunca actualiza la identidad compartida.
            def normalized(field, value):
                if field == "telefono":
                    return "".join(c for c in value if c.isdigit())
                return " ".join(value.split()).casefold()
            if any(normalized(k, getattr(owner, k)) != normalized(k, v)
                   for k, v in declared.items()):
                raise ValidationError({"detail": "No se pueden vincular estos datos automáticamente. Revisa el formulario o solicita ayuda en recepción para corregirlos."})
        return owner

    @classmethod
    def search_triaje(cls, query: str, evento=None) -> tuple[list[Propietario], float]:
        """Búsqueda normalizada Propietario -> Dispositivo[] -> FichaAtencion con medición RNF07."""
        t0 = time.perf_counter()
        q = (query or "").strip()
        q_norm = normalize_rut(q)

        qs = Propietario.objects.prefetch_related(
            "dispositivos__fichas__servicios",
            "dispositivos__fichas__checklist_items",
        )
        if evento is not None:
            qs = qs.filter(fichas__evento=evento).distinct()
        if q:
            cond = Q(nombre_completo__icontains=q) | Q(fichas__numero_ticket__icontains=q)
            if q_norm:
                cond |= Q(rut_normalizado__icontains=q_norm)
            qs = qs.filter(cond).distinct()

        owners = list(qs.order_by("nombre_completo")[:30])
        elapsed = round(time.perf_counter() - t0, 4)
        return owners, elapsed

    @staticmethod
    def get_metrics_summary(qs=None) -> dict:
        qs = qs if qs is not None else FichaAtencion.objects.all()
        agg = qs.aggregate(
            total=Count("id"),
            recepcionados=Count("id", filter=~Q(estado="Preinscrito")),
            en_taller=Count("id", filter=Q(estado__in=["Recibido", "En proceso", "En espera"])),
            entregados=Count("id", filter=Q(estado="Entregado conforme")),
            en_custodia=Count("id", filter=Q(estado="En custodia")),
            incidencias_activas=Count("id", filter=Q(incidencia_activa=True)),
            ley_21459_retenidos=Count("id", filter=Q(hallazgo_ilicito_ley_21459=True)),
        )
        servicios = {
            "Mantención Física": qs.filter(servicios__nombre="Mantención Física").count(),
            "Mantención Lógica": qs.filter(servicios__nombre="Mantención Lógica").count(),
            "Formateo / Instalación de SO": qs.filter(
                servicios__nombre="Formateo / Instalación de SO"
            ).count(),
        }
        return {**agg, "servicios": servicios}
