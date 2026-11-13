# Eventos y sedes de Clínica del PC

Actualización del 13 de noviembre de 2026.

## Cómo usarlo

1. Abrir http://127.0.0.1:8000/ y actualizar con Ctrl + F5.
2. Ingresar como docente y abrir **Eventos y sedes**.
3. Seleccionar la sede en la barra superior. La pantalla muestra sus jornadas y permite filtrar por año.
4. Crear un evento indicando nombre, fechas de inicio y término y lugar de atención. Comienza en **Borrador**.
5. Abrir inscripciones cuando esté preparado. El **Enlace de inscripción** incluye el identificador del evento y puede utilizarse como destino del QR.
6. Iniciar el evento para pasar a **En curso** y abrir el primer día desde **Días y participantes**. Las fichas y las métricas se consultan dentro del evento seleccionado.
7. Resolver las atenciones o documentar su resguardo y cerrar el día antes de **Finalizar evento**. El taller finalizado sigue visible en consulta; Aviso y Entrega permiten registrar retiros posteriores. Solo el docente puede reabrir el evento y debe indicar un motivo, que se registra en la auditoría.

La planificación por día, los horarios, participantes y continuidad excepcional se describen en [JORNADAS_Y_CONTINUIDAD.md](JORNADAS_Y_CONTINUIDAD.md).

El público solo ve jornadas con inscripciones abiertas o en curso. No puede crear eventos ni acceder a fichas internas. La consulta pública individual mantiene la validación de ticket y RUT.

## Incorporar otra sede

En **Eventos y sedes**, el docente puede registrar una sede con nombre, código único y dirección. El creador obtiene acceso; un docente puede habilitar en esa sede a operadores de las sedes que ya administra. La creación de usuarios nuevos y la asignación de su rol se mantienen en Administración Django.

Recepción y técnicos solo acceden a atenciones de sus sedes autorizadas. El superusuario representa una administración central con acceso a todas las sedes. Las asignaciones se administran también en **Perfil de operador → Sedes**.

Cada sede puede personalizar sus plantillas desde **Plantillas y Nómina**. Cuando todavía no tiene una plantilla propia, utiliza el catálogo base. Las ejecuciones de checklist conservan sus ítems anteriores; publicar una plantilla local no cambia las de otras sedes.

## Historial conservado

Las cinco fichas que ya estaban en la instalación local quedaron asociadas a **Jornada inicial de demostración**, en San Pedro de la Paz. Se tomó la fecha del primer registro existente, no se atribuyó una fecha de actividad real confirmada. No se renumeraron tickets ni se borraron atenciones.

Una jornada nueva comienza sin atenciones. El filtro de contexto separa triaje, listado de fichas, detalle, escrituras, métricas y exportación CSV. Los tickets siguen siendo únicos en toda la instalación.

Se evitó también que el proceso de anonimización de una custodia antigua elimine los datos compartidos de un propietario que tenga otra atención posterior o fuera del conjunto de custodias vencidas seleccionado.

## Replicar en otras instalaciones

El mismo código puede ejecutarse con una sola base central para varias sedes o en una instalación independiente por sede. En una instalación nueva se preparan Python, PostgreSQL, el archivo .env y las migraciones, como indica el README. Después se crea un superusuario con `python manage.py createsuperuser`, se registra la sede y se crean sus eventos desde la interfaz. No es necesario ejecutar `seed_clinica`: ese comando carga las cuentas y atenciones ficticias de San Pedro de la Paz para demostración.

Las instalaciones independientes no sincronizan sus datos entre sí. Para un historial central de todas las sedes deben utilizar una misma instancia y sus permisos por sede. Este trabajo deja esa estructura disponible en el servidor local; no publica ni instala el sistema en servidores de INACAP.

## Verificación y respaldo

- Se agregó la migración 0003 de sedes y eventos, incluida la asociación de las fichas previas.
- La migración 0004 agrega plantillas locales por sede.
- La migración 0005 identifica la sede de los registros nuevos de auditoría; los anteriores sin sede identificable quedan disponibles para administración central.
- Las pruebas cubren nuevas jornadas, separación de datos y métricas, permisos entre sedes, fechas inválidas, catálogo público, cierre con pendientes, reapertura con motivo, plantillas independientes y conservación de propietarios con otra atención.
- Pasaron las 45 pruebas de Django y las comprobaciones de modelos y migraciones. Se repitieron las pruebas de navegador de permisos y constancia de entrega, y se comprobó el flujo de tres días, horarios, participantes y copia anual.
- Se probó en navegador la creación de una sede y jornada temporales, el ciclo de estados, el filtro por año, la consulta de métricas, la reapertura y la presentación a 390 px. Los registros temporales se retiraron al terminar.
- Respaldo anterior a la migración: `backups/antes_eventos_y_sedes_2026-11-13.dump`.

Este repositorio contiene el prototipo Django; el mockup HTML independiente se mantiene fuera de esta entrega.
