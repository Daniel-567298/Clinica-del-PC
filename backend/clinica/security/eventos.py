from django.db.models import Q
from contextvars import ContextVar
from rest_framework.exceptions import ValidationError, PermissionDenied
from clinica.models import Sede, EventoClinica, FichaAtencion, ResguardoEntreJornadas
from django.utils import timezone
current_request = ContextVar("clinica_request", default=None)


def sedes_permitidas(user):
    if not user or not user.is_authenticated:
        return Sede.objects.none()
    if user.is_superuser:
        return Sede.objects.all()
    return Sede.objects.filter(operadores__user=user).distinct()


def eventos_permitidos(user):
    return EventoClinica.objects.filter(sede__in=sedes_permitidas(user))


def evento_seleccionado(request, public=False, allow_final=False):
    value = request.headers.get("X-Clinica-Evento") or request.query_params.get("evento")
    if not value and request.method not in ("GET", "HEAD"):
        value = request.data.get("evento_id")
    qs = EventoClinica.objects.filter(sede__activa=True) if public else eventos_permitidos(request.user)
    if value:
        try:
            event = qs.get(pk=int(value))
        except (ValueError, TypeError, EventoClinica.DoesNotExist):
            raise ValidationError({"detail": "Evento inexistente o sin permisos para su sede."})
    else:
        candidates = list(qs.filter(estado__in=["Inscripciones abiertas", "En curso"])[:2])
        if len(candidates) != 1:
            raise ValidationError({"detail": "Selecciona la sede y el evento de esta atención."})
        event = candidates[0]
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if event.estado == "Finalizado" and not allow_final:
            raise ValidationError({"detail": "El evento está finalizado y su historial es de solo lectura."})
        if public and event.estado not in ("Inscripciones abiertas", "En curso"):
            raise ValidationError({"detail": "Este evento no está recibiendo inscripciones."})
        if public:
            now = timezone.now()
            if (event.inscripcion_desde and now < event.inscripcion_desde) or (event.inscripcion_hasta and now > event.inscripcion_hasta):
                raise ValidationError({"detail": "La preinscripción está fuera del plazo configurado para este evento."})
    return event


def fichas_permitidas(request, qs=None, allow_final=False, allow_resguardo=False):
    qs = qs if qs is not None else FichaAtencion.objects.all()
    qs = qs.filter(evento__sede__in=sedes_permitidas(request.user))
    value = request.headers.get("X-Clinica-Evento") or request.query_params.get("evento")
    if value:
        event = evento_seleccionado(request, allow_final=allow_final)
        qs = qs.filter(evento=event)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not allow_final:
            qs = qs.exclude(evento__estado="Finalizado")
        if not allow_resguardo:
            ticket = (getattr(request, 'parser_context', None) or {}).get('kwargs', {}).get('numero_ticket')
            if ticket and qs.filter(numero_ticket=ticket.upper(),resguardos__reanudado_en__isnull=True,resguardos__isnull=False).exists():
                raise ValidationError({"detail": "El equipo está en resguardo entre jornadas. El docente debe registrar su retorno antes de continuar."})
    return qs
