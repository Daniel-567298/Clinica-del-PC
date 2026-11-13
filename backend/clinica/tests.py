# -*- coding: utf-8 -*-
"""
Suite automatizada de pruebas Django/DRF (GoF, OWASP Top 10:2025, Leyes 21.719/21.459).
Diseñada para correr directamente sobre PostgreSQL mediante `python manage.py test`.
"""

from datetime import timedelta
from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from clinica.models import (
    BitacoraNota,
    EventoSeguridadOWASP,
    FichaAtencion,
    Propietario,
    Sede,
    EventoClinica,
    PerfilOperador,
    PlantillaTarea,
    ServicioCatalogo,
)
from clinica.patterns.state_machine import TicketStateMachine
from clinica.security.validators import sanitize_csv_cell, validar_rut_chileno


class ClinicaPostgreSQLSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_clinica", verbosity=0)

    def setUp(self):
        self.client = APIClient()

    def make_event(self, sede=None, estado="En curso", nombre="Nueva jornada"):
        return EventoClinica.objects.create(sede=sede or Sede.objects.first(), nombre=nombre,
            fecha_inicio=date(2027, 4, 10), fecha_fin=date(2027, 4, 10), lugar="Mesón demo", estado=estado)

    def test_existing_fichas_belong_to_initial_event(self):
        self.assertEqual(FichaAtencion.objects.filter(evento__isnull=True).count(), 0)
        self.assertEqual(FichaAtencion.objects.values('evento_id').distinct().count(), 1)
        self.assertTrue(User.objects.get(username='recepcion').perfil.sedes.exists())

    def test_event_creation_validates_dates_and_roles(self):
        sede = Sede.objects.first()
        data = {"sede": sede.id, "nombre": "Clínica 2027", "fecha_inicio": "2027-04-10", "fecha_fin": "2027-04-09", "lugar": "Mesón"}
        self.client.force_authenticate(user=User.objects.get(username='pablo.pesce'))
        self.assertEqual(self.client.post('/api/v1/eventos/', data, format='json').status_code, 400)
        data['fecha_fin'] = '2027-04-10'
        response = self.client.post('/api/v1/eventos/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['estado'], 'Borrador')
        self.client.force_authenticate(user=User.objects.get(username='diego.astudillo'))
        self.assertEqual(self.client.post('/api/v1/eventos/', data, format='json').status_code, 403)

    def test_new_event_has_independent_metrics_and_triaje(self):
        event = self.make_event()
        self.client.force_authenticate(user=User.objects.get(username='pablo.pesce'))
        headers = {'HTTP_X_CLINICA_EVENTO': str(event.id)}
        self.assertEqual(self.client.get('/api/v1/fichas/', **headers).data, [])
        self.assertEqual(self.client.get('/api/v1/metricas/', **headers).data['total'], 0)
        self.assertEqual(self.client.get('/api/v1/triaje/', **headers).data['propietarios'], [])
        original = FichaAtencion.objects.get(numero_ticket='PC-024').evento
        response = self.client.get('/api/v1/metricas/', HTTP_X_CLINICA_EVENTO=str(original.id))
        self.assertEqual(response.data['total'], 5)
        self.assertEqual(self.client.get('/api/v1/fichas/PC-024/', **headers).status_code, 404)

    def test_sede_permissions_apply_to_details_writes_metrics_and_export(self):
        sede = Sede.objects.create(nombre='Sede de prueba', codigo='sede-prueba')
        event = self.make_event(sede=sede)
        ficha = FichaAtencion.objects.get(numero_ticket='PC-026')
        ficha.evento = event; ficha.save(update_fields=['evento'])
        self.client.force_authenticate(user=User.objects.get(username='recepcion'))
        self.assertEqual(self.client.get('/api/v1/fichas/PC-026/').status_code, 404)
        self.assertEqual(self.client.post('/api/v1/fichas/PC-026/aviso/', {'tipo':'llamada'}, format='json').status_code, 404)
        teacher = User.objects.get(username='pablo.pesce')
        teacher.is_superuser = False; teacher.save(update_fields=['is_superuser'])
        self.client.force_authenticate(user=teacher)
        self.assertEqual(self.client.get('/api/v1/metricas/').data['total'], 4)
        self.assertNotIn('PC-026', self.client.get('/api/v1/metricas/exportar-csv/').content.decode('utf8'))
        self.assertNotIn(event.id, [e['id'] for e in self.client.get('/api/v1/eventos/').data])

    def test_closed_event_is_read_only_and_requires_reason_to_reopen(self):
        event = self.make_event(estado='Finalizado')
        ficha = FichaAtencion.objects.get(numero_ticket='PC-026'); ficha.evento=event;ficha.save(update_fields=['evento'])
        self.client.force_authenticate(user=User.objects.get(username='pablo.pesce'))
        headers={'HTTP_X_CLINICA_EVENTO':str(event.id)}
        self.assertEqual(self.client.get('/api/v1/fichas/PC-026/', **headers).status_code, 200)
        self.assertEqual(self.client.post('/api/v1/fichas/PC-026/notas/', {'contenido':'Cambio'}, format='json', **headers).status_code, 400)
        url=f'/api/v1/eventos/{event.id}/estado/'
        self.assertEqual(self.client.post(url, {'estado':'En curso'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {'estado':'En curso','motivo':'Coordinar retiro pendiente'}, format='json').status_code, 200)

    def test_event_cannot_close_with_unresolved_fichas(self):
        event=FichaAtencion.objects.first().evento
        self.client.force_authenticate(user=User.objects.get(username='pablo.pesce'))
        self.assertEqual(self.client.post(f'/api/v1/eventos/{event.id}/estado/', {'estado':'Finalizado'}, format='json').status_code, 409)

    def test_public_registration_is_bound_to_selected_open_event(self):
        event=self.make_event(estado='Inscripciones abiertas')
        owner=Propietario.objects.get(rut_normalizado='123456785')
        data={k:getattr(owner,k) for k in ['rut','nombre_completo','telefono','correo','comuna_direccion']}
        data.update({'evento_id':event.id,'marca_modelo':'Equipo nuevo','tipo':'Notebook','problema_declarado':'Falla','servicios':['Mantención Lógica']})
        response=self.client.post('/api/v1/public/preinscripcion/',data,format='json')
        self.assertEqual(response.status_code,201)
        ficha=FichaAtencion.objects.get(numero_ticket=response.data['numero_ticket'])
        self.assertEqual(ficha.evento_id,event.id)
        event.estado='Finalizado';event.save()
        self.assertEqual(self.client.post('/api/v1/public/preinscripcion/',data,format='json').status_code,400)

    def test_public_catalog_hides_closed_and_draft_events(self):
        draft=self.make_event(estado='Borrador',nombre='Borrador')
        closed=self.make_event(estado='Finalizado',nombre='Pasado')
        rows=self.client.get('/api/v1/eventos/').data
        self.assertNotIn(draft.id,[r['id'] for r in rows]);self.assertNotIn(closed.id,[r['id'] for r in rows])
        self.assertTrue(all(r['total_fichas'] is None for r in rows))

    def test_teacher_can_create_sede_and_link_only_authorized_operators(self):
        teacher=User.objects.get(username='pablo.pesce');self.client.force_authenticate(user=teacher)
        response=self.client.post('/api/v1/sedes/',{'nombre':'Sede nueva','codigo':'sede-nueva'},format='json')
        self.assertEqual(response.status_code,201)
        new_id=response.data['id']
        self.assertTrue(teacher.perfil.sedes.filter(pk=new_id).exists())
        technician=User.objects.get(username='diego.astudillo')
        response=self.client.post('/api/v1/sedes/operadores/',{'sede':new_id,'usuario':technician.id},format='json')
        self.assertEqual(response.status_code,200)
        self.assertTrue(technician.perfil.sedes.filter(pk=new_id).exists())

    def test_site_template_change_does_not_affect_another_site(self):
        from clinica.patterns.plantillas import plantillas_para_sede
        sede=Sede.objects.first();other=Sede.objects.create(nombre='Otra sede',codigo='otra')
        event=self.make_event(sede=sede)
        self.client.force_authenticate(user=User.objects.get(username='pablo.pesce'))
        servicio=ServicioCatalogo.objects.get(nombre='Mantención Física')
        before=list(plantillas_para_sede(servicio,other)[0].values_list('descripcion',flat=True))
        response=self.client.put('/api/v1/admin/plantillas/',{'servicio':servicio.nombre,'tareas':['Tarea exclusiva de sede']},format='json',HTTP_X_CLINICA_EVENTO=str(event.id))
        self.assertEqual(response.status_code,200)
        self.assertEqual(list(plantillas_para_sede(servicio,sede)[0].values_list('descripcion',flat=True)),['Tarea exclusiva de sede'])
        self.assertEqual(list(plantillas_para_sede(servicio,other)[0].values_list('descripcion',flat=True)),before)

    def test_old_custody_anonymization_preserves_owner_with_later_attention(self):
        ficha=FichaAtencion.objects.get(numero_ticket='PC-028')
        ficha.fecha_limite_60_dias=(timezone.localdate()-timedelta(days=2));ficha.save()
        event=self.make_event()
        from clinica.patterns.factory import FichaAndChecklistFactory
        FichaAndChecklistFactory.create_qr_preinscription(owner=ficha.propietario,brand_model='Otro PC',device_type='Notebook',problem='Revisión',service_names=['Mantención Física'],evento=event)
        self.client.force_authenticate(user=User.objects.get(username='pablo.pesce'))
        response=self.client.post('/api/v1/custodia/anonimizar-vencidos/',HTTP_X_CLINICA_EVENTO=str(ficha.evento_id))
        self.assertEqual(response.status_code,200)
        ficha.propietario.refresh_from_db();self.assertFalse(ficha.propietario.anonimizado)

    def test_audit_logs_are_scoped_by_site_not_only_by_actor(self):
        sede=Sede.objects.first();other=Sede.objects.create(nombre='Sede separada',codigo='separada')
        teacher=User.objects.get(username='pablo.pesce');teacher.is_superuser=False;teacher.save(update_fields=['is_superuser'])
        EventoSeguridadOWASP.objects.create(sede=sede,usuario=teacher,evento='REVISION',detalle='Solo mi sede')
        EventoSeguridadOWASP.objects.create(sede=other,usuario=teacher,evento='REVISION',detalle='Datos de otra sede')
        self.client.force_authenticate(user=teacher)
        response=self.client.get('/api/v1/seguridad/auditoria/')
        self.assertEqual(response.status_code,200)
        self.assertIn('Solo mi sede',str(response.data));self.assertNotIn('Datos de otra sede',str(response.data))

    def test_public_registration_cannot_change_existing_identity(self):
        owner = Propietario.objects.get(rut_normalizado="123456785")
        before = {k: getattr(owner, k) for k in ("nombre_completo", "telefono", "correo", "comuna_direccion")}
        count = FichaAtencion.objects.count()
        payload = {**before, "rut": owner.rut, "marca_modelo": "PC de prueba", "tipo": "Notebook",
                   "problema_declarado": "Falla", "servicios": ["Mantención Lógica"]}
        for field in before:
            with self.subTest(field=field):
                data = {**payload, field: "otro@example.com" if field == "correo" else "Dato alterado"}
                res = self.client.post("/api/v1/public/preinscripcion/", data, format="json")
                self.assertEqual(res.status_code, 400)
                owner.refresh_from_db()
                self.assertEqual({k: getattr(owner, k) for k in before}, before)
                self.assertEqual(FichaAtencion.objects.count(), count)
                self.assertNotIn(before["correo"], str(res.data))

    def test_public_registration_creates_new_owner(self):
        response = self.client.post("/api/v1/public/preinscripcion/", {
            "nombre_completo": "Titular nuevo demo", "rut": "14.321.987-9", "telefono": "+56 9 0000 0000",
            "correo": "nuevo@example.com", "comuna_direccion": "Comuna demo", "marca_modelo": "PC demo",
            "tipo": "Notebook", "problema_declarado": "Falla demo", "servicios": ["Mantención Lógica"],
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Propietario.objects.filter(rut_normalizado="143219879", nombre_completo="Titular nuevo demo").exists())

    def test_contact_notes_visible_only_to_reception_and_teacher(self):
        self.client.force_authenticate(user=User.objects.get(username="recepcion"))
        res = self.client.post("/api/v1/fichas/PC-026/aviso/", {"tipo": "whatsapp"}, format="json")
        self.assertEqual(res.status_code, 200)
        note = BitacoraNota.objects.filter(ficha__numero_ticket="PC-026").first()
        self.assertTrue(note.privada_meson)
        phone = note.ficha.propietario.telefono
        for username, visible in (("recepcion", True), ("pablo.pesce", True), ("diego.astudillo", False)):
            with self.subTest(username=username):
                self.client.force_authenticate(user=User.objects.get(username=username))
                response = self.client.get("/api/v1/fichas/PC-026/")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(phone in str(response.data), visible)
                self.assertEqual(note.id in [n["id"] for n in response.data["notas"]], visible)

    def test_legacy_technical_notes_redact_owner_contacts(self):
        ficha = FichaAtencion.objects.get(numero_ticket="PC-026")
        owner = ficha.propietario
        text = f"Revisado. Contacto {owner.telefono}; {owner.correo}; {owner.rut}; {owner.comuna_direccion}."
        note = BitacoraNota.objects.create(ficha=ficha, autor_nombre="Técnico", contenido=text)
        self.client.force_authenticate(user=User.objects.get(username="diego.astudillo"))
        response = self.client.get("/api/v1/fichas/PC-026/")
        row = next(n for n in response.data["notas"] if n["id"] == note.id)
        self.assertIn("Revisado.", row["contenido"])
        for value in (owner.telefono, owner.correo, owner.rut, owner.comuna_direccion):
            self.assertNotIn(value, str(response.data))
        note.refresh_from_db()
        self.assertEqual(note.contenido, text)

    def test_delivery_requires_joint_test_without_closing_order_on_failure(self):
        self.client.force_authenticate(user=User.objects.get(username="recepcion"))
        before = BitacoraNota.objects.count()
        res = self.client.post("/api/v1/fichas/PC-027/entrega/", {"tipo_receptor": "Titular", "resultado": "Entregado conforme"}, format="json")
        self.assertEqual(res.status_code, 400)
        ficha = FichaAtencion.objects.get(numero_ticket="PC-027")
        self.assertEqual(ficha.estado, "Listo para entrega")
        self.assertIsNone(ficha.entrega_registrada_en)
        self.assertEqual(BitacoraNota.objects.count(), before)

    def test_delivery_stores_joint_test_actor_and_time_and_rejects_overwrite(self):
        user = User.objects.get(username="recepcion")
        self.client.force_authenticate(user=user)
        data = {"tipo_receptor": "Titular", "resultado": "Entregado conforme",
                "prueba_conjunta_resultado": "Conforme", "prueba_conjunta_observaciones": "Encendido y teclado revisados.",
                "receptor_confirma_prueba": True}
        res = self.client.post("/api/v1/fichas/PC-027/entrega/", data, format="json")
        self.assertEqual(res.status_code, 200)
        ficha = FichaAtencion.objects.get(numero_ticket="PC-027")
        self.assertEqual(ficha.estado, "Entregado conforme")
        self.assertEqual(ficha.prueba_conjunta_resultado, "Conforme")
        self.assertEqual(ficha.prueba_conjunta_observaciones, data["prueba_conjunta_observaciones"])
        self.assertTrue(ficha.receptor_confirma_prueba)
        self.assertEqual(ficha.entrega_registrada_por, user)
        self.assertIsNotNone(ficha.entrega_registrada_en)
        self.assertFalse(hasattr(ficha, "encuesta"))
        res = self.client.post("/api/v1/fichas/PC-027/entrega/", {**data, "prueba_conjunta_observaciones": "Reescritura"}, format="json")
        self.assertEqual(res.status_code, 400)
        ficha.refresh_from_db()
        self.assertEqual(ficha.prueba_conjunta_observaciones, data["prueba_conjunta_observaciones"])

    def test_delivery_rejects_false_confirmation_and_nonconforming_delivery(self):
        self.client.force_authenticate(user=User.objects.get(username="recepcion"))
        base = {"tipo_receptor": "Titular", "resultado": "Entregado conforme", "prueba_conjunta_resultado": "Conforme", "receptor_confirma_prueba": True}
        for changes in ({"receptor_confirma_prueba": False}, {"prueba_conjunta_resultado": "No conforme"}, {"resultado": "En proceso"}):
            with self.subTest(changes=changes):
                res = self.client.post("/api/v1/fichas/PC-027/entrega/", {**base, **changes}, format="json")
                self.assertEqual(res.status_code, 400)

    def test_return_without_test_requires_reason(self):
        self.client.force_authenticate(user=User.objects.get(username="recepcion"))
        data = {"tipo_receptor": "Titular", "resultado": "Devuelto sin reparación", "prueba_conjunta_resultado": "No se pudo probar", "receptor_confirma_prueba": True}
        res = self.client.post("/api/v1/fichas/PC-027/entrega/", data, format="json")
        self.assertEqual(res.status_code, 400)
        res = self.client.post("/api/v1/fichas/PC-027/entrega/", {**data, "prueba_conjunta_observaciones": "El equipo no enciende; se revisó con el titular."}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_third_party_delivery_still_requires_authorization(self):
        self.client.force_authenticate(user=User.objects.get(username="recepcion"))
        data = {"tipo_receptor": "Tercero", "resultado": "Entregado conforme", "prueba_conjunta_resultado": "Conforme", "receptor_confirma_prueba": True,
                "tercero_nombre": "Persona demo", "tercero_rut": "15.890.123-4", "tercero_autorizado_telefono": False}
        self.assertEqual(self.client.post("/api/v1/fichas/PC-027/entrega/", data, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/v1/fichas/PC-027/entrega/", {**data, "tercero_autorizado_telefono": True}, format="json").status_code, 200)

    def test_survey_validates_invalid_values_as_400(self):
        self.client.force_authenticate(user=User.objects.get(username="recepcion"))
        base = {"claridad": "Muy clara", "recomendaria": "Sí, totalmente"}
        for stars in ("texto", None, 0, 6, -1, 2.5, True, {}, []):
            with self.subTest(stars=stars):
                response = self.client.post("/api/v1/fichas/PC-024/encuesta/", {**base, "estrellas": stars}, format="json")
                self.assertEqual(response.status_code, 400)
        for stars in (1, 5):
            response = self.client.post("/api/v1/fichas/PC-024/encuesta/", {**base, "estrellas": stars}, format="json")
            self.assertEqual(response.status_code, 201)

    def test_public_survey_still_requires_matching_owner(self):
        data = {"estrellas": 5, "claridad": "Clara", "recomendaria": "No"}
        self.assertEqual(self.client.post("/api/v1/fichas/PC-024/encuesta/", data, format="json").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/fichas/PC-024/encuesta/", {**data, "rut": "12.345.678-5"}, format="json").status_code, 201)

    def test_rut_modulo11_validation(self):
        self.assertTrue(validar_rut_chileno("12.345.678-5"))
        self.assertTrue(validar_rut_chileno("15.890.123-4"))
        self.assertFalse(validar_rut_chileno("14.321.987-6"))
        self.assertTrue(validar_rut_chileno("14.321.987-9"))

    def test_public_qr_preinscription_and_idor_protection(self):
        res = self.client.post(
            "/api/v1/public/preinscripcion/",
            {
                "nombre_completo": "Camila Rojas Méndez",
                "rut": "12.345.678-5",
                "telefono": "+56 9 8765 4321",
                "correo": "camila.rojas@inacapmail.cl",
                "comuna_direccion": "San Pedro de la Paz (Huertos Familiares)",
                "marca_modelo": "Acer Aspire 5",
                "tipo": "Notebook",
                "problema_declarado": "Pantalla parpadea",
                "servicios": ["Mantención Lógica"],
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        ticket = res.data["numero_ticket"]
        self.assertEqual(Propietario.objects.get(rut_normalizado="123456785").dispositivos.count(), 3)

        # OWASP A01 IDOR: RUT distinto bloqueado
        bad = self.client.get(f"/api/v1/public/ticket/{ticket}/?rut=15.890.123-4")
        self.assertEqual(bad.status_code, 403)
        ok = self.client.get(f"/api/v1/public/ticket/{ticket}/?rut=12.345.678-5")
        self.assertEqual(ok.status_code, 200)

    def test_ley_21719_pii_masking_in_api_for_tecnico_and_rbac_403(self):
        self.client.force_authenticate(user=User.objects.get(username="diego.astudillo"))

        res_ficha = self.client.get("/api/v1/fichas/PC-024/")
        self.assertEqual(res_ficha.status_code, 200)
        prop = res_ficha.data["propietario"]
        self.assertEqual(prop["rut"], "**.***.***-5")
        self.assertNotIn("12.345.678-5", str(res_ficha.data))
        self.assertNotIn("Huertos Familiares", str(res_ficha.data))
        self.assertEqual(len(res_ficha.data["checklist_items"]), 10)

        # OWASP A01 RBAC 403 al intentar acceder a módulo Docente/Admin
        forbidden = self.client.get("/api/v1/admin/nomina/")
        self.assertEqual(forbidden.status_code, 403)
        self.assertTrue(EventoSeguridadOWASP.objects.filter(evento="RBAC_403_FORBIDDEN").exists())

    def test_state_pattern_blocks_ca08_and_ley_21459(self):
        f24 = FichaAtencion.objects.get(numero_ticket="PC-024")
        ok, reason = TicketStateMachine.can_transition(f24, "Listo para entrega")
        self.assertFalse(ok)
        self.assertIn("Transición inválida", reason)

        # Hallazgo ilícito Ley 21.459 sobre PC-026 (que tenía checklist al 100%)
        self.client.force_authenticate(user=User.objects.get(username="diego.astudillo"))
        hold = self.client.post("/api/v1/fichas/PC-026/hallazgo-ilicito/")
        self.assertEqual(hold.status_code, 200)
        self.assertTrue(EventoSeguridadOWASP.objects.filter(evento="LEGAL_21459_HOLD").exists())

        verif = self.client.post(
            "/api/v1/fichas/PC-026/verificar-final/",
            {"condicion_final": "OK", "metricas_post_estres": "45C", "comparacion_final": "OK"},
            format="json",
        )
        self.assertEqual(verif.status_code, 400)

    def test_owasp_a07_lockout_after_5_failed_logins(self):
        for _ in range(4):
            r = self.client.post("/api/v1/auth/login/", {"username": "recepcion", "password": "wrong"}, format="json")
            self.assertEqual(r.status_code, 401)
        r5 = self.client.post("/api/v1/auth/login/", {"username": "recepcion", "password": "wrong"}, format="json")
        self.assertEqual(r5.status_code, 429)
        self.assertTrue(EventoSeguridadOWASP.objects.filter(evento="ACCOUNT_LOCKED").exists())

    def test_owasp_a05_csv_injection_and_worm_immutability(self):
        self.assertEqual(sanitize_csv_cell("=cmd|'/C calc'!A0"), "'=cmd|'/C calc'!A0")
        self.client.force_authenticate(user=User.objects.get(username="pablo.pesce"))
        res = self.client.post(
            "/api/v1/admin/nomina/importar-csv/",
            {"csv_text": "20.456.789-1,=SUM(1+1),TI3043-01"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(EventoSeguridadOWASP.objects.filter(evento="CSV_INJECTION_SANITIZED").exists())

        nota = BitacoraNota.objects.first()
        nota.contenido = "Alteración fraudulenta"
        with self.assertRaises(ValidationError):
            nota.save()

    def test_ley_21719_60_day_custody_anonymization(self):
        f28 = FichaAtencion.objects.get(numero_ticket="PC-028")
        f28.fecha_limite_60_dias = (timezone.now() - timedelta(days=2)).date()
        f28.save()
        self.client.force_authenticate(user=User.objects.get(username="pablo.pesce"))
        res = self.client.post("/api/v1/custodia/anonimizar-vencidos/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["anonimizados"], 1)
        f28.refresh_from_db()
        self.assertTrue(f28.propietario.anonimizado)
        self.assertTrue(f28.propietario.rut.startswith("ANON-"))
