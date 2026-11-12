# -*- coding: utf-8 -*-
"""
Patrón GoF 3 (Creacional): Factory — FichaAndChecklistFactory.
Genera códigos correlativos (PC-XXX, DEV-XX, CL-XX) e instancia ítems de checklist
con claves únicas compuestas (`Servicio::orden`) evitando colisiones multi-servicio.
"""

import re
from django.db import transaction

from clinica.models import (
    BitacoraNota,
    ChecklistItemEjecucion,
    Dispositivo,
    FichaAtencion,
    PlantillaTarea,
    Propietario,
    ServicioCatalogo,
    TransicionEstadoLog,
)


class FichaAndChecklistFactory:
    @staticmethod
    def _next_numeric_suffix(existing_codes, prefix: str) -> int:
        max_num = 0
        pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
        for code in existing_codes:
            m = pattern.match(str(code or ""))
            if m:
                max_num = max(max_num, int(m.group(1)))
        return max_num + 1

    @classmethod
    def next_device_code(cls) -> str:
        codes = Dispositivo.objects.values_list("codigo_dispositivo", flat=True)
        n = cls._next_numeric_suffix(codes, "DEV-")
        return f"DEV-{n:02d}"

    @classmethod
    def next_clone_code(cls) -> str:
        codes = Dispositivo.objects.exclude(codigo_interno_clon__isnull=True).values_list(
            "codigo_interno_clon", flat=True
        )
        n = cls._next_numeric_suffix(codes, "CL-")
        return f"CL-{n:02d}"

    @classmethod
    def next_ticket_number(cls) -> str:
        codes = FichaAtencion.objects.values_list("numero_ticket", flat=True)
        n = max(24, cls._next_numeric_suffix(codes, "PC-"))
        return f"PC-{n:03d}"

    @staticmethod
    def task_unique_key(service_name: str, orden_zero_based: int) -> str:
        return f"{service_name}::{orden_zero_based}"

    @classmethod
    def materialize_checklist_items(
        cls,
        ficha: FichaAtencion,
        services: list[ServicioCatalogo],
        reset_missing_only: bool = True,
    ) -> list[ChecklistItemEjecucion]:
        """
        Genera ChecklistItemEjecucion desde la versión activa de PlantillaTarea en PostgreSQL.
        Si se cambian servicios en recepción, conserva avances de claves vigentes y agrega los nuevos.
        """
        selected_ids = {s.id for s in services}
        if not reset_missing_only:
            ficha.checklist_items.all().delete()
        else:
            ficha.checklist_items.exclude(servicio_id__in=selected_ids).delete()

        existing_map = {item.clave_unica: item for item in ficha.checklist_items.all()}
        created_or_kept = []

        for srv in services:
            plantillas = list(
                PlantillaTarea.objects.filter(servicio=srv, version=srv.version_actual).order_by("orden")
            )
            for idx, tarea in enumerate(plantillas):
                key = cls.task_unique_key(srv.nombre, idx)
                if key in existing_map:
                    created_or_kept.append(existing_map[key])
                else:
                    obj = ChecklistItemEjecucion.objects.create(
                        ficha=ficha,
                        servicio=srv,
                        clave_unica=key,
                        orden=idx,
                        descripcion_tarea=tarea.descripcion,
                        estado="Pendiente",
                    )
                    created_or_kept.append(obj)

        return created_or_kept

    @classmethod
    @transaction.atomic
    def create_qr_preinscription(
        cls,
        owner: Propietario,
        brand_model: str,
        device_type: str,
        problem: str,
        service_names: list[str],
        actor_name: str = "Propietario QR",
        device_existing: Dispositivo | None = None,
    ) -> FichaAtencion:
        if device_existing is None:
            dev = Dispositivo.objects.create(
                codigo_dispositivo=cls.next_device_code(),
                propietario=owner,
                tipo=device_type or "Notebook",
                marca_modelo=brand_model,
            )
        else:
            dev = device_existing

        services = list(ServicioCatalogo.objects.filter(nombre__in=service_names, activo=True))
        if not services:
            services = list(ServicioCatalogo.objects.filter(activo=True)[:1])

        max_ver = max((s.version_actual for s in services), default=1)
        ficha = FichaAtencion.objects.create(
            numero_ticket=cls.next_ticket_number(),
            propietario=owner,
            dispositivo=dev,
            problema_declarado=problem,
            estado="Preinscrito",
            version_plantilla_usada=max_ver,
        )
        ficha.servicios.set(services)
        cls.materialize_checklist_items(ficha, services)

        TransicionEstadoLog.objects.create(
            ficha=ficha,
            estado_origen="Inicio",
            estado_destino="Preinscrito",
            actor_nombre=actor_name[:120],
        )
        BitacoraNota.objects.create(
            ficha=ficha,
            autor_nombre=actor_name[:120],
            contenido="Preinscripción registrada vía flujo QR público.",
        )
        return ficha
