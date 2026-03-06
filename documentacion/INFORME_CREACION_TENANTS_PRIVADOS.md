# 📋 Informe Completo: Proceso de Creación de Tenants Privados

## 🎯 Resumen Ejecutivo

Este documento describe el proceso completo de creación de **tenants privados** (clientes/empresas) desde la consola de administración pública en `http://localhost:8000/console/tenants/new/`.

El proceso es **asíncrono** usando Celery, garantiza **atomicidad** mediante transacciones, e implementa una estrategia **"Zero-Orphan"** que asegura que un tenant nunca se cree sin su administrador y perfil asociado.

---

## 📍 Punto de Entrada

### URL Principal
```
http://localhost:8000/console/tenants/new/
```

### Requisitos de Acceso
- ✅ Usuario autenticado (`@login_required`)
- ✅ Usuario con permisos de staff (`is_staff=True`)
- ✅ Acceso desde esquema `public` (validado por `_ensure_public_schema_or_404()`)

---

## 🔄 Flujo Completo del Proceso

### Fase 1: Formulario de Creación (`tenants_new_page`)

**Archivo:** `apps/public/console/views.py` (líneas 100-121)

**Template:** `apps/public/console/templates/console/pages/tenants/new.html`

#### Campos del Formulario:

1. **`nombre`** (requerido)
   - Nombre de la empresa/tenant
   - Ejemplo: "Acme SAS"

2. **`schema_name`** (opcional)
   - Código único del tenant en PostgreSQL
   - Si no se proporciona, se genera automáticamente desde `nombre` usando `slugify()`
   - Validaciones:
     - Solo letras minúsculas, números y guiones bajos (`[a-z0-9_]+`)
     - Máximo 63 caracteres (límite de PostgreSQL)
     - No puede ser `"public"` (reservado)
     - No puede contener puntos (v2.17: estandarización de subdominios)
   - Ejemplo: `"acme"` o `"mi_empresa"`

3. **`admin_user_id`** (requerido)
   - ID del usuario administrador existente (debe existir en el esquema `public`)
   - Se selecciona de un dropdown con usuarios existentes (máximo 500)

#### Validaciones del Frontend:

- Validación en tiempo real del campo `schema_name`
- Preview del dominio que se creará: `{schema_name}.{TENANT_DOMAIN_BASE}`
- Normalización automática a minúsculas

---

### Fase 2: Procesamiento del Formulario (`tenants_create`)

**Archivo:** `apps/public/console/views.py` (líneas 125-223)

#### Validaciones del Backend:

1. **Método HTTP:** Solo acepta `POST`
2. **Campos requeridos:**
   - `nombre`: No puede estar vacío
   - `admin_user_id`: Debe existir
3. **Validación de `schema_name`:**
   - Si se proporciona, se valida con `validate_schema_name()`
   - No puede contener puntos
   - No puede existir previamente
4. **Usuario administrador:**
   - Debe existir en la base de datos

#### Procesamiento:

```python
# 1. Validar datos
nombre = request.POST.get("nombre", "").strip()
schema_name = request.POST.get("schema_name", "").strip().lower() or None
admin_user_id = request.POST.get("admin_user_id")

# 2. Validar schema_name si se proporciona
if schema_name:
    validate_schema_name(schema_name)
    if Client.objects.filter(schema_name=schema_name).exists():
        raise ValueError("Schema name ya existe")

# 3. Encolar tarea Celery
from apps.public.tenants.tasks import onboard_tenant_task

task = onboard_tenant_task.delay(
    nombre=nombre,
    admin_user_id=int(admin_user_id),
    schema_name=schema_name  # Opcional
)

# 4. Redirigir a página de estado
return redirect(f"{reverse('console:tenants-status')}?task_id={task.id}")
```

---

### Fase 3: Tarea Celery Asíncrona (`onboard_tenant_task`)

**Archivo:** `apps/public/tenants/tasks.py` (líneas 16-112)

**Cola:** `high_priority` (procesamiento inmediato)

**Configuración:**
- `autoretry_for=(Exception,)`: Reintenta automáticamente en caso de error
- `retry_backoff=True`: Espera exponencial entre reintentos
- `max_retries=3`: Máximo 3 reintentos

#### Proceso de la Tarea:

```python
@shared_task(bind=True, queue='high_priority')
def onboard_tenant_task(self, nombre, admin_user_id, schema_name=None):
    # 1. Asegurar esquema público
    connection.set_schema_to_public()
    
    # 2. Llamar al servicio de creación
    tenant, domain, login_url = crear_tenant(
        nombre=nombre,
        admin_user_id=admin_user_id,
        schema_name=schema_name
    )
    
    # 3. Retornar resultado
    return {
        "client_id": tenant.id,
        "schema_name": tenant.schema_name,
        "domain": domain.domain,
        "login_url": login_url,
    }
```

---

### Fase 4: Servicio de Creación (`crear_tenant`)

**Archivo:** `apps/services/onboarding/empresa_service.py` (líneas 20-136)

**Decorador:** `@transaction.atomic` (garantiza atomicidad)

#### Flujo Estandarizado (Zero-Orphan):

##### 1. Preparación y Validaciones

```python
# Generar schema_name si no se proporciona
if not schema_name:
    from django.utils.text import slugify
    schema_name = slugify(nombre).replace('-', '_')

# Validar schema_name
validate_schema_name(schema_name)

# Verificar unicidad
if Client.objects.filter(schema_name=schema_name).exists():
    raise ValueError(f"El schema '{schema_name}' ya existe.")

# Verificar usuario admin
admin_user = User.objects.get(pk=admin_user_id)
```

##### 2. Creación del Client (Tenant)

```python
client = Client.objects.create(
    schema_name=schema_name,
    nombre=nombre,
    on_trial=es_trial,
    is_active=True
)
# auto_create_schema=True crea el esquema físico en PostgreSQL
```

**Señal Automática:** `post_save` en `apps/public/tenants/signals.py` (líneas 7-76)

La señal `create_client_domain` se ejecuta automáticamente y:

1. **Construye el dominio:** `{schema_name}.{TENANT_DOMAIN_BASE}`
   - Ejemplo: `"acme.localhost"` (si `TENANT_DOMAIN_BASE="localhost"`)

2. **Crea el dominio principal:**
   ```python
   Domain.objects.create(
       domain=domain_name,  # "acme.localhost"
       tenant=client,
       is_primary=True
   )
   ```

3. **En desarrollo (DEBUG=True):** Crea dominio adicional con puerto:
   ```python
   Domain.objects.create(
       domain=f"{domain_name}:8000",  # "acme.localhost:8000"
       tenant=client,
       is_primary=False  # Solo alias, no principal
   )
   ```

##### 3. Migración del Esquema

```python
call_command(
    'migrate_schemas',
    schema_name=schema_name,
    interactive=False,
    verbosity=0
)
```

**Resultado:** Se crean todas las tablas del tenant en el esquema `{schema_name}`:
- `tenant_empresa_empresa`
- `tenant_facturas_factura`
- `tenant_contabilidad_cuentacontable`
- `tenant_perfil_tenantprofile`
- etc.

##### 4. Vinculación de Membresía (TenantMembership)

```python
TenantMembership.objects.create(
    user=admin_user,
    client=client,
    is_active=True,
    is_primary_admin=True,
    rol='ADMIN'
)
```

**Ubicación:** Esquema `public` (tabla `tenants_tenantmembership`)

**Propósito:** Vincula el usuario global con el tenant específico, permitiendo que el usuario acceda al tenant.

##### 5. Creación del Perfil del Colaborador (TenantProfile)

```python
with tenant_context(client):
    perfil = obtener_o_crear_perfil(
        user=admin_user,
        defaults={
            'cargo': 'Administrador Principal',
            'departamento': 'Gerencia',
            'configuracion': {'theme': 'light', 'notifications': True}
        }
    )
```

**Ubicación:** Esquema privado del tenant (tabla `tenant_perfil_tenantprofile`)

**Propósito:** Crea el perfil del colaborador dentro del tenant, siguiendo la estrategia **"Zero-Orphan"**.

**Servicio:** `apps/services/perfil/perfil_service.py` → `obtener_o_crear_perfil()`

##### 6. Construcción de URL de Acceso

```python
protocol = "https" if not settings.DEBUG else "http"
login_domain = domain_obj.domain

if settings.DEBUG:
    port = getattr(settings, 'APP_PORT', '8000')
    domain_with_port = Domain.objects.filter(
        tenant=client,
        domain=f"{normalize_domain(domain_obj.domain)}:{port}"
    ).first()
    if domain_with_port:
        login_domain = domain_with_port.domain

login_url = f"{protocol}://{login_domain}/"
```

**Resultado:**
- Desarrollo: `http://acme.localhost:8000/`
- Producción: `https://acme.sintel.com/`

---

### Fase 5: Monitoreo del Proceso (`tenants_status_page`)

**Archivo:** `apps/public/console/views.py` (líneas 227-290)

**Template:** `apps/public/console/templates/console/pages/tenants/status.html`

#### Funcionalidad:

1. **Polling HTMX:** Actualiza el estado cada pocos segundos
2. **Estados posibles:**
   - `PENDING`: Tarea en cola
   - `STARTED`: Tarea en ejecución
   - `SUCCESS`: Tarea completada
   - `FAILURE`: Tarea fallida
3. **Información mostrada:**
   - Estado actual
   - Resultado (si está disponible):
     - `client_id`
     - `schema_name`
     - `domain`
     - `login_url`
   - Error (si falló)

#### Ejemplo de Resultado Exitoso:

```json
{
    "client_id": 5,
    "schema_name": "acme",
    "domain": "acme.localhost",
    "login_url": "http://acme.localhost:8000/"
}
```

---

## 🔐 Seguridad y Validaciones

### Validaciones de Entrada

1. **Schema Name:**
   - ✅ Solo letras minúsculas, números y guiones bajos
   - ✅ Máximo 63 caracteres
   - ✅ No puede ser `"public"` (reservado)
   - ✅ No puede contener puntos
   - ✅ Debe ser único

2. **Usuario Administrador:**
   - ✅ Debe existir en la base de datos
   - ✅ Debe estar en el esquema `public`

3. **Nombre de Empresa:**
   - ✅ No puede estar vacío
   - ✅ Se normaliza automáticamente

### Atomicidad

- ✅ `@transaction.atomic` en `crear_tenant()`
- ✅ Si falla cualquier paso, se revierte TODO:
  - Creación del Client
  - Creación del Domain
  - Creación del esquema PostgreSQL
  - Creación de TenantMembership
  - Creación de TenantProfile

### Aislamiento de Datos

- ✅ Cada tenant tiene su propio esquema PostgreSQL
- ✅ Los datos están completamente aislados
- ✅ No hay posibilidad de acceso cruzado entre tenants

---

## 📊 Estructura de Datos Creada

### Esquema `public` (Compartido)

1. **`tenants_client`** (tabla de tenants)
   ```sql
   id | schema_name | nombre | on_trial | is_active | created_at
   ```

2. **`tenants_domain`** (tabla de dominios)
   ```sql
   id | domain | tenant_id | is_primary | created_at
   ```

3. **`tenants_tenantmembership`** (vinculación usuario-tenant)
   ```sql
   id | user_id | client_id | is_active | is_primary_admin | rol
   ```

### Esquema `{schema_name}` (Privado del Tenant)

1. **`tenant_empresa_empresa`** (datos fiscales)
2. **`tenant_facturas_factura`** (facturación)
3. **`tenant_contabilidad_cuentacontable`** (contabilidad)
4. **`tenant_perfil_tenantprofile`** (perfiles de colaboradores)
5. **Otras tablas según TENANT_APPS**

---

## 🚀 Acceso al Tenant Creado

### URL de Acceso

Una vez completada la creación, el usuario puede acceder al tenant en:

```
http://{schema_name}.{TENANT_DOMAIN_BASE}:{PORT}/
```

**Ejemplo:**
- Desarrollo: `http://acme.localhost:8000/`
- Producción: `https://acme.sintel.com/`

### Flujo de Acceso

1. **Usuario accede a la URL del tenant**
2. **TenantMainMiddleware** resuelve el tenant por dominio
3. **Django usa `TENANT_URLCONF`** (`config.urls_tenant`)
4. **Se carga `apps.tenant.landing.urls`**
5. **Se ejecuta `TenantLandingView`**:
   - Si está autenticado → Redirige a `/dashboard/`
   - Si es anónimo → Muestra landing page con botón de login

### Login

- **URL de login:** `http://acme.localhost:8000/login/`
- **Vista:** `TenantLoginView` (usa `TenantAuthenticationForm`)
- **Validación:** 
  - Credenciales del usuario
  - Membresía activa en el tenant (`TenantMembership`)
  - Tenant activo (`is_active=True`)

---

## 🔍 Diagnóstico y Troubleshooting

### Verificar Creación Exitosa

```python
from apps.public.tenants.models import Client, Domain, TenantMembership
from django_tenants.utils import set_tenant_to_public

set_tenant_to_public()

# Verificar tenant
client = Client.objects.get(schema_name='acme')
print(f"Tenant: {client.nombre} ({client.schema_name})")

# Verificar dominio
domain = Domain.objects.get(tenant=client, is_primary=True)
print(f"Dominio: {domain.domain}")

# Verificar membresía
membership = TenantMembership.objects.get(client=client)
print(f"Admin: {membership.user.email}")

# Verificar perfil (en esquema del tenant)
from django_tenants.utils import tenant_context
with tenant_context(client):
    from apps.tenant.perfil.models import TenantProfile
    perfil = TenantProfile.objects.get(user=membership.user)
    print(f"Perfil: {perfil}")
```

### Errores Comunes

1. **"Schema name ya existe"**
   - **Causa:** El `schema_name` ya está en uso
   - **Solución:** Usar un `schema_name` diferente

2. **"El usuario con ID X no existe"**
   - **Causa:** El `admin_user_id` no existe en la base de datos
   - **Solución:** Verificar que el usuario exista antes de crear el tenant

3. **"Error al crear dominio"**
   - **Causa:** La señal `create_client_domain` falló
   - **Solución:** Verificar logs y configuración de `TENANT_DOMAIN_BASE`

4. **"Error al crear perfil"**
   - **Causa:** Fallo en `obtener_o_crear_perfil()`
   - **Solución:** Verificar que las migraciones del tenant se hayan ejecutado correctamente

---

## 📝 Logs y Monitoreo

### Logs del Proceso

El proceso genera logs detallados en cada fase:

```
🚀 Iniciando creación de tenant: Acme SAS (acme)
✅ Tenant y Dominio creados: acme / acme.localhost
🛠 Aplicando migraciones al esquema 'acme'...
👤 Membresía creada para usuario ID 1
👤 Creando TenantProfile en esquema 'acme'...
✅ Perfil creado: <TenantProfile> en acme
✅ Tenant creado: acme (acme.localhost) -> http://acme.localhost:8000/
```

### Monitoreo de Tareas Celery

```bash
# Ver tareas en cola
docker compose exec celery celery -A config inspect active

# Ver logs del worker
docker compose logs -f celery

# Ver estado de una tarea específica
docker compose exec web python manage.py shell -c "
from celery.result import AsyncResult
result = AsyncResult('task-id-aqui')
print(result.state)
print(result.result)
"
```

---

## 🎯 Resumen de Archivos Involucrados

### Vistas y URLs
- `apps/public/console/views.py` → `tenants_new_page()`, `tenants_create()`, `tenants_status_page()`
- `apps/public/console/urls.py` → Definición de rutas
- `config/urls_public.py` → Inclusión de rutas de consola

### Templates
- `apps/public/console/templates/console/pages/tenants/new.html` → Formulario de creación
- `apps/public/console/templates/console/pages/tenants/status.html` → Página de estado

### Servicios
- `apps/services/onboarding/empresa_service.py` → `crear_tenant()`
- `apps/services/perfil/perfil_service.py` → `obtener_o_crear_perfil()`

### Tareas Celery
- `apps/public/tenants/tasks.py` → `onboard_tenant_task()`

### Señales
- `apps/public/tenants/signals.py` → `create_client_domain()`

### Modelos
- `apps/public/tenants/models.py` → `Client`, `Domain`, `TenantMembership`
- `apps/tenant/perfil/models.py` → `TenantProfile`

---

## ✅ Checklist de Verificación Post-Creación

- [ ] Tenant creado en `tenants_client`
- [ ] Dominio principal creado en `tenants_domain` con `is_primary=True`
- [ ] Dominio con puerto creado (si `DEBUG=True`)
- [ ] Esquema PostgreSQL `{schema_name}` existe
- [ ] Migraciones aplicadas al esquema del tenant
- [ ] `TenantMembership` creada en esquema `public`
- [ ] `TenantProfile` creado en esquema del tenant
- [ ] URL de acceso funciona: `http://{schema_name}.{TENANT_DOMAIN_BASE}:{PORT}/`
- [ ] Login funciona con el usuario administrador
- [ ] Dashboard accesible después del login

---

## 📚 Referencias

- **Documentación Django Tenants:** https://django-tenants.readthedocs.io/
- **Documentación Celery:** https://docs.celeryproject.org/
- **Arquitectura General:** `documentacion/arquitectura_general.md`
- **Diagnóstico Forense:** `documentacion/DIAGNOSTICO_FORENSE_TENANT_REDIRECCION.md`

---

**Última actualización:** 2026-01-23  
**Versión del proceso:** v2.18 (Zero-Orphan Strategy)
