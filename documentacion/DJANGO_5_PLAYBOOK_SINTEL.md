# Django 5.0.x — Playbook Normalizado (Fuente de Verdad) para Arquitectura SINTEL

**Fuente primaria (oficial, local):** `documentacion/django-readthedocs-io-en-5.0.x.pdf`  
**Fuente primaria (oficial, online):** `https://docs.djangoproject.com/en/5.0/` (misma base, navegación más fácil)

**Objetivo:** Convertir la documentación oficial de Django 5 en un conjunto de **reglas**, **decisiones arquitectónicas** y **checklists** aplicables a SINTEL (Django 5 + DRF + docker + `django-tenants`).

---

## 1) Invariantes (lo que no se negocia en SINTEL)

- **Django 5.x como base**: mantener compatibilidad con Python 3.12 en contenedor y con el stack actual.
- **Separación de responsabilidades**:
  - **`apps/services/`**: lógica de negocio “pura” (sin ORM, sin HTTP).
  - **`apps/tenant/*`**: apps privadas por tenant (datos aislados).
  - **`apps/public/*`**: apps compartidas en `public` (tenants, accounts, catálogos).
- **Settings declarativos**: evitar lógica de negocio en `settings.py`. Configurar por variables de entorno.
- **Seguridad por defecto**: todo endpoint debe tener auth/permissions explícitas (salvo whitelists públicas).

---

## 2) Ciclo Request/Response (cómo pensar problemas en producción)

En cualquier incidente, diagnostica en este orden:

- **Host / routing**: ¿la request entró al “mundo” correcto? (public vs tenant, ver playbook `DJANGO_TENANTS_PLAYBOOK_SINTEL.md`)
- **URLConf**: ¿la ruta se resuelve en `urls_public.py` o `urls_tenant.py`?
- **Middleware**: ¿qué middleware puede estar transformando la request (security, auth, CSRF, CORS)?
- **Vista / permisos**: ¿se bloqueó por auth/permissions?
- **DB / ORM**: ¿consulta lenta, N+1, tabla inexistente, schema incorrecto?

---

## 3) Configuración (settings) — patrón recomendado para SINTEL

Reglas prácticas:

- **Nunca hardcodear secretos**:
  - `SECRET_KEY` y cualquier credencial viene de `.env`/variables de entorno.
- **DEBUG**:
  - En producción: `DEBUG=False`.
  - En tests: **Django fuerza `DEBUG=False`** aunque tu config diga otra cosa (esto explica diferencias en páginas de error).
- **ALLOWED_HOSTS**:
  - En prod: mínimo dominio base + wildcard seguro (en SINTEL ya está modelado).
- **Logging**:
  - Log estructurado (nivel INFO/WARN/ERROR), sin ruido, sin datos sensibles.

Checklist al tocar `settings.py`:

- ¿Afecta `MIDDLEWARE` (orden)?
- ¿Afecta `ROOT_URLCONF`/`TENANT_URLCONF`?
- ¿Afecta `DATABASES` / `DATABASE_ROUTERS`?
- ¿Afecta `SECURE_*`, cookies, CSRF, CORS?

---

## 4) Seguridad (hardening) — lo mínimo viable para producción

En SINTEL, el baseline de seguridad incluye:

- **`SecurityMiddleware` habilitado** (ya está) y settings de seguridad revisados en modo prod.
- **Cookies**:
  - `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True` (prod).
  - `SESSION_COOKIE_HTTPONLY=True`.
  - `CSRF_TRUSTED_ORIGINS` coherente con dominios multi-tenant.
- **CSRF**:
  - No deshabilitar globalmente. Solo excepciones puntuales (y justificadas) con `csrf_exempt` y compensaciones.
- **Headers**:
  - `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD` (prod, con cuidado).
  - `SECURE_REFERRER_POLICY`, `SECURE_CONTENT_TYPE_NOSNIFF`, etc.

Regla SINTEL:

- Cualquier cambio de seguridad debe venir con **checklist de verificación** y (si aplica) tests.

---

## 5) Performance (ORM + APIs)

Reglas ORM:

- Evitar N+1:
  - usar `select_related()` / `prefetch_related()`.
- Evitar cargas de columnas innecesarias:
  - `only()` / `defer()` cuando aplica (especialmente en DataTables).
- Paginación obligatoria en listados.

Reglas DRF:

- Serializadores con **whitelist** de campos.
- Para APIs públicas: **no filtrar por “lo que no se debe”**; definir explícitamente lo permitido.

---

## 6) Testing (arquitectura de pruebas)

Reglas:

- Tests deterministas (sin depender de orden).
- Aislamiento:
  - Para multi-tenant: usar `TenantTestCase` (vía `SintelTenantTestCase`) y fijar `HTTP_HOST`.
- Preferir **tests de servicio (service-layer)** para lógica pura.
- Tests de integración para routing, auth y permisos.

Checklist cuando un test “pasa local pero falla en CI”:

- ¿Depende de `DEBUG`? (en tests suele ser `False`)
- ¿Depende del `Host`? (multi-tenant)
- ¿Depende de timezone/locale?
- ¿Depende de data global compartida?

---

## 7) Deployment (docker + Django)

SINTEL baseline:

- **`DEBUG=False` en prod**
- Servir estáticos:
  - `collectstatic` + WhiteNoise (o CDN/proxy), consistente con `STATIC_ROOT`.
- Servidor:
  - `gunicorn` (WSGI) para Django (y ASGI si se incorpora algo async real).

Checklist pre-release:

- Revisar “Deployment checklist” oficial de Django 5.0 (ver fuente online).
- Validar healthcheck básico por dominio public y por tenant.

---

## 8) Referencias cruzadas internas (SINTEL)

- Multi-tenancy: `documentacion/DJANGO_TENANTS_PLAYBOOK_SINTEL.md`
- Fuente de verdad de arquitectura: `documentacion/arquitectura_general.md`
- Seguridad HTTPS/dev: `documentacion/SOLUCION_ERROR_HTTPS.md` y `documentacion/SOLUCION_HTTPS_TENANT.md`

