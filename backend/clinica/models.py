# -*- coding: utf-8 -*-
"""Modelos relacionales normalizados en PostgreSQL (cero SQLite y cero archivos JSON)."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from clinica.security.validators import format_rut_chileno, normalize_rut, validate_rut_field


class Propietario(models.Model):
    rut = models.CharField(max_length=16, unique=True, validators=[validate_rut_field])
    rut_normalizado = models.CharField(max_length=12, unique=True, db_index=True, editable=False)
    nombre_completo = models.CharField(max_length=120)
    telefono = models.CharField(max_length=30)
    correo = models.EmailField(max_length=120)
    comuna_direccion = models.CharField(max_length=160)
    anonimizado = models.BooleanField(default=False)
    anonimizado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Propietario"
        verbose_name_plural = "Propietarios"
        ordering = ["nombre_completo"]

    def save(self, *args, **kwargs):
        if not self.anonimizado:
            self.rut = format_rut_chileno(self.rut)
            self.rut_normalizado = normalize_rut(self.rut)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre_completo} ({self.rut})"


class Dispositivo(models.Model):
    TIPOS = [
        ("Notebook", "Notebook"),
        ("Desktop / Torre", "Desktop / Torre"),
        ("All-in-One", "All-in-One"),
        ("Mini PC", "Mini PC"),
    ]

    codigo_dispositivo = models.CharField(max_length=16, unique=True, db_index=True)
    propietario = models.ForeignKey(Propietario, on_delete=models.PROTECT, related_name="dispositivos")
    tipo = models.CharField(max_length=40, choices=TIPOS, default="Notebook")
    marca_modelo = models.CharField(max_length=120)
    numero_serie = models.CharField(max_length=60, blank=True, default="")
    es_clon = models.BooleanField(default=False)
    codigo_interno_clon = models.CharField(max_length=16, unique=True, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Dispositivo"
        verbose_name_plural = "Dispositivos"
        ordering = ["codigo_dispositivo"]

    def clean(self):
        if not self.es_clon:
            self.codigo_interno_clon = None

    def save(self, *args, **kwargs):
        if not self.es_clon or not str(self.codigo_interno_clon or "").strip():
            self.codigo_interno_clon = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo_dispositivo} · {self.marca_modelo}"


class ServicioCatalogo(models.Model):
    codigo = models.SlugField(max_length=40, unique=True)
    nombre = models.CharField(max_length=80, unique=True)
    version_actual = models.PositiveIntegerField(default=1)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Servicio Oficial"
        verbose_name_plural = "Servicios Oficiales"
        ordering = ["id"]

    def __str__(self):
        return f"{self.nombre} (v{self.version_actual})"


class PlantillaTarea(models.Model):
    servicio = models.ForeignKey(ServicioCatalogo, on_delete=models.CASCADE, related_name="plantillas")
    version = models.PositiveIntegerField(default=1)
    orden = models.PositiveIntegerField()
    descripcion = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Tarea de Plantilla"
        verbose_name_plural = "Plantillas de Tareas"
        unique_together = [("servicio", "version", "orden")]
        ordering = ["servicio_id", "version", "orden"]

    def __str__(self):
        return f"{self.servicio.nombre} v{self.version} #{self.orden}: {self.descripcion}"


class PerfilOperador(models.Model):
    ROLES = [
        ("RECEPCIONISTA", "Recepcionista"),
        ("TECNICO", "Alumno Técnico"),
        ("DOCENTE_PO", "Docente / PO"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    rol = models.CharField(max_length=20, choices=ROLES)
    rut = models.CharField(max_length=16, unique=True, null=True, blank=True)
    seccion = models.CharField(max_length=20, blank=True, default="TI3043-01")
    token_temporal_hash = models.CharField(max_length=80, blank=True, default="")
    habilitado_jornada = models.BooleanField(default=True)
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Perfil Operador"
        verbose_name_plural = "Perfiles de Operadores"
        ordering = ["rol", "user__username"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.rol})"


class FichaAtencion(models.Model):
    ESTADOS = [
        ("Preinscrito", "Preinscrito"),
        ("Recibido", "Recibido"),
        ("En proceso", "En proceso"),
        ("En espera", "En espera"),
        ("Listo para entrega", "Listo para entrega"),
        ("En custodia", "En custodia"),
        ("Entregado conforme", "Entregado conforme"),
        ("Devuelto sin reparación", "Devuelto sin reparación"),
    ]

    numero_ticket = models.CharField(max_length=16, unique=True, db_index=True)
    propietario = models.ForeignKey(Propietario, on_delete=models.PROTECT, related_name="fichas")
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.PROTECT, related_name="fichas")
    servicios = models.ManyToManyField(ServicioCatalogo, related_name="fichas")
    problema_declarado = models.TextField()
    estado = models.CharField(max_length=32, choices=ESTADOS, default="Preinscrito", db_index=True)

    # Inspección mesón + consentimiento Ley 21.719 / SHA-256 OWASP A08
    prueba_inicial = models.CharField(max_length=60, default="Pendiente inspección")
    danos_preexistentes = models.TextField(default="Pendiente inspección en mesón")
    accesorios = models.CharField(max_length=200, default="Por registrar")
    consentimiento_firmado = models.BooleanField(default=False)
    fecha_consentimiento = models.DateTimeField(null=True, blank=True)
    firma_hash_sha256 = models.CharField(max_length=80, blank=True, default="")
    firma_trazo_svg_data = models.TextField(blank=True, default="")

    # Taller
    tecnico_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fichas_asignadas",
    )
    tecnico_asignado_nombre = models.CharField(max_length=100, default="Por Asignar")
    seccion = models.CharField(max_length=20, default="TI3043-01")
    version_plantilla_usada = models.PositiveIntegerField(default=1)

    # Incidencias CA07 y Ley 21.459
    incidencia_activa = models.BooleanField(default=False)
    hallazgo_ilicito_ley_21459 = models.BooleanField(default=False)
    descripcion_incidencia = models.TextField(blank=True, default="")
    directriz_docente = models.TextField(blank=True, default="")

    # Verificación final, aviso y entrega
    estado_llamada = models.CharField(max_length=60, default="Pendiente")
    correo_enviado = models.BooleanField(default=False)
    verificado_salida = models.BooleanField(default=False)
    condicion_final = models.CharField(max_length=120, blank=True, default="")
    metricas_post_estres = models.CharField(max_length=120, blank=True, default="")
    comparacion_final = models.TextField(blank=True, default="")
    tipo_receptor = models.CharField(max_length=20, default="Titular")
    tercero_nombre = models.CharField(max_length=120, blank=True, default="")
    tercero_rut = models.CharField(max_length=16, blank=True, default="")
    tercero_autorizado_telefono = models.BooleanField(default=False)
    resultado_entrega = models.CharField(max_length=40, blank=True, default="")

    # Custodia 18:00 hrs & retención 60 días (Ley 21.719)
    ubicacion_custodia = models.CharField(max_length=140, blank=True, default="")
    responsable_custodia = models.CharField(max_length=140, blank=True, default="")
    acta_custodia_numero = models.CharField(max_length=40, blank=True, default="")
    fecha_custodia = models.DateTimeField(null=True, blank=True)
    fecha_limite_60_dias = models.DateField(null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ficha de Atención"
        verbose_name_plural = "Fichas de Atención"
        ordering = ["-creado_en", "-id"]

    def __str__(self):
        return f"{self.numero_ticket} [{self.estado}] - {self.dispositivo.marca_modelo}"


class ChecklistItemEjecucion(models.Model):
    ESTADOS_ITEM = [
        ("Pendiente", "Pendiente"),
        ("Realizado", "Realizado"),
        ("No aplica", "No aplica"),
    ]

    ficha = models.ForeignKey(FichaAtencion, on_delete=models.CASCADE, related_name="checklist_items")
    servicio = models.ForeignKey(ServicioCatalogo, on_delete=models.PROTECT)
    clave_unica = models.CharField(max_length=80)
    orden = models.PositiveIntegerField(default=0)
    descripcion_tarea = models.CharField(max_length=255)
    estado = models.CharField(max_length=20, choices=ESTADOS_ITEM, default="Pendiente")
    justificacion = models.TextField(blank=True, default="")
    actualizado_por = models.CharField(max_length=100, blank=True, default="")
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ítem de Checklist"
        verbose_name_plural = "Ítems de Checklist"
        unique_together = [("ficha", "clave_unica")]
        ordering = ["servicio_id", "orden"]


class BitacoraNota(models.Model):
    """Registro WORM (Write-Once-Read-Many): prohíbe edición o borrado posterior (RNF05)."""

    ficha = models.ForeignKey(FichaAtencion, on_delete=models.PROTECT, related_name="notas")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    autor_nombre = models.CharField(max_length=120)
    contenido = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Nota de Bitácora (WORM)"
        verbose_name_plural = "Bitácora de Auditoría (WORM)"
        ordering = ["-creado_en", "-id"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Registro WORM inmutable (RNF05): no se permite editar notas históricas.")
        super().save(*args, **kwargs)


class TransicionEstadoLog(models.Model):
    """Auditoría inmutable de transiciones del Patrón State."""

    ficha = models.ForeignKey(FichaAtencion, on_delete=models.PROTECT, related_name="transiciones")
    estado_origen = models.CharField(max_length=32)
    estado_destino = models.CharField(max_length=32)
    actor_nombre = models.CharField(max_length=120)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Transición de Estado (WORM)"
        verbose_name_plural = "Historial Patrón State (WORM)"
        ordering = ["creado_en", "id"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Transición WORM inmutable: no se permite alterar historial de estados.")
        super().save(*args, **kwargs)


class EncuestaSatisfaccion(models.Model):
    ficha = models.OneToOneField(FichaAtencion, on_delete=models.CASCADE, related_name="encuesta")
    estrellas = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    claridad = models.CharField(max_length=40)
    recomendaria = models.CharField(max_length=40)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Encuesta de Satisfacción"
        verbose_name_plural = "Encuestas de Satisfacción"


class EventoSeguridadOWASP(models.Model):
    """Bitácora OWASP A09 persistida en PostgreSQL."""

    NIVELES = [("INFO", "INFO"), ("WARN", "WARN"), ("CRITICAL", "CRITICAL")]

    nivel = models.CharField(max_length=16, choices=NIVELES, default="INFO")
    evento = models.CharField(max_length=60, db_index=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    actor_nombre = models.CharField(max_length=100, blank=True, default="")
    ruta = models.CharField(max_length=160, blank=True, default="")
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    detalle = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento de Seguridad OWASP (A09)"
        verbose_name_plural = "Bitácora de Seguridad OWASP (A09)"
        ordering = ["-creado_en", "-id"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Registro A09 WORM inmutable.")
        super().save(*args, **kwargs)
