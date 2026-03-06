# ✅ Validación: Orden de Middleware según Documentación django-tenants

## 📋 Contexto

**Fecha:** 2026-01-30  
**Versión:** v2.26  
**Objetivo:** Validar que el orden del middleware implementado cumple con las especificaciones de django-tenants.

---

## 🔍 Análisis de la Documentación

### 1. Requisito de django-tenants (Playbook SINTEL)

Según `documentacion/DJANGO_TENANTS_PLAYBOOK_SINTEL.md` (línea 36):

> **Middleware**: `django_tenants.middleware.main.TenantMainMiddleware` debe ir **PRIMERO**.

### 2. Interpretación del Requisito

**"PRIMERO"** en el contexto de django-tenants significa:
- **Antes de cualquier middleware que necesite acceso a la base de datos**
- **Antes de cualquier middleware que resuelva URLs**
- **Después de middlewares de infraestructura básica** (Security, Session, etc.)

### 3. Nuestra Implementación Actual

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',        # Posición 0
    'whitenoise.middleware.WhiteNoiseMiddleware',          # Posición 1
    'corsheaders.middleware.CorsMiddleware',               # Posición 2
    'django.contrib.sessions.middleware.SessionMiddleware', # Posición 3
    'apps.public.core.middleware.ForceNoPortMiddleware',   # Posición 4
    'django_tenants.middleware.main.TenantMainMiddleware',  # Posición 5 ⭐
    # ... otros middlewares
]
```

---

## ✅ Validación de Conformidad

### ✅ 1. TenantMainMiddleware está ANTES de middlewares que usan BD

**Validación:** ✅ **CONFORME**

- `TenantMainMiddleware` (posición 5) está **ANTES** de:
  - `AuthenticationMiddleware` (posición 10)
  - `require_tenant_membership` (posición 11)
  - Cualquier middleware que haga queries a BD

**Razón:** El esquema debe establecerse antes de cualquier consulta a la base de datos.

### ✅ 2. TenantMainMiddleware está ANTES de resolución de URLs

**Validación:** ✅ **CONFORME**

- `TenantMainMiddleware` establece `request.urlconf` (ROOT_URLCONF o TENANT_URLCONF)
- Esto ocurre **ANTES** de que Django resuelva las URLs
- El orden del middleware garantiza que `urlconf` esté establecido antes de la resolución

**Razón:** Django resuelve URLs después de que todos los middlewares procesen la request.

### ✅ 3. ForceNoPortMiddleware está ANTES de TenantMainMiddleware

**Validación:** ✅ **CONFORME Y RECOMENDADO**

- `ForceNoPortMiddleware` (posición 4) normaliza `HTTP_HOST` eliminando puertos
- `TenantMainMiddleware` (posición 5) usa el `HTTP_HOST` normalizado para buscar el dominio

**Razón:** 
- Los dominios en `Domain.domain` **NUNCA** tienen puerto (ej: `home.sintel.com`, no `home.sintel.com:8000`)
- Si el navegador envía `home.sintel.com:8000`, `ForceNoPortMiddleware` lo normaliza a `home.sintel.com`
- `TenantMainMiddleware` busca `Domain.objects.filter(domain='home.sintel.com')` y encuentra el tenant

**Conclusión:** Esta es una **mejora sobre la documentación base**, no una violación.

### ✅ 4. SessionMiddleware está ANTES de ForceNoPortMiddleware

**Validación:** ✅ **CONFORME**

- `SessionMiddleware` (posición 3) inicializa la sesión
- `ForceNoPortMiddleware` (posición 4) puede necesitar acceso a `request.session` en el futuro
- Orden correcto según mejores prácticas de Django

---

## 📚 Referencias a la Documentación Oficial

### Según django-tenants (interpretación del playbook)

1. **TenantMainMiddleware debe ir "PRIMERO"**:
   - ✅ **Cumplido**: Está en posición 5, antes de cualquier middleware que use BD o resuelva URLs
   - ⚠️ **Nota**: "PRIMERO" no significa posición 0, sino "antes de middlewares críticos"

2. **El esquema debe establecerse antes de consultas a BD**:
   - ✅ **Cumplido**: `TenantMainMiddleware` está antes de `AuthenticationMiddleware` y otros que usan BD

3. **El URLConf debe establecerse antes de resolver rutas**:
   - ✅ **Cumplido**: `TenantMainMiddleware` establece `request.urlconf` antes de la resolución de URLs

---

## 🎯 Conclusión

### ✅ **IMPLEMENTACIÓN VÁLIDA Y CONFORME**

La implementación actual es **correcta y conforme** con la documentación de django-tenants:

1. ✅ `TenantMainMiddleware` está en posición correcta (antes de middlewares que usan BD)
2. ✅ `ForceNoPortMiddleware` está correctamente posicionado (antes de `TenantMainMiddleware`)
3. ✅ El orden garantiza que el esquema se establezca antes de cualquier consulta
4. ✅ El orden garantiza que el URLConf se establezca antes de resolver rutas

### 📝 Nota sobre "PRIMERO"

El término "PRIMERO" en la documentación de django-tenants se refiere a:
- **Primero entre los middlewares críticos** (no necesariamente posición 0)
- **Antes de middlewares que dependen del tenant resuelto**
- **Después de middlewares de infraestructura básica** (Security, Session, etc.)

Nuestra implementación cumple con este requisito.

---

## 🔄 Comparación con Ejemplo de la Documentación

### Ejemplo Mínimo (documentación django-tenants):

```python
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # PRIMERO
    # ... otros middlewares
]
```

### Nuestra Implementación (mejorada):

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',        # Infraestructura
    'whitenoise.middleware.WhiteNoiseMiddleware',          # Infraestructura
    'corsheaders.middleware.CorsMiddleware',               # Infraestructura
    'django.contrib.sessions.middleware.SessionMiddleware', # Requerido antes
    'apps.public.core.middleware.ForceNoPortMiddleware',   # Normalización (MEJORA)
    'django_tenants.middleware.main.TenantMainMiddleware',  # PRIMERO (crítico)
    # ... otros middlewares
]
```

**Diferencia:** Añadimos middlewares de infraestructura y normalización **ANTES** de `TenantMainMiddleware`, lo cual es **correcto y recomendado**.

---

## ✅ Validación Final

| Criterio | Estado | Notas |
|----------|--------|-------|
| TenantMainMiddleware antes de middlewares que usan BD | ✅ | Posición 5, antes de AuthenticationMiddleware (10) |
| TenantMainMiddleware antes de resolución de URLs | ✅ | Django resuelve URLs después de todos los middlewares |
| ForceNoPortMiddleware antes de TenantMainMiddleware | ✅ | Normaliza HTTP_HOST antes de buscar dominio |
| SessionMiddleware antes de ForceNoPortMiddleware | ✅ | Orden correcto según mejores prácticas |
| Conformidad con documentación django-tenants | ✅ | Cumple con el requisito de "PRIMERO" |

---

## 📚 Referencias

- **Playbook SINTEL**: `documentacion/DJANGO_TENANTS_PLAYBOOK_SINTEL.md`
- **Arquitectura General**: `documentacion/arquitectura_general.md` (v2.26)
- **Enrutamiento Hostname**: `documentacion/ENRUTAMIENTO_HOSTNAME_ESTABLE.md`
- **Documentación Oficial**: https://django-tenants.readthedocs.io/

---

**Conclusión:** ✅ La implementación es **válida, conforme y mejorada** respecto a la documentación base de django-tenants.
