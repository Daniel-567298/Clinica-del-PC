# -*- coding: utf-8 -*-
"""
Comando de poblamiento inicial directamente sobre PostgreSQL mediante Django ORM.
Cero archivos .json utilizados (cumple política estricta de base de datos relacional).
"""

import hashlib
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from clinica.models import (
    BitacoraNota,
    ChecklistItemEjecucion,
    Dispositivo,
    EventoSeguridadOWASP,
    FichaAtencion,
    PerfilOperador,
    PlantillaTarea,
    Propietario,
    ServicioCatalogo,
    TransicionEstadoLog,
)
from clinica.patterns.factory import FichaAndChecklistFactory
from clinica.security.permissions import ROLE_DOCENTE_PO, ROLE_RECEPCIONISTA, ROLE_TECNICO
from clinica.security.validators import compute_consent_sha256


class Command(BaseCommand):
    help = "Inicializa servicios, usuarios RBAC y fichas demo en PostgreSQL (sin archivos JSON)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Poblando catálogo de servicios oficiales y plantillas...")
        catalogo = {
            "Mantención Física": (
                "mantencion-fisica",
                [
                    "Desarmado y apertura con pulsera antiestática",
                    "Limpieza y remoción de polvo en ventilador y disipador térmico",
                    "Retiro de pasta térmica degradada y aplicación de pasta nueva de alta conductividad",
                    "Limpieza de contactos de memoria RAM y puertos con alcohol isopropílico",
                    "Ensamblado de chasis y comprobación de encendido post-servicio",
                ],
            ),
            "Mantención Lógica": (
                "mantencion-logica",
                [
                    "Escaneo integral y remoción de malware, adware y troyanos",
                    "Limpieza profunda de archivos temporales del sistema y caché de navegadores",
                    "Desactivación de aplicaciones y servicios innecesarios en el arranque",
                    "Comprobación de integridad de archivos de sistema (sfc /scannow)",
                    "Verificación de suite ofimática y conectividad a red WiFi institucional",
                ],
            ),
            "Formateo / Instalación de SO": (
                "formateo-so",
                [
                    "Verificación de consentimiento y respaldo de datos personales del titular",
                    "Particionado y formateo de unidad de almacenamiento (SSD/HDD)",
                    "Instalación limpia de Sistema Operativo oficial (Windows 11 / Linux)",
                    "Descarga e instalación de drivers oficiales del fabricante",
                    "Instalación de paquetes básicos (Navegador, Antivirus, Suite Ofimática)",
                ],
            ),
        }

        servicios_map = {}
        for nombre, (slug, tareas) in catalogo.items():
            srv, _ = ServicioCatalogo.objects.get_or_create(codigo=slug, defaults={"nombre": nombre, "version_actual": 1})
            servicios_map[nombre] = srv
            if not srv.plantillas.exists():
                for idx, desc in enumerate(tareas, start=1):
                    PlantillaTarea.objects.create(servicio=srv, version=1, orden=idx, descripcion=desc)

        self.stdout.write("Creando operadores RBAC (PBKDF2/SHA256)...")
        operadores = [
            ("recepcion", "recepcion@inacap.cl", "Recepción", "Mesón", "ClinicaPC!26", ROLE_RECEPCIONISTA, "19.111.222-9", "TI3043-01", False),
            ("daniel.meliman", "daniel.meliman@inacapmail.cl", "Daniel", "Melimán", "ClinicaPC!26", ROLE_RECEPCIONISTA, "20.111.222-2", "TI3043-01", True),
            ("diego.astudillo", "diego.astudillo@inacapmail.cl", "Diego", "Astudillo", "TallerPC!26", ROLE_TECNICO, "20.456.789-1", "TI3043-01", False),
            ("pablo.pesce", "pablo.pesce@inacap.cl", "Pablo E.", "Pesce Sánchez", "DocentePO!26", ROLE_DOCENTE_PO, "14.321.987-9", "TI3043-01", True),
        ]
        users = {}
        for uname, email, fn, ln, raw_pwd, rol, rut, sec, is_staff in operadores:
            user, created = User.objects.get_or_create(
                username=uname,
                defaults={"email": email, "first_name": fn, "last_name": ln, "is_staff": is_staff, "is_superuser": rol == ROLE_DOCENTE_PO},
            )
            if created:
                user.set_password(raw_pwd)
                user.save()
            tok_hash = "SHA256:" + hashlib.sha256(f"{uname}|TI3043_2026".encode()).hexdigest()[:16]
            PerfilOperador.objects.get_or_create(
                user=user,
                defaults={"rol": rol, "rut": rut, "seccion": sec, "token_temporal_hash": tok_hash, "habilitado_jornada": True},
            )
            users[uname] = user

        if FichaAtencion.objects.exists():
            self.stdout.write(self.style.WARNING("La base PostgreSQL ya contiene fichas; seed idempotente omitido."))
            return

        self.stdout.write("Insertando propietarios, dispositivos multi-PC y fichas iniciales en PostgreSQL...")
        o_camila = Propietario.objects.create(rut="12.345.678-5", nombre_completo="Camila Rojas Méndez", telefono="+56 9 8765 4321", correo="camila.rojas@inacapmail.cl", comuna_direccion="San Pedro de la Paz (Huertos Familiares)")
        o_carlos = Propietario.objects.create(rut="15.890.123-4", nombre_completo="Carlos Soto Bravo", telefono="+56 9 9123 4567", correo="carlos.soto@gmail.com", comuna_direccion="Concepción (Centro)")
        o_maria = Propietario.objects.create(rut="18.432.765-1", nombre_completo="María Ignacia Parra", telefono="+56 9 7654 3210", correo="m.parra@gmail.com", comuna_direccion="Talcahuano (Las Higueras)")
        o_jorge = Propietario.objects.create(rut="9.876.543-3", nombre_completo="Jorge Venegas Lagos", telefono="+56 9 6543 2109", correo="jorge.venegas@gmail.com", comuna_direccion="Coronel (Lagunillas)")

        d1 = Dispositivo.objects.create(codigo_dispositivo="DEV-01", propietario=o_camila, tipo="Notebook", marca_modelo="Lenovo ThinkPad T14 Gen 2", numero_serie="PF2X9A01")
        d2 = Dispositivo.objects.create(codigo_dispositivo="DEV-02", propietario=o_camila, tipo="Desktop / Torre", marca_modelo="Torre Armada Personalizada (Gamer)", es_clon=True, codigo_interno_clon="CL-01")
        d3 = Dispositivo.objects.create(codigo_dispositivo="DEV-03", propietario=o_carlos, tipo="Notebook", marca_modelo="HP Pavilion 15-dw", numero_serie="5CD9321XY")
        d4 = Dispositivo.objects.create(codigo_dispositivo="DEV-04", propietario=o_maria, tipo="Notebook", marca_modelo="Dell Inspiron 14 3000", numero_serie="DL9876543")
        d5 = Dispositivo.objects.create(codigo_dispositivo="DEV-05", propietario=o_jorge, tipo="Notebook", marca_modelo="Asus ZenBook 14 UX425", numero_serie="SN-ASUS-9912")

        now = timezone.now()

        # PC-024: Camila Device 1 (Recibido, Multi-servicio 2 de 10 tareas completas)
        f24 = FichaAtencion.objects.create(
            numero_ticket="PC-024", propietario=o_camila, dispositivo=d1,
            problema_declarado="Se calienta en exceso y se apaga de golpe a los 10 minutos de uso intensivo.",
            estado="Recibido", prueba_inicial="Enciende normalmente",
            danos_preexistentes="Rayón superficial en tapa superior y polvo visible en rejilla.",
            accesorios="Cargador original Lenovo USB-C 65W",
            consentimiento_firmado=True, fecha_consentimiento=now,
            firma_hash_sha256=compute_consent_sha256("PC-024", o_camila.rut_normalizado, "Rayón superficial", "Cargador", now.isoformat()),
            tecnico_asignado=users["diego.astudillo"], tecnico_asignado_nombre="Diego Astudillo (AL-014)",
        )
        s24 = [servicios_map["Mantención Física"], servicios_map["Mantención Lógica"]]
        f24.servicios.set(s24)
        FichaAndChecklistFactory.materialize_checklist_items(f24, s24)
        for k in ("Mantención Física::0", "Mantención Física::1"):
            ChecklistItemEjecucion.objects.filter(ficha=f24, clave_unica=k).update(estado="Realizado", actualizado_por="Diego Astudillo")
        TransicionEstadoLog.objects.create(ficha=f24, estado_origen="Inicio", estado_destino="Preinscrito", actor_nombre="Propietario QR")
        TransicionEstadoLog.objects.create(ficha=f24, estado_origen="Preinscrito", estado_destino="Recibido", actor_nombre="Daniel Melimán (Recepción)")
        BitacoraNota.objects.create(ficha=f24, autor=users["daniel.meliman"], autor_nombre="Daniel Melimán (Recepción)", contenido="Se recepciona equipo con cargador. Prueba inicial en mesón exitosa.")
        BitacoraNota.objects.create(ficha=f24, autor=users["diego.astudillo"], autor_nombre="Diego Astudillo (Técnico)", contenido="Apertura de tapa inferior completada. Pasta térmica solidificada.")

        # PC-025: Camila Device 2 (Torre Clon CL-01 Preinscrita)
        f25 = FichaAtencion.objects.create(
            numero_ticket="PC-025", propietario=o_camila, dispositivo=d2,
            problema_declarado="No bootea disco principal; arroja pantalla azul WHEA_UNCORRECTABLE_ERROR.",
            estado="Preinscrito", prueba_inicial="Enciende pero no da video",
            danos_preexistentes="Falta un tornillo en panel lateral acrílico.",
            accesorios="Cable de poder trifásico",
        )
        s25 = [servicios_map["Mantención Física"], servicios_map["Formateo / Instalación de SO"]]
        f25.servicios.set(s25)
        FichaAndChecklistFactory.materialize_checklist_items(f25, s25)
        TransicionEstadoLog.objects.create(ficha=f25, estado_origen="Inicio", estado_destino="Preinscrito", actor_nombre="Propietario QR")
        BitacoraNota.objects.create(ficha=f25, autor_nombre="Propietario QR", contenido="Preinscripción registrada vía QR.")

        # PC-026: Carlos (En proceso, 100% checklist listo para verificación Paso 6)
        f26 = FichaAtencion.objects.create(
            numero_ticket="PC-026", propietario=o_carlos, dispositivo=d3,
            problema_declarado="Ventilador emite ruido de roce estridente y se traba la bisagra derecha.",
            estado="En proceso", prueba_inicial="No enciende",
            danos_preexistentes="Bisagra derecha con juego y fisura en plástico.",
            accesorios="Cargador original HP punta azul",
            consentimiento_firmado=True, fecha_consentimiento=now,
            firma_hash_sha256=compute_consent_sha256("PC-026", o_carlos.rut_normalizado, "Bisagra", "Cargador HP", now.isoformat()),
            tecnico_asignado_nombre="Daniel Melimán (AL-002)",
        )
        s26 = [servicios_map["Mantención Física"]]
        f26.servicios.set(s26)
        FichaAndChecklistFactory.materialize_checklist_items(f26, s26)
        f26.checklist_items.all().update(estado="Realizado", actualizado_por="Daniel Melimán")
        TransicionEstadoLog.objects.create(ficha=f26, estado_origen="Preinscrito", estado_destino="Recibido", actor_nombre="Recepción")
        TransicionEstadoLog.objects.create(ficha=f26, estado_origen="Recibido", estado_destino="En proceso", actor_nombre="Daniel Melimán")
        BitacoraNota.objects.create(ficha=f26, autor_nombre="Daniel Melimán", contenido="Limpieza de ventilador y ajuste de bisagra completado.")

        # PC-027: María (Listo para entrega - prueba entrega tercero Paso 8)
        f27 = FichaAtencion.objects.create(
            numero_ticket="PC-027", propietario=o_maria, dispositivo=d4,
            problema_declarado="Inundación de ventanas emergentes y lentitud al abrir navegadores.",
            estado="Listo para entrega", prueba_inicial="Enciende normalmente",
            danos_preexistentes="Sin daños visibles.", accesorios="Cargador Dell y funda",
            consentimiento_firmado=True, fecha_consentimiento=now,
            firma_hash_sha256=compute_consent_sha256("PC-027", o_maria.rut_normalizado, "Sin daños", "Cargador Dell", now.isoformat()),
            estado_llamada="Contacto confirmado", correo_enviado=True, verificado_salida=True,
            condicion_final="Enciende y opera perfectamente", comparacion_final="Mejora notoria sin pop-ups.",
        )
        s27 = [servicios_map["Mantención Lógica"]]
        f27.servicios.set(s27)
        FichaAndChecklistFactory.materialize_checklist_items(f27, s27)
        f27.checklist_items.all().update(estado="Realizado", actualizado_por="Diego Astudillo")
        TransicionEstadoLog.objects.create(ficha=f27, estado_origen="En proceso", estado_destino="Listo para entrega", actor_nombre="Diego Astudillo")
        BitacoraNota.objects.create(ficha=f27, autor_nombre="Diego Astudillo", contenido="Se eliminaron extensiones maliciosas y adware.")

        # PC-028: Jorge (En custodia 18:00 hrs Paso 9)
        f28 = FichaAtencion.objects.create(
            numero_ticket="PC-028", propietario=o_jorge, dispositivo=d5,
            problema_declarado="Mantenimiento preventivo semestral y cambio de pasta.",
            estado="En custodia", prueba_inicial="Enciende normalmente",
            danos_preexistentes="Desgaste normal de bordes.", accesorios="Cargador Asus Tipo C",
            consentimiento_firmado=True, fecha_consentimiento=now,
            firma_hash_sha256=compute_consent_sha256("PC-028", o_jorge.rut_normalizado, "Desgaste", "Cargador Asus", now.isoformat()),
            estado_llamada="Sin respuesta (2 intentos)", correo_enviado=True, verificado_salida=True,
            condicion_final="Enciende y opera al 100%", comparacion_final="Temperaturas estables a 45°C.",
            ubicacion_custodia="Sala de Profesores · Segundo Piso (INACAP)",
            responsable_custodia="Prof. Pablo E. Pesce Sánchez",
            acta_custodia_numero="ACTA-CUST-2026-028",
            fecha_custodia=now, fecha_limite_60_dias=(now + timedelta(days=60)).date(),
        )
        s28 = [servicios_map["Mantención Física"]]
        f28.servicios.set(s28)
        FichaAndChecklistFactory.materialize_checklist_items(f28, s28)
        f28.checklist_items.all().update(estado="Realizado", actualizado_por="Diego Astudillo")
        TransicionEstadoLog.objects.create(ficha=f28, estado_origen="Listo para entrega", estado_destino="En custodia", actor_nombre="Prof. Pablo Pesce")
        BitacoraNota.objects.create(ficha=f28, autor_nombre="Prof. Pablo Pesce", contenido="18:05 hrs: Traslado a custodia 2° piso (retención máx. 60 días Ley 21.719).")

        EventoSeguridadOWASP.objects.create(
            nivel="INFO",
            evento="POSTGRES_SEED_OK",
            actor_nombre="seed_clinica",
            detalle="Esquema PostgreSQL inicializado sin archivos JSON (5 fichas, 4 propietarios, 4 operadores RBAC).",
        )
        self.stdout.write(self.style.SUCCESS("Seed PostgreSQL completado exitosamente."))
