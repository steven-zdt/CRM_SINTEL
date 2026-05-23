# Marco de Pruebas Multi-Tenant y Service Layer (SINTEL v3.7+)

Este documento establece las directrices y estructuras obligatorias para la creación y mantenimiento de pruebas unitarias y de integración (smoke tests, CRUD, enrutamiento) en el ERP SINTEL. Su objetivo es evitar errores comunes de integridad de datos y bloqueos de seguridad que surgen de la evolución hacia modelos anémicos y aislamiento estricto (Zero Trust).

## 1. Principios Fundamentales del Testing en SINTEL

Con la migración a la v3.7+ (Feature-Sliced Design y Service Layer), los modelos de la base de datos se han vuelto **Anémicos** (solo definen estructura). Toda la lógica de negocio (como cálculos de totales, validaciones complejas y verificación de seguridad) reside exclusivamente en la capa de servicios (`services.py`).

### Reglas de Oro para Pruebas
1. **Modelos Anémicos:** Al usar `Model.objects.create()` en las pruebas, la lógica de `save()` NO calculará totales ni derivará información. Todos los campos obligatorios (`neto_pagar`, `total`, etc.) deben ser proporcionados de manera explícita en el payload del test.
2. **SSoT (Single Source of Truth):** Todas las entidades deben estar vinculadas a la misma instancia de `Empresa`. El `empresa_id` es el pilar del aislamiento.
3. **Validación Dura (Choices):** Los campos con opciones (`choices`) aplican validación estricta desde la base de datos (Ej: `eps="EPS004"` no `"SURA"`). Siempre consulta `choices.py`.
4. **Middlewares de Seguridad (Zero Trust):** Todo endpoint requiere no solo autenticación, sino autorización en el esquema actual mediante `TenantMembership` (esquema público) y `TenantProfile` (esquema tenant).

---

## 2. Estructura Obligatoria del Entorno (`conftest.py`)

Para evitar los errores `403 Forbidden` al acceder a los endpoints API, los clientes de prueba deben emular la autenticación de doble capa de SINTEL.

### Fixture `admin_user`
El archivo `conftest.py` de cada app DEBE incluir o heredar un fixture que aprovisione los permisos requeridos:

```python
import pytest
from django_tenants.utils import schema_context

@pytest.fixture
def admin_user(django_user_model, tenant):
    """
    Crea un usuario administrador aprovisionado con TenantMembership 
    y TenantProfile para evadir los bloqueos 403 del middleware de seguridad.
    """
    user = django_user_model.objects.create_user(
        username="admin_test",
        password="password123",
        email="admin@test.com"
    )
    
    # 1. Membresía Pública
    from apps.public.tenants.models import TenantMembership
    TenantMembership.objects.create(
        client=tenant,
        user=user,
        rol='ADMIN',
        is_active=True
    )
    
    # 2. Perfil en el esquema del Tenant
    with schema_context(tenant.schema_name):
        from apps.tenant.empresa.models import Empresa
        from apps.tenant.perfil.models import TenantProfile
        empresa = Empresa.objects.first()
        TenantProfile.objects.create(
            user=user,
            empresa=empresa,
            rol='ADMIN'
        )
    return user
```

**Uso en pruebas:** `client.force_login(admin_user)` debe invocarse antes de cualquier petición `client.get()` o `client.post()`.

---

## 3. Prevención de Errores Comunes de Integridad (`IntegrityError`)

### Error 1: Violación de Restricciones Not-Null en Cálculos
**Causa:** Se espera que el modelo calcule campos (e.g., `neto_pagar`) automáticamente, pero esto ahora se delega a `business_service.py`.
**Solución:** Inyectar explícitamente los valores pre-calculados en `Model.objects.create()`.

```python
# INCORRECTO: Falla por null value in "neto_pagar"
Devengo.objects.create(salario_base=1000, ...) 

# CORRECTO: El test asume el rol del Service Layer al usar el ORM directamente
Devengo.objects.create(
    salario_base=Decimal("1000.00"),
    neto_pagar=Decimal("1000.00"), # Valor pre-calculado explícito
    ...
)
```

### Error 2: `invalid_choice` en Campos Estrictos
**Causa:** Uso de nombres de display (ej. `"SURA"`) en lugar de las llaves del catálogo (ej. `"EPS004"`).
**Solución:** Referenciar y utilizar las llaves exactas definidas en `choices.py` para construir los payloads y objetos ORM.

```python
# CORRECTO
Empleado.objects.create(
    eps="EPS004",   # Sura
    afp="AFP001",   # Protección
    arl="ARL002"    # ARL Sura
)
```

---

## 4. Pruebas de Aislamiento Multi-Tenant

Al implementar pruebas para verificar que un `Tenant1` no tiene acceso a los datos del `Tenant2`, sigue este patrón:

1. Utiliza `tenant_factory` para generar un `tenant2`.
2. Emplea el contexto `with schema_context(tenant2.schema_name):` para aislar la creación de registros usando el ORM.
3. Asegúrate de replicar la creación de `Empresa` en el nuevo esquema, ya que los *factories* podrían no correr las migraciones poblacionales.
4. Concede membresía al `admin_user` en el `tenant2` para que las pruebas puedan enrutar correctamente la llamada simulada al middleware `HTTP_HOST`.

```python
def test_multitenancy_isolation(client, admin_user, tenant, tenant_factory):
    tenant2 = tenant_factory(schema_name="tenant2")
    
    # ...crear datos en schema_context(tenant.schema_name)
    # ...crear datos en schema_context(tenant2.schema_name)
    
    client.force_login(admin_user)
    
    # Evaluar aislamiento mediante HTTP_HOST
    resp1 = client.get("/api/v1/ruta/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    resp2 = client.get("/api/v1/ruta/", HTTP_HOST=f"{tenant2.schema_name}.sintel.com")
    
    # Validar que resp1 NO contenga datos de resp2
```

## Resumen del Workflow de Pruebas
1. Revisar `models.py` para identificar `constraints`, `choices` y campos obligatorios (`not-null`).
2. Nunca confiar en `save()` para cálculos; proveer todos los datos vía ORM.
3. Usar `admin_user` (con `TenantProfile`) para evadir el `403 Forbidden`.
4. Utilizar `schema_context` de manera atómica por cada tenant.
