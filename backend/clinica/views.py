# -*- coding: utf-8 -*-
"""Vistas DRF de la Clínica del PC (INACAP TI3043) con RBAC OWASP y PostgreSQL."""

import csv
import io
import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.db import connection, transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from clinica.models import (
    BitacoraNota,
    Dispositivo,
    EncuestaSatisfaccion,
    EventoSeguridadOWASP,
    FichaAtencion,
    PerfilOperador,
    PlantillaTarea,
    Propietario,
    ServicioCatalogo,
)
from clinica.patterns.factory import FichaAndChecklistFactory
from clinica.patterns.observer import ClinicEventBus
from clinica.patterns.repository import ClinicaRepository
from clinica.patterns.state_machine import TicketStateMachine
from clinica.security.permissions import (
    ROLE_DOCENTE_PO,
    ROLE_TECNICO,
    IsAnyInternalRole,
    IsDocentePO,
    IsRecepcionOrDocente,
    IsTecnicoOrDocente,
    get_user_role,
)
from clinica.security.validators import (
    calc_rut_dv,
    compute_consent_sha256,
    normalize_rut,
    sanitize_csv_cell,
    validar_rut_chileno,
)
from clinica.serializers import (
    EventoSeguridadSerializer,
    FichaDetailSerializer,
    FichaSummarySerializer,
    PerfilNominaSerializer,
    QRPreinscriptionInputSerializer,
    ServicioPlantillaSerializer,
    TriajeOwnerSerializer,
)


def _client_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _actor_label(user) -> str:
    if not user or not user.is_authenticated:
        return "Público"
    nombre = user.get_full_name() or user.username
    return f"{nombre} ({get_user_role(user)})"


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        with connection.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        return Response({"status": "ok", "database_vendor": connection.vendor})


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AuthCSRFView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrf": "ok"})


class AuthMeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"authenticated": False, "rol": "PUBLIC"})
        perfil = getattr(request.user, "perfil", None)
        return Response(
            {
                "authenticated": True,
                "username": request.user.username,
                "full_name": request.user.get_full_name() or request.user.username,
                "email": request.user.email,
                "rol": get_user_role(request.user),
                "seccion": perfil.seccion if perfil else "TI3043-01",
            }
        )


class AuthLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login_attempts"

    def post(self, request):
        ident = str(request.data.get("username", "")).strip()
        password = str(request.data.get("password", ""))
        bus = ClinicEventBus.get_instance()
        ip = _client_ip(request)

        if not ident or not password:
            return Response(
                {"detail": "Credenciales inválidas."}, status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(Q(username__iexact=ident) | Q(email__iexact=ident)).first()
        perfil = getattr(user, "perfil", None) if user else None

        if perfil and perfil.bloqueado_hasta and perfil.bloqueado_hasta > timezone.now():
            return Response(
                {"detail": "Cuenta bloqueada temporalmente por exceso de intentos fallidos (OWASP A07)."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if not user or not user.check_password(password) or not user.is_active or (perfil and not perfil.habilitado_jornada):
            if perfil:
                perfil.intentos_fallidos += 1
                if perfil.intentos_fallidos >= 5:
                    perfil.bloqueado_hasta = timezone.now() + timedelta(minutes=15)
                    perfil.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
                    bus.publish(
                        "ACCOUNT_LOCKED",
                        {
                            "nivel": "CRITICAL",
                            "usuario": user,
                            "actor": ident,
                            "ruta": request.path,
                            "ip": ip,
                            "detalle": f"Bloqueo OWASP A07 activado para '{ident}' tras 5 intentos fallidos.",
                        },
                    )
                    return Response(
                        {"detail": "Cuenta bloqueada temporalmente por exceso de intentos fallidos (OWASP A07)."},
                        status=status.HTTP_429_TOO_MANY_REQUESTS,
                    )
                perfil.save(update_fields=["intentos_fallidos"])

            bus.publish(
                "LOGIN_FAIL",
                {
                    "nivel": "WARN",
                    "actor": ident,
                    "ruta": request.path,
                    "ip": ip,
                    "detalle": f"Intento fallido de inicio de sesión para identificador '{ident}'.",
                },
            )
            return Response(
                {"detail": "Credenciales inválidas (error genérico OWASP A10)."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if perfil:
            perfil.intentos_fallidos = 0
            perfil.bloqueado_hasta = None
            perfil.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])

        login(request, user)
        bus.publish(
            "LOGIN_OK",
            {
                "nivel": "INFO",
                "usuario": user,
                "actor": _actor_label(user),
                "ruta": request.path,
                "ip": ip,
                "detalle": f"Sesión HttpOnly iniciada para {user.username} ({get_user_role(user)}).",
            },
        )
        return AuthMeView().get(request)


class AuthLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        actor = _actor_label(request.user)
        ClinicEventBus.get_instance().publish(
            "LOGOUT",
            {
                "nivel": "INFO",
                "usuario": request.user,
                "actor": actor,
                "ruta": request.path,
                "ip": _client_ip(request),
                "detalle": f"Cierre de sesión limpio para {actor}.",
            },
        )
        logout(request)
        return Response({"authenticated": False})


class AuthUnlockDemoView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not settings.DEBUG and get_user_role(request.user) != ROLE_DOCENTE_PO:
            return Response(
                {"detail": "Operación restringida al entorno de evaluación o Docente PO."},
                status=status.HTTP_403_FORBIDDEN,
            )
        PerfilOperador.objects.update(intentos_fallidos=0, bloqueado_hasta=None)
        ClinicEventBus.get_instance().publish(
            "DEMO_UNLOCK",
            {
                "nivel": "INFO",
                "actor": "Evaluador / Demo",
                "ruta": request.path,
                "ip": _client_ip(request),
                "detalle": "Contadores de bloqueo OWASP A07 reiniciados en ambiente de evaluación.",
            },
        )
        return Response({"unlocked": True})


# ==============================================================================
# PASO 1: PREINSCRIPCIÓN PÚBLICA QR (SIN CUENTA DE USUARIO)
# ==============================================================================
class PublicPreinscriptionView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        ser = QRPreinscriptionInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        owner = ClinicaRepository.upsert_owner(
            rut=d["rut"],
            nombre_completo=d["nombre_completo"].strip(),
            telefono=d["telefono"].strip(),
            correo=d["correo"].strip(),
            comuna_direccion=d["comuna_direccion"].strip(),
        )
        ficha = FichaAndChecklistFactory.create_qr_preinscription(
            owner=owner,
            brand_model=d["marca_modelo"].strip(),
            device_type=d.get("tipo", "Notebook"),
            problem=d["problema_declarado"].strip(),
            service_names=d["servicios"],
        )
        ClinicEventBus.get_instance().publish(
            "QR_PREINSCRIPTION",
            {
                "nivel": "INFO",
                "actor": owner.nombre_completo,
                "ruta": request.path,
                "ip": _client_ip(request),
                "detalle": f"Preinscripción QR generó ticket {ficha.numero_ticket} ({ficha.dispositivo.codigo_dispositivo}).",
            },
        )
        return Response(
            {
                "numero_ticket": ficha.numero_ticket,
                "estado": ficha.estado,
                "titular": owner.nombre_completo,
                "rut": owner.rut,
                "dispositivo": ficha.dispositivo.marca_modelo,
                "codigo_dispositivo": ficha.dispositivo.codigo_dispositivo,
                "problema_declarado": ficha.problema_declarado,
                "servicios": list(ficha.servicios.values_list("nombre", flat=True)),
            },
            status=status.HTTP_201_CREATED,
        )


class PublicTicketLookupView(APIView):
    """Consulta pública protegida contra IDOR (OWASP A01): exige Ticket + RUT coincidente."""

    permission_classes = [AllowAny]

    def get(self, request, numero_ticket: str):
        rut = request.query_params.get("rut", "")
        if not validar_rut_chileno(rut):
            return Response(
                {"detail": "Debe indicar un RUT válido coincidente para consultar su ficha."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ficha = get_object_or_404(
            FichaAtencion.objects.select_related("propietario", "dispositivo").prefetch_related("servicios"),
            numero_ticket=numero_ticket.upper(),
        )
        if ficha.propietario.rut_normalizado != normalize_rut(rut):
            return Response(
                {"detail": "HTTP 403 Forbidden (OWASP A01 IDOR): el RUT no corresponde al titular del ticket."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            {
                "numero_ticket": ficha.numero_ticket,
                "estado": ficha.estado,
                "titular": ficha.propietario.nombre_completo,
                "rut": ficha.propietario.rut,
                "dispositivo": ficha.dispositivo.marca_modelo,
                "problema_declarado": ficha.problema_declarado,
                "servicios": list(ficha.servicios.values_list("nombre", flat=True)),
                "ubicacion_custodia": ficha.ubicacion_custodia,
            }
        )


# ==============================================================================
# PASO 2: TRIAJE MULTI-DISPOSITIVO POR RUT
# ==============================================================================
class TriajeSearchView(APIView):
    permission_classes = [IsRecepcionOrDocente]

    def get(self, request):
        q = request.query_params.get("q", "")
        owners, latency = ClinicaRepository.search_triaje(q)
        return Response(
            {
                "latencia_segundos": latency,
                "cumple_rnf07": latency <= 2.0,
                "propietarios": TriajeOwnerSerializer(owners, many=True).data,
            }
        )


class NuevoTicketDispositivoView(APIView):
    permission_classes = [IsRecepcionOrDocente]

    def post(self, request, codigo_dispositivo: str):
        dev = get_object_or_404(
            Dispositivo.objects.select_related("propietario"),
            codigo_dispositivo=codigo_dispositivo.upper(),
        )
        problema = str(request.data.get("problema_declarado", "Nueva atención en jornada actual.")).strip()
        servicios = request.data.get("servicios") or ["Mantención Física"]
        ficha = FichaAndChecklistFactory.create_qr_preinscription(
            owner=dev.propietario,
            brand_model=dev.marca_modelo,
            device_type=dev.tipo,
            problem=problema,
            service_names=servicios,
            actor_name=_actor_label(request.user),
            device_existing=dev,
        )
        return Response(FichaDetailSerializer(ficha, context={"request": request}).data, status=status.HTTP_201_CREATED)


# ==============================================================================
# FICHAS: LISTADO, DETALLE Y PASOS 3 AL 9
# ==============================================================================
class FichaListView(APIView):
    permission_classes = [IsAnyInternalRole]

    def get(self, request):
        fichas = ClinicaRepository.base_ficha_queryset().all()
        return Response(FichaSummarySerializer(fichas, many=True, context={"request": request}).data)


class FichaDetailView(APIView):
    permission_classes = [IsAnyInternalRole]

    def get(self, request, numero_ticket: str):
        ficha = get_object_or_404(ClinicaRepository.base_ficha_queryset(), numero_ticket=numero_ticket.upper())
        return Response(FichaDetailSerializer(ficha, context={"request": request}).data)


class RecepcionFichaView(APIView):
    permission_classes = [IsRecepcionOrDocente]

    @transaction.atomic
    def post(self, request, numero_ticket: str):
        ficha = get_object_or_404(ClinicaRepository.base_ficha_queryset(), numero_ticket=numero_ticket.upper())
        data = request.data
        services_names = data.get("servicios") or []
        if not services_names:
            return Response({"detail": "Seleccione al menos un servicio oficial (RF06)."}, status=400)

        es_clon = bool(data.get("es_clon", False))
        serie = str(data.get("numero_serie", "")).strip()
        if not serie and not es_clon:
            return Response({"detail": "Ingrese el N° de Serie o marque Equipo Clon (RF04)."}, status=400)

        if not data.get("firma_aceptada"):
            return Response(
                {"detail": "El consentimiento y firma digital del propietario son obligatorios (Ley 21.719)."},
                status=400,
            )

        dev = ficha.dispositivo
        dev.tipo = data.get("tipo", dev.tipo)
        dev.marca_modelo = str(data.get("marca_modelo", dev.marca_modelo)).strip()
        dev.es_clon = es_clon
        if es_clon:
            dev.numero_serie = ""
            if not dev.codigo_interno_clon:
                dev.codigo_interno_clon = FichaAndChecklistFactory.next_clone_code()
        else:
            dev.numero_serie = serie
            dev.codigo_interno_clon = None
        dev.save()

        services = list(ServicioCatalogo.objects.filter(nombre__in=services_names, activo=True))
        if not services:
            return Response({"detail": "Servicios inválidos."}, status=400)

        ficha.problema_declarado = str(data.get("problema_declarado", ficha.problema_declarado)).strip()
        ficha.prueba_inicial = str(data.get("prueba_inicial", ficha.prueba_inicial)).strip()
        ficha.accesorios = str(data.get("accesorios", ficha.accesorios)).strip()
        ficha.danos_preexistentes = str(data.get("danos_preexistentes", ficha.danos_preexistentes)).strip()
        ficha.servicios.set(services)
        ficha.version_plantilla_usada = max(s.version_actual for s in services)

        now = timezone.now()
        ficha.consentimiento_firmado = True
        ficha.fecha_consentimiento = now
        ficha.firma_trazo_svg_data = str(data.get("firma_trazo_svg_data", "CANVAS_SIGNED"))[:8000]
        ficha.firma_hash_sha256 = compute_consent_sha256(
            ficha.numero_ticket,
            ficha.propietario.rut_normalizado,
            ficha.danos_preexistentes,
            ficha.accesorios,
            now.isoformat(),
        )
        ficha.save()

        FichaAndChecklistFactory.materialize_checklist_items(ficha, services, reset_missing_only=True)

        actor = _actor_label(request.user)
        note = (
            f"Recepción confirmada. Servicios: {', '.join(s.nombre for s in services)}. "
            f"Hash firma: {ficha.firma_hash_sha256[:24]}..."
        )
        if ficha.estado == "Preinscrito":
            TicketStateMachine.transition(ficha, "Recibido", actor, request.user, note)
        else:
            BitacoraNota.objects.create(ficha=ficha, autor=request.user, autor_nombre=actor, contenido=note)

        ficha.refresh_from_db()
        return Response(FichaDetailSerializer(ficha, context={"request": request}).data)


class TallerChecklistView(APIView):
    permission_classes = [IsTecnicoOrDocente]

    @transaction.atomic
    def post(self, request, numero_ticket: str):
        ficha = get_object_or_404(ClinicaRepository.base_ficha_queryset(), numero_ticket=numero_ticket.upper())
        if ficha.hallazgo_ilicito_ley_21459:
            return Response(
                {"detail": "Bloqueo Legal (Ley 21.459): intervención suspendida por hallazgo ilícito."},
                status=status.HTTP_423_LOCKED,
            )

        items_payload = request.data.get("items") or []
        if not isinstance(items_payload, list) or not items_payload:
            return Response({"detail": "Debe enviar la lista de ítems del checklist."}, status=400)

        items_by_key = {it.clave_unica: it for it in ficha.checklist_items.all()}
        actor = _actor_label(request.user)

        for entry in items_payload:
            clave = entry.get("clave_unica")
            st = entry.get("estado")
            just = str(entry.get("justificacion", "")).strip()
            if clave not in items_by_key or st not in ("Pendiente", "Realizado", "No aplica"):
                return Response({"detail": f"Ítem o estado inválido: {clave}"}, status=400)
            if st == "No aplica" and not just:
                return Response(
                    {"detail": f"Debe ingresar justificación técnica para '{items_by_key[clave].descripcion_tarea}' marcada como No aplica."},
                    status=400,
                )
            obj = items_by_key[clave]
            obj.estado = st
            obj.justificacion = just
            obj.actualizado_por = actor[:100]
            obj.save()

        if ficha.tecnico_asignado is None and get_user_role(request.user) == ROLE_TECNICO:
            ficha.tecnico_asignado = request.user
            ficha.tecnico_asignado_nombre = request.user.get_full_name() or request.user.username
            ficha.save(update_fields=["tecnico_asignado", "tecnico_asignado_nombre"])

        if ficha.estado == "Recibido":
            TicketStateMachine.transition(ficha, "En proceso", actor, request.user)

        ficha = ClinicaRepository.base_ficha_queryset().get(pk=ficha.pk)
        return Response(FichaDetailSerializer(ficha, context={"request": request}).data)


class BitacoraNotaCreateView(APIView):
    permission_classes = [IsTecnicoOrDocente]

    def post(self, request, numero_ticket: str):
        ficha = get_object_or_404(FichaAtencion, numero_ticket=numero_ticket.upper())
        contenido = str(request.data.get("contenido", "")).strip()
        if not contenido:
            return Response({"detail": "El texto de observación no puede estar vacío."}, status=400)

        BitacoraNota.objects.create(
            ficha=ficha,
            autor=request.user,
            autor_nombre=_actor_label(request.user)[:120],
            contenido=contenido,
        )
        ficha = ClinicaRepository.base_ficha_queryset().get(pk=ficha.pk)
        return Response(FichaDetailSerializer(ficha, context={"request": request}).data, status=201)


class VerificarFinalView(APIView):
    permission_classes = [IsTecnicoOrDocente]

    @transaction.atomic
    def post(self, request, numero_ticket: str):
        ficha = get_object_or_404(ClinicaRepository.base_ficha_queryset(), numero_ticket=numero_ticket.upper())
        condicion = str(request.data.get("condicion_final", "")).strip()
        metricas = str(request.data.get("metricas_post_estres", "")).strip()
        comparacion = str(request.data.get("comparacion_final", "")).strip()
        if not condicion or not comparacion:
            return Response({"detail": "Complete condición final y comparación obligatoria con el ingreso."}, status=400)

        actor = _actor_label(request.user)
        TicketStateMachine.transition(
            ficha,
            "Listo para entrega",
            actor,
            request.user,
            note_text=f"CONTROL DE CALIDAD APROBADO: {condicion}. {metricas}. {comparacion}",
        )
        ficha.condicion_final = condicion
        ficha.metricas_post_estres = metricas
        ficha.comparacion_final = comparacion
        ficha.verificado_salida = True
        ficha.correo_enviado = True
        ficha.save(
            update_fields=["condicion_final", "metricas_post_estres", "comparacion_final", "verificado_salida", "correo_enviado"]
        )
        ficha = ClinicaRepository.base_ficha_queryset().get(pk=ficha.pk)
        return Response(FichaDetailSerializer(ficha, context={"request": request}).data)


class AvisoRetiroView(APIView):
    permission_classes = [IsRecepcionOrDocente]

    @transaction.atomic
    def post(self, request, numero_ticket: str):
        ficha = get_object_or_404(FichaAtencion, numero_ticket=numero_ticket.upper())
        tipo = request.data.get("tipo", "llamada")
        actor = _actor_label(request.user)

        if tipo == "whatsapp":
            BitacoraNota.objects.create(
                ficha=ficha,
                autor=request.user,
                autor_nombre=actor,
                contenido=f"Notificación WhatsApp registrada para contacto {ficha.propietario.telefono}.",
            )
        else:
            estado_llamada = str(request.data.get("estado_llamada", "Contacto confirmado")).strip()
            obs = str(request.data.get("observacion", "")).strip()
            ficha.estado_llamada = estado_llamada
            ficha.save(update_fields=["estado_llamada"])
            BitacoraNota.objects.create(
                ficha=ficha,
                autor=request.user,
                autor_nombre=actor,
                contenido=f"CONTACTO RETIRO: {estado_llamada}. {obs}",
            )

        ficha = ClinicaRepository.base_ficha_queryset().get(pk=ficha.pk)
        return Response(FichaDetailSerializer(ficha, context={"request": request}).data)


class EntregaSalidaView(APIView):
    permission_classes = [IsRecepcionOrDocente]

    @transaction.atomic
    def post(self, request, numero_ticket: str):
        ficha = get_object_or_404(ClinicaRepository.base_ficha_queryset(), numero_ticket=numero_ticket.upper())
        data = request.data
        tipo_receptor = data.get("tipo_receptor", "Titular")
        resultado = data.get("resultado", "Entregado conforme")

        if tipo_receptor == "Tercero":
            t_nom = str(data.get("tercero_nombre", "")).strip()
            t_rut = str(data.get("tercero_rut", "")).strip()
            t_auth = bool(data.get("tercero_autorizado_telefono", False))
            if not t_nom or not validar_rut_chileno(t_rut):
                return Response({"detail": "Ingrese nombre y RUT válido (Módulo 11) del tercero receptor."}, status=400)
            if not t_auth:
                return Response(
                    {"detail": "Bloqueo RF10: debe confirmar la llamada de autorización al titular."}, status=400
                )
            ficha.tipo_receptor = "Tercero"
            ficha.tercero_nombre = t_nom
            ficha.tercero_rut = t_rut
            ficha.tercero_autorizado_telefono = True
        else:
            ficha.tipo_receptor = "Titular"

        actor = _actor_label(request.user)
        det = f" ({ficha.tercero_nombre} - {ficha.tercero_rut})" if ficha.tipo_receptor == "Tercero" else ""
        TicketStateMachine.transition(
            ficha,
            resultado,
            actor,
            request.user,
            note_text=f"ENTREGA REGISTRADA ({resultado}). Receptor: {ficha.tipo_receptor}{det}.",
        )
        ficha.resultado_entrega = resultado
        ficha.incidencia_activa = False
        ficha.save()

        ficha = ClinicaRepository.base_ficha_queryset().get(pk=ficha.pk)
        return Response(FichaDetailSerializer(ficha, context={"request": request}).data)


class EncuestaSatisfaccionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, numero_ticket: str):
        ficha = get_object_or_404(FichaAtencion, numero_ticket=numero_ticket.upper())
        if not request.user.is_authenticated:
            rut = request.data.get("rut", "")
            if normalize_rut(rut) != ficha.propietario.rut_normalizado:
                return Response({"detail": "Se requiere sesión interna o RUT del titular."}, status=403)
        estrellas = int(request.data.get("estrellas", 5))
        claridad = str(request.data.get("claridad", "Muy clara"))
        rec = str(request.data.get("recomendaria", "Sí, totalmente"))
        EncuestaSatisfaccion.objects.update_or_create(
            ficha=ficha,
            defaults={"estrellas": max(1, min(5, estrellas)), "claridad": claridad, "recomendaria": rec},
        )
        return Response({"saved": True}, status=201)


class CustodiaTrasladoView(APIView):
    permission_classes = [IsRecepcionOrDocente]

    @transaction.atomic
    def post(self, request, numero_ticket: str):
        ficha = get_object_or_404(ClinicaRepository.base_ficha_queryset(), numero_ticket=numero_ticket.upper())
        ubicacion = str(request.data.get("ubicacion_custodia", "Sala de Profesores · Segundo Piso (INACAP)")).strip()
        resp = str(request.data.get("responsable_custodia", "Prof. Pablo E. Pesce Sánchez")).strip()
        acta = f"ACTA-CUST-2026-{ficha.numero_ticket.replace('PC-', '')}"

        actor = _actor_label(request.user)
        TicketStateMachine.transition(
            ficha,
            "En custodia",
            actor,
            request.user,
            note_text=f"CUSTODIA 18:00h: {ubicacion} · {resp} · {acta} (retención máx. 60 días Ley 21.719).",
        )
        now = timezone.now()
        ficha.ubicacion_custodia = ubicacion
        ficha.responsable_custodia = resp
        ficha.acta_custodia_numero = acta
        ficha.fecha_custodia = now
        ficha.fecha_limite_60_dias = (now + timedelta(days=60)).date()
        ficha.save()

        ficha = ClinicaRepository.base_ficha_queryset().get(pk=ficha.pk)
        return Response(FichaDetailSerializer(ficha, context={"request": request}).data)


class CustodiaAnonimizarVencidosView(APIView):
    """Ley N° 21.719: Anonimización irreversible de PII tras 60 días de custodia sin retiro."""

    permission_classes = [IsDocentePO]

    @transaction.atomic
    def post(self, request):
        today = timezone.now().date()
        vencidas = FichaAtencion.objects.select_related("propietario").filter(
            estado="En custodia", fecha_limite_60_dias__lt=today
        )
        owners_done = 0
        for f in vencidas:
            ow = f.propietario
            if not ow.anonimizado:
                ow.anonimizado = True
                ow.anonimizado_en = timezone.now()
                ow.rut = f"ANON-{ow.id:06d}"
                ow.rut_normalizado = f"ANON{ow.id:06d}"
                ow.nombre_completo = "Titular Anonimizado (Ley 21.719)"
                ow.telefono = "[Eliminado tras 60 días]"
                ow.correo = f"anon-{ow.id}@eliminado.local"
                ow.comuna_direccion = "[Eliminado tras 60 días]"
                ow.save()
                owners_done += 1

        ClinicEventBus.get_instance().publish(
            "LEY_21719_ANONYMIZATION",
            {
                "nivel": "INFO",
                "usuario": request.user,
                "actor": _actor_label(request.user),
                "ruta": request.path,
                "ip": _client_ip(request),
                "detalle": f"Proceso retención 60 días ejecutado: {owners_done} titular(es) anonimizado(s).",
            },
        )
        return Response({"anonimizados": owners_done})


# ==============================================================================
# INCIDENCIAS (CA07) Y PROTOCOLO HALLAZGO ILÍCITO (LEY 21.459)
# ==============================================================================
class ReportarIncidenciaView(APIView):
    permission_classes = [IsTecnicoOrDocente]

    @transaction.atomic
    def post(self, request, numero_ticket: str):
        ficha = get_object_or_404(FichaAtencion, numero_ticket=numero_ticket.upper())
        desc = str(request.data.get("descripcion_incidencia", "")).strip()
        if not desc:
            return Response({"detail": "Describa la falla imprevista detectada."}, status=400)
        ficha.incidencia_activa = True
        ficha.descripcion_incidencia = desc
        ficha.save(update_fields=["incidencia_activa", "descripcion_incidencia"])

        TicketStateMachine.transition(
            ficha,
            "En espera",
            _actor_label(request.user),
            request.user,
            note_text=f"⚠️ FALLA IMPREVISTA (CA07): {desc}. Trabajo suspendido hasta directriz docente.",
        )
        ficha = ClinicaRepository.base_ficha_queryset().get(pk=ficha.pk)
        return Response(FichaDetailSerializer(ficha, context={"request": request}).data)


class HallazgoIlicitoLey21459View(APIView):
    permission_classes = [IsTecnicoOrDocente]

    @transaction.atomic
    def post(self, request, numero_ticket: str):
        ficha = get_object_or_404(FichaAtencion, numero_ticket=numero_ticket.upper())
        ficha.hallazgo_ilicito_ley_21459 = True
        ficha.incidencia_activa = True
        ficha.descripcion_incidencia = (
            "PROTOCOLO LEY N° 21.459: Detección de presunto material ilícito durante intervención técnica."
        )
        ficha.save(update_fields=["hallazgo_ilicito_ley_21459", "incidencia_activa", "descripcion_incidencia"])

        actor = _actor_label(request.user)
        TicketStateMachine.transition(
            ficha,
            "En espera",
            actor,
            request.user,
            note_text="🚨 SUSPENSIÓN INMEDIATA LEY 21.459: Dispositivo aislado sin alterar metadatos. Cadena de custodia activa.",
        )
        ClinicEventBus.get_instance().publish(
            "LEGAL_21459_HOLD",
            {
                "nivel": "CRITICAL",
                "usuario": request.user,
                "actor": actor,
                "ruta": request.path,
                "ip": _client_ip(request),
                "detalle": f"Ticket {ficha.numero_ticket} retenido bajo cadena de custodia (Ley N° 21.459).",
            },
        )
        ficha = ClinicaRepository.base_ficha_queryset().get(pk=ficha.pk)
        return Response(FichaDetailSerializer(ficha, context={"request": request}).data)


class ResolverIncidenciaDocenteView(APIView):
    permission_classes = [IsDocentePO]

    @transaction.atomic
    def post(self, request, numero_ticket: str):
        ficha = get_object_or_404(FichaAtencion, numero_ticket=numero_ticket.upper())
        accion = request.data.get("accion", "directriz")
        actor = _actor_label(request.user)

        if accion == "directriz":
            inst = str(request.data.get("directriz_docente", "")).strip()
            if not inst:
                return Response({"detail": "Ingrese la directriz docente."}, status=400)
            ficha.directriz_docente = inst
            ficha.save(update_fields=["directriz_docente"])
            BitacoraNota.objects.create(
                ficha=ficha, autor=request.user, autor_nombre=actor, contenido=f"INSTRUCCIÓN DOCENTE: {inst}"
            )
        elif accion == "autorizar":
            ficha.incidencia_activa = False
            ficha.hallazgo_ilicito_ley_21459 = False
            ficha.save(update_fields=["incidencia_activa", "hallazgo_ilicito_ley_21459"])
            TicketStateMachine.transition(
                ficha,
                "En proceso",
                actor,
                request.user,
                note_text="TITULAR AUTORIZA CONTINUAR: Incidencia resuelta y ficha reanudada en taller.",
            )
        elif accion == "devolver":
            ficha.incidencia_activa = False
            ficha.resultado_entrega = "Devuelto sin reparación"
            ficha.save(update_fields=["incidencia_activa", "resultado_entrega"])
            TicketStateMachine.transition(
                ficha,
                "Devuelto sin reparación",
                actor,
                request.user,
                note_text="CIERRE ANTICIPADO DOCENTE: Devuelto sin reparación por inviabilidad/rechazo.",
            )
        else:
            return Response({"detail": "Acción inválida."}, status=400)

        ficha = ClinicaRepository.base_ficha_queryset().get(pk=ficha.pk)
        return Response(FichaDetailSerializer(ficha, context={"request": request}).data)


# ==============================================================================
# ADMINISTRACIÓN DOCENTE: PLANTILLAS, NÓMINA CSV (OWASP A05), MÉTRICAS & AUDITORÍA
# ==============================================================================
class AdminPlantillasView(APIView):
    permission_classes = [IsDocentePO]

    def get(self, request):
        servicios = ServicioCatalogo.objects.filter(activo=True).order_by("id")
        return Response(ServicioPlantillaSerializer(servicios, many=True).data)

    @transaction.atomic
    def put(self, request):
        srv_nombre = request.data.get("servicio")
        tareas = [str(t).strip() for t in (request.data.get("tareas") or []) if str(t).strip()]
        if not srv_nombre or not tareas:
            return Response({"detail": "Especifique servicio y al menos una tarea."}, status=400)

        srv = get_object_or_404(ServicioCatalogo, nombre=srv_nombre)
        srv.version_actual += 1
        srv.save(update_fields=["version_actual"])

        for idx, desc in enumerate(tareas, start=1):
            PlantillaTarea.objects.create(servicio=srv, version=srv.version_actual, orden=idx, descripcion=desc[:255])

        ClinicEventBus.get_instance().publish(
            "TEMPLATE_VERSIONED",
            {
                "nivel": "INFO",
                "usuario": request.user,
                "actor": _actor_label(request.user),
                "ruta": request.path,
                "ip": _client_ip(request),
                "detalle": f"Plantilla '{srv.nombre}' actualizada a versión v{srv.version_actual}.0 ({len(tareas)} tareas).",
            },
        )
        return self.get(request)


class AdminNominaView(APIView):
    permission_classes = [IsDocentePO]

    def get(self, request):
        perfiles = PerfilOperador.objects.select_related("user").filter(rol=ROLE_TECNICO).order_by("id")
        activos = perfiles.filter(habilitado_jornada=True).count()
        return Response(
            {
                "total": perfiles.count(),
                "activos": activos,
                "estudiantes": PerfilNominaSerializer(perfiles, many=True).data,
            }
        )


class AdminNominaImportCSVView(APIView):
    permission_classes = [IsDocentePO]

    @transaction.atomic
    def post(self, request):
        import hashlib

        bus = ClinicEventBus.get_instance()
        registros = []

        if request.data.get("simular_65"):
            for i in range(1, 66):
                cuerpo = str(20100200 + i * 137)
                rev = cuerpo[::-1]
                grupos = [rev[j : j + 3][::-1] for j in range(0, len(rev), 3)]
                rut_fmt = f"{'.'.join(reversed(grupos))}-{calc_rut_dv(cuerpo)}"
                registros.append(
                    (
                        rut_fmt,
                        f"Estudiante Taller #{i:02d}",
                        "TI3043-02" if i % 2 == 0 else "TI3043-01",
                    )
                )
        else:
            raw_csv = str(request.data.get("csv_text", ""))
            if "file" in request.FILES:
                raw_csv = request.FILES["file"].read().decode("utf-8", errors="replace")
            if not raw_csv.strip():
                return Response({"detail": "Adjunte un archivo .csv o envíe simular_65=true."}, status=400)

            reader = csv.reader(io.StringIO(raw_csv))
            sanitized_hits = 0
            for row in reader:
                if len(row) < 2 or re.search(r"rut", row[0], re.I):
                    continue
                raw_rut, raw_name = row[0], row[1]
                raw_sec = row[2] if len(row) > 2 else "TI3043-01"
                s_rut = sanitize_csv_cell(raw_rut)
                s_name = sanitize_csv_cell(raw_name)
                s_sec = sanitize_csv_cell(raw_sec)
                if s_name.startswith("'") or s_rut.startswith("'"):
                    sanitized_hits += 1
                registros.append((s_rut, s_name, s_sec))

            if sanitized_hits:
                bus.publish(
                    "CSV_INJECTION_SANITIZED",
                    {
                        "nivel": "WARN",
                        "usuario": request.user,
                        "actor": _actor_label(request.user),
                        "ruta": request.path,
                        "ip": _client_ip(request),
                        "detalle": f"Neutralizadas {sanitized_hits} celdas peligrosas (=,+,-,@) en CSV (OWASP A05).",
                    },
                )

        if not registros:
            return Response({"detail": "No se encontraron registros válidos en el CSV."}, status=400)

        for idx, (rut, nombre, seccion) in enumerate(registros, start=1):
            clean_rut = rut[:16]
            existing_perfil = PerfilOperador.objects.select_related("user").filter(rut=clean_rut).first()
            if existing_perfil:
                user = existing_perfil.user
                if not user.has_usable_password():
                    user.first_name = nombre[:60]
                user.is_active = True
                user.save()
                perfil = existing_perfil
            else:
                rut_slug = normalize_rut(clean_rut).lower() or hashlib.sha256(clean_rut.encode()).hexdigest()[:10]
                uname = f"al_{rut_slug}"[:30]
                user, created = User.objects.get_or_create(
                    username=uname,
                    defaults={"first_name": nombre[:60], "email": f"{uname}@inacapmail.cl"},
                )
                user.first_name = nombre[:60]
                user.is_active = True
                if created or not user.has_usable_password():
                    user.set_unusable_password()
                user.save()
                perfil, _ = PerfilOperador.objects.get_or_create(
                    user=user,
                    defaults={"rol": ROLE_TECNICO, "rut": clean_rut},
                )

            tok_hash = "SHA256:" + hashlib.sha256(f"{user.username}|TI3043".encode()).hexdigest()[:16]
            perfil.seccion = seccion[:20]
            perfil.token_temporal_hash = tok_hash
            perfil.habilitado_jornada = True
            perfil.save()

        bus.publish(
            "CSV_MASS_IMPORT",
            {
                "nivel": "INFO",
                "usuario": request.user,
                "actor": _actor_label(request.user),
                "ruta": request.path,
                "ip": _client_ip(request),
                "detalle": f"Nómina de {len(registros)} alumnos técnicos habilitada en PostgreSQL con tokens SHA-256.",
            },
        )
        return AdminNominaView().get(request)


class AdminNominaRevokeView(APIView):
    permission_classes = [IsDocentePO]

    @transaction.atomic
    def post(self, request):
        perfiles = PerfilOperador.objects.select_related("user").filter(rol=ROLE_TECNICO)
        count = 0
        for p in perfiles:
            if p.user.username not in ("diego.astudillo", "daniel.meliman"):
                p.habilitado_jornada = False
                p.save(update_fields=["habilitado_jornada"])
                p.user.is_active = False
                p.user.save(update_fields=["is_active"])
                count += 1

        ClinicEventBus.get_instance().publish(
            "CSV_MASS_REVOKE",
            {
                "nivel": "WARN",
                "usuario": request.user,
                "actor": _actor_label(request.user),
                "ruta": request.path,
                "ip": _client_ip(request),
                "detalle": f"Credenciales temporales de {count} alumnos técnicos revocadas al cierre de jornada.",
            },
        )
        return AdminNominaView().get(request)


class MetricasView(APIView):
    permission_classes = [IsDocentePO]

    def get(self, request):
        return Response(ClinicaRepository.get_metrics_summary())


class ExportarMetricasCSVView(APIView):
    """Exportación CSV segura (OWASP A05 anti-fórmulas), sin generar archivos JSON."""

    permission_classes = [IsDocentePO]

    def get(self, request):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="respaldo_clinica_pc.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(["Ticket", "Dispositivo", "Serie_o_Clon", "Titular", "RUT", "Servicios", "Estado"])
        for f in ClinicaRepository.base_ficha_queryset().all():
            writer.writerow(
                [
                    sanitize_csv_cell(f.numero_ticket),
                    sanitize_csv_cell(f.dispositivo.marca_modelo),
                    sanitize_csv_cell(f.dispositivo.numero_serie or f.dispositivo.codigo_interno_clon or "N/A"),
                    sanitize_csv_cell(f.propietario.nombre_completo),
                    sanitize_csv_cell(f.propietario.rut),
                    sanitize_csv_cell(", ".join(s.nombre for s in f.servicios.all())),
                    sanitize_csv_cell(f.estado),
                ]
            )
        return response


class SeguridadAuditoriaView(APIView):
    permission_classes = [IsDocentePO]

    def get(self, request):
        logs = EventoSeguridadOWASP.objects.all()[:60]
        return Response(
            {
                "database_engine": f"PostgreSQL ({connection.settings_dict['NAME']})",
                "gof_patterns": [
                    {"pattern": "State", "class": "TicketStateMachine", "purpose": "Transiciones válidas + CA07/CA08/Ley 21.459"},
                    {"pattern": "Repository + Singleton", "class": "ClinicaRepository", "purpose": "ORM PostgreSQL optimizado y medición RNF07"},
                    {"pattern": "Factory", "class": "FichaAndChecklistFactory", "purpose": "Correlativos PC/DEV/CL e ítems multi-servicio únicos"},
                    {"pattern": "Observer", "class": "ClinicEventBus", "purpose": "Registro automático WORM OWASP A09"},
                ],
                "logs": EventoSeguridadSerializer(logs, many=True).data,
            }
        )
