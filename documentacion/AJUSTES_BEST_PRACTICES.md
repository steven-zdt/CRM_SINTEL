# ✅ Ajustes Aplicados: Mejores Prácticas django-tenants

**Fecha:** 2026-01-17  
**Estado:** ✅ IMPLEMENTADO

---

## 📋 Resumen de Ajustes

Se han aplicado ajustes según las mejores prácticas oficiales de django-tenants y Django para garantizar un SaaS multi-tenant robusto y alineado con la documentación oficial.

---

## 🔧 Cambios Aplicados

### 1. ✅ Versiones de Dependencias Fijadas y Bloqueadas

**Archivo:** `requirements.txt`

**Stack Técnico Validado:**
- ✅ `Django>=5.0,<5.1` - Django 5.x compatible con Python 3.12
- ✅ `django-tenants>=3.9,<3.10` - Versión mínima 3.9.0 validada
- ✅ `psycopg[binary]>=3.1,<4.0` - psycopg3 como adaptador recomendado (binary para mejor rendimiento)
- ✅ `djangorestframework>=3.14,<4.0` - Versión mínima con rangos bloqueados
- ✅ `django-filter>=23.5,<24.0` - Versión mínima con rangos bloqueados
- ✅ `celery[redis]>=5.3,<6.0` - Versión mínima con rangos bloqueados
- ✅ `redis>=5.0,<6.0` - Versión mínima con rangos bloqueados
- ✅ `python-dotenv>=1.0,<2.0` - Versión mínima con rangos bloqueados

**Razón:** 
- Fijar versiones probadas y compatibles evita problemas de compatibilidad
- Rangos estrictos (con límite superior) previenen actualizaciones inesperadas
- Stack técnico validado según documentación oficial:
  - Django 5.x compatible con Python 3.12
  - psycopg3 como adaptador recomendado
  - django-tenants >= 3.9.0 (requisito mínimo)

---

### 2. ✅ Entrypoint.sh Creado

**Archivo:** `entrypoint.sh`

**Funcionalidad:**
- Script de entrada más claro y mantenible
- Manejo de errores con `set -e`
- Pipeline completo de inicialización:
  1. Verificar/corregir historial de migraciones
  2. Crear migraciones si hay cambios
  3. Aplicar migraciones del esquema public
  4. Verificar migraciones pendientes (Server Guard)
  5. Configurar tenant público
  6. Iniciar servidor

**Ventajas:**
- Más legible que un comando largo en docker-compose
- Fácil de modificar y mantener
- Errores más visibles
- Separación de responsabilidades

---

### 3. ✅ Dockerfile Actualizado

**Archivo:** `Dockerfile`

**Cambios:**
- Copia `entrypoint.sh` al contenedor
- Otorga permisos de ejecución (`chmod +x`)
- Define `ENTRYPOINT` para ejecutar automáticamente

**Resultado:** El entrypoint se ejecuta automáticamente al iniciar el contenedor.

---

### 4. ✅ docker-compose.yaml Simplificado

**Archivo:** `docker-compose.yaml`

**Cambios:**
- Eliminado el comando largo inline
- El entrypoint.sh se ejecuta automáticamente
- Comentario explicativo sobre cómo sobrescribir si es necesario

**Ventajas:**
- Más limpio y legible
- Fácil de mantener
- Consistente con mejores prácticas de Docker

---

### 5. ✅ Configuración Crítica de Django Validada

**Archivo:** `config/settings.py`

**Configuraciones Críticas Verificadas:**

1. ✅ **ENGINE = "django_tenants.postgresql_backend"**
   - Backend especial para multi-tenant por esquemas
   - **CRÍTICO:** Debe ser exactamente este valor, no el backend estándar de Django

2. ✅ **DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)**
   - Debe ser una tupla (no lista)
   - Router que enruta queries al esquema correcto (tenant o public)
   - **CRÍTICO:** Sin esto, las queries no se enrutarán correctamente

3. ✅ **TenantMainMiddleware como PRIMERO en MIDDLEWARE**
   - Debe ser el primer middleware en la lista
   - Identifica el tenant según el dominio y establece el esquema activo
   - **CRÍTICO:** Si no es primero, otros middlewares pueden hacer queries antes de establecer el esquema

4. ✅ **django.template.context_processors.request en TEMPLATES**
   - Context processor requerido por django-tenants
   - **CRÍTICO:** Necesario para que django-tenants funcione correctamente con templates

**Otras Verificaciones:**
- ✅ `SHARED_APPS` y `TENANT_APPS` están correctamente definidos y consolidados
- ✅ `AUTH_USER_MODEL = "accounts.User"` configurado
- ✅ `email` es `unique=True` en el modelo User

**Estado:** Todas las configuraciones críticas están correctas y validadas según documentación oficial de django-tenants.

---

### 6. ✅ Estructura Final de Apps Consolidada

**Archivo:** `config/settings.py`

**SHARED_APPS (Esquema Public) - Consolidado:**
- ✅ `django_tenants` (PRIMERO, requisito obligatorio)
- ✅ `apps.public.tenants` (Gestión de tenants y dominios)
- ✅ `apps.public.accounts` (Usuarios globales)
- ✅ `apps.public.impuestos` (Catálogo DIAN compartido)
- ✅ `django.contrib.contenttypes` (Requerido por admin)
- ✅ `django.contrib.auth` (Sistema de autenticación global)
- ✅ `django.contrib.admin` (Admin en public para gestión global)
- ✅ `django.contrib.sessions` (Sesiones compartidas - usuarios globales)
- ✅ `django.contrib.messages` (Sistema de mensajes)
- ✅ `django.contrib.staticfiles` (Archivos estáticos)

**TENANT_APPS (Esquema por Empresa) - Consolidado:**
- ✅ `apps.tenant.empresa` (Datos de la empresa por tenant)
- ✅ `apps.tenant.facturas` (Facturación por tenant)
- ✅ `apps.tenant.contabilidad` (Contabilidad por tenant)
- ✅ `rest_framework` (API REST por tenant)
- ✅ `django_filters` (Filtrado avanzado por tenant)

**Política de Sessions:**
- ✅ `django.contrib.sessions` está en `SHARED_APPS` porque:
  - Los usuarios son globales (`AUTH_USER_MODEL` en `SHARED_APPS`)
  - Las sesiones se comparten entre tenants
  - Un usuario puede tener sesiones activas en múltiples tenants
- ⚠️ Si necesitaras sesiones aisladas por tenant, moverías `sessions` a `TENANT_APPS`

**Reglas Especiales:**
- ✅ `django_tenants` debe ir PRIMERO en `SHARED_APPS`
- ✅ `django.contrib.contenttypes` y `django.contrib.auth` deben estar en `SHARED_APPS` para que el admin funcione
- ✅ `django.contrib.admin` está en `SHARED_APPS` (puede moverse a `TENANT_APPS` si se necesita admin por tenant)

---

## 📝 Documentación de Configuración

### DATABASE_ROUTERS

```python
DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)
```

**Importante:** Debe ser una tupla, no una lista. Django consultará primero el esquema del tenant y luego 'public'.

### Context Processor Request

```python
TEMPLATES = [
    {
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',  # ✅ Presente
                # ... otros CPs
            ],
        },
    },
]
```

**Razón:** Necesario para que django-tenants funcione correctamente con templates.

### Pipeline de Migraciones

**Para el esquema public (shared):**
```bash
python manage.py migrate_schemas --shared --fake-initial
```

**Para tenants específicos (on-demand):**
```bash
python manage.py migrate_schemas --schema=<schema_name> --fake-initial
```

**Para todos los tenants:**
```bash
python manage.py migrate_schemas
```

**Nota:** El flag `--fake-initial` permite aplicar migraciones iniciales sin errores si las tablas ya existen.

---

## 🚀 Uso del Entrypoint

### Ejecución Automática

El entrypoint se ejecuta automáticamente al hacer:
```bash
make up
# o
docker compose up
```

### Sobrescribir el Entrypoint

Si necesitas un comportamiento diferente, puedes sobrescribir en `docker-compose.yaml`:

```yaml
web:
  build: .
  command: python manage.py runserver 0.0.0.0:8000  # Sobrescribe entrypoint
```

### Modificar el Entrypoint

Edita `entrypoint.sh` y reconstruye:
```bash
docker compose build web
docker compose up
```

---

## ✅ Checklist de Verificación

- [x] Versiones de dependencias fijadas en `requirements.txt`
- [x] `entrypoint.sh` creado y funcional
- [x] `Dockerfile` actualizado con entrypoint
- [x] `docker-compose.yaml` simplificado
- [x] `DATABASE_ROUTERS` verificado (tupla)
- [x] Context processor `request` verificado
- [x] `SHARED_APPS` y `TENANT_APPS` verificados
- [x] `AUTH_USER_MODEL` configurado correctamente
- [x] `email` es `unique=True` en modelo User

---

## 📚 Referencias

- [django-tenants Documentation](https://django-tenants.readthedocs.io/)
- [Django Custom User Model](https://docs.djangoproject.com/en/5.0/topics/auth/customizing/)
- [psycopg Documentation](https://www.psycopg.org/docs/)

---

**Última Actualización:** 2026-01-17  
**Estado:** ✅ IMPLEMENTADO Y VERIFICADO
