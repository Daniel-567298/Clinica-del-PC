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
    EventoClinica,
    Sede,
    PerfilOperador,
    PlantillaTarea,
    Propietario,
    ServicioCatalogo,
    JornadaEvento,
    TransicionEstadoLog,
)
from clinica.patterns.state_machine import TicketStateMachine
from clinica.security.permissions import get_user_role
from clinica.security.privacy import project_owner_for_role, redact_note_for_technician
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
    evento_nombre = serializers.CharField(source="evento.nombre", read_only=True)
    sede_nombre = serializers.CharField(source="evento.sede.nombre", read_only=True)
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
            "evento",
            "evento_nombre",
            "sede_nombre",
            "jornada_preferida", "jornada_recepcion",
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
    resguardo_activo = serializers.SerializerMethodField()
    checklist_items = ChecklistItemSerializer(many=True, read_only=True)
    notas = serializers.SerializerMethodField()
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
            "prueba_conjunta_resultado",
            "prueba_conjunta_observaciones",
            "receptor_confirma_prueba",
            "entrega_registrada_en",
            "entrega_registrada_por",
            "responsable_custodia",
            "fecha_custodia",
            "fecha_limite_60_dias",
            "checklist_items",
            "notas",
            "transiciones",
            "encuesta",
            "allowed_transitions",
            "quality_gate",
            "resguardo_activo", "derivacion_destino", "derivacion_motivo", "derivacion_registrada_en",
        ]

    def get_allowed_transitions(self, obj):
        return TicketStateMachine.allowed_targets(obj.estado)

    def get_resguardo_activo(self, obj):
        r = obj.resguardos.filter(reanudado_en__isnull=True).select_related('hasta').first()
        return {"id":r.id,"hasta":r.hasta_id,"fecha":r.hasta.fecha,"lugar":r.lugar,"responsable":r.responsable} if r else None

    def get_notas(self, obj):
        role = get_user_role(getattr(self.context.get("request"), "user", None))
        notes = [n for n in obj.notas.all() if role != "TECNICO" or not n.privada_meson]
        rows = BitacoraNotaSerializer(notes, many=True).data
        if role == "TECNICO":
            for row in rows:
                row["contenido"] = redact_note_for_technician(row["contenido"], obj)
        return rows

    def to_representation(self, instance):
        data = super().to_representation(instance)
        role = get_user_role(getattr(self.context.get("request"), "user", None))
        if role == "TECNICO":
            for field in ("prueba_conjunta_observaciones", "descripcion_incidencia", "directriz_docente", "derivacion_motivo", "derivacion_destino"):
                data[field] = redact_note_for_technician(data[field], instance)
        return data

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
    jornada_preferida = serializers.IntegerField(required=False, allow_null=True)
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


class EntregaInputSerializer(serializers.Serializer):
    tipo_receptor = serializers.ChoiceField(choices=["Titular", "Tercero"])
    resultado = serializers.ChoiceField(choices=["Entregado conforme", "Devuelto sin reparación"])
    tercero_nombre = serializers.CharField(max_length=120, required=False, allow_blank=True)
    tercero_rut = serializers.CharField(max_length=16, required=False, allow_blank=True)
    tercero_autorizado_telefono = serializers.BooleanField(default=False)
    prueba_conjunta_resultado = serializers.ChoiceField(choices=["Conforme", "No conforme", "No se pudo probar"])
    prueba_conjunta_observaciones = serializers.CharField(max_length=2000, allow_blank=True, default="")
    receptor_confirma_prueba = serializers.BooleanField()

    def validate(self, data):
        if not data["receptor_confirma_prueba"]:
            raise serializers.ValidationError("Debe confirmar que la prueba o su imposibilidad se revisó con quien retira.")
        if data["resultado"] == "Entregado conforme" and data["prueba_conjunta_resultado"] != "Conforme":
            raise serializers.ValidationError("La entrega conforme requiere una prueba conjunta conforme.")
        if data["prueba_conjunta_resultado"] != "Conforme" and not data["prueba_conjunta_observaciones"]:
            raise serializers.ValidationError("Explique la disconformidad o por qué no se pudo probar el equipo.")
        return data


class EncuestaInputSerializer(serializers.Serializer):
    estrellas = serializers.IntegerField(min_value=1, max_value=5)
    claridad = serializers.ChoiceField(choices=["Muy clara", "Clara", "Regular"])
    recomendaria = serializers.ChoiceField(choices=["Sí, totalmente", "Probablemente sí", "No"])


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
        event_id = self.context.get("evento_id")
        allowed_sedes = self.context.get("sedes")
        for d in obj.dispositivos.all():
            fichas_qs = [f for f in d.fichas.all()
                         if (not event_id or f.evento_id == event_id)
                         and (allowed_sedes is None or f.evento.sede_id in allowed_sedes)]
            fichas_qs.sort(key=lambda f: f.creado_en, reverse=True)
            if not fichas_qs:
                continue
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


class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = ["id", "nombre", "codigo", "direccion", "activa"]


class EventoSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source="sede.nombre", read_only=True)
    total_fichas = serializers.SerializerMethodField()
    jornadas = serializers.SerializerMethodField()

    class Meta:
        model = EventoClinica
        fields = ["id", "sede", "sede_nombre", "nombre", "fecha_inicio", "fecha_fin", "lugar", "estado", "total_fichas", "jornadas", "permite_continuidad", "inscripcion_desde", "inscripcion_hasta"]
        read_only_fields = ["estado"]

    def get_total_fichas(self, obj):
        return obj.fichas.count() if self.context.get("internal") else None

    def get_jornadas(self, obj):
        return list(obj.jornadas.values('id','fecha','apertura','cierre','limite_recepcion','estado'))

    def validate(self, data):
        if data["fecha_fin"] < data["fecha_inicio"]:
            raise serializers.ValidationError("La fecha de término no puede ser anterior al inicio.")
        if (data['fecha_fin'] - data['fecha_inicio']).days >= 366:
            raise serializers.ValidationError('El rango del evento no puede superar un año.')
        if data.get('inscripcion_desde') and data.get('inscripcion_hasta') and data['inscripcion_hasta'] <= data['inscripcion_desde']:
            raise serializers.ValidationError('El cierre de inscripción debe ser posterior a su apertura.')
        return data


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
    version_actual = serializers.SerializerMethodField()

    class Meta:
        model = ServicioCatalogo
        fields = ["id", "codigo", "nombre", "version_actual", "tareas"]

    def get_tareas(self, obj):
        from clinica.patterns.plantillas import plantillas_para_sede
        if self.context.get("sede"):
            return list(plantillas_para_sede(obj, self.context["sede"])[0].values_list("descripcion", flat=True))
        return list(
            PlantillaTarea.objects.filter(servicio=obj, version=obj.version_actual)
            .order_by("orden")
            .values_list("descripcion", flat=True)
        )

    def get_version_actual(self, obj):
        from clinica.patterns.plantillas import plantillas_para_sede
        return plantillas_para_sede(obj, self.context["sede"])[1] if self.context.get("sede") else obj.version_actual
