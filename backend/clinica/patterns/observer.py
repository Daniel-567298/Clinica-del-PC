# -*- coding: utf-8 -*-
"""
Patrón GoF 1 (Comportamiento): Observer / Singleton — ClinicEventBus.
Desacopla la lógica del dominio de la auditoría OWASP A09 en PostgreSQL.
"""

from collections import defaultdict
from threading import Lock


class ClinicEventBus:
    _instance = None
    _lock = Lock()

    def __init__(self):
        self._listeners = defaultdict(list)
        self._bootstrapped = False

    @classmethod
    def get_instance(cls) -> "ClinicEventBus":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    bus = cls()
                    bus._register_default_observers()
                    cls._instance = bus
        return cls._instance

    def subscribe(self, event_type: str, callback):
        if callback not in self._listeners[event_type]:
            self._listeners[event_type].append(callback)

    def publish(self, event_type: str, payload: dict):
        for cb in list(self._listeners.get(event_type, [])):
            try:
                cb(event_type, payload)
            except Exception:
                # Fail-safe OWASP A10: el observador no tumba la transacción principal
                pass
        for cb in list(self._listeners.get("*", [])):
            try:
                cb(event_type, payload)
            except Exception:
                pass

    def _register_default_observers(self):
        if self._bootstrapped:
            return
        self._bootstrapped = True

        def persist_security_audit(event_type: str, payload: dict):
            from clinica.models import EventoSeguridadOWASP, EventoClinica
            from clinica.security.eventos import current_request, sedes_permitidas
            sede_id = payload.get("sede_id")
            request = current_request.get()
            if sede_id is None and request is not None:
                event_id = request.headers.get("X-Clinica-Evento") or request.GET.get("evento")
                if event_id:
                    try:
                        sede_id = EventoClinica.objects.filter(pk=int(event_id)).values_list("sede_id", flat=True).first()
                    except (ValueError, TypeError):
                        pass
                elif getattr(request, "user", None) is not None:
                    candidates = list(sedes_permitidas(request.user).values_list("id", flat=True)[:2])
                    if len(candidates) == 1:
                        sede_id = candidates[0]

            nivel = payload.get("nivel") or (
                "CRITICAL"
                if "21459" in event_type or "LOCKED" in event_type
                else ("WARN" if "403" in event_type or "FAIL" in event_type or "CSV" in event_type else "INFO")
            )
            EventoSeguridadOWASP.objects.create(
                sede_id=sede_id,
                nivel=nivel,
                evento=event_type[:60],
                usuario=payload.get("usuario"),
                actor_nombre=str(payload.get("actor", "Sistema"))[:100],
                ruta=str(payload.get("ruta", ""))[:160],
                ip_origen=payload.get("ip"),
                detalle=str(payload.get("detalle", event_type)),
            )

        self.subscribe("*", persist_security_audit)
