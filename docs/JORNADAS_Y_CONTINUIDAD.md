# Jornadas diarias y continuidad excepcional

Actualización local: 13 de noviembre de 2026.

## Planificación recomendada

Un evento corresponde a una edición de la Clínica del PC en una sede. Al indicar sus fechas de inicio y término se generan sus días de atención. Por ejemplo, una edición anual de tres días conserva un solo conjunto de fichas, con tres jornadas diferenciadas.

En **Días y participantes**, el docente configura apertura, cierre y límite de recepción de cada día. El cierre propuesto es **18:00**, editable; la apertura inicial de 09:00 es una propuesta configurable, no un horario confirmado por el profesor. Cambiar el horario de una jornada ya abierta exige un motivo y deja auditoría.

La apertura y el cierre de cada día son manuales: los horarios comunican la planificación, no ejecutan un cierre automático del servidor ni bloquean por reloj. Primero se inicia el evento en **Eventos y sedes**, después se abre su primer día en **Días y participantes**. Solo puede haber un día abierto por evento; las jornadas pendientes se abren en orden. La recepción exige que haya una jornada abierta.

Los participantes son una lista sencilla de operadores previstos por día. Cada uno debe tener acceso a la sede y conserva su rol. No agrega control de asistencia, calificaciones, turnos por horas ni cambios de permisos. Recepción y técnicos pueden consultar la planificación; el docente la administra.

## Inscripción

Se pueden definir fecha y hora de apertura y cierre de preinscripciones; dejarlas vacías mantiene la apertura según el estado del evento. El servidor valida el plazo. El formulario permite elegir un día preferido y muestra sus horarios; mesón registra por separado el día efectivo de recepción. No se incorporan cupos obligatorios.

## Equipos que continúan otro día

La continuidad está **deshabilitada por defecto**. Solo si el evento la habilita, el docente puede autorizar un caso en **Custodia al cierre y resguardo**:

1. Debe ser un equipo recibido cuyo trabajo esté pendiente.
2. Se elige un día posterior pendiente del mismo evento.
3. Se registran motivo, lugar, responsable y la autorización declarada del titular.
4. El sistema registra al docente y la fecha y hora de autorización.
5. El trabajo queda bloqueado durante el resguardo. Al abrir el día acordado, el docente registra el retorno.

Se mantienen el ticket, los ítems del checklist y sus avances. Este resguardo es distinto de la custodia de un equipo terminado que su dueño todavía no retira. El formulario deja constancia declarada de autorización; no incorpora firma electrónica del cliente ni envío de comunicaciones.

No se puede cerrar un día si quedan equipos recibidos sin entrega registrada ni resguardo documentado. Finalizar el evento exige cerrar el día abierto y resolver sus fichas según las reglas existentes. Los días futuros pendientes pasan a **No realizada** al finalizar la edición. Reabrir un día cerrado exige motivo.

## Derivación a un especialista

En **Checklist de Taller** se puede solicitar una derivación indicando destino sugerido y motivo. El equipo queda **En espera**, con incidencia activa para coordinación del docente. No se registra automáticamente entrega física, envío de datos ni autorización del cliente: deben seguir el flujo existente de coordinación y devolución documentada.

## Historial y edición siguiente

El evento finalizado conserva el taller en consulta. **Aviso de Retiro**, **Entrega y Encuesta** siguen disponibles para registrar retiros posteriores sin reabrir el trabajo técnico.

En **Eventos y sedes → Preparar otra edición desde este evento**, se copia duración, sede, lugar, horarios y configuración de continuidad a un borrador con nuevas fechas. No se copian fichas, participantes, autorizaciones ni plazos antiguos de inscripción.

El resumen diario separa recepciones, certificaciones y entregas. La continuidad no genera una recepción adicional. El total de equipos únicos se calcula por dispositivo dentro del evento. Las cinco fichas anteriores se conservan; no se inventó un día de recepción para sus registros históricos.

## Validación

- Migración `0006_operacion_diaria_y_continuidad` aplicada sobre la instalación local.
- Respaldo previo: `backups/antes_operacion_diaria.dump`.
- 45 pruebas de Django aprobadas sobre PostgreSQL, incluidas 12 para las reglas nuevas.
- Comprobación de modelos sin migraciones pendientes.
- Navegador Edge: tres días de atención, elección de día en inscripción, ampliación de horario, participantes, cierre y apertura diaria, copia anual y vista móvil a 390 px. Se retiraron los eventos y la sede temporales al terminar.
- Pruebas anteriores de permisos y constancia de entrega repetidas sin alterar las fichas demo.

Esta guía corresponde al prototipo Django. El mockup HTML independiente se mantiene fuera de este repositorio.
