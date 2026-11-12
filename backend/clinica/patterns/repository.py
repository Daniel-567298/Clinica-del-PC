# -*- coding: utf-8 -*-
"""
Patrón GoF 4 (Arquitectónico / Creacional): Repository + Singleton — ClinicaRepository.
Centraliza las consultas optimizadas PostgreSQL evitando N+1 y midiendo latencia (RNF07 <= 2.0s).
"""

import time
from threading import Lock
from django.db.models import Count, Q

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
        owner = Propietario.objects.filter(rut_normalizado=rut_norm).first()
        if owner:
            owner.rut = rut_fmt
            owner.nombre_completo = nombre_completo
            owner.telefono = telefono
            owner.correo = correo
            owner.comuna_direccion = comuna_direccion
            owner.anonimizado = False
            owner.anonimizado_en = None
            owner.save()
            return owner
        return Propietario.objects.create(
            rut=rut_fmt,
            nombre_completo=nombre_completo,
            telefono=telefono,
            correo=correo,
            comuna_direccion=comuna_direccion,
        )

    @classmethod
    def search_triaje(cls, query: str) -> tuple[list[Propietario], float]:
        """Búsqueda normalizada Propietario -> Dispositivo[] -> FichaAtencion con medición RNF07."""
        t0 = time.perf_counter()
        q = (query or "").strip()
        q_norm = normalize_rut(q)

        qs = Propietario.objects.prefetch_related(
            "dispositivos__fichas__servicios",
            "dispositivos__fichas__checklist_items",
        )
        if q:
            cond = Q(nombre_completo__icontains=q) | Q(fichas__numero_ticket__icontains=q)
            if q_norm:
                cond |= Q(rut_normalizado__icontains=q_norm)
            qs = qs.filter(cond).distinct()

        owners = list(qs.order_by("nombre_completo")[:30])
        elapsed = round(time.perf_counter() - t0, 4)
        return owners, elapsed

    @staticmethod
    def get_metrics_summary() -> dict:
        agg = FichaAtencion.objects.aggregate(
            total=Count("id"),
            recepcionados=Count("id", filter=~Q(estado="Preinscrito")),
            en_taller=Count("id", filter=Q(estado__in=["Recibido", "En proceso", "En espera"])),
            entregados=Count("id", filter=Q(estado="Entregado conforme")),
            en_custodia=Count("id", filter=Q(estado="En custodia")),
            incidencias_activas=Count("id", filter=Q(incidencia_activa=True)),
            ley_21459_retenidos=Count("id", filter=Q(hallazgo_ilicito_ley_21459=True)),
        )
        servicios = {
            "Mantención Física": FichaAtencion.objects.filter(servicios__nombre="Mantención Física").count(),
            "Mantención Lógica": FichaAtencion.objects.filter(servicios__nombre="Mantención Lógica").count(),
            "Formateo / Instalación de SO": FichaAtencion.objects.filter(
                servicios__nombre="Formateo / Instalación de SO"
            ).count(),
        }
        return {**agg, "servicios": servicios}
