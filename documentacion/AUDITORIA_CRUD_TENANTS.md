# 🔍 Auditoría Completa: CRUD de Tenants desde Consola

## 📋 Resumen Ejecutivo

Este documento detalla todas las fases del proceso de creación de tenants privados desde la consola web (`http://localhost:8000/console/tenants/`) y diagnostica por qué una tarea puede quedarse en estado `PENDING`.

## 🔄 Flujo Completo del Proceso

### FASE 1: Interfaz de Usuario (Frontend)

**Ubicación**: `apps/public/console/templates/console/pages/tenants/new.html`

1. Usuario completa formulario:
   - `nombre`: Nombre de la empresa
   - `schema_name`: Identificador del esquema (requerido)
   - `dominio`: Dominio opcional
   - `admin_user_id`: ID del usuario administrador

2. Submit del formulario → `POST /console/tenants/create/`

### FASE 2: Vista de Creación (Backend)

**Ubicación**: `apps/public/console/views.py` → `tenants_create()`

**Proceso**:
1. ✅ Validación de permisos (`@login_required` + `is_staff`)
2. ✅ Validación de esquema (`_ensure_public_schema_or_404()`)
3. ✅ Validación de campos requeridos
4. ✅ Validación de `schema_name` con `validate_schema_name()`
5. ✅ Verificación de duplicados (`Client.objects.filter(schema_name=...)`)
6. ✅ Validación de dominio (si se proporciona)
7. ✅ **Llamada directa a Celery**: `onboard_tenant_task.delay(**task_kwargs)`
8. ✅ Redirección a página de estado: `/console/tenants/status/?task_id=...`

**Código crítico**:
```python
from apps.public.tenants.tasks import onboard_tenant_task

task_kwargs = {
    'nombre': nombre,
    'schema_name': schema_name,
    'admin_user_id': int(admin_user_id)
}
if dominio:
    task_kwargs['dominio'] = dominio_normalizado

task = onboard_tenant_task.delay(**task_kwargs)
return redirect(f"{reverse('console:tenants-status')}?task_id={task.id}")
```

### FASE 3: Página de Estado (Polling HTMX)

**Ubicación**: `apps/public/console/templates/console/pages/tenants/status.html`

1. Renderiza página completa con `task_id`
2. Incluye partial HTMX: `_status_card.html`
3. Partial inicia polling automático con `hx-trigger="load"`

**Vista de Estado**: `apps/public/console/views.py` → `tenants_status_page()`

- Si es petición HTMX (`HX-Request`): Devuelve solo el partial
- Si es petición normal: Devuelve página completa

**Código crítico**:
```python
if request.headers.get('HX-Request'):
    from celery.result import AsyncResult
    result = AsyncResult(task_id)
    
    context = {
        "task_id": task_id,
        "state": result.state,  # ← Aquí se consulta el estado
        "result": result.result if result.successful() else None,
        "error": str(result.info) if result.failed() else None,
    }
    return render(request, "console/pages/tenants/_status_card.html", context)
```

### FASE 4: Tarea Celery

**Ubicación**: `apps/public/tenants/tasks.py` → `onboard_tenant_task()`

**Decorador**: `@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)`

**Proceso**:
1. ✅ Asegurar esquema `public`: `connection.set_schema_to_public()`
2. ✅ Llamar servicio: `crear_tenant(nombre, schema_name, admin_user_id)`
3. ✅ Actualizar dominio si se proporcionó uno explícito
4. ✅ Retornar resultado: `{"client_id": ..., "schema_name": ..., "domain": ..., "login_url": ...}`

**Código crítico**:
```python
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def onboard_tenant_task(self, nombre, schema_name, admin_user_id, dominio=None):
    connection.set_schema_to_public()
    
    try:
        tenant, domain, login_url = crear_tenant(
            nombre=nombre,
            schema_name=schema_name,
            admin_user_id=admin_user_id
        )
        # ... actualizar dominio si es necesario ...
        return {"client_id": tenant.id, ...}
    except Exception as ex:
        logger.error(f"Error creando tenant: {ex}", exc_info=True)
        raise  # ← Esto marca la tarea como FAILURE
```

### FASE 5: Servicio de Onboarding

**Ubicación**: `apps/services/onboarding/empresa_service.py` → `crear_tenant()`

**Proceso**:
1. ✅ Validar `schema_name` con `validate_schema_name()`
2. ✅ Verificar que `schema_name` no exista
3. ✅ Obtener usuario admin: `User.objects.get(pk=admin_user_id)`
4. ✅ **Crear Client**: `Client.objects.create(...)` → Dispara señal `post_save`
5. ✅ **Señal crea Domain automáticamente** (ver `apps/public/tenants/signals.py`)
6. ✅ Obtener Domain creado: `Domain.objects.filter(tenant=client, is_primary=True).first()`
7. ✅ Ejecutar migraciones: `call_command("migrate_schemas", "--schema", schema_name, ...)`
8. ✅ Crear TenantMembership: `TenantMembership.objects.create(...)`
9. ✅ Retornar: `(client, domain, login_url)`

**Código crítico**:
```python
@transaction.atomic
def crear_tenant(nombre, schema_name, admin_user_id, ...):
    # Validaciones...
    admin = User.objects.get(pk=admin_user_id)
    
    # Crear Client (dispara señal post_save que crea Domain)
    client = Client(
        schema_name=schema_normalized,
        nombre=nombre.strip(),
        auto_create_schema=True
    )
    client.save()  # ← Dispara señal
    
    # Obtener Domain creado por señal
    domain = Domain.objects.filter(tenant=client, is_primary=True).first()
    if not domain:
        raise ValidationError("No se pudo crear el dominio principal")
    
    # Migraciones
    call_command("migrate_schemas", "--schema", schema_normalized, ...)
    
    # Membresía
    TenantMembership.objects.create(client=client, user=admin, rol="ADMIN", ...)
    
    return client, domain, login_url
```

### FASE 6: Señal Post-Save

**Ubicación**: `apps/public/tenants/signals.py` → `create_client_domain()`

**Proceso**:
1. Se dispara automáticamente cuando se crea un `Client`
2. Crea `Domain` automáticamente basado en `schema_name`
3. Si `schema_name` contiene punto (FQDN), usa el schema_name como dominio
4. Si no, construye: `{schema_name}.{TENANT_DOMAIN_BASE}`

**Código crítico**:
```python
@receiver(post_save, sender=Client)
def create_client_domain(sender, instance, created, **kwargs):
    if created:
        if '.' in instance.schema_name:
            domain_name = instance.schema_name
        else:
            domain_name = f"{instance.schema_name}.{settings.TENANT_DOMAIN_BASE}"
        
        Domain.objects.create(
            domain=domain_name,
            tenant=instance,
            is_primary=True
        )
```

## 🔴 Diagnóstico: ¿Por qué se queda en PENDING?

### Síntoma

```
Estado: PENDING
⏳ Creación en progreso...
Por favor espera mientras se configura el tenant.
```

### Causas Posibles

#### 1. ❌ Celery Worker No Está Corriendo

**Síntoma**: La tarea se encola pero nunca se ejecuta.

**Diagnóstico**:
```bash
# Verificar workers activos
docker-compose ps celery
# o
ps aux | grep celery

# Verificar logs
docker-compose logs celery
```

**Solución**:
```bash
# Iniciar worker
docker-compose up -d celery
# o
celery -A config worker -l info
```

#### 2. ❌ Broker (Redis) No Está Disponible

**Síntoma**: La tarea no se puede encolar.

**Diagnóstico**:
```bash
# Verificar Redis
docker-compose ps redis
redis-cli ping  # Debe responder "PONG"
```

**Solución**:
```bash
docker-compose up -d redis
```

#### 3. ❌ Tarea No Se Encoló Correctamente

**Síntoma**: `task.id` existe pero la tarea no aparece en las colas.

**Diagnóstico**:
```python
from celery.result import AsyncResult
result = AsyncResult(task_id)
print(result.state)  # PENDING
print(result.info)   # None
```

**Solución**: Verificar que `onboard_tenant_task.delay()` se ejecutó sin errores.

#### 4. ❌ Worker SobreCargado

**Síntoma**: Worker está procesando otras tareas y no puede atender esta.

**Diagnóstico**:
```python
from celery import current_app
inspect = current_app.control.inspect()
active = inspect.active()
# Ver cuántas tareas están activas
```

**Solución**: Aumentar número de workers o esperar.

#### 5. ❌ Error Silencioso en la Tarea

**Síntoma**: La tarea se ejecuta pero falla sin reportar error.

**Diagnóstico**:
```bash
# Ver logs de Celery
docker-compose logs celery | grep -i error
docker-compose logs celery | grep <task_id>
```

**Solución**: Revisar logs y corregir el error.

## 🛠️ Herramientas de Diagnóstico

### Comando de Management

```bash
python manage.py diagnostico_tenant <task_id>
```

Ejemplo:
```bash
python manage.py diagnostico_tenant 261514e4-35d4-4e2d-87d4-09b01f702565
```

### Script Python Directo

```python
from celery.result import AsyncResult
from apps.public.tenants.models import Client, Domain

task_id = "261514e4-35d4-4e2d-87d4-09b01f702565"
result = AsyncResult(task_id)

print(f"Estado: {result.state}")
print(f"Listo: {result.ready()}")
print(f"Info: {result.info}")
print(f"Traceback: {result.traceback}")
```

### Verificación Manual

1. **Verificar Celery**:
   ```bash
   docker-compose exec web celery -A config inspect active
   ```

2. **Verificar Redis**:
   ```bash
   docker-compose exec redis redis-cli ping
   ```

3. **Verificar Logs**:
   ```bash
   docker-compose logs -f celery
   ```

## 📊 Flujo de Estados de Celery

```
PENDING → STARTED → SUCCESS
              ↓
           FAILURE
              ↓
           RETRY (si autoretry_for está configurado)
```

- **PENDING**: Tarea esperando ser ejecutada
- **STARTED**: Tarea en ejecución
- **SUCCESS**: Tarea completada exitosamente
- **FAILURE**: Tarea falló
- **RETRY**: Tarea en reintento

## ✅ Checklist de Verificación

- [ ] Celery worker está corriendo
- [ ] Redis está disponible
- [ ] La tarea se encoló correctamente (`task.id` existe)
- [ ] No hay errores en logs de Celery
- [ ] El worker no está sobrecargado
- [ ] La tarea está registrada (`onboard_tenant_task`)
- [ ] No hay problemas de conexión a la base de datos
- [ ] El esquema `public` existe y es accesible

## 🔧 Soluciones Rápidas

### Reiniciar Todo el Stack

```bash
docker-compose down
docker-compose up -d
```

### Reiniciar Solo Celery

```bash
docker-compose restart celery
```

### Limpiar Colas de Celery

```bash
docker-compose exec web celery -A config purge
```

### Ver Tareas en Cola

```bash
docker-compose exec web celery -A config inspect scheduled
docker-compose exec web celery -A config inspect reserved
```

## 📝 Notas Importantes

1. **La tarea usa `@shared_task`**: Puede ejecutarse desde cualquier worker
2. **La tarea tiene `autoretry_for=(Exception,)`**: Reintentará automáticamente en caso de error
3. **La tarea usa `connection.set_schema_to_public()`**: Asegura que corre en el esquema correcto
4. **El servicio usa `@transaction.atomic`**: Garantiza atomicidad de la operación

## 🎯 Próximos Pasos

Si la tarea sigue en PENDING después de verificar todo:

1. Ejecutar diagnóstico: `python manage.py diagnostico_tenant <task_id>`
2. Revisar logs: `docker-compose logs celery | grep <task_id>`
3. Verificar configuración de Celery en `config/celery.py`
4. Verificar configuración de broker en `config/settings.py`
5. Considerar crear la tarea manualmente para probar:
   ```python
   from apps.public.tenants.tasks import onboard_tenant_task
   result = onboard_tenant_task.delay(
       nombre="Test",
       schema_name="test",
       admin_user_id=1
   )
   print(result.id)
   ```

---

## 🔧 Solución: Problema de 404 por Dominios No Resueltos

### ❌ Problema Original

Cuando se accede a un tenant privado (ej: `http://cliente.localhost:8000/`), el sistema devuelve un 404 porque `django-tenants` no resuelve el dominio correctamente, provocando un fallback al esquema `public` (`config.urls_public`) que no contiene las rutas del tenant.

**Causa Raíz:**
- `django-tenants` requiere coincidencia exacta del host en la tabla `tenants_domain`
- En desarrollo, el navegador envía el hostname sin puerto (ej: `cliente.localhost`)
- Si el dominio con puerto no existe en la BD, `django-tenants` no resuelve el tenant
- Resultado: Redirección al esquema público → 404

### ✅ Solución Implementada

#### 1. Comando de Reparación de Dominios

**Archivo**: `apps/public/tenants/management/commands/fix_tenant_domains.py`

**Función**: Garantiza que todos los tenants tengan registrados TODAS las variantes de dominios necesarias.

**Características**:
- Crea dominio sin puerto (producción/local): `{schema}.localhost` (is_primary=True)
- Crea dominio con puerto (desarrollo): `{schema}.localhost:8000` (is_primary=False)
- Opción `--force` para recrear dominios existentes
- Opción `--schema` para procesar un tenant específico
- Opción `--port` para especificar puerto personalizado

**Uso**:
```bash
# Reparar todos los tenants
python manage.py fix_tenant_domains

# Con opciones
python manage.py fix_tenant_domains --force  # Recrear dominios existentes
python manage.py fix_tenant_domains --port 8000  # Especificar puerto
python manage.py fix_tenant_domains --schema cliente  # Procesar solo un tenant
```

**Ejemplo de Salida**:
```
🔧 REPARACIÓN DE DOMINIOS DE TENANTS
======================================================================
📊 Procesando 3 tenant(s)...

  🔍 Procesando tenant: cliente (Cliente S.A.)
    ✅ Creado dominio principal: cliente.localhost (is_primary=True)
    ✅ Creado dominio con puerto: cliente.localhost:8000 (is_primary=False)

📊 RESUMEN DE REPARACIÓN
======================================================================
  Total de tenants procesados: 3
  ✅ Dominios creados: 6
  ⏭️  Dominios omitidos: 0
```

#### 2. Configuración de Enrutamiento Privado

**Archivo**: `config/urls_tenant.py`

**Cambios Implementados**:
- ✅ Ruta raíz blindada: `path('', include('apps.tenant.landing.urls'))`
- ✅ Eliminada referencia a `admin/login/` (ya no es necesaria)
- ✅ Documentación actualizada con arquitectura API-First

**Estructura Final**:
```python
urlpatterns = [
    # 1. Ruta Raíz - Landing Page del Tenant (ÚNICA ENTRADA)
    path('', include('apps.tenant.landing.urls')),
    
    # 2. Dashboard Privado
    path('dashboard/', include('apps.tenant.dashboard.urls', namespace='tenant_dashboard')),
    
    # 3. Admin oculto
    path('admin/', tenant_admin_trap, name='tenant-admin-trap'),
    path('soporte-tecnico-seguro/', tenant_admin_site.urls),
    
    # 4. APIs del Tenant
    path('api/v1/', include('config.api_urls')),
    path('api/v1/landing/', include('apps.tenant.landing.api.urls', namespace='tenant_landing_api')),
    
    # 5. Autenticación JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # ...
]
```

#### 3. Configuración Global de LOGIN_URL

**Archivo**: `config/settings.py`

**Configuración**:
```python
# ⚠️ CRÍTICO: URL de login para tenants privados
# Esta configuración asegura que @login_required nunca redirija a /admin/login/ en tenants privados
# En tenants privados: /login/ -> TenantLoginView
# En esquema público: /login/ -> /admin/login/ (redirección en config/urls.py)
LOGIN_URL = '/login/'  # ✅ FORZADO: URL relativa que se resuelve según el contexto
```

**Comportamiento**:
- En público: `/login/` → `/admin/login/`
- En privado: `/login/` → `TenantLoginView`

---

## 🏗️ Arquitectura API-First (Refactorización Completa)

### Objetivo

Migrar el módulo de Landing/Login hacia un modelo **API-First** estricto, donde las vistas HTML son ligeras y consumen una API centralizada.

### Estructura Final

```
apps/tenant/landing/
├── api/
│   ├── serializers.py      # Lógica de negocio (validación, membresía)
│   ├── views.py            # Endpoints REST (APIView)
│   └── urls.py             # Rutas de API (/api/v1/landing/)
├── views.py                # Vistas HTML ligeras (solo renderizado)
├── urls.py                 # Rutas HTML (/, /login/, /logout/)
└── forms.py                # (Deprecado - lógica movida a serializers)
```

### Componentes

#### A. Serializers (`api/serializers.py`)

**`TenantLoginSerializer`**:
- ✅ Valida `username` y `password`
- ✅ Valida `TenantMembership` activa usando `connection.set_schema_to_public()`
- ✅ Verifica que el `Client` esté activo
- ✅ Distingue entre "credenciales inválidas" y "sin membresía"

**Código Crítico**:
```python
def validate(self, attrs):
    # Autenticar contra backends
    user = authenticate(request=request, username=username, password=password)
    
    if user is None:
        # Distinguir entre credenciales inválidas y sin membresía
        user = self._get_user_by_identifier(username)
        if user and user.check_password(password):
            raise ValidationError("Tu cuenta existe, pero no tienes acceso a esta empresa.")
        raise ValidationError("Nombre de usuario o contraseña incorrectos.")
    
    # Validar membresía
    self._validate_membership(user, tenant)
    
    attrs["user"] = user
    return attrs
```

#### B. API Views (`api/views.py`)

**`TenantLoginAPIView`**:
- ✅ Endpoint público (`AllowAny`)
- ✅ Recibe POST con credenciales
- ✅ Usa `TenantLoginSerializer` para validar
- ✅ Ejecuta `login(request, user)` para establecer sesión
- ✅ Retorna 200 OK con URL de redirección

**Código Crítico**:
```python
class TenantLoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = TenantLoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data["user"]
        login(request, user)  # Establece sesión (cookie)
        
        return Response({
            "detail": "Login exitoso.",
            "redirect_url": reverse("tenant_dashboard:index")
        }, status=status.HTTP_200_OK)
```

#### C. Vistas HTML Ligeras (`views.py`)

**`TenantLandingView`**:
- ✅ Solo renderiza template `tenant/landing/index.html`
- ✅ Redirige a `/dashboard/` si está autenticado
- ✅ NO contiene lógica de negocio

**`TenantLoginView`**:
- ✅ Renderiza template `tenant/landing/login.html`
- ✅ POST opcional usa `TenantLoginSerializer` (compatibilidad sin JS)
- ✅ El frontend debe usar la API para autenticación

**Código Crítico**:
```python
class TenantLandingView(TemplateView):
    template_name = 'tenant/landing/index.html'
    
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(reverse('tenant_dashboard:index'))
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Solo URLs de API - el frontend consume las APIs
        context['api_info_url'] = reverse('tenant_landing_api:info')
        context['api_login_url'] = reverse('tenant_landing_api:login')
        return context
```

#### D. URLs

**`apps/tenant/landing/urls.py`**:
```python
app_name = 'tenant_landing'

urlpatterns = [
    path('', views.TenantLandingView.as_view(), name='index'),
    path('login/', views.TenantLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
]
```

**`apps/tenant/landing/api/urls.py`**:
```python
app_name = "tenant_landing_api"

urlpatterns = [
    path("info/", LandingInfoView.as_view(), name="info"),
    path("auth/login/", TenantLoginAPIView.as_view(), name="login"),
]
```

### Flujo Completo (API-First)

```
1. Usuario accede a http://cliente.localhost:8000/
   ↓
2. django-tenants resuelve el dominio → carga TENANT_URLCONF
   ↓
3. TenantLandingView.render() → Template HTML
   ↓
4. Template carga JavaScript → Consume /api/v1/landing/info/
   ↓
5. Usuario hace clic en "Login" → Template consume /api/v1/landing/auth/login/
   ↓
6. TenantLoginAPIView valida con TenantLoginSerializer
   ↓
7. Si válido: login(request, user) → Redirige a /dashboard/
```

---

## ✅ Checklist de Verificación Post-Implementación

### Dominios

- [ ] Ejecutar `python manage.py fix_tenant_domains`
- [ ] Verificar que cada tenant tenga dominio sin puerto (is_primary=True)
- [ ] Verificar que cada tenant tenga dominio con puerto en desarrollo (is_primary=False)
- [ ] Probar acceso: `http://cliente.localhost:8000/` → Debe mostrar landing page (NO 404)

### Enrutamiento

- [ ] Verificar que `config/urls_tenant.py` tenga ruta raíz: `path('', include('apps.tenant.landing.urls'))`
- [ ] Verificar que no haya referencias a `admin/login/` en `urls_tenant.py`
- [ ] Verificar que `LOGIN_URL = '/login/'` en `settings.py`

### API-First

- [ ] Verificar que `TenantLoginSerializer` tenga lógica completa de validación
- [ ] Verificar que `TenantLoginAPIView` use el serializer y ejecute `login()`
- [ ] Verificar que `TenantLandingView` y `TenantLoginView` sean ligeras (solo renderizado)
- [ ] Probar API: `curl -X POST http://cliente.localhost:8000/api/v1/landing/auth/login/ -d '{"username":"...","password":"..."}'`

### Testing

- [ ] Probar acceso a tenant: `http://cliente.localhost:8000/` → Landing page
- [ ] Probar login HTML: `http://cliente.localhost:8000/login/` → Formulario de login
- [ ] Probar login API: POST a `/api/v1/landing/auth/login/` → Retorna 200 OK
- [ ] Verificar que NO redirija a `/admin/login/` en ningún caso

---

## 📚 Referencias

- **Comando de Reparación**: `apps/public/tenants/management/commands/fix_tenant_domains.py`
- **Configuración de URLs**: `config/urls_tenant.py`
- **Serializers**: `apps/tenant/landing/api/serializers.py`
- **API Views**: `apps/tenant/landing/api/views.py`
- **Vistas HTML**: `apps/tenant/landing/views.py`
- **Configuración Global**: `config/settings.py` (LOGIN_URL)
