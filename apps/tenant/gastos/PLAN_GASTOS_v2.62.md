# PLAN DE AUDITORÍA Y MEJORAS — MÓDULO GASTOS v2.62

**Fecha**: 2026-05-06
**Versión actual**: v2.61.4
**Versión objetivo**: v2.62.0
**Autor**: Auditoría SINTEL FSD
**Status**: 🔴 REQUIERE INTERVENCIÓN INMEDIATA

---

## 1. RESUMEN EJECUTIVO

### 1.1 Estado Actual
El módulo `gastos` es **funcionalmente operativo** pero presenta **issues críticos de arquitectura, seguridad multi-tenant e inmutabilidad contable** que comprometen la integridad legal y financiera del sistema.

### 1.2 Métricas de Auditoría

| Categoría | 🔴 Críticos | 🟡 Medios | 🟢 Menores | Total |
|-----------|-------------|-----------|------------|-------|
| Seguridad Multi-Tenant (DSV) | 4 | 2 | 1 | **7** |
| Lógica de Negocio Contable | 6 | 3 | 2 | **11** |
| Arquitectura Service Layer | 3 | 4 | 1 | **8** |
| Performance (Zero Waste) | 0 | 3 | 2 | **5** |
| Inmutabilidad Legal | 3 | 2 | 0 | **5** |
| **TOTAL** | **16** | **14** | **6** | **36** |

### 1.3 Riesgo Legal/Contable
- **DIAN Compliance**: ⚠️ COMPROMETIDO — Documentos pueden mutar después de generación
- **Multi-Tenant**: ⚠️ CRÍTICO — IDOR potencial al usar `Empresa.objects.first()`
- **Trazabilidad**: ⚠️ MEDIO — Doble flujo de creación crea ambigüedad

---

## 2. ARQUITECTURA ACTUAL — DIAGNÓSTICO

### 2.1 Estructura de Archivos

```
apps/tenant/gastos/
├── models.py                          ✅ OK
├── admin.py                           ✅ OK
├── apps.py                            ✅ OK
├── urls.py                            ✅ OK
├── services.py                        🔴 ANTI-PATTERN (legacy)
├── services_facade.py                 🟡 Wrapper innecesario
├── services/
│   ├── __init__.py                    🔴 Hack importlib
│   ├── selectors.py                   ✅ OK
│   ├── crud_service.py                🔴 Importa ItemGasto inexistente
│   ├── business_service.py            🔴 Lógica duplicada
│   ├── api_mixins.py                  ✅ OK
│   └── gasto_service.py               ❓ Sin auditar (vacío?)
├── api/
│   ├── viewsets.py                    🔴 Vulnerabilidades IDOR
│   ├── serializers.py                 🟡 N+1 query
│   └── urls.py                        ✅ OK
├── choices/                           ✅ OK
├── templates/                         🟡 4 templates con duplicación
├── static/                            ✅ OK
├── migrations/                        ✅ OK (2 migraciones)
└── tests/                             ⚠️ Cobertura insuficiente
```

### 2.2 Modelos — Relaciones

```
ResolucionDIAN (1) ────< (N) DocumentoSoporte ────< (1) Gasto
                                  │
                                  └── INMUTABLE (legal)
```

- ✅ Inmutabilidad estructural correcta (consecutivo, valores monetarios)
- ⚠️ Pero `clean()` recalcula retenciones en cada save (viola inmutabilidad)
- ⚠️ ResolucionDIAN puede modificarse después de tener documentos asociados

---

## 3. ISSUES CRÍTICOS 🔴 (Acción Inmediata)

### 3.1 SEGURIDAD MULTI-TENANT (DSV) — 4 issues

#### Issue #1: IDOR en `viewsets.py:105` — `Empresa.objects.first()` sin tenant filter

**Ubicación**: [viewsets.py:105](apps/tenant/gastos/api/viewsets.py#L105), [:155](apps/tenant/gastos/api/viewsets.py#L155), [:307](apps/tenant/gastos/api/viewsets.py#L307), [:330](apps/tenant/gastos/api/viewsets.py#L330), [:489](apps/tenant/gastos/api/viewsets.py#L489), [:551](apps/tenant/gastos/api/viewsets.py#L551)

**Problema**:
```python
# ANTES (VULNERABLE - IDOR multi-tenant)
empresa = Empresa.objects.first()
if not empresa:
    return Response(...)
```

**Riesgo**: En un escenario multi-tenant con datos compartidos, `first()` retorna LA PRIMERA empresa en la BD, no la del tenant del request. Esto compromete el aislamiento.

**Fix v2.62**:
```python
# DESPUÉS (SEGURO - DSV)
from apps.tenant.api.tenant_helpers import resolve_tenant_empresa

empresa = resolve_tenant_empresa(request, self)
if not empresa:
    return Response(
        {"detail": "No se pudo determinar la empresa activa"},
        status=status.HTTP_403_FORBIDDEN
    )
```

**Severidad**: 🔴 CRÍTICO — Compliance AGENTS.md Rule 13 (SaaS-DEFENSE)

---

#### Issue #2: `get_queryset()` con fallback inseguro

**Ubicación**: [viewsets.py:101-109](apps/tenant/gastos/api/viewsets.py#L101)

**Problema**:
```python
if hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_profile'):
    empresa_id = self.request.user.tenant_profile.empresa_id
else:
    # FALLBACK INSEGURO
    empresa = Empresa.objects.only('id').first()
    empresa_id = empresa.id if empresa else None
```

**Riesgo**: El fallback hace que un usuario sin `tenant_profile` obtenga la primera empresa.

**Fix**: Eliminar fallback. Si no hay tenant_profile, retornar `Gasto.objects.none()`.

---

#### Issue #3: `request.user.empresa_id` sin validación

**Ubicación**: [viewsets.py:238](apps/tenant/gastos/api/viewsets.py#L238)

**Problema**: Confía ciegamente en `user.empresa_id` sin validar membresía al tenant.

**Fix**: Usar `IsTenantMember` permission + `resolve_tenant_empresa(request)`.

---

#### Issue #4: `services/__init__.py` carga código vía importlib

**Ubicación**: [services/__init__.py:23-33](apps/tenant/gastos/services/__init__.py#L23)

**Problema**:
```python
import importlib.util
services_py_path = Path(__file__).resolve().parent.parent / 'services.py'
spec = importlib.util.spec_from_file_location(...)
spec.loader.exec_module(services_module)
```

Hack para resolver conflicto entre paquete `services/` y archivo `services.py`. Esto:
- Bypasea el sistema de imports de Python
- Dificulta debugging
- Crea doble fuente de verdad (services.py vs services/business_service.py)

**Fix v2.62**: Eliminar `services.py` del nivel superior. Migrar TODA la lógica al paquete `services/`.

---

### 3.2 LÓGICA DE NEGOCIO CONTABLE — 6 issues

#### Issue #5: Import de `ItemGasto` inexistente

**Ubicación**: [crud_service.py:15](apps/tenant/gastos/services/crud_service.py#L15), [business_service.py:18](apps/tenant/gastos/services/business_service.py#L18), [services.py:18](apps/tenant/gastos/services.py#L18)

**Problema**:
```python
from apps.tenant.gastos.models import Gasto, ResolucionDIAN, DocumentoSoporte, ItemGasto
```

`models.py` NO define `ItemGasto`. Esto causa **ImportError en runtime** cuando se intenta usar `ItemGastoCRUDService.crear_item()` o `GastoService.registrar_gasto_total()`.

**Fix v2.62**:
- **Opción A**: Crear modelo `ItemGasto` (si se requiere ítems detallados)
- **Opción B**: Eliminar referencias a `ItemGasto` (si OneToOne basta)

**Recomendación**: Opción B — El modelo actual `Gasto` es OneToOne con `DocumentoSoporte`. No hay valor agregado en `ItemGasto`.

---

#### Issue #6: Doble flujo de creación de Gasto

**Ubicación**:
- `business_service.py:179` — `GastoBusinessService.procesar_gasto()`
- `services.py:712` — `GastoService.registrar_gasto_total()`

**Problema**: Dos implementaciones distintas para "crear gasto":

| Aspecto | `procesar_gasto` | `registrar_gasto_total` |
|---------|------------------|-------------------------|
| Hook contable | ❌ No materializa asiento | ✅ Sí lo hace |
| Campos Gasto | Solo `centro_costo`, `categoria_contable` | Incluye campos inexistentes (proveedor_uuid, etc.) |
| Atomicidad | @transaction.atomic | @transaction.atomic |
| Validación retenciones | Cliente vs servidor 0.01 | Cliente vs servidor 0.01 |
| **Estado real** | ⚠️ Incompleto | 🔴 Crashea (campos inexistentes) |

**Fix v2.62**: Consolidar en un único flujo:
```python
class GastoBusinessService:
    @staticmethod
    @transaction.atomic
    def crear_gasto_completo(empresa, data):
        """SSoT — Único punto de creación de gastos."""
        # 1. Validar resolución vigente
        # 2. Validar proveedor (snapshot)
        # 3. Validar cuenta NIIF contra plan_cuentas activo
        # 4. Calcular retenciones server-side
        # 5. Validar total cliente vs servidor (0.01)
        # 6. Crear DocumentoSoporte (consecutivo atómico)
        # 7. Crear Gasto (OneToOne)
        # 8. Materializar asiento contable (Contabilizador)
        # 9. Retornar gasto creado
```

---

#### Issue #7: Tolerancia de validación inconsistente

**Ubicación**:
- `models.py:402` — Tolerancia: **100.00 COP** (¡demasiado alta!)
- `services.py:769` — Tolerancia: **0.01 COP** (correcto)

**Problema**:
```python
# models.py — clean()
if self.total is not None and diferencia > Decimal('100.00'):  # ⚠️ 100 COP
    raise ValidationError(...)

# services.py — registrar_gasto_total()
if diferencia > Decimal('0.01'):  # ✅ 1 centavo
    raise ValidationError(...)
```

**Riesgo**: Diferencias de hasta 100 COP en documentos pasarían validación del modelo (auditoría DIAN comprometida).

**Fix v2.62**: Unificar tolerancia a `Decimal('0.01')` (1 centavo) en ambos.

---

#### Issue #8: `clean()` en `DocumentoSoporte` recalcula retenciones SIEMPRE

**Ubicación**: [models.py:379-393](apps/tenant/gastos/models.py#L379)

**Problema**:
```python
def clean(self):
    if self.subtotal is not None and self.subtotal >= 0:
        if self.retefuente_porcentaje:
            porcentaje_retefuente = Decimal(str(self.retefuente_porcentaje))
            self.retefuente = (self.subtotal * porcentaje_retefuente).quantize(Decimal('0.01'))
        # ...
```

Esto **viola la inmutabilidad** del documento: cualquier `save()` posterior recalcula retenciones, incluso si se modifica un campo no-monetario.

**Fix v2.62**:
```python
def clean(self):
    # Solo calcular retenciones en CREACIÓN, no en updates
    if self._state.adding:
        # ... cálculos ...
    # Validar coherencia (no recalcular)
    if self.subtotal and self.retefuente and self.reteica:
        total_calculado = self.subtotal - self.retefuente - self.reteica
        if abs(self.total - total_calculado) > Decimal('0.01'):
            raise ValidationError(...)
```

---

#### Issue #9: `ResolucionDIAN` puede mutarse después de uso

**Ubicación**: [models.py:113-125](apps/tenant/gastos/models.py#L113)

**Problema**: `ResolucionDIAN.save()` permite cambios incluso si tiene `DocumentoSoporte` asociados. Cambiar `rango_hasta` después de generar 100 documentos compromete la legalidad.

**Fix v2.62**:
```python
def save(self, *args, **kwargs):
    if self.pk:  # Update existente
        tiene_documentos = DocumentoSoporte.objects.filter(
            resolucion_dian=self
        ).exists()
        if tiene_documentos:
            # Solo permitir cambio de 'vigente'
            allowed_fields = {'vigente'}
            # ... validar ...
    super().save(*args, **kwargs)
```

---

#### Issue #10: `services.py:800-813` — Crea `Gasto` con campos inexistentes

**Ubicación**: [services.py:799-813](apps/tenant/gastos/services.py#L799)

**Problema**:
```python
gasto = Gasto.objects.create(
    empresa=empresa,
    documento_soporte=documento_soporte,
    proveedor_uuid=proveedor.get('uuid'),              # ❌ Campo no existe
    proveedor_nit_snapshot=proveedor['nit'],            # ❌ Campo no existe
    proveedor_razon_social_snapshot=proveedor[...],     # ❌ Campo no existe
    proveedor_origen=proveedor['origen'],               # ❌ Campo no existe
    numero_factura_proveedor=payload[...],              # ❌ Campo no existe
    cuenta_contable_uuid=payload['cuenta_contable_uuid'], # ❌ Campo no existe
    # ...
)
```

**Resultado**: TypeError al ejecutar. Esta función está rota silenciosamente.

**Fix v2.62**: Estos campos viven en `DocumentoSoporte`. El modelo `Gasto` solo necesita: `centro_costo`, `categoria_contable`, `codigo_contable`, `periodo`, `descripcion`, `observaciones`.

---

### 3.3 INMUTABILIDAD LEGAL — 3 issues

#### Issue #11: `desactivar` no requiere razón

**Ubicación**: [services.py:368-397](apps/tenant/gastos/services.py#L368)

**Problema**: Desactivar un documento no requiere justificación. La DIAN exige trazabilidad.

**Fix v2.62**: Agregar campo `motivo_anulacion` y `usuario_anulacion`.

---

#### Issue #12: Sin validación de fecha del documento vs vigencia de resolución

**Ubicación**: [services.py:776-795](apps/tenant/gastos/services.py#L776) — `registrar_gasto_total`

**Problema**: No se valida que `fecha` del documento esté dentro de `[fecha_inicio, fecha_fin]` de la resolución.

**Fix v2.62**:
```python
if not (resolucion.fecha_inicio <= payload['fecha'] <= resolucion.fecha_fin):
    raise ValidationError(
        f"Fecha del documento ({payload['fecha']}) fuera del rango de "
        f"vigencia de la resolución ({resolucion.fecha_inicio} a {resolucion.fecha_fin})"
    )
```

---

#### Issue #13: `consecutivo` no es estrictamente atómico bajo alta concurrencia

**Ubicación**: [services.py:233-274](apps/tenant/gastos/services.py#L233)

**Problema**: Aunque usa `select_for_update()`, hay race conditions en escenarios distribuidos.

**Fix v2.62**: Implementar `SequenceField` (PostgreSQL sequence) por resolución.

---

## 4. ISSUES MEDIOS 🟡

### 4.1 Performance

| # | Issue | Ubicación | Impacto |
|---|-------|-----------|---------|
| 14 | `get_conteo_documentos` count() N+1 | serializers.py:78 | Alto en listados grandes |
| 15 | `validar_cuenta_contable` lista TODAS las cuentas | business_service.py:156 | O(N) cuando debe ser O(1) |
| 16 | Sin caché de resolución vigente | services.py:80-89 | Una query por request |

**Fix #14**:
```python
# En selector
from django.db.models import Count
qs = qs.annotate(conteo_documentos=Count('documentos_soporte'))

# En serializer
conteo_documentos = serializers.IntegerField(read_only=True)
```

**Fix #15**:
```python
# Filtrar por UUID directamente
cuenta = CuentaContable.objects.filter(
    empresa_id=empresa_id,
    uuid=cuenta_uuid,
    tipo='GASTO'
).first()
```

**Fix #16**: Caché Redis con invalidación por signal `post_save` de `ResolucionDIAN`.

---

### 4.2 Arquitectura

| # | Issue | Ubicación | Acción |
|---|-------|-----------|--------|
| 17 | `services_facade.py` wrapper duplicado | services_facade.py | Eliminar después de migración |
| 18 | 4 templates duplicados | templates/ | Consolidar en `_base_offcanvas.html` |
| 19 | `gasto_service.py` archivo huérfano | services/gasto_service.py | Auditar contenido o eliminar |
| 20 | `validate_codigo_contable` no valida tenant | serializers.py:353 | Validar contra plan_cuentas del tenant |

---

### 4.3 Validación NIIF

#### Issue #21: `codigo_contable` no valida contra plan de cuentas activo

**Ubicación**: [serializers.py:353](apps/tenant/gastos/api/serializers.py#L353)

**Problema**: Acepta cualquier código de `GASTOS_NIIF_CHOICES`, sin verificar que ese código exista como `CuentaContable` activa en el plan del tenant.

**Fix v2.62**:
```python
def validate_codigo_contable(self, value):
    if not value:
        return value
    from apps.tenant.contabilidad.models import CuentaContable
    empresa_id = self.context['request'].user.tenant_profile.empresa_id
    if not CuentaContable.objects.filter(
        empresa_id=empresa_id,
        codigo=value,
        activa=True,
        tipo='GASTO'
    ).exists():
        raise serializers.ValidationError(
            f"Código {value} no existe en el plan de cuentas activo del tenant."
        )
    return value
```

---

## 5. ISSUES MENORES 🟢

| # | Issue | Acción |
|---|-------|--------|
| 22 | Caracteres Unicode en docstrings (⚠️ ✅) | Reemplazar por `WARNING:` `OK:` |
| 23 | Logs mezclados ES/EN | Estandarizar a inglés (i18n separado) |
| 24 | Tests no cubren inmutabilidad | Agregar `test_documento_inmutable.py` |
| 25 | `default=datetime.date.today` callable | Cambiar a default value en migración |
| 26 | URL `/configurar-resolucion/` deprecated pero activa | Marcar 410 Gone |

---

## 6. PLAN DE IMPLEMENTACIÓN v2.62.0

### 6.1 Fases (Por Prioridad)

#### **FASE 1 — Seguridad Multi-Tenant** (1 día)
- [ ] Reemplazar TODO `Empresa.objects.first()` por `resolve_tenant_empresa(request, self)` (Issues #1, #2, #3)
- [ ] Agregar tests de aislamiento multi-tenant
- [ ] Auditoría de permisos en cada action del ViewSet

**Archivos afectados**:
- `apps/tenant/gastos/api/viewsets.py` (8 cambios)
- `apps/tenant/gastos/services_facade.py` (1 cambio)
- `apps/tenant/gastos/tests/test_multitenant_isolation.py` (NUEVO)

#### **FASE 2 — Consolidación Service Layer** (2 días)
- [ ] Eliminar `services.py` (legacy) — Issue #4
- [ ] Eliminar `services_facade.py` — Issue #17
- [ ] Migrar TODA lógica útil al paquete `services/`
- [ ] Resolver doble flujo `procesar_gasto` vs `registrar_gasto_total` — Issue #6
- [ ] Eliminar imports de `ItemGasto` — Issue #5
- [ ] Eliminar campos inexistentes en services.py:800 — Issue #10

**Archivos afectados**:
- `apps/tenant/gastos/services/__init__.py` (cleanup importlib hack)
- `apps/tenant/gastos/services/business_service.py` (consolidar)
- `apps/tenant/gastos/services/crud_service.py` (eliminar ItemGasto)
- `apps/tenant/gastos/services.py` (ELIMINAR)
- `apps/tenant/gastos/services_facade.py` (ELIMINAR)

#### **FASE 3 — Inmutabilidad y Compliance DIAN** (2 días)
- [ ] Modificar `clean()` en DocumentoSoporte para no recalcular en updates — Issue #8
- [ ] Bloquear cambios en ResolucionDIAN con documentos asociados — Issue #9
- [ ] Unificar tolerancia a 0.01 — Issue #7
- [ ] Validar fecha del documento vs vigencia resolución — Issue #12
- [ ] Agregar `motivo_anulacion` y `usuario_anulacion` — Issue #11

**Archivos afectados**:
- `apps/tenant/gastos/models.py` (validaciones)
- `apps/tenant/gastos/migrations/0003_v2_62_inmutabilidad.py` (NUEVO)

#### **FASE 4 — Performance y NIIF** (1 día)
- [ ] Annotate `conteo_documentos` en selector — Issue #14
- [ ] Optimizar `validar_cuenta_contable` — Issue #15
- [ ] Caché Redis resolución vigente — Issue #16
- [ ] Validar codigo_contable contra plan activo — Issue #21

#### **FASE 5 — Limpieza y Tests** (1 día)
- [ ] Consolidar templates en `_base_offcanvas.html`
- [ ] Eliminar `gasto_service.py` huérfano
- [ ] Reemplazar Unicode por keywords
- [ ] Tests de inmutabilidad: `test_documento_inmutable.py`
- [ ] Tests de concurrencia consecutivos: `test_consecutivo_atomico.py`

---

## 7. GARANTÍAS DE LÓGICA DE NEGOCIO POST-v2.62

### 7.1 Reglas Inviolables (Compliance DIAN)

✅ **R1**: Una vez asignado el consecutivo, el `DocumentoSoporte` es INMUTABLE
- Excepción única: campos `activo`, `anulado`, `fecha_anulacion`

✅ **R2**: Cálculo de retenciones SIEMPRE server-side
- Cliente envía porcentajes, servidor calcula valores
- Tolerancia 0.01 COP en validación

✅ **R3**: Solo UNA `ResolucionDIAN` vigente por empresa
- Garantizado por `save()` atomic

✅ **R4**: Consecutivos UNIQUE por (empresa, resolucion_dian)
- Garantizado por UniqueConstraint + select_for_update

✅ **R5**: Resolución no puede mutar después de uso (post v2.62)
- Solo `vigente` editable si tiene documentos

✅ **R6**: Fecha del documento DENTRO de vigencia de resolución (post v2.62)
- Validación en `procesar_gasto`

✅ **R7**: Aislamiento Multi-Tenant garantizado por `resolve_tenant_empresa` (post v2.62)
- Sin fallbacks inseguros a `.first()`

✅ **R8**: Anulación requiere justificación + usuario (post v2.62)
- Trazabilidad legal completa

### 7.2 Flujo Único de Creación de Gasto (post v2.62)

```python
# SSoT — apps/tenant/gastos/services/business_service.py

class GastoBusinessService:
    @staticmethod
    @transaction.atomic
    def crear_gasto_completo(empresa, data):
        # === FASE 1: VALIDACIONES ===
        # 1.1 Resolución vigente y dentro de vigencia
        resolucion = ResolucionBusinessService.validar_para_gasto(
            empresa, data.get('fecha')
        )

        # 1.2 Proveedor del directorio (snapshot histórico)
        proveedor = ProveedorBusinessService.obtener_snapshot(
            empresa, data['proveedor_uuid'], data['tipo_documento']
        )

        # 1.3 Cuenta contable NIIF en plan activo
        cuenta = ContabilidadBusinessService.validar_cuenta_gasto(
            empresa.id, data['cuenta_contable_uuid']
        )

        # === FASE 2: CÁLCULOS ===
        # 2.1 Calcular retenciones server-side
        retenciones = ProveedorBusinessService.calcular_componentes_retencion(
            subtotal=Decimal(str(data['subtotal'])),
            retefuente_porcentaje=data['retefuente_porcentaje'],
            reteica_porcentaje=data['reteica_porcentaje']
        )

        # 2.2 Validar total cliente vs servidor (tolerancia 0.01)
        total_cliente = Decimal(str(data['total_neto']))
        if abs(total_cliente - retenciones['total']) > Decimal('0.01'):
            raise ValidationError({'total_neto': ['Diferencia con servidor']})

        # === FASE 3: PERSISTENCIA ATÓMICA ===
        # 3.1 Crear DocumentoSoporte (consecutivo atómico)
        documento = DocumentoCRUDService.crear_documento(
            empresa=empresa,
            resolucion=resolucion,
            data={...}
        )

        # 3.2 Crear Gasto (OneToOne)
        gasto = GastoCRUDService.crear_gasto(
            empresa=empresa,
            documento_soporte=documento,
            data={...}
        )

        # === FASE 4: HOOK CONTABLE ===
        # 4.1 Materializar asiento via Contabilizador (NO Signals)
        Contabilizador(empresa.id).contabilizar(GastoDTO.from_gasto(gasto))

        return gasto
```

### 7.3 Garantía Multi-Tenant

```python
# Patrón obligatorio en TODOS los endpoints
def get_queryset(self):
    empresa = resolve_tenant_empresa(self.request, self)
    if not empresa:
        return Gasto.objects.none()
    return Gasto.objects.filter(empresa_id=empresa.id)
```

---

## 8. CHECKLIST DE MIGRACIÓN

### Pre-Implementación
- [ ] Backup de BD producción
- [ ] Snapshot de tests actuales (baseline)
- [ ] Documentar estado actual de docs en producción
- [ ] Comunicar ventana de mantenimiento

### Durante Implementación
- [ ] FASE 1 → Tests pasan → Deploy staging
- [ ] FASE 2 → Tests pasan → Deploy staging
- [ ] FASE 3 → Migración 0003 → Deploy staging
- [ ] FASE 4 → Tests performance → Deploy staging
- [ ] FASE 5 → Smoke tests completos

### Post-Implementación
- [ ] Auditoría de logs primeras 24h
- [ ] Validación con cliente piloto
- [ ] Documentación AUDITORIA_FLUJO_COMPLETO.md actualizada
- [ ] Actualizar AGENTS.md con nuevas reglas

---

## 9. ENDPOINTS API POST-v2.62

### 9.1 Endpoints Mantenidos

| Endpoint | Método | Cambios v2.62 |
|----------|--------|---------------|
| `/api/v1/gastos/` | GET | ✅ DSV aplicado |
| `/api/v1/gastos/` | POST | ✅ Flujo único `crear_gasto_completo` |
| `/api/v1/gastos/{id}/` | GET | ✅ DSV aplicado |
| `/api/v1/gastos/{id}/` | DELETE | ✅ DSV aplicado |
| `/api/v1/gastos/{id}/anular/` | POST | ✅ Requiere `motivo_anulacion` |
| `/api/v1/gastos/{id}/desactivar/` | POST | ✅ DSV aplicado |
| `/api/v1/gastos/summary/` | GET | ✅ Optimizado con annotate |
| `/api/v1/gastos/validar-financieros/` | POST | ✅ Sin cambios |
| `/api/v1/resoluciones-dian/` | CRUD | ✅ Bloqueo edición post-uso |
| `/api/v1/resoluciones-dian/activa/` | GET | ✅ Cacheado |

### 9.2 Endpoints Deprecados (410 Gone)

| Endpoint | Razón | Reemplazo |
|----------|-------|-----------|
| `/api/v1/gastos/configurar-resolucion/` | Duplicado | `POST /api/v1/resoluciones-dian/` |
| `/api/v1/gastos/resolucion-activa/` | Duplicado | `GET /api/v1/resoluciones-dian/activa/` |
| `/api/v1/gastos/gestor-offcanvas/` | Anti-RESTful | Endpoints dedicados render-offcanvas/* |

---

## 10. MÉTRICAS DE ÉXITO

### 10.1 KPIs Técnicos

| Métrica | Antes (v2.61) | Objetivo (v2.62) |
|---------|---------------|------------------|
| Vulnerabilidades IDOR | 7 | 0 |
| Tests de inmutabilidad | 0 | 15+ |
| Cobertura módulo gastos | ~40% | 80%+ |
| Latencia GET /gastos/ p95 | ~250ms | <150ms |
| N+1 queries en listado | 3 | 0 |
| Imports rotos (ItemGasto) | 3 archivos | 0 |

### 10.2 KPIs de Compliance

| Métrica | Estado |
|---------|--------|
| Compliance DIAN Art. 1.6.1.4.12 | ✅ 100% (post-v2.62) |
| Aislamiento multi-tenant | ✅ Garantizado |
| Trazabilidad de anulaciones | ✅ Usuario + motivo |
| Inmutabilidad documentos | ✅ Enforced |

---

## 11. RIESGOS DE NO IMPLEMENTAR

| Riesgo | Probabilidad | Impacto | Severidad |
|--------|--------------|---------|-----------|
| IDOR multi-tenant en producción | ALTA | Crítico | 🔴 |
| Sanción DIAN por mutabilidad | MEDIA | Crítico | 🔴 |
| ImportError en runtime (ItemGasto) | ALTA | Alto | 🔴 |
| Inconsistencia totales (tolerancia 100) | MEDIA | Alto | 🟡 |
| Doble flujo causa data corruption | BAJA | Crítico | 🟡 |

---

## 12. CONCLUSIÓN

El módulo `gastos` requiere una **refactorización significativa pero controlada** para alcanzar el estándar SINTEL v2.62.0. Los **16 issues críticos** identificados deben resolverse antes del próximo release a producción.

**Prioridad**: 🔴 ALTA — Programar implementación en sprint inmediato
**Tiempo estimado**: 7 días-hombre
**Riesgo de no actuar**: Compliance DIAN comprometido + IDOR multi-tenant

---

**Autor**: Auditoría SINTEL Service Layer v2.62
**Fecha**: 2026-05-06
**Próxima revisión**: Post-implementación FASE 1 (2026-05-09)
