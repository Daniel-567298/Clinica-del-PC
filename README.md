# Clínica del PC — INACAP

Sistema académico para gestionar preinscripciones, recepción, checklist de taller, bitácora, calidad, entrega y encuesta. Organiza distintas ediciones por sede y año, con uno o varios días de atención.

**Asignatura:** Ingeniería de Software TI3043 · Evaluación Sumativa N.º 3

**Sede de referencia:** San Pedro de la Paz

**Docente / Product Owner:** Pablo E. Pesce Sánchez

**Equipo:** Daniel Melimán y Diego Astudillo

## Estado y arquitectura

Prototipo funcional de frontend y backend para desarrollo y evaluación; no es un despliegue de producción ni una certificación de cumplimiento legal o de seguridad. El alcance definitivo de la entrega académica debe acordarse con el docente.

- Frontend: HTML, CSS y JavaScript, servido por Django.
- Backend: Django y Django REST Framework; versiones en [requirements.txt](backend/requirements.txt).
- Base de datos: PostgreSQL 17. No utiliza SQLite.
- Patrones: State, Factory, Observer y Repository con Singleton.
- Validación: **45 pruebas automatizadas** sobre PostgreSQL.

## Funcionalidades

| Área | Comportamiento |
| --- | --- |
| Inscripción | Un formulario por equipo, RUT validado y día preferido. No sobrescribe los datos de un propietario existente. |
| Recepción | Búsqueda por ticket o RUT, inspección, consentimiento y día efectivo de ingreso. |
| Taller | Checklist por servicio y sede, autor, fecha, bitácora e incidencias. |
| Privacidad | Permisos por rol y sede; contactos y notas privadas de mesón ocultos al técnico. |
| Entrega | Constancia obligatoria de prueba conjunta; devolución sin reparación con observaciones cuando corresponda. |
| Encuesta | Valoración validada; entradas inválidas reciben un error de validación. |
| Eventos y sedes | Historial por año y separación de fichas, plantillas, métricas y auditoría por sede. |
| Jornadas | Horarios por día, cierre propuesto a las 18:00, participantes y apertura/cierre manual del docente. |
| Continuidad | Resguardo excepcional autorizado entre días; conserva ticket y checklist. Deshabilitado inicialmente. |
| Derivación | Solicitud a especialista; equipo en espera para coordinación del docente. |
| Historial | Retiros posteriores al evento y copia de configuración para otra edición sin copiar fichas ni participantes. |

## Estructura

```text
backend/
  config/          Configuración, rutas y versiones de archivos del frontend
  clinica/
    models.py      Atención, sedes, eventos y jornadas
    jornadas.py    Operación diaria y continuidad
    migrations/    Evolución del esquema y conservación de datos anteriores
    patterns/      State, Factory, Observer y Repository
    security/      Roles, contexto de sede/evento y privacidad
    tests*.py      Pruebas de atención, jornadas y sesión
  .env.example
  manage.py
  requirements.txt
frontend/          Interfaz conectada a la API
docs/              Guías de sedes, jornadas e inicio de sesión
```

## Instalación local en Windows

Requisitos: Git, **Python 3.12** (versión usada en la validación) y **PostgreSQL 17** en ejecución. Comandos para PowerShell:

```powershell
git clone https://github.com/Daniel-567298/Clinica-del-PC.git
cd Clinica-del-PC
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
```

Crear una base vacía desde `psql` o pgAdmin:

```sql
CREATE DATABASE clinica_del_pc WITH ENCODING 'UTF8';
```

Editar `backend/.env`: configurar `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT`. El puerto habitual es **5432**; debe coincidir con el de tu instalación. Generar una clave propia para `DJANGO_SECRET_KEY`:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
cd backend
..\.venv\Scripts\python.exe manage.py migrate
```

No subir `.env`, credenciales reales ni copias de bases de datos al repositorio.

### Demostración con datos ficticios

Solo en una instalación de prueba, desde `backend`:

```powershell
..\.venv\Scripts\python.exe manage.py seed_clinica
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Abrir **http://127.0.0.1:8000/**. Aparece **San Pedro de la Paz → Jornada inicial de demostración**, con cinco fichas de ejemplo. Se ingresa desde **Iniciar sesión**; no es necesario utilizar Casos de prueba.

| Perfil | Usuario | Contraseña de demostración |
| --- | --- | --- |
| Recepción | `daniel.meliman` o `recepcion` | `ClinicaPC!26` |
| Técnico | `diego.astudillo` | `TallerPC!26` |
| Docente / administración central | `pablo.pesce` | `DocentePO!26` |

Credenciales públicas exclusivas de la demo. El docente demo es superusuario y ve todas las sedes. La carga demo modifica cuentas de prueba: no ejecutarla sobre datos reales ni como procedimiento de actualización.

### Instalación vacía para otra sede

Después de migrar, omitir `seed_clinica`:

```powershell
..\.venv\Scripts\python.exe manage.py createsuperuser
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

1. Ingresar con el superusuario y registrar la sede en **Eventos y sedes**.
2. Crear cuentas y perfiles en **/admin/**; asignar rol, sedes y habilitación.
3. Cargar servicios y plantillas en Administración Django. Personalizar las tareas por sede desde **Plantillas y Nómina** cuando exista el catálogo.
4. Crear un evento y configurar sus días y horarios en **Días y participantes**.
5. Abrir inscripciones, iniciar el evento y abrir el primer día antes de recibir equipos.

Una instancia puede atender varias sedes con permisos separados. Las instalaciones con bases independientes no sincronizan sus datos entre sí.

## Uso de eventos y jornadas

El selector superior indica la sede y edición actuales. **Eventos y sedes** permite consultar años anteriores y crear una nueva edición en borrador.

Los horarios son planificación: **no cierran automáticamente el sistema por reloj**. El docente abre y cierra cada día; modificar el horario de un día abierto exige motivo. El cierre se bloquea si quedan equipos recibidos sin entrega o resguardo documentados.

Los participantes son operadores previstos para el día; la lista no cambia sus permisos ni registra asistencia o calificaciones. No existen cupos obligatorios de inscripción.

La continuidad requiere habilitarla en el evento y autorizar cada caso: titular, docente, lugar, responsable y día de retorno. Durante el resguardo se bloquea el taller hasta registrar el retorno. Se conservan el ticket y los avances del checklist.

Al finalizar, el taller queda en consulta; **Aviso de Retiro** y **Entrega y Encuesta** permiten retiros posteriores. Reabrir exige motivo. Detalles en [Eventos y sedes](docs/EVENTOS_Y_SEDES.md) y [Jornadas y continuidad](docs/JORNADAS_Y_CONTINUIDAD.md).

## Actualizar una instalación existente

Respaldar previamente la base con herramientas de PostgreSQL y conservar el `.env`. En una copia sin modificaciones pendientes:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
cd backend
..\.venv\Scripts\python.exe manage.py migrate
```

Reiniciar el servidor y recargar con **Ctrl + F5**. No repetir la carga demo. Las migraciones asocian fichas anteriores a la sede y evento iniciales conservando sus tickets; no inventan días de recepción para registros históricos sin ese dato.

## Pruebas

Desde `backend`, con PostgreSQL disponible:

```powershell
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe manage.py test clinica --verbosity 2
```

El usuario PostgreSQL necesita `CREATEDB` para crear y retirar la base temporal. Las 45 pruebas cubren privacidad, entrega, encuesta, permisos, sedes, eventos, jornadas, continuidad, copia anual, archivos y sesión con CSRF.

## Solución de problemas

- **PostgreSQL sin conexión:** revisar servicio, base, usuario, contraseña y puerto del `.env`.
- **Sedes vacías o interfaz antigua:** abrir el servidor Django y recargar con Ctrl + F5. Los archivos llevan versión según su contenido; un fallo de catálogo muestra **Reintentar carga**. Ver [Inicio y sesión](docs/INICIO_Y_SESION.md).
- **Recepción bloqueada:** verificar evento en curso y día abierto por el docente.
- **Sin eventos públicos:** revisar estado y fechas opcionales de inscripción.
- **Operador sin acceso:** revisar perfil habilitado y sedes asignadas.

El inicio recomendado es Django en el puerto 8000. Abrir `index.html` directamente no proporciona una API ni una sesión funcionales.

## Límites del prototipo

- Correo y WhatsApp registran acciones o estados; no existe una integración validada de envío real. `correo_enviado` no acredita recepción del mensaje.
- Consentimientos y autorizaciones son constancias del prototipo, sin integración certificada de firma electrónica.
- La política existente de custodia y anonimización debe validarse con la institución antes de usar datos reales; los plazos mostrados no constituyen asesoría legal.
- El CSV de métricas es una exportación, no un respaldo recuperable de toda la base.
- Faltan validación de carga/concurrencia y revisión de correlativos ante inscripciones simultáneas. Las pruebas funcionales no sustituyen esas verificaciones.
- Antes de producción se requieren alojamiento adecuado, HTTPS, correo, recuperación de respaldos y políticas institucionales de acceso y tratamiento de datos. El servidor de desarrollo no es un servicio de producción.
