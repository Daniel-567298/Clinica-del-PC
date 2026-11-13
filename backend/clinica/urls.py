# -*- coding: utf-8 -*-
from django.urls import path

from clinica import views
from clinica import jornadas

urlpatterns = [
    path('eventos/<int:evento_id>/jornadas/', jornadas.JornadasView.as_view()),
    path('eventos/<int:evento_id>/copiar/', jornadas.CopiarEventoView.as_view()),
    path('eventos/<int:evento_id>/metricas-diarias/', jornadas.MetricasDiariasView.as_view()),
    path('eventos/<int:evento_id>/opciones/', jornadas.OpcionesEventoView.as_view()),
    path('jornadas/<int:jornada_id>/horario/', jornadas.ConfigJornadaView.as_view()),
    path('jornadas/<int:jornada_id>/estado/', jornadas.EstadoJornadaView.as_view()),
    path('jornadas/<int:jornada_id>/participantes/', jornadas.ParticipantesJornadaView.as_view()),
    path('fichas/<str:numero_ticket>/resguardo-diario/', jornadas.ResguardoView.as_view()),
    path('fichas/<str:numero_ticket>/retorno-resguardo/', jornadas.ReanudarResguardoView.as_view()),
    path('fichas/<str:numero_ticket>/derivar/', jornadas.DerivarEspecialistaView.as_view()),
    path("sedes/", views.SedesView.as_view(), name="sedes"),
    path("sedes/operadores/", views.OperadoresSedeView.as_view(), name="sede-operadores"),
    path("eventos/", views.EventosView.as_view(), name="eventos"),
    path("eventos/<int:evento_id>/estado/", views.EstadoEventoView.as_view(), name="evento-estado"),
    path("health/", views.HealthCheckView.as_view(), name="api-health"),
    # Autenticación y sesión OWASP A07
    path("auth/csrf/", views.AuthCSRFView.as_view(), name="auth-csrf"),
    path("auth/me/", views.AuthMeView.as_view(), name="auth-me"),
    path("auth/login/", views.AuthLoginView.as_view(), name="auth-login"),
    path("auth/logout/", views.AuthLogoutView.as_view(), name="auth-logout"),
    path("auth/unlock-demo/", views.AuthUnlockDemoView.as_view(), name="auth-unlock-demo"),
    # Flujo público QR (Paso 1)
    path("public/preinscripcion/", views.PublicPreinscriptionView.as_view(), name="public-qr"),
    path("public/ticket/<str:numero_ticket>/", views.PublicTicketLookupView.as_view(), name="public-ticket"),
    # Mesón & Triaje Multi-PC (Paso 2)
    path("triaje/", views.TriajeSearchView.as_view(), name="triaje-search"),
    path("dispositivos/<str:codigo_dispositivo>/nueva-ficha/", views.NuevoTicketDispositivoView.as_view(), name="new-ticket-dev"),
    # Fichas y flujo 9 pasos
    path("fichas/", views.FichaListView.as_view(), name="ficha-list"),
    path("fichas/<str:numero_ticket>/", views.FichaDetailView.as_view(), name="ficha-detail"),
    path("fichas/<str:numero_ticket>/recepcion/", views.RecepcionFichaView.as_view(), name="ficha-recepcion"),
    path("fichas/<str:numero_ticket>/checklist/", views.TallerChecklistView.as_view(), name="ficha-checklist"),
    path("fichas/<str:numero_ticket>/notas/", views.BitacoraNotaCreateView.as_view(), name="ficha-notas"),
    path("fichas/<str:numero_ticket>/verificar-final/", views.VerificarFinalView.as_view(), name="ficha-verificar"),
    path("fichas/<str:numero_ticket>/aviso/", views.AvisoRetiroView.as_view(), name="ficha-aviso"),
    path("fichas/<str:numero_ticket>/entrega/", views.EntregaSalidaView.as_view(), name="ficha-entrega"),
    path("fichas/<str:numero_ticket>/encuesta/", views.EncuestaSatisfaccionView.as_view(), name="ficha-encuesta"),
    path("fichas/<str:numero_ticket>/custodia/", views.CustodiaTrasladoView.as_view(), name="ficha-custodia"),
    path("custodia/anonimizar-vencidos/", views.CustodiaAnonimizarVencidosView.as_view(), name="custodia-anonimizar"),
    # Incidencias & Ley 21.459
    path("fichas/<str:numero_ticket>/incidencia/", views.ReportarIncidenciaView.as_view(), name="ficha-incidencia"),
    path("fichas/<str:numero_ticket>/hallazgo-ilicito/", views.HallazgoIlicitoLey21459View.as_view(), name="ficha-ilicito"),
    path("fichas/<str:numero_ticket>/resolver-incidencia/", views.ResolverIncidenciaDocenteView.as_view(), name="ficha-resolver"),
    # Administración Docente, Métricas & Auditoría
    path("admin/plantillas/", views.AdminPlantillasView.as_view(), name="admin-plantillas"),
    path("admin/nomina/", views.AdminNominaView.as_view(), name="admin-nomina"),
    path("admin/nomina/importar-csv/", views.AdminNominaImportCSVView.as_view(), name="admin-nomina-csv"),
    path("admin/nomina/revocar-masivo/", views.AdminNominaRevokeView.as_view(), name="admin-nomina-revocar"),
    path("metricas/", views.MetricasView.as_view(), name="metricas"),
    path("metricas/exportar-csv/", views.ExportarMetricasCSVView.as_view(), name="metricas-csv"),
    path("seguridad/auditoria/", views.SeguridadAuditoriaView.as_view(), name="seguridad-auditoria"),
]
