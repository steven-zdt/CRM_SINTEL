# Sintel Project - Multi-tenant SaaS

Proyecto Django multi-tenant usando django-tenants, PostgreSQL (psycopg v3), DRF (API-first), Celery y Redis.

> **⚠️ IMPORTANTE:** 
> - **TODA la documentación está consolidada en `documentacion/` (ÚNICA FUENTE DE VERDAD)**
> - La estructura del proyecto debe estar siempre alineada con `documentacion/arquitectura_general.md`
> - Ver `documentacion/` para todos los documentos de referencia

## Arquitectura

- **Multi-tenant por esquemas**: django-tenants con esquemas `public` y `tenant`
- **Base de datos**: PostgreSQL 16 con driver psycopg v3
- **API**: Django REST Framework (DRF) con enfoque **API-first** + django-filter + drf-spectacular
- **Tareas asíncronas**: Celery + Redis
- **Python**: 3.12
- **Django**: 5.x

### API-First Architecture

El proyecto sigue una arquitectura **API-first** donde todas las funcionalidades están expuestas a través de APIs REST:

- **Estructura por app**: Cada app tiene una carpeta `api/` con serializers, viewsets, routers
- **Endpoints principales**:
  - APIs por tenant: `http://tenant.localhost:8000/api/v1/`
  - APIs públicas: `http://localhost:8000/api/public/v1/`
  - OpenAPI Schema: `http://localhost:8000/api/schema/`
  - Swagger UI: `http://localhost:8000/api/docs/`
  - ReDoc: `http://localhost:8000/api/redoc/`

> **Nota sobre Chrome DevTools:**
> - Si ves un 404 en `/.well-known/appspecific/com.chrome.devtools.json`, es normal
> - Es una sonda de Chrome DevTools para "Automatic Workspace Folders"
> - El proyecto incluye un handler que retorna JSON vacío para silenciar el 404
> - Puedes deshabilitarlo en Chrome: `chrome://flags/#devtools-project-settings`
- **Paginación**: 25 resultados por página (configurable con `?page_size=`)
- **Filtrado**: django-filter + SearchFilter + OrderingFilter
- **Versionado**: NamespaceVersioning (`/api/v1/`, `/api/v2/` en el futuro)

> **📚 Documentación Completa:** 
> - **Arquitectura General:** `documentacion/arquitectura_general.md` (ÚNICA FUENTE DE VERDAD)
> - **Índice de Documentación:** `documentacion/README.md`
> - **Todos los documentos:** `documentacion/` (consolidados - ÚNICA UBICACIÓN)

## Estructura del Proyecto

```
sintel_project/
├── apps/
│   ├── public/             # Aplicaciones compartidas (Esquema public)
│   │   ├── tenants/        # Gestión de clientes y dominios
│   │   ├── accounts/       # Usuarios globales
│   │   └── impuestos/      # Core Legal/DIAN
│   ├── tenant/             # Aplicaciones privadas (Esquema por empresa)
│   │   ├── empresa/
│   │   ├── facturas/       # Core: Procesamiento XML
│   │   └── contabilidad/
│   ├── services/           # Lógica pura (Python packages) sin modelos
│   │   ├── maildigester/
│   │   ├── document_ingest/ # Pipeline universal de ingestión de documentos
│   │   ├── document_parser/ # Parsers para XML, PDF, XLS/XLSX, CSV, TXT
│   │   └── xml_parser/      # Parser XML legacy (mantenido por compatibilidad)
│   └── documentacion/      # Documentación del proyecto
│       ├── arquitectura_general.md  # Fuente única de verdad
│       └── REGLAS_ALINEACION.md     # Reglas de alineación
├── config/                 # Ajustes de Django
├── manage.py
├── requirements.txt
├── docker-compose.yaml
├── Dockerfile
└── .env.sample
```

> **⚠️ IMPORTANTE:** La estructura debe estar siempre alineada con `documentacion/arquitectura_general.md`. Ver `documentacion/REGLAS_ALINEACION.md` para las reglas de alineación.

## Instalación y Uso

### Opción 1: Con Docker (Recomendado)

1. **Copiar archivo de entorno**:
   ```bash
   cp .env.sample .env
   ```

2. **Levantar los servicios**:
   ```bash
   make up
   ```

> **⚠️ IMPORTANTE - HTTPS en Desarrollo:**
> - Django's `runserver` **solo soporta HTTP**, NO HTTPS
> - **Siempre usar HTTP en desarrollo**: `http://localhost:8000` (NO `https://`)
> - Si el navegador fuerza HTTPS, limpiar HSTS: `chrome://net-internals/#hsts`
> - Para HTTPS local, usar un proxy reverso (nginx + mkcert) o herramientas de desarrollo

3. **Ejecutar migraciones**:
   ```bash
   make migrate
   ```

4. **Crear superusuario**:
   ```bash
   make superuser
   ```

5. **Acceder al admin**:
   - URL: http://localhost:8000/admin/
   - El primer tenant se crea desde el admin o shell
   - El dominio debe apuntar a `public` inicialmente

### Opción 2: Sin Docker (Virtualenv)

1. **Crear y activar virtualenv**:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar base de datos PostgreSQL**:
   - Crear base de datos `sintel`
   - Configurar variables de entorno en `.env`

4. **Ejecutar migraciones**:
   ```bash
   python manage.py migrate_schemas --shared
   ```

5. **Crear superusuario**:
   ```bash
   python manage.py createsuperuser
   ```

6. **Ejecutar servidor**:
   ```bash
   python manage.py runserver
   ```

## Comandos Makefile

### Servicios Docker
- `make up`: Levantar contenedores Docker (detached)
- `make down`: Detener y eliminar contenedores
- `make shell`: Acceder a shell del contenedor web
- `make logs`: Ver logs del contenedor web

### Migraciones
- `make makemigrations`: Crear migraciones para todas las apps
- `make makemigrations-accounts`: Crear migraciones solo para accounts
- `make migrate-shared`: Aplicar migraciones del esquema public (--fake-initial)
- `make migrate-tenants`: Aplicar migraciones de tenant apps (--fake-initial)
- `make check-migrations`: Verificar migraciones pendientes (server guard)
- `make fix-migrations`: Corregir historial de migraciones inconsistente
- `make reset-migrations`: ⚠️ Resetear todo el historial de migraciones (solo desarrollo)

### Setup y Configuración
- `make setup`: Crear tenant público
- `make poblar-dian`: Poblar catálogo DIAN
- `make superuser`: Crear superusuario
- `make crear-empresa`: Crear nueva empresa (tenant) - Ver uso abajo

**Crear nueva empresa:**
```powershell
make crear-empresa NOMBRE="Mi Empresa S.A." DOMINIO="mi-empresa.localhost" EMAIL="admin@mi-empresa.com"
```

### Backups y Restauración (Fase 7)
- `make backup-tenant SCHEMA="schema_name"`: Backup de un tenant específico
- `make backup-all`: Backup de todos los tenants
- `make restore-tenant FILE="ruta/al/backup.dump"`: Restaurar backup

**Ejemplo de backup:**
```powershell
make backup-tenant SCHEMA="mi_empresa"
make backup-all
make restore-tenant FILE="backups/mi_empresa_20240101_120000.dump"
```

## Estado del Proyecto

### Fases Completadas

- ✅ **Fase 5: Pruebas y CI** - Smoke UX tests, auditoría automatizada, GitHub Actions
- ✅ **Fase 4: Migración por App** (En progreso) - Migración de módulos a DataTables server-side
- ✅ **Pipeline Universal de Documentos** - Sistema unificado para ingestión de XML, PDF, XLS/XLSX, CSV, TXT
- ✅ **Alineación Técnica Fase 0** - Normalización de assets, sanity checks, ajuste automático de columnas
- ✅ **Refactorización Cotizaciones v2.60** - Limpieza profunda, eliminación de monolitos, Feature-Sliced

### Documentación de Fases

- `FASE5_RESUMEN.md` - Resumen de Fase 5 (Pruebas y CI)
- `FASE4_MIGRACION_PROGRESO.md` - Estado de migración por app
- `documentacion/ALINEACION_TECNICA_O0.md` - Alineación técnica Fase 0
- `LIMPEZA_COTIZACIONES_v2.60.md` - Limpieza del módulo Cotizaciones

## Notas Importantes

- El primer tenant se crea desde el admin o shell Django
- El dominio debe apuntar a `public` inicialmente
- Las migraciones del esquema `public` se ejecutan con `migrate_schemas --shared`
- Las migraciones de tenant se ejecutan automáticamente al crear un nuevo tenant

## Configuración

Las variables de entorno se configuran en el archivo `.env` (ver `documentacion/VARIABLES_ENTORNO_EMAIL.md` para configuración completa):

**Variables básicas:**
- `DJANGO_DEBUG`: Modo debug (True/False)
- `DJANGO_SECRET_KEY`: Clave secreta de Django
- `DJANGO_ALLOWED_HOSTS`: Hosts permitidos (separados por comas)
- `DATABASE_*`: Configuración de PostgreSQL
- `REDIS_URL`: URL de conexión a Redis
- `TIME_ZONE`: Zona horaria (por defecto: America/Bogota)

**Variables de Email/SMTP (para invitaciones):**
- `EMAIL_BACKEND`: Backend de email (console para desarrollo, smtp para producción)
- `EMAIL_HOST`: Servidor SMTP (ej: smtp.gmail.com)
- `EMAIL_PORT`: Puerto SMTP (587 para TLS, 465 para SSL)
- `EMAIL_USE_TLS`: Usar TLS (True/False)
- `EMAIL_HOST_USER`: Usuario SMTP
- `EMAIL_HOST_PASSWORD`: Contraseña SMTP (o App Password para Gmail)
- `DEFAULT_FROM_EMAIL`: Email remitente por defecto
- `CONTACT_EMAIL`: Email de contacto (opcional)

Ver `documentacion/VARIABLES_ENTORNO_EMAIL.md` para configuración detallada de email.
#   C R M _ S I N T E L  
 