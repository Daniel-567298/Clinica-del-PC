# -*- coding: utf-8 -*-
"""
Suite automatizada de pruebas Django/DRF (GoF, OWASP Top 10:2025, Leyes 21.719/21.459).
Diseñada para correr directamente sobre PostgreSQL mediante `python manage.py test`.
"""

from datetime import timedelta

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
)
from clinica.patterns.state_machine import TicketStateMachine
from clinica.security.validators import sanitize_csv_cell, validar_rut_chileno


class ClinicaPostgreSQLSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_clinica", verbosity=0)

    def setUp(self):
        self.client = APIClient()

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
                "comuna_direccion": "San Pedro de la Paz",
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
