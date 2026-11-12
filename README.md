# Sistema de Gestión: Clínica del PC — Prototipo Profesional (Django + DRF + PostgreSQL 17)

**Asignatura:** Ingeniería de Software (`TI3043`) — Evaluación Sumativa N° 3  
**Sede:** INACAP San Pedro de la Paz  
**Docente / Product Owner:** Prof. Pablo E. Pesce Sánchez  
**Equipo:** Daniel Melimán & Diego Astudillo  

---

## 1. Arquitectura y Decisiones Técnicas

- **Backend:** Django 6.1 + Django REST Framework (DRF) bajo arquitectura API REST + RBAC estricta (`IsAuthenticated` por defecto).
- **Base de Datos:** **PostgreSQL 17** relacional normalizada (`psycopg[binary]`, 11 tablas en `clinica/models.py`).
  - **Cero SQLite:** No existe fallback a SQLite.
  - **Cero archivos `.json`:** Toda la configuración, catálogo, plantillas, bitácoras WORM, auditoría OWASP y nóminas residen en PostgreSQL (exportaciones únicamente en `.csv` sanitizado contra CSV Injection).
- **Frontend Desacoplado (`frontend/`):** HTML5 + CSS3 + JavaScript ES6 puro con arquitectura orientada a componentes API (`validators.js`, `api.js`, `app.js`), CSP estricta (`script-src 'self'`, cero scripts o eventos inline).
- **Patrones GoF Implementados en Python (`backend/clinica/patterns/`):**
  1. **State (`TicketStateMachine`):** Gobierna transiciones estrictas de `FichaAtencion` e impone compuertas `CA07`, `CA08` y bloqueo legal `Ley 21.459`.
  2. **Factory (`FichaAndChecklistFactory`):** Genera correlativos (`PC-XXX`, `DEV-XX`, `CL-XX`) y materializa ítems de checklist multi-servicio con clave única `Servicio::orden`.
  3. **Observer (`ClinicEventBus`):** Bus de eventos interno que persiste automáticamente trazabilidad WORM en `EventoSeguridadOWASP` (OWASP A09).
  4. **Repository + Singleton (`ClinicaRepository`):** Encapsula consultas optimizadas con `select_related`/`prefetch_related` y mide cumplimiento de latencia `RNF07 <= 2.0 s`.
- **Seguridad OWASP Top 10:2025 y Cumplimiento Legal Chileno:**
  - **A01 Control de Acceso:** RBAC por perfil (`RECEPCIONISTA`, `TECNICO`, `DOCENTE_PO`), consulta pública anti-IDOR (Ticket + RUT coincidente) y proyección server-side **Ley N° 21.719** (el rol `TECNICO` nunca recibe RUT real, apellidos, teléfono, correo ni dirección en HTTP JSON).
  - **A04 / A07 Autenticación:** Django `SessionAuthentication` (`HttpOnly`, `SameSite=Lax`, CSRF), hashes PBKDF2 y bloqueo temporal tras 5 intentos fallidos (`HTTP 429`).
  - **A05 / A08 Integridad:** Sanitización anti-CSV Injection (`= + - @`), hash `SHA-256` server-side de consentimiento digital (**Ley N° 19.799**), registros WORM inmutables (`BitacoraNota`, `TransicionEstadoLog`, `EventoSeguridadOWASP`) y purga/anonimización tras 60 días de custodia.
  - **Ley N° 21.459:** Bloqueo inmediato (`HTTP 423 Locked`) ante hallazgo presuntamente ilícito hasta resolución del Docente PO.

---

## 2. Estructura del Proyecto

```text
Clinica-del-PC/
├── backend/
│   ├── config/                # settings.py (PostgreSQL-only), urls.py
│   ├── clinica/
│   │   ├── models.py          # 11 tablas relacionales normalizadas + WORM
│   │   ├── patterns/          # State, Factory, Observer, Repository + Singleton
│   │   ├── security/          # RBAC, DTO privacidad Ley 21.719, Módulo 11, CSV, CSP, A10
│   │   ├── management/commands/seed_clinica.py
│   │   ├── migrations/
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests.py           # Suite PostgreSQL (GoF, RBAC, IDOR, A07, A05, 21.719/21.459)
│   ├── .env.example
│   ├── manage.py
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── css/app.css
    └── js/{validators.js, api.js, app.js}
```

---

## 3. Requisitos e Instalación (PostgreSQL 17 + Windows)

1. **Instalar PostgreSQL 17** en Windows (por ejemplo vía `winget install PostgreSQL.PostgreSQL.17` o instalador oficial EDB) y asegurarse de que el servicio `postgresql-x64-17` esté en ejecución en `127.0.0.1:5432`.
2. **Crear la base de datos en PostgreSQL (`psql`):**
   ```sql
   CREATE DATABASE clinica_del_pc WITH ENCODING 'UTF8';
   ```
3. **Instalar dependencias Python:**
   ```powershell
   cd backend
   pip install -r requirements.txt
   ```
4. **Configurar variables de entorno (`backend/.env`):**
   Copiar `.env.example` a `.env` y completar `DB_PASSWORD` con la clave de tu usuario `postgres` y una `DJANGO_SECRET_KEY` segura.
5. **Aplicar migraciones y poblar datos iniciales en PostgreSQL:**
   ```powershell
   python manage.py migrate
   python manage.py seed_clinica
   ```
6. **Ejecutar servidor:**
   ```powershell
   python manage.py runserver
   ```
   Abrir en el navegador: `http://127.0.0.1:8000/` (también soporta Live Server en `:5500` vía CORS configurado).

---

## 4. Cuentas Demo Sembradas (`seed_clinica`)

| Rol | Usuario | Correo | Contraseña Demo |
| :--- | :--- | :--- | :--- |
| **Recepcionista** | `daniel.meliman` | `daniel.meliman@inacapmail.cl` | `ClinicaPC!26` |
| **Recepcionista (Mesón)** | `recepcion` | `recepcion@inacap.cl` | `ClinicaPC!26` |
| **Alumno Técnico** | `diego.astudillo` | `diego.astudillo@inacapmail.cl` | `TallerPC!26` |
| **Docente / PO** | `pablo.pesce` | `pablo.pesce@inacap.cl` | `DocentePO!26` |

---

## 5. Ejecución de Pruebas Automatizadas (PostgreSQL)

```powershell
cd backend
python manage.py test clinica --verbosity 2
```
> **Nota:** El usuario PostgreSQL configurado en `.env` debe tener privilegio `CREATEDB` para que Django cree y destruya la base temporal `test_clinica_del_pc` durante las pruebas.
