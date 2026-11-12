# -*- coding: utf-8 -*-
"""
Patrón GoF 2 (Comportamiento): State — TicketStateMachine.
Gobierna el ciclo de vida estricto de FichaAtencion e impone CA07, CA08 y Ley 21.459.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from clinica.models import BitacoraNota, FichaAtencion, TransicionEstadoLog
from clinica.patterns.observer import ClinicEventBus


class TicketStateMachine:
    TRANSITIONS = {
        "Preinscrito": ["Recibido", "Devuelto sin reparación"],
        "Recibido": ["En proceso", "En espera", "Devuelto sin reparación"],
        "En proceso": ["En espera", "Listo para entrega", "Devuelto sin reparación"],
        "En espera": ["En proceso", "Devuelto sin reparación"],
        "Listo para entrega": ["Entregado conforme", "Devuelto sin reparación", "En custodia"],
        "En custodia": ["Listo para entrega", "Entregado conforme", "Devuelto sin reparación"],
        "Entregado conforme": [],
        "Devuelto sin reparación": [],
    }

    @classmethod
    def allowed_targets(cls, current_state: str) -> list[str]:
        return list(cls.TRANSITIONS.get(current_state, []))

    @classmethod
    def can_transition(cls, ficha: FichaAtencion, target_state: str) -> tuple[bool, str]:
        if ficha.estado == target_state:
            return True, ""

        allowed = cls.allowed_targets(ficha.estado)
        if target_state not in allowed:
            return (
                False,
                f"Transición inválida desde '{ficha.estado}' hacia '{target_state}'.",
            )

        if target_state == "Listo para entrega":
            if ficha.hallazgo_ilicito_ley_21459:
                return (
                    False,
                    "Bloqueo Legal (Ley 21.459): equipo retenido bajo cadena de custodia por hallazgo ilícito.",
                )
            if ficha.incidencia_activa:
                return (
                    False,
                    "Bloqueo CA07: existe una incidencia abierta sin resolución del Docente PO / titular.",
                )
            pending = ficha.checklist_items.filter(estado="Pendiente").count()
            if pending > 0:
                return (
                    False,
                    f"Bloqueo Calidad (CA08): faltan {pending} tareas del checklist por completar o justificar.",
                )
            if ficha.checklist_items.count() == 0:
                return (
                    False,
                    "Bloqueo Calidad (CA08): la ficha no posee ítems de checklist generados.",
                )

        if target_state in ("Entregado conforme", "Devuelto sin reparación"):
            if ficha.hallazgo_ilicito_ley_21459 and target_state == "Entregado conforme":
                return (
                    False,
                    "Bloqueo Legal (Ley 21.459): no se puede entregar conforme un equipo con bloqueo ilícito activo.",
                )

        return True, ""

    @classmethod
    @transaction.atomic
    def transition(
        cls,
        ficha: FichaAtencion,
        target_state: str,
        actor_name: str,
        user=None,
        note_text: str = "",
    ) -> FichaAtencion:
        ok, reason = cls.can_transition(ficha, target_state)
        if not ok:
            raise ValidationError({"estado": reason})

        prev_state = ficha.estado
        if prev_state != target_state:
            ficha.estado = target_state
            ficha.save(update_fields=["estado", "actualizado_en"])
            TransicionEstadoLog.objects.create(
                ficha=ficha,
                estado_origen=prev_state,
                estado_destino=target_state,
                actor_nombre=actor_name[:120],
            )
            ClinicEventBus.get_instance().publish(
                "STATE_TRANSITION",
                {
                    "nivel": "INFO",
                    "usuario": user,
                    "actor": actor_name,
                    "detalle": f"Ticket {ficha.numero_ticket}: {prev_state} -> {target_state}.",
                },
            )

        if note_text:
            BitacoraNota.objects.create(
                ficha=ficha,
                autor=user if getattr(user, "is_authenticated", False) else None,
                autor_nombre=actor_name[:120],
                contenido=note_text,
            )

        return ficha
