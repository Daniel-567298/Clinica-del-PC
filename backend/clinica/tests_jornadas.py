from datetime import date, time, timedelta
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from clinica.models import EventoClinica, Sede, FichaAtencion, ParticipacionJornada


class JornadasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_clinica', verbosity=0)

    def setUp(self):
        self.client = APIClient()
        self.doc = User.objects.get(username='pablo.pesce')
        self.client.force_authenticate(self.doc)
        self.event = EventoClinica.objects.create(sede=Sede.objects.first(), nombre='Evento tres días',
            fecha_inicio=date(2027,4,10), fecha_fin=date(2027,4,12), lugar='Mesón', estado='En curso')
        self.days = list(self.event.jornadas.all())
        self.header = {'HTTP_X_CLINICA_EVENTO':str(self.event.id)}

    def post(self, path, data=None):
        return self.client.post('/api/v1/'+path, data or {}, format='json', **self.header)

    def move_pc(self, number='PC-026'):
        f = FichaAtencion.objects.get(numero_ticket=number)
        f.evento = self.event
        f.jornada_recepcion = self.days[0]
        f.save()
        return f

    def test_three_days_default_close_and_order(self):
        self.assertEqual(len(self.days),3)
        self.assertTrue(all(j.cierre == time(18) for j in self.days))
        self.assertFalse(self.event.permite_continuidad)
        self.assertEqual(self.post(f'jornadas/{self.days[1].id}/estado/',{'estado':'Abierta'}).status_code,400)
        self.assertEqual(self.post(f'jornadas/{self.days[0].id}/estado/',{'estado':'Cerrada'}).status_code,200)
        self.assertEqual(self.post(f'jornadas/{self.days[2].id}/estado/',{'estado':'Abierta'}).status_code,400)
        self.assertEqual(self.post(f'jornadas/{self.days[1].id}/estado/',{'estado':'Abierta'}).status_code,200)

    def test_schedule_extension_requires_reason_and_teacher(self):
        url=f'/api/v1/jornadas/{self.days[0].id}/horario/'
        self.assertEqual(self.client.put(url,{'cierre':'19:00'},format='json').status_code,400)
        r=self.client.put(url,{'cierre':'19:00','motivo':'Extensión autorizada'},format='json')
        self.assertEqual(r.status_code,200)
        self.days[0].refresh_from_db();self.assertEqual(self.days[0].cierre,time(19))
        self.assertEqual(self.client.put(url,{'limite_recepcion':'20:00','motivo':'Ajuste'},format='json').status_code,400)
        self.client.force_authenticate(User.objects.get(username='diego.astudillo'))
        self.assertEqual(self.client.put(url,{'cierre':'20:00','motivo':'Ajuste'},format='json').status_code,403)

    def test_cannot_close_day_with_unaccounted_pc(self):
        self.move_pc()
        r=self.post(f'jornadas/{self.days[0].id}/estado/',{'estado':'Cerrada'})
        self.assertEqual(r.status_code,400)
        self.days[0].refresh_from_db();self.assertEqual(self.days[0].estado,'Abierta')

    def hold(self):
        return {'hasta':self.days[1].id,'lugar':'Armario cerrado','responsable':'Docente encargado',
                'motivo':'Continuar revisión básica','titular_autoriza':True}

    def test_continuity_requires_event_permission_owner_consent_and_teacher(self):
        f=self.move_pc();url=f'fichas/{f.numero_ticket}/resguardo-diario/'
        self.assertEqual(self.post(url,self.hold()).status_code,400)
        self.event.permite_continuidad=True;self.event.save()
        self.assertEqual(self.post(url,{**self.hold(),'titular_autoriza':False}).status_code,400)
        self.assertEqual(self.post(url,{**self.hold(),'hasta':self.days[0].id}).status_code,400)
        self.client.force_authenticate(User.objects.get(username='diego.astudillo'))
        self.assertEqual(self.post(url,self.hold()).status_code,403)
        self.assertFalse(f.resguardos.exists())

    def test_hold_and_return_preserve_ticket_and_checklist(self):
        f=self.move_pc();before=list(f.checklist_items.values_list('id','estado'))
        self.event.permite_continuidad=True;self.event.save()
        url=f'fichas/{f.numero_ticket}/'
        self.assertEqual(self.post(url+'resguardo-diario/',self.hold()).status_code,201)
        self.assertEqual(self.post(url+'retorno-resguardo/').status_code,400)
        self.assertEqual(self.post(url+'derivar/',{'motivo':'Revisar','destino':'Especialista'}).status_code,400)
        self.assertEqual(self.post(f'jornadas/{self.days[0].id}/estado/',{'estado':'Cerrada'}).status_code,200)
        self.assertEqual(self.post(f'jornadas/{self.days[1].id}/estado/',{'estado':'Abierta'}).status_code,200)
        self.assertEqual(self.post(url+'retorno-resguardo/').status_code,200)
        f.refresh_from_db();self.assertEqual(f.numero_ticket,'PC-026')
        self.assertEqual(list(f.checklist_items.values_list('id','estado')),before)
        self.assertFalse(f.resguardos.filter(reanudado_en__isnull=True).exists())

    def test_cannot_disable_continuity_with_active_hold(self):
        f=self.move_pc();self.event.permite_continuidad=True;self.event.save()
        self.assertEqual(self.post(f'fichas/{f.numero_ticket}/resguardo-diario/',self.hold()).status_code,201)
        r=self.client.put(f'/api/v1/eventos/{self.event.id}/opciones/',{'permite_continuidad':False},format='json')
        self.assertEqual(r.status_code,400)

    def test_copy_annual_configuration_without_people_or_tickets(self):
        self.move_pc()
        ParticipacionJornada.objects.create(jornada=self.days[0],operador=self.doc)
        r=self.post(f'eventos/{self.event.id}/copiar/',{'nombre':'Edición siguiente','fecha_inicio':'2028-05-02'})
        self.assertEqual(r.status_code,201)
        event=EventoClinica.objects.get(pk=r.data['id'])
        self.assertEqual(event.estado,'Borrador');self.assertEqual(event.fecha_fin,date(2028,5,4))
        self.assertEqual(event.jornadas.count(),3);self.assertFalse(event.fichas.exists())
        self.assertFalse(ParticipacionJornada.objects.filter(jornada__evento=event).exists())

    def test_daily_participants_only_belong_to_same_sede(self):
        tech=User.objects.get(username='diego.astudillo')
        url=f'jornadas/{self.days[0].id}/participantes/'
        self.assertEqual(self.post(url,{'operador':tech.id}).status_code,200)
        self.assertEqual(self.post(url,{'operador':tech.id}).status_code,200)
        self.assertEqual(self.days[0].participantes.count(),1)
        tech.perfil.sedes.clear()
        self.assertEqual(self.post(url,{'operador':tech.id}).status_code,404)

    def test_daily_metrics_count_continuing_equipment_once(self):
        self.move_pc()
        r=self.client.get(f'/api/v1/eventos/{self.event.id}/metricas-diarias/')
        self.assertEqual(r.status_code,200);self.assertEqual(r.data['equipos_unicos'],1)
        self.assertEqual([d['equipos_recibidos'] for d in r.data['dias']],[1,0,0])

    def test_final_event_can_deliver_but_not_modify_workshop(self):
        self.move_pc('PC-027')
        self.event.estado='Finalizado';self.event.save()
        self.assertEqual(self.post('fichas/PC-027/aviso/',{'tipo':'whatsapp'}).status_code,200)
        self.assertEqual(self.post('fichas/PC-027/entrega/',{'tipo_receptor':'Titular','resultado':'Entregado conforme',
            'prueba_conjunta_resultado':'Conforme','receptor_confirma_prueba':True}).status_code,200)
        self.assertEqual(self.post('fichas/PC-027/derivar/',{'motivo':'Cambiar','destino':'Otro'}).status_code,400)

    def test_enrollment_window_is_enforced_server_side(self):
        self.event.inscripcion_desde=timezone.now()+timedelta(days=1);self.event.save()
        self.client.force_authenticate(None)
        r=self.post('public/preinscripcion/',{})
        self.assertEqual(r.status_code,400);self.assertIn('plazo',str(r.data))

    def test_referral_pauses_work_for_teacher_coordination(self):
        f=self.move_pc();self.client.force_authenticate(User.objects.get(username='diego.astudillo'))
        r=self.post('fichas/PC-026/derivar/',{'motivo':'Falla fuera de alcance','destino':'Técnico experimentado'})
        self.assertEqual(r.status_code,200)
        f.refresh_from_db();self.assertEqual(f.estado,'En espera');self.assertTrue(f.incidencia_activa)
        self.assertEqual(f.derivacion_destino,'Técnico experimentado');self.assertFalse(f.resultado_entrega)
