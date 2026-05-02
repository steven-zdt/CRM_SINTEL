# 📐 Reglas de Alineación - Proyecto SINTEL

**Versión:** 1.0  
**Fecha:** 2026-01-17  
**Estado:** ⚠️ ACTIVO - OBLIGATORIO

---

## 🎯 REGLA FUNDAMENTAL

> **LA ESTRUCTURA DEL PROYECTO (directorios, archivos, dependencias, tecnologías, configuración) DEBE ESTAR SIEMPRE ALINEADA CON `arquitectura_general.md` (ubicado en `documentacion/`)**

Este documento es la **fuente única de verdad**. Cualquier discrepancia debe resolverse:
1. **Actualizando el código** para que coincida con la documentación, O
2. **Actualizando la documentación** si hay una razón arquitectónica válida

---

## 📋 Checklist de Alineación Obligatorio

### ✅ Estructura de Directorios

**DEBE coincidir exactamente con `arquitectura_general.md` sección "Estructura de Directorios":**

```
sintel_project/
├── apps/
│   ├── public/              ✅ REQUERIDO
│   │   ├── tenants/        ✅ REQUERIDO
│   │   ├── accounts/       ✅ REQUERIDO
│   │   └── impuestos/      ✅ REQUERIDO
│   ├── tenant/             ✅ REQUERIDO
│   │   ├── empresa/        ✅ REQUERIDO
│   │   ├── facturas/       ✅ REQUERIDO
│   │   └── contabilidad/   ✅ REQUERIDO
│   ├── services/           ✅ REQUERIDO
│   │   ├── maildigester/   ✅ REQUERIDO
│   │   └── xml_parser/     ✅ REQUERIDO
│   └── documentacion/      ✅ REQUERIDO (ÚNICA UBICACIÓN: documentacion/)
│       └── arquitectura_general.md  ✅ FUENTE ÚNICA DE VERDAD
├── config/                 ✅ REQUERIDO
├── manage.py               ✅ REQUERIDO
├── requirements.txt        ✅ REQUERIDO
├── docker-compose.yaml     ✅ REQUERIDO
├── Dockerfile              ✅ REQUERIDO
└── .env.sample             ✅ REQUERIDO
```

### ✅ Dependencias (requirements.txt)

**DEBE coincidir con Stack Tecnológico en `arquitectura_general.md`:**

- ✅ `django>=5.0,<5.1`
- ✅ `django-tenants>=3.7.0`
- ✅ `psycopg>=3.1.0` (v3 - obligatorio)
- ✅ `djangorestframework` (DRF - API-first)
- ✅ `django-filter`
- ✅ `celery[redis]`
- ✅ `redis`
- ✅ `python-dotenv`

**NO agregar dependencias sin actualizar la documentación primero.**

### ✅ Configuración Docker

**docker-compose.yaml DEBE tener:**
- ✅ Servicio `db` con `postgres:16`
- ✅ Servicio `redis` con `redis:7-alpine`
- ✅ Servicio `web` con build desde Dockerfile
- ✅ Comando: `migrate_schemas --shared && setup_public_tenant || true && runserver`

**Dockerfile DEBE tener:**
- ✅ Base: `python:3.12-slim`
- ✅ Dependencias: `gcc`, `libpq-dev`
- ✅ Variables: `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`

### ✅ Configuración Django (settings.py)

**SHARED_APPS DEBE incluir (en orden):**
1. ✅ `django_tenants` (PRIMERO)
2. ✅ `apps.public.tenants`
3. ✅ `apps.public.accounts`
4. ✅ `apps.public.impuestos`
5. ✅ Django contrib apps (contenttypes, auth, admin, sessions, messages, staticfiles)

**TENANT_APPS DEBE incluir:**
1. ✅ `apps.tenant.empresa`
2. ✅ `apps.tenant.facturas`
3. ✅ `apps.tenant.contabilidad`
4. ✅ `rest_framework` (DRF - API-first)
5. ✅ `django_filters`

**Configuración OBLIGATORIA:**
- ✅ `TENANT_MODEL = "tenants.Client"`
- ✅ `TENANT_DOMAIN_MODEL = "tenants.Domain"`
- ✅ `AUTH_USER_MODEL = "accounts.User"`
- ✅ `ENGINE = "django_tenants.postgresql_backend"`
- ✅ `TenantMainMiddleware` como PRIMER middleware
- ✅ `DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)`

### ✅ Modelos Implementados

**apps.public.tenants:**
- ✅ `Client` (TenantMixin) con `auto_create_schema = True`
- ✅ `Domain` (DomainMixin)

**apps.public.accounts:**
- ✅ `User` (AbstractUser)
- ✅ Email único y obligatorio
- ✅ Generación automática de username desde email

**apps.public.impuestos:**
- ✅ `TipoImpuesto`
- ✅ `TarifaIVA`
- ✅ `ConceptoRetencion`
- ✅ `CodigoTributario`
- ✅ `ActividadEconomica`

---

## 🔄 Proceso de Alineación

### Al Agregar un Nuevo Componente

1. **PRIMERO:** Actualizar `arquitectura_general.md`
2. **SEGUNDO:** Implementar según la documentación
3. **TERCERO:** Verificar alineación con este checklist
4. **CUARTO:** Actualizar este documento si es necesario

### Al Modificar un Componente Existente

1. **Verificar impacto** en `arquitectura_general.md`
2. **Actualizar documentación** si el cambio es arquitectónico
3. **Implementar el cambio** en el código
4. **Verificar alineación** con este checklist

### Al Detectar una Discrepancia

1. **Identificar fuente de verdad:** ¿Documentación o código?
2. **Si documentación es correcta:** Actualizar código
3. **Si código es correcto:** Actualizar documentación
4. **Documentar razón** del cambio

---

## 📝 Verificación Obligatoria

### Antes de cada Release

- [ ] Estructura de directorios alineada
- [ ] Dependencias en requirements.txt alineadas
- [ ] Configuración Docker alineada
- [ ] settings.py alineado
- [ ] Modelos implementados según documentación
- [ ] `arquitectura_general.md` actualizado

### Antes de cada Commit Importante

- [ ] Cambios documentados en `arquitectura_general.md`
- [ ] Estructura sigue la documentación
- [ ] Dependencias actualizadas si es necesario

---

## 🚨 Discrepancias Conocidas

| Fecha | Componente | Discrepancia | Resolución | Estado |
|-------|-----------|--------------|------------|--------|
| 2026-01-17 | documentacion/ | Duplicado en raíz | Consolidado en documentacion/ (raíz) | ✅ Resuelto |

---

## 📚 Referencias

- **Fuente Única de Verdad:** `arquitectura_general.md` (ubicado en `documentacion/`)
- **Documento Base Original:** `aquitectura_crm_sintel_v_1_operativo.docx`

---

## ✅ Estado Actual

**Última Verificación:** 2026-01-17  
**Estado:** ✅ ALINEADO

Todos los componentes verificados están alineados con la documentación.

---

**⚠️ IMPORTANTE:** Esta regla es OBLIGATORIA. Cualquier cambio que no esté alineado con la documentación debe ser corregido o documentado antes de ser mergeado.

**Mantenido por:** Equipo de Desarrollo SINTEL  
**Revisar:** Antes de cada release y después de cambios arquitectónicos
