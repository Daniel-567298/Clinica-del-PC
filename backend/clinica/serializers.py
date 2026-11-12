# -*- coding: utf-8 -*-
"""Serializers DRF con proyección server-side Ley 21.719 y validación Módulo 11."""

from rest_framework import serializers

from clinica.models import (
    BitacoraNota,
    ChecklistItemEjecucion,
    Dispositivo,
    EncuestaSatisfaccion,
    EventoSeguridadOWASP,
    FichaAtencion,
    PerfilOperador,
    PlantillaTarea,
    Propietario,
    ServicioCatalogo,
    TransicionEstadoLog,
)
from clinica.patterns.state_machine import TicketStateMachine
from clinica.security.permissions import get_user_role
from clinica.security.privacy import project_owner_for_role
from clinica.security.validators import validar_rut_chileno


class DispositivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispositivo
        fields = [
            "id",
            "codigo_dispositivo",
            "tipo",
            "marca_modelo",
            "numero_serie",
            "es_clon",
            "codigo_interno_clon",
            "creado_en",
        ]


class ChecklistItemSerializer(serializers.ModelSerializer):
    servicio_nombre = serializers.CharField(source="servicio.nombre", read_only=True)

    class Meta:
        model = ChecklistItemEjecucion
        fields = [
            "id",
            "servicio_nombre",
            "clave_unica",
            "orden",
            "descripcion_tarea",
            "estado",
            "justificacion",
            "actualizado_por",
            "actualizado_en",
        ]


class BitacoraNotaSerializer(serializers.ModelSerializer):
    fecha = serializers.DateTimeField(source="creado_en", format="%d/%m/%Y %H:%M", read_only=True)

    class Meta:
        model = BitacoraNota
        fields = ["id", "autor_nombre", "contenido", "fecha", "creado_en"]


class TransicionEstadoLogSerializer(serializers.ModelSerializer):
    fecha = serializers.DateTimeField(source="creado_en", format="%d/%m/%Y %H:%M", read_only=True)

    class Meta:
        model = TransicionEstadoLog
        fields = ["id", "estado_origen", "estado_destino", "actor_nombre", "fecha"]


class EncuestaSatisfaccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EncuestaSatisfaccion
        fields = ["estrellas", "claridad", "recomendaria", "creado_en"]


class FichaSummarySerializer(serializers.ModelSerializer):
    propietario = serializers.SerializerMethodField()
    dispositivo = DispositivoSerializer(read_only=True)
    servicios = serializers.SlugRelatedField(many=True, read_only=True, slug_field="nombre")
    checklist_total = serializers.SerializerMethodField()
    checklist_pendientes = serializers.SerializerMethodField()

    class Meta:
        model = FichaAtencion
        fields = [
            "id",
            "numero_ticket",
            "estado",
            "problema_declarado",
            "servicios",
            "propietario",
            "dispositivo",
            "tecnico_asignado_nombre",
            "consentimiento_firmado",
            "incidencia_activa",
            "hallazgo_ilicito_ley_21459",
            "ubicacion_custodia",
            "acta_custodia_numero",
            "checklist_total",
            "checklist_pendientes",
            "creado_en",
        ]

    def get_propietario(self, obj):
        request = self.context.get("request")
        role = get_user_role(getattr(request, "user", None))
        return project_owner_for_role(obj.propietario, role)

    def get_checklist_total(self, obj):
        return obj.checklist_items.count()

    def get_checklist_pendientes(self, obj):
        return obj.checklist_items.filter(estado="Pendiente").count()


class FichaDetailSerializer(FichaSummarySerializer):
    checklist_items = ChecklistItemSerializer(many=True, read_only=True)
    notas = BitacoraNotaSerializer(many=True, read_only=True)
    transiciones = TransicionEstadoLogSerializer(many=True, read_only=True)
    encuesta = EncuestaSatisfaccionSerializer(read_only=True)
    allowed_transitions = serializers.SerializerMethodField()
    quality_gate = serializers.SerializerMethodField()
    tercero_rut = serializers.SerializerMethodField()

    class Meta(FichaSummarySerializer.Meta):
        fields = FichaSummarySerializer.Meta.fields + [
            "prueba_inicial",
            "danos_preexistentes",
            "accesorios",
            "fecha_consentimiento",
            "firma_hash_sha256",
            "seccion",
            "version_plantilla_usada",
            "descripcion_incidencia",
            "directriz_docente",
            "estado_llamada",
            "correo_enviado",
            "verificado_salida",
            "condicion_final",
            "metricas_post_estres",
            "comparacion_final",
            "tipo_receptor",
            "tercero_nombre",
            "tercero_rut",
            "tercero_autorizado_telefono",
            "resultado_entrega",
            "responsable_custodia",
            "fecha_custodia",
            "fecha_limite_60_dias",
            "checklist_items",
            "notas",
            "transiciones",
            "encuesta",
            "allowed_transitions",
            "quality_gate",
        ]

    def get_allowed_transitions(self, obj):
        return TicketStateMachine.allowed_targets(obj.estado)

    def get_quality_gate(self, obj):
        ok, reason = TicketStateMachine.can_transition(obj, "Listo para entrega")
        return {"ok": ok, "reason": reason}

    def get_tercero_rut(self, obj):
        request = self.context.get("request")
        role = get_user_role(getattr(request, "user", None))
        if role == "TECNICO" and obj.tercero_rut:
            return "[Protegido Ley 21.719]"
        return obj.tercero_rut


class QRPreinscriptionInputSerializer(serializers.Serializer):
    nombre_completo = serializers.CharField(max_length=120)
    rut = serializers.CharField(max_length=16)
    telefono = serializers.CharField(max_length=30)
    correo = serializers.EmailField(max_length=120)
    comuna_direccion = serializers.CharField(max_length=160)
    marca_modelo = serializers.CharField(max_length=120)
    tipo = serializers.ChoiceField(
        choices=[t[0] for t in Dispositivo.TIPOS], default="Notebook", required=False
    )
    problema_declarado = serializers.CharField(max_length=600)
    servicios = serializers.ListField(
        child=serializers.CharField(max_length=80), allow_empty=False
    )

    def validate_rut(self, value):
        if not validar_rut_chileno(value):
            raise serializers.ValidationError("RUT chileno inválido (falló dígito verificador Módulo 11).")
        return value


class TriajeOwnerSerializer(serializers.ModelSerializer):
    dispositivos = serializers.SerializerMethodField()

    class Meta:
        model = Propietario
        fields = [
            "id",
            "rut",
            "nombre_completo",
            "telefono",
            "correo",
            "comuna_direccion",
            "dispositivos",
        ]

    def get_dispositivos(self, obj):
        devs = []
        for d in obj.dispositivos.all():
            fichas_qs = sorted(d.fichas.all(), key=lambda f: f.creado_en, reverse=True)
            active = fichas_qs[0] if fichas_qs else None
            devs.append(
                {
                    "id": d.id,
                    "codigo_dispositivo": d.codigo_dispositivo,
                    "tipo": d.tipo,
                    "marca_modelo": d.marca_modelo,
                    "numero_serie": d.numero_serie,
                    "es_clon": d.es_clon,
                    "codigo_interno_clon": d.codigo_interno_clon,
                    "historial_count": len(fichas_qs),
                    "ficha_activa": (
                        {
                            "numero_ticket": active.numero_ticket,
                            "estado": active.estado,
                            "problema_declarado": active.problema_declarado,
                        }
                        if active
                        else None
                    ),
                }
            )
        return devs


class EventoSeguridadSerializer(serializers.ModelSerializer):
    fecha = serializers.DateTimeField(source="creado_en", format="%d/%m/%Y %H:%M:%S", read_only=True)

    class Meta:
        model = EventoSeguridadOWASP
        fields = ["id", "fecha", "nivel", "evento", "actor_nombre", "ruta", "ip_origen", "detalle"]


class PerfilNominaSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = PerfilOperador
        fields = ["id", "rut", "nombre", "seccion", "username", "token_temporal_hash", "habilitado_jornada"]

    def get_nombre(self, obj):
        return obj.user.get_full_name() or obj.user.username


class ServicioPlantillaSerializer(serializers.ModelSerializer):
    tareas = serializers.SerializerMethodField()

    class Meta:
        model = ServicioCatalogo
        fields = ["id", "codigo", "nombre", "version_actual", "tareas"]

    def get_tareas(self, obj):
        return list(
            PlantillaTarea.objects.filter(servicio=obj, version=obj.version_actual)
            .order_by("orden")
            .values_list("descripcion", flat=True)
        )
