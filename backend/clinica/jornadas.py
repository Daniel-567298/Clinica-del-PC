"""Jornadas diarias, planificación sencilla y continuidad excepcional autorizada."""
from datetime import timedelta
from django.db import transaction
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from clinica.models import (EventoClinica, JornadaEvento, ParticipacionJornada, PerfilOperador,
                            FichaAtencion, ResguardoEntreJornadas, BitacoraNota)
from clinica.security.permissions import IsAnyInternalRole, IsDocentePO, IsTecnicoOrDocente
from clinica.security.eventos import eventos_permitidos, fichas_permitidas
from clinica.serializers import EventoSerializer, FichaDetailSerializer
from clinica.patterns.observer import ClinicEventBus
from clinica.patterns.state_machine import TicketStateMachine


def event_for(request, event_id):
    event = get_object_or_404(eventos_permitidos(request.user), pk=event_id)
    if request.method not in ('GET','HEAD','OPTIONS') and event.estado == 'Finalizado':
        raise ValidationError('El evento está finalizado. La entrega posterior se gestiona en Entrega y Encuesta.')
    return event


def audit(request, event, message):
    ClinicEventBus.get_instance().publish('DAILY_OPERATION', {'usuario':request.user,
        'actor':request.user.get_full_name() or request.user.username, 'sede_id':event.sede_id,
        'detalle':f'Evento {event.id}: {message}'})


class OpcionesSerializer(serializers.ModelSerializer):
    class Meta:
        model=EventoClinica
        fields=['permite_continuidad','inscripcion_desde','inscripcion_hasta']
    def validate(self,data):
        start=data.get('inscripcion_desde',self.instance.inscripcion_desde)
        end=data.get('inscripcion_hasta',self.instance.inscripcion_hasta)
        if start and end and end<=start:raise ValidationError('El cierre de inscripción debe ser posterior a la apertura.')
        if data.get('permite_continuidad') is False and self.instance.fichas.filter(resguardos__reanudado_en__isnull=True,resguardos__isnull=False).exists():
            raise ValidationError('Hay resguardos activos; registra su retorno antes de deshabilitar la continuidad.')
        return data


class OpcionesEventoView(APIView):
    permission_classes=[IsDocentePO]
    def put(self,request,evento_id):
        event=event_for(request,evento_id)
        ser=OpcionesSerializer(event,data=request.data,partial=True);ser.is_valid(raise_exception=True);ser.save()
        audit(request,event,'Opciones de continuidad y plazo de inscripción actualizadas.')
        return Response(EventoSerializer(event,context={'internal':True}).data)


class HorarioSerializer(serializers.ModelSerializer):
    motivo = serializers.CharField(required=False,allow_blank=True,max_length=500,write_only=True)
    class Meta:
        model = JornadaEvento
        fields = ['apertura','cierre','limite_recepcion','motivo']
    def validate(self,data):
        opening=data.get('apertura',self.instance.apertura);closing=data.get('cierre',self.instance.cierre)
        cutoff=data.get('limite_recepcion',self.instance.limite_recepcion)
        if not opening < closing or not opening <= cutoff <= closing:
            raise ValidationError('Revisa los horarios: apertura < cierre y recepción dentro de ese intervalo.')
        if self.instance.estado == 'Cerrada':
            raise ValidationError('No se modifica el horario de un día cerrado.')
        if self.instance.estado == 'Abierta' and not data.get('motivo','').strip():
            raise ValidationError('Indica el motivo de la modificación o extensión de horario.')
        return data


class JornadasView(APIView):
    permission_classes=[IsAnyInternalRole]
    def get(self,request,evento_id):
        event=event_for(request,evento_id)
        rows=[]
        for j in event.jornadas.prefetch_related('participantes__operador__perfil'):
            rows.append({'id':j.id,'fecha':j.fecha,'apertura':j.apertura,'cierre':j.cierre,
                'limite_recepcion':j.limite_recepcion,'estado':j.estado,
                'participantes':[{'id':p.operador_id,'nombre':p.operador.get_full_name() or p.operador.username,
                    'rol':p.operador.perfil.rol} for p in j.participantes.all()]})
        return Response(rows)


class ConfigJornadaView(APIView):
    permission_classes=[IsDocentePO]
    def put(self,request,jornada_id):
        j=get_object_or_404(JornadaEvento.objects.select_related('evento'),pk=jornada_id,evento__in=eventos_permitidos(request.user))
        event_for(request,j.evento_id)
        ser=HorarioSerializer(j,data=request.data,partial=True);ser.is_valid(raise_exception=True)
        reason=ser.validated_data.pop('motivo','')
        ser.save();audit(request,j.evento,f'Horario del {j.fecha}: {j.apertura} a {j.cierre}, recepción hasta {j.limite_recepcion}. {reason}')
        return Response({'guardado':True})


class EstadoJornadaView(APIView):
    permission_classes=[IsDocentePO]
    @transaction.atomic
    def post(self,request,jornada_id):
        j=get_object_or_404(JornadaEvento.objects.select_related('evento'),pk=jornada_id,evento__in=eventos_permitidos(request.user))
        event=get_object_or_404(EventoClinica.objects.select_for_update(),pk=j.evento_id)
        if event.estado != 'En curso': raise ValidationError('Primero inicia el evento.')
        j.refresh_from_db()
        target=request.data.get('estado')
        if target=='Abierta' and j.estado in ('Pendiente','Cerrada','No realizada'):
            if event.jornadas.filter(estado='Abierta').exclude(pk=j.pk).exists():
                raise ValidationError('Cierra la jornada abierta antes de iniciar otra.')
            if event.jornadas.filter(fecha__lt=j.fecha,estado='Pendiente').exists():
                raise ValidationError('Las jornadas se abren en orden de fecha.')
            if j.estado in ('Cerrada','No realizada') and not str(request.data.get('motivo','')).strip():
                raise ValidationError('Indica el motivo de la reapertura diaria.')
        elif target=='Cerrada' and j.estado=='Abierta':
            safe=ResguardoEntreJornadas.objects.filter(ficha__evento=event,reanudado_en__isnull=True,hasta__fecha__gt=j.fecha).values('ficha_id')
            pending=event.fichas.filter(Q(jornada_recepcion__fecha__lte=j.fecha)|Q(jornada_recepcion__isnull=True)).exclude(estado='Preinscrito').filter(resultado_entrega='').exclude(estado='En custodia').exclude(pk__in=safe)
            if pending.exists():
                raise ValidationError('Hay equipos sin entregar ni resguardo autorizado. Registra su devolución, custodia o continuidad antes de cerrar el día.')
        else: raise ValidationError('Cambio de jornada no permitido.')
        j.estado=target;j.save(update_fields=['estado'])
        audit(request,event,f'Jornada {j.fecha}: {target}. {str(request.data.get("motivo",""))[:500]}')
        return Response({'estado':target})


class ParticipantesJornadaView(APIView):
    permission_classes=[IsDocentePO]
    def post(self,request,jornada_id):
        j=get_object_or_404(JornadaEvento.objects.select_related('evento'),pk=jornada_id,evento__in=eventos_permitidos(request.user))
        event_for(request,j.evento_id)
        if j.estado=='Cerrada': raise ValidationError('La planificación de un día cerrado se conserva como historial.')
        try: user_id=int(request.data.get('operador'))
        except (ValueError,TypeError): raise ValidationError('Selecciona un operador.')
        perfil=get_object_or_404(PerfilOperador, user_id=user_id, sedes=j.evento.sede)
        action=request.data.get('accion','agregar')
        if action=='agregar': ParticipacionJornada.objects.get_or_create(jornada=j,operador=perfil.user)
        elif action=='quitar': ParticipacionJornada.objects.filter(jornada=j,operador=perfil.user).delete()
        else: raise ValidationError('Acción no válida.')
        audit(request,j.evento,f'Participante {perfil.user.username}: {action} en {j.fecha}.')
        return Response({'guardado':True})


class CopiarEventoView(APIView):
    permission_classes=[IsDocentePO]
    @transaction.atomic
    def post(self,request,evento_id):
        source=get_object_or_404(eventos_permitidos(request.user),pk=evento_id)
        start=serializers.DateField().run_validation(request.data.get('fecha_inicio'))
        data={'sede':source.sede_id,'nombre':request.data.get('nombre',''),'fecha_inicio':start,
            'fecha_fin':start+(source.fecha_fin-source.fecha_inicio),'lugar':source.lugar,
            'permite_continuidad':source.permite_continuidad}
        ser=EventoSerializer(data=data);ser.is_valid(raise_exception=True)
        new=ser.save(creado_por=request.user)
        old_days=list(source.jornadas.all());new_days=list(new.jornadas.all())
        for old,day in zip(old_days,new_days):
            day.apertura=old.apertura;day.cierre=old.cierre;day.limite_recepcion=old.limite_recepcion
            day.save(update_fields=['apertura','cierre','limite_recepcion'])
        audit(request,new,f'Creado desde evento {source.id}, sin copiar fichas, participantes ni autorizaciones.')
        return Response(EventoSerializer(new,context={'internal':True}).data,status=201)


class ResguardoSerializer(serializers.ModelSerializer):
    class Meta:
        model=ResguardoEntreJornadas
        fields=['hasta','lugar','responsable','motivo','titular_autoriza']
    def validate_titular_autoriza(self,value):
        if not value:raise ValidationError('Debe registrarse la autorización del titular para dejar el equipo.')
        return value


class ResguardoView(APIView):
    permission_classes=[IsDocentePO]
    @transaction.atomic
    def post(self,request,numero_ticket):
        f=get_object_or_404(fichas_permitidas(request,FichaAtencion.objects.select_for_update()),numero_ticket=numero_ticket)
        if not f.evento.permite_continuidad:raise ValidationError('Este evento no habilita continuidad entre días. La permanencia es excepcional.')
        if f.estado not in ('Recibido','En proceso','En espera'):raise ValidationError('La continuidad es para un equipo recibido cuyo trabajo aún no termina.')
        day=f.evento.jornadas.filter(estado='Abierta').first()
        if not day:raise ValidationError('Debe existir una jornada abierta para registrar el resguardo.')
        ser=ResguardoSerializer(data=request.data);ser.is_valid(raise_exception=True)
        target=ser.validated_data['hasta']
        if target.evento_id!=f.evento_id or target.fecha<=day.fecha or target.estado!='Pendiente':
            raise ValidationError('Selecciona una jornada posterior pendiente del mismo evento.')
        r=ser.save(ficha=f,desde=day,autorizado_por=request.user)
        BitacoraNota.objects.create(ficha=f,autor=request.user,autor_nombre=request.user.get_full_name(),contenido=f'Resguardo entre jornadas autorizado hasta {target.fecha}. Lugar: {r.lugar}. Responsable: {r.responsable}.')
        audit(request,f.evento,f'Continuidad excepcional de {f.numero_ticket} hasta {target.fecha}.')
        return Response({'id':r.id,'registrado':True},status=201)


class ReanudarResguardoView(APIView):
    permission_classes=[IsDocentePO]
    @transaction.atomic
    def post(self,request,numero_ticket):
        f=get_object_or_404(fichas_permitidas(request,FichaAtencion.objects.select_for_update(),allow_resguardo=True),numero_ticket=numero_ticket)
        r=get_object_or_404(f.resguardos.select_related('hasta'),reanudado_en__isnull=True)
        if r.hasta.estado!='Abierta':raise ValidationError('Abre la jornada de retorno antes de recibir nuevamente el equipo.')
        r.reanudado_en=timezone.now();r.reanudado_por=request.user;r.save(update_fields=['reanudado_en','reanudado_por'])
        BitacoraNota.objects.create(ficha=f,autor=request.user,autor_nombre=request.user.get_full_name(),contenido=f'Retorno desde resguardo registrado para {r.hasta.fecha}. Se conserva la ficha y el avance del checklist.')
        audit(request,f.evento,f'Retorno de {f.numero_ticket} desde resguardo.')
        return Response({'reanudado':True})


class DerivarEspecialistaView(APIView):
    permission_classes=[IsTecnicoOrDocente]
    @transaction.atomic
    def post(self,request,numero_ticket):
        f=get_object_or_404(fichas_permitidas(request,FichaAtencion.objects.select_for_update()),numero_ticket=numero_ticket)
        motivo=serializers.CharField(max_length=2000).run_validation(request.data.get('motivo'))
        destino=serializers.CharField(max_length=160).run_validation(request.data.get('destino'))
        if f.estado not in ('Recibido','En proceso','En espera'):raise ValidationError('La derivación corresponde a una atención técnica activa.')
        if f.hallazgo_ilicito_ley_21459:raise ValidationError('El bloqueo existente debe ser resuelto primero por el docente.')
        f.derivacion_destino=destino;f.derivacion_motivo=motivo;f.derivacion_registrada_en=timezone.now()
        f.incidencia_activa=True;f.descripcion_incidencia=f'Derivación a especialista: {motivo}';f.save()
        TicketStateMachine.transition(f,'En espera',request.user.get_full_name(),request.user,note_text=f'DERIVACIÓN SOLICITADA: {destino}. {motivo}. Requiere coordinación del docente; no representa una entrega física.')
        return Response(FichaDetailSerializer(f,context={'request':request}).data)


class MetricasDiariasView(APIView):
    permission_classes=[IsDocentePO]
    def get(self,request,evento_id):
        event=event_for(request,evento_id)
        return Response({'equipos_unicos':event.fichas.exclude(estado='Preinscrito').values('dispositivo_id').distinct().count(),
            'sin_jornada_registrada':event.fichas.exclude(estado='Preinscrito').filter(jornada_recepcion__isnull=True).count(),
            'dias':[{'jornada':j.id,'fecha':j.fecha,
                'equipos_recibidos':event.fichas.filter(jornada_recepcion=j).values('dispositivo_id').distinct().count(),
                'atenciones_recibidas':event.fichas.filter(jornada_recepcion=j).count(),
                'terminados':event.fichas.filter(verificado_salida_en__date=j.fecha).count(),
                'entregados':event.fichas.filter(entrega_registrada_en__date=j.fecha).count()} for j in event.jornadas.all()]})
