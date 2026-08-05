# Django Tenants (django-tenants) — Playbook Normalizado para SINTEL

**Objetivo:** Tener una referencia “operativa” y consistente para diagnosticar y resolver problemas de **multi-tenancy por schemas** (PostgreSQL) en SINTEL: routing por dominio, URLConf público vs tenant, migraciones por esquema, y testing robusto.

## Fuentes oficiales (consulta cuando haya dudas)

- **Documentación oficial (ReadTheDocs):** `https://django-tenants.readthedocs.io/`
- **Repositorio oficial (GitHub):** `https://github.com/django-tenants/django-tenants`

> Nota: Este playbook NO copia la documentación; la **normaliza** en reglas y checklists aplicables a este repo.

---

## 0) Modelo mental (SINTEL)

En SINTEL hay **dos mundos**:

- **Schema `public`**: “global/shared” (gestión de tenants, dominios, usuarios globales, catálogos DIAN, etc.)
- **Schema por tenant** (ej. `acme`, `empresa1`, etc.): “privado” (empresa, landing privada, dashboard, facturas, contabilidad…)

**Regla de oro:** si el middleware no identifica el tenant por `Host`, caes al mundo `public` → se usa `ROOT_URLCONF` → rutas tenant (p.ej. `/dashboard/`) pueden dar `404`.

---

## 1) Invariantes de configuración (lo que NO se negocia)

Valida en `config/settings.py`:

- **Backend DB**: `ENGINE = "django_tenants.postgresql_backend"`
- **Router**: `DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)`
- **Apps**:
  - `SHARED_APPS`: apps que viven en `public` (incluye `django_tenants` primero).
  - `TENANT_APPS`: apps que viven por tenant.
  - `INSTALLED_APPS = SHARED_APPS + (TENANT_APPS sin duplicados)`
- **Middleware**:
  - `django_tenants.middleware.main.TenantMainMiddleware` debe ir **PRIMERO**.
- **URLConf**:
  - `ROOT_URLCONF = "config.urls_public"`
  - `TENANT_URLCONF = "config.urls_tenant"`
- **Modelos**:
  - `TENANT_MODEL = "tenants.Client"`
  - `TENANT_DOMAIN_MODEL = "tenants.Domain"`

Checklist rápido:

- Si algo se “ve” como public cuando debería ser tenant → sospecha de **`Host`/dominio** + `TenantMainMiddleware`.

---

## 2) Routing por dominio (Host → tenant)

`django-tenants` decide el tenant usando el **Host** (dominio) de la request.

### Síntomas típicos de routing incorrecto

- `/dashboard/` devuelve `404` en tests o en entorno local.
- El template/handler que se ejecuta es el de `public`, no el de tenant.
- DRF devuelve HTML de `404` en vez de JSON del endpoint tenant.

### Diagnóstico (lo primero que revisas)

- ¿El dominio existe en `tenants_domain` y apunta a un `Client`?
- ¿El request trae `Host` correcto?
  - En tests: `Client(HTTP_HOST=...)` y `APIClient(HTTP_HOST=...)`.
  - En navegador: dominio real (subdominio) o uno de los dominios permitidos.

### Regla práctica para SINTEL

- **Toda request tenant debe tener `HTTP_HOST` del tenant** (p.ej. `acme.sintel.net.co` o el dominio que tengas en `Domain`).

---

## 3) Migraciones (schema-aware)

### Principio

- **Migraciones de apps en `SHARED_APPS`** se aplican al schema `public`.
- **Migraciones de apps en `TENANT_APPS`** se aplican a cada schema de tenant.

### Comandos operativos (docker compose)

Crear migraciones:

- `docker compose run --rm web python manage.py makemigrations`

Aplicar migraciones:

- **Solo `public` (shared):** `docker compose run --rm web python manage.py migrate_schemas --shared`
- **Tenants (según flags/config):** `docker compose run --rm web python manage.py migrate_schemas`

> En SINTEL ya existe un flujo que crea tenant público y dominios (ver `setup_public_tenant`).

### Pitfall clásico

Ejecutar `python manage.py migrate` “a secas” en un proyecto multi-tenant suele ser ambiguo.
En SINTEL, prioriza `migrate_schemas` para evitar “aplicar en el schema equivocado”.

---

## 4) Testing robusto (la regla: TenantTestCase)

### Por qué falla el test “normal” de Django

Porque no crea ni enruta schemas/domains como lo hace `django-tenants`.

### Regla para SINTEL

- **Toda prueba tenant** hereda de `django_tenants.test.cases.TenantTestCase` (vía `SintelTenantTestCase`).
- En tests, el routing depende de `HTTP_HOST` (si falta, cae a `public`).

### Setup mínimo que SIEMPRE debes tener

En `SintelTenantTestCase.setUp()` (resumen conceptual):

- Crear tenant + domain (lo hace `TenantTestCase`).
- Crear usuario global + `TenantMembership` en schema `public`.
- Crear clientes con `HTTP_HOST` apuntando al dominio del tenant:
  - `self.client = Client(HTTP_HOST=self.domain.domain)`
  - `self.api_client = APIClient(HTTP_HOST=self.domain.domain)`

### Síntoma más común y su causa raíz

- **Test espera 302 a login pero recibe 404**
  - **Causa raíz**: `HTTP_HOST` faltante → se usa `ROOT_URLCONF` (public) → `/dashboard/` no existe → `404`.

---

## 5) Aislamiento de datos (cross-tenant isolation)

### Regla de oro

- Los modelos tenant (`apps.tenant.*`) **no deben ser accesibles** desde `public`.

### Cómo validarlo en tests

- Crear dato en schema tenant (normal).
- Cambiar a schema `public` y:
  - o bien `ProgrammingError` (tabla no existe en public),
  - o bien count/consulta retorna 0 (dependiendo de cómo esté migrado/modelado).

Pitfall:

- Si atrapas un `ProgrammingError` dentro de una transacción, puede quedar “aborted” → si necesitas continuar en el mismo test, haz `connection.rollback()`.

---

## 6) Troubleshooting “rápido” (80/20)

### “Me da 404 pero la ruta existe”

- **Confirmar `HTTP_HOST`** (tests y requests reales).
- Confirmar el dominio en `Domain`.
- Confirmar `TenantMainMiddleware` primero.
- Confirmar `TENANT_URLCONF` correcto.

### “TemplateDoesNotExist en tenants”

- Si el template vive en un app tenant, esa app debe estar en `TENANT_APPS`.
- En SINTEL: `apps.tenant.core` debe estar en `TENANT_APPS` si allí viven templates/handlers tenant.

### “makemigrations/migrate falla por ImageField”

- Pillow debe estar instalado (`Pillow` en `requirements.txt`).

---

## 7) Comandos de reset (desarrollo)

### Linux/Mac (migraciones)

```bash
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
```

### Windows PowerShell (migraciones)

```powershell
Get-ChildItem -Path . -Recurse -Filter "*.py" |
  Where-Object { $_.FullName -like "*\migrations\*.py" -and $_.Name -ne "__init__.py" } |
  Remove-Item -Force

Get-ChildItem -Path . -Recurse -Filter "*.pyc" |
  Where-Object { $_.FullName -like "*\migrations\*.pyc" } |
  Remove-Item -Force
```

### Docker DB limpia (volúmenes)

```bash
docker compose down -v
docker compose up -d db redis
```

---

## 8) Convenciones SINTEL (para evitar regresiones)

- **Nunca** escribir tests tenant con `TestCase`/`APITestCase` “planos”.
- En tests tenant, **siempre** fijar `HTTP_HOST`.
- Cambios en `TENANT_APPS`/`SHARED_APPS` se acompañan de:
  - revisión de migraciones (¿dónde vive la tabla?),
  - revisión de templates (¿quién los carga?),
  - smoke-test de routing (public vs tenant).

