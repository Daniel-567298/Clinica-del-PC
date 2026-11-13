# -*- coding: utf-8 -*-
from django.contrib import admin
from clinica.models import Sede, EventoClinica
admin.site.register(Sede)
admin.site.register(EventoClinica)

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


@admin.register(Propietario)
class PropietarioAdmin(admin.ModelAdmin):
    list_display = ("rut", "nombre_completo", "telefono", "correo", "anonimizado")
    search_fields = ("rut", "rut_normalizado", "nombre_completo", "correo")


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ("codigo_dispositivo", "marca_modelo", "tipo", "numero_serie", "es_clon", "codigo_interno_clon", "propietario")
    list_filter = ("tipo", "es_clon")
    search_fields = ("codigo_dispositivo", "marca_modelo", "numero_serie", "codigo_interno_clon")


@admin.register(ServicioCatalogo)
class ServicioCatalogoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "version_actual", "activo")


@admin.register(PlantillaTarea)
class PlantillaTareaAdmin(admin.ModelAdmin):
    list_display = ("servicio", "version", "orden", "descripcion")
    list_filter = ("servicio", "version")


@admin.register(PerfilOperador)
class PerfilOperadorAdmin(admin.ModelAdmin):
    filter_horizontal = ("sedes",)
    list_display = ("user", "rol", "rut", "seccion", "habilitado_jornada", "intentos_fallidos", "bloqueado_hasta")
    list_filter = ("rol", "habilitado_jornada", "seccion")


@admin.register(FichaAtencion)
class FichaAtencionAdmin(admin.ModelAdmin):
    list_display = ("numero_ticket", "estado", "dispositivo", "propietario", "consentimiento_firmado", "incidencia_activa", "hallazgo_ilicito_ley_21459")
    list_filter = ("estado", "consentimiento_firmado", "incidencia_activa", "hallazgo_ilicito_ley_21459")
    search_fields = ("numero_ticket", "propietario__rut", "propietario__nombre_completo", "dispositivo__marca_modelo")


@admin.register(ChecklistItemEjecucion)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ("ficha", "servicio", "clave_unica", "estado", "actualizado_por")
    list_filter = ("estado", "servicio")


@admin.register(BitacoraNota)
class BitacoraNotaAdmin(admin.ModelAdmin):
    list_display = ("ficha", "autor_nombre", "creado_en")
    readonly_fields = ("ficha", "autor", "autor_nombre", "contenido", "creado_en")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TransicionEstadoLog)
class TransicionEstadoLogAdmin(admin.ModelAdmin):
    list_display = ("ficha", "estado_origen", "estado_destino", "actor_nombre", "creado_en")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EventoSeguridadOWASP)
class EventoSeguridadAdmin(admin.ModelAdmin):
    list_display = ("creado_en", "nivel", "evento", "actor_nombre", "ruta")
    list_filter = ("nivel", "evento")

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(EncuestaSatisfaccion)
