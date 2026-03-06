# Fase 0: Lista de Verificación de Preparación

**Objetivo**: Dejar el proyecto listo para migrar el parseo/validación/normalización XML a un servicio general reusable (multi‑app), sin romper contratos, respetando el aislamiento por esquema, y manteniendo SSoT y Service Layer.

**Fecha de verificación**: 2026-02-09

---

## 0.1 Arquitectura & Dependencias

### ✅ SSoT de Empresa disponible (tenant-aware)

**Estado**: ✅ **COMPLETO**

- **Ubicación**: `apps/tenant/empresa/services.py` (archivo, no paquete)
- **Provider canónico**: `get_empresa_emisor_data()`
  - Retorna `Dict[str, Any]` con NIT válido
  - Lanza `EmpresaNotConfiguredError` si falta empresa/NIT
  - **Contrato**: Nunca retorna `None`; falla 422 si falta empresa/NIT
- **Excepción**: `EmpresaNotConfiguredError` definida y documentada
- **Comando de auditoría**: `apps/tenant/empresa/management/commands/audit_empresa_nit.py` existe

**Tests**: ✅ `apps/tenant/facturas/tests/test_ssot_empresa_provider.py` creado

**Import canónico verificado**:
```python
# apps/tenant/facturas/services.py
from apps.tenant.empresa.services import (
    get_empresa_emisor_data,
    EmpresaNotConfiguredError,
)
```

---

### ✅ Service Layer vigente en apps tenant

**Estado**: ✅ **COMPLETO**

- **Ubicación**: `apps/tenant/facturas/services.py`
- **Lógica centralizada**:
  - ✅ Importación UBL: `importar_ubl()`
  - ✅ Determinación de naturaleza: `_determinar_naturaleza()`
  - ✅ Idempotencia: `upsert_factura_desde_ubl()`
  - ✅ Separación de anexos: `_split_factura_payload()`
- **Sin lógica en vistas/serializers**: ✅ Confirmado
- **Sin lógica en plantillas**: ✅ Confirmado

**Patrón mantenido**: Service Layer Pattern (v2.30)

---

### ✅ API‑First + Listas Mínimas

**Estado**: ✅ **COMPLETO**

- **ListSerializer**: `FacturaListSerializer`
  - ✅ No incluye blobs (`ubl_xml`, `application_response_xml`)
  - ✅ Solo campos necesarios para tabla
  - ✅ Incluye `naturaleza` (calculada por backend)
- **DetailSerializer**: `FacturaDetailSerializer`
  - ✅ Incluye anexos bajo demanda (via `SerializerMethodField`)
  - ✅ Carga desde `FacturaAnexos` (no desde fila principal)
- **Endpoints**: JSON-only, versionado `/api/v1/...`

---

### ✅ Multi‑tenant por esquema (django‑tenants)

**Estado**: ✅ **COMPLETO**

- **Middleware**: `TenantMainMiddleware` configurado
- **Utilidades disponibles**:
  - ✅ `schema_context` (django-tenants)
  - ✅ `tenant_command` / `all_tenants_command` (si aplica)
- **Tests**: `TenantTestCase` disponible y en uso

**Ejemplo de uso**:
```python
from django_tenants.utils import schema_context
from django_tenants.test.cases import TenantTestCase
```

---

### ⚠️ Celery & Broker (Pendiente de verificación)

**Estado**: ⚠️ **REQUIERE VERIFICACIÓN MANUAL**

- **Ubicación esperada**: `config/celery.py` o similar
- **Variables requeridas**:
  - `BROKER_URL`
  - `RESULT_BACKEND`
- **Workers**: Requiere verificación manual en entorno dev/prod
- **schema_context en tareas**: Requiere verificación

**Acción requerida**: Verificar configuración de Celery y disponibilidad de workers.

---

### ✅ Rutas estáticas/JS en workspace

**Estado**: ✅ **COMPLETO**

- **Rutas relativas**: ✅ Sin `http(s)://`, sin `//` dobles
- **Orden de assets**: ✅ Loader core antes de módulos
- **Sin duplicación**: ✅ Verificado en tests
- **CSRF + credentials**: ✅ Implementado en `facturas.page.js`
- **URLs relativas**: ✅ `/api/v1/facturas/...` (sin host/protocolo)

**Tests**: ✅ `apps/tenant/core/tests/test_workspace_links_strict.py` valida enlaces estrictos y columna Naturaleza

---

## 0.2 Controles de Código

### ✅ Import canónico del SSoT (sin shadowing)

**Estado**: ✅ **COMPLETO**

- **Import correcto**: `from apps.tenant.empresa.services import ...`
- **Sin shadowing**: El paquete `services/` fue renombrado a `impl/` (si existía)
- **Archivo canónico**: `apps/tenant/empresa/services.py` es la única fuente

**Verificado en**: `apps/tenant/facturas/services.py` líneas 50-53

---

### ✅ Manejo de errores estándar en Service Layer

**Estado**: ✅ **COMPLETO**

- **Mapeo de errores**:
  - ✅ `422` (SSoT faltante/validaciones): `EmpresaNotConfiguredError`, `ValidationError`
  - ✅ `409` (duplicado/constraint): `IntegrityError`, `DuplicateNumero`
  - ✅ `413` (payload XL): `DataError`
  - ✅ `500` (inesperados): Solo para excepciones no esperables
- **Logging sobrio**: ✅ Sin volcar XML completo (solo tamaño/hash)

**Implementado en**: `apps/tenant/facturas/services.py` función `importar_ubl()`

---

### ✅ Blobs/XML fuera del modelo principal

**Estado**: ✅ **COMPLETO**

- **Modelo anexo**: `FacturaAnexos` (OneToOne con `Factura`)
  - ✅ `ubl_xml`: `TextField`
  - ✅ `application_response_xml`: `TextField`
- **Separación**: ✅ `_split_factura_payload()` previene kwargs inesperados
- **Migración**: ✅ `0010_add_factura_anexos.py` creada

**Verificado**: `Factura.objects.create(**clean_data)` nunca recibe `ubl_xml` ni `application_response_xml`

---

## 0.3 Verificaciones Automatizables

### ✅ SSoT operativo

**Tests creados**: `apps/tenant/facturas/tests/test_ssot_empresa_provider.py`

- ✅ `test_sin_empresa_lanza`: Valida que sin Empresa lanza `EmpresaNotConfiguredError`
- ✅ `test_sin_nit_lanza`: Valida que sin NIT lanza excepción
- ✅ `test_con_empresa_ok`: Valida que con Empresa retorna datos correctos
- ✅ `test_contrato_nunca_none`: Valida contrato (nunca retorna None)

---

### ✅ Naturaleza (VENTA/COMPRA) con normalización

**Tests existentes**: `apps/tenant/facturas/tests/test_naturaleza_unit.py`

**Tests adicionales creados**: `apps/tenant/facturas/tests/test_naturaleza_rule_ssot.py`

- ✅ `test_norm_nit_elimina_separadores`: Normalización de NIT
- ✅ `test_norm_nit_elimina_ceros_izquierda`: Normalización de ceros
- ✅ `test_norm_nit_maneja_dv`: Extracción de base NIT (sin DV)
- ✅ `test_venta_si_igual`: Regla VENTA cuando emisor == empresa
- ✅ `test_compra_si_distinto`: Regla COMPRA cuando emisor != empresa

---

### ✅ Workspace: enlaces estrictos + columna Naturaleza

**Tests existentes**: `apps/tenant/core/tests/test_workspace_links_strict.py`

- ✅ `test_links_estrictos_y_columna_naturaleza`: Valida enlaces y columna
- ✅ Verifica rutas relativas (sin host/protocolo)
- ✅ Verifica columna "Naturaleza" presente en tabla

---

## 0.4 Comandos de Auditoría (tenant‑aware)

### ✅ NIT por tenant

**Comando existente**: `apps/tenant/empresa/management/commands/audit_empresa_nit.py`

**Uso**:
```bash
python manage.py all_tenants_command audit_empresa_nit
```

**Esperado**: `OK: <nit>` para cada tenant con Empresa configurada.

---

### ⚠️ Mismatch de naturaleza (histórico)

**Estado**: ⚠️ **REQUIERE CREACIÓN**

**Comando sugerido**: `apps/tenant/facturas/management/commands/audit_naturaleza_mismatches.py`

**Acción requerida**: Crear comando para auditar inconsistencias de naturaleza históricas.

---

## 0.5 Celery & Entorno

**Estado**: ⚠️ **REQUIERE VERIFICACIÓN MANUAL**

- **Variables**: Requiere verificación de `BROKER_URL`, `RESULT_BACKEND`
- **Workers**: Requiere verificación de workers activos
- **schema_context en tareas**: Requiere verificación de uso

**Acción requerida**: Verificar configuración y disponibilidad de Celery.

---

## 0.6 Observabilidad Mínima

### ✅ Logging

**Loggers configurados**:
- ✅ `tenant.facturas.naturaleza` (INFO): Comparaciones emisor vs empresa
- ✅ `facturas.import` (INFO/WARN/ERROR): Parse/persist
- ✅ `facturas.delete` (INFO/WARN/ERROR): Eliminación
- ✅ Sin log de XML completo (solo tamaño/hash)

**Implementado en**: `apps/tenant/facturas/services.py`

---

### ⚠️ Métricas

**Estado**: ⚠️ **NO IMPLEMENTADO**

**Sugerido**:
- Conteo de tareas parseadas
- Tiempos medios
- % reintentos
- % errores 4xx/5xx

**Acción requerida**: Implementar métricas si se requiere para la migración.

---

## 0.7 Criterios de Go/No‑Go

### ✅ Go/No‑Go Checklist

- ✅ `get_empresa_emisor_data()` disponible, import desde `services.py` (archivo), sin shadowing
- ✅ Reglas de negocio (naturaleza) probadas (unitarias + tenant‑aware)
- ✅ Listas API sin blobs; detalle opcional con anexos; Service Layer mapea errores (409/413/422)
- ✅ `schema_context` y comandos tenant‑aware operativos
- ⚠️ Celery en marcha (requiere verificación manual)
- ✅ Workspace con rutas estrictas y assets sin duplicación
- ✅ `FacturaAnexos` para blobs, sin kwargs inesperados al crear `Factura`

---

## Resumen Ejecutivo

### ✅ Completado (6/7)

1. ✅ SSoT de Empresa operativo y sin shadowing
2. ✅ Service Layer vigente y centralizado
3. ✅ API‑First con listas mínimas
4. ✅ Multi‑tenant por esquema configurado
5. ✅ Rutas estáticas/JS correctas
6. ✅ Blobs fuera del modelo principal

### ⚠️ Pendiente de Verificación (1/7)

1. ⚠️ Celery & Broker: Requiere verificación manual de configuración y workers

### 📝 Acciones Recomendadas

1. **Verificar Celery**: Confirmar que Celery está configurado y workers están activos
2. **Crear comando de auditoría de naturaleza**: `audit_naturaleza_mismatches.py` (opcional)
3. **Implementar métricas**: Si se requiere para la migración (opcional)

---

## Conclusión

**Estado General**: ✅ **LISTO PARA FASE 1** (con verificación manual de Celery)

El proyecto está preparado para migrar el parseo/validación/normalización XML a un servicio general reusable. Todos los criterios críticos están cumplidos, excepto la verificación manual de Celery que debe realizarse en el entorno de desarrollo/producción.

**Próximo paso**: Fase 1 - Creación del paquete `apps/services/xml_ingest/` (router, parsers, contratos, normalizadores, tareas Celery) y "enganche" desde facturas como primer consumidor.
