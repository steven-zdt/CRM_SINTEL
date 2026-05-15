# ADR-001: Retencion Pull Model (v3.7.1)

**Status:** ACCEPTED  
**Date:** 2026-05-13  
**Version:** v3.7.1  
**Author:** steven-zdt  
**Relates to:** FASES 1-9 Migration, Bounded Context Enforcement

---

## Summary

Migrate **Retencion** (retention) data management from `Facturas` app to `Contabilidad` app using a **Pull Model** pattern. Facturas queries Contabilidad API for retention configuration and records instead of owning the data directly. This enforces bounded context separation and makes Contabilidad the authoritative source for all accounting-related data.

---

## Problem Statement

### Current State (v3.7.0 and earlier)
- `Factura.retefuente`, `.reteica`, `.reteiva` are direct database fields
- `ItemFactura.porcentaje_retefuente`, `.valor_retefuente`, etc. stored redundantly
- When retention logic changes, both Facturas and Contabilidad need updates
- No single source of truth (SSoT) for retention configuration
- Client code couples to Facturas model directly

### Issues with Direct Field Ownership
1. **Bounded Context Violation** — Facturas shouldn't own accounting-domain data
2. **Data Duplication** — Same retention values in Facturas AND Contabilidad records
3. **Inconsistency Risk** — Fields can diverge if one app updates without the other
4. **Scalability** — Every source app (Facturas, Gastos, Inventario, etc.) would need redundant retention fields
5. **Audit Trail Loss** — Original retention values lost; no history of when they changed

---

## Decision

Implement a **Pull Model** where:

1. **Contabilidad owns** `Retencion` model as the authoritative source
   - Single table: `contabilidad_retencion` with fields: `uuid`, `tipo` (RETEFUENTE/RETEICA/RETEIVA), `monto`, `porcentaje`, `documento_origen_app`, `documento_origen_modelo`, `documento_origen_id`, `reversada`, `retencion_reversada_por`, `created_at`, `updated_at`, `empresa_id`
   - Supports generic FK to any document (Factura, ItemFactura, Gasto, etc.)

2. **Facturas reads via Contabilidad API**
   - Bridge endpoint: `obtener_retenciones_desde_cliente()` → `RetencionesService.obtener_retenciones_desde_tercero()`
   - Uses `ConfiguracionRetenciones` (Contabilidad) as config SSoT
   - Queries: `/api/v1/contabilidad/retenciones/obtener-por-tercero/?nit=&tipo_tercero=&naturaleza=`

3. **Backward Compatibility via @property**
   - `Factura.total_retencion_fuente` @property reads from `Retencion` table
   - Similarly for `.total_reteica` and `.total_reteiva`
   - Gradual migration: fields marked as `editable=False`, later removed in v3.9.0

4. **API Contract Unchanged**
   - `FacturaListSerializer` still includes `retefuente`, `reteica`, `reteiva` fields (read_only)
   - Serializers compute values from Retencion records via @property
   - Clients see same JSON structure (no breaking API changes)

---

## Rationale

### 1. Bounded Context (§18 from AGENTS.md)
> Facturas = sales document management  
> Contabilidad = financial data owner

Retenciones are **accounting concepts** (tax withholdings), not sales concepts. Contabilidad is the right bounded context.

### 2. Single Source of Truth (SSoT)
- One `Retencion` record per withholding event
- `ConfiguracionRetenciones` centralizes retention rules by client/vendor
- Eliminates sync issues between apps

### 3. Scalability
Other source apps (Gastos, Inventario, Cotizaciones) can all use the same Retencion table without code duplication. No need to add `retention_fields` to every model.

### 4. Audit Trail
- `Retencion.created_at` / `updated_at` track when withholdings were created/modified
- `Retencion.reversada` flag + `retencion_reversada_por` FK tracks reversals
- `notas` field logs migration origin (`migrate_v371_from_facturas`)

### 5. Backward Compatibility
- `@property` methods allow existing code to read `factura.total_retencion_fuente` without refactoring
- Serializers map to @property values (no code changes in frontend)
- Gradual deprecation: v3.7.1 (read-only fields) → v3.8.x (users upgrade) → v3.9.0 (fields removed)

### 6. Testability
- Service layer completely decoupled from Facturas
- 59 new tests cover:
  - RetencionesService (14 tests) - CRUD, normalization, calculations
  - RetencionViewSet + ConfiguracionRetencionesViewSet API (18 tests)
  - Factura/ItemFactura backward compatibility (27 tests)

---

## Implementation Details

### Phase Timeline

| FASE | Version | Scope | Status |
|------|---------|-------|--------|
| 1-3B | v3.7.1 | Models, Service, API, Bridge | ✅ DONE |
| 4 | v3.7.1 | Data Migration (RunPython) | ✅ DONE |
| 5-8 | v3.7.1 | Deprecation (fields → editable=False) | ✅ DONE |
| 9 | v3.7.1 | Comprehensive Tests (59 tests) | ✅ DONE |
| 10 | v3.9.0 | Remove deprecated fields (FASE 10) | ⏳ PLANNED |
| 11 | v3.7.1 | Documentation + ADR | ✅ DONE |

### Code Changes Summary

**New Models:**
- `Retencion` in `contabilidad/models.py` (UUID PK, generic FK via `documento_origen_*`)
- `ConfiguracionRetenciones` (NIT-based rules, per naturaleza)

**New Service:**
- `RetencionesService` static methods: `obtener_retenciones_desde_tercero()`, `crear_retencion()`, `listar_retenciones_por_documento()`, `calcular_monto_retencion()`, etc.

**Bridge Endpoint:**
- `FacturaBusinessService.obtener_retenciones_desde_cliente()` → delegates to `RetencionesService.obtener_retenciones_desde_tercero()`

**Backward Compat @property:**
- `Factura.total_retencion_fuente`, `.total_reteica`, `.total_reteiva`
- `ItemFactura.total_retefuente_item`, `.total_reteiva_item`, `.total_reteica_item`

**Serializer Changes:**
- Mark `retefuente`, `reteica`, `reteiva` as `read_only_fields`
- Prevents writes; reads from @property

**Data Migration:**
- `0007_migrate_retenciones_from_facturas.py` — reads old fields, creates Retencion records, supports rollback

---

## Alternatives Considered

### A. Keep fields in Facturas (Status Quo)
**Pros:** No migration needed, minimal code changes  
**Cons:** Violates Bounded Context, duplicates data, scales poorly to other apps  
**Decision:** ❌ Rejected (architectural debt accumulates)

### B. Read from Facturas, Write from Contabilidad (Dual Write)
**Pros:** Backward compatible reads, clean writes  
**Cons:** Sync issues, eventual inconsistency, complex audit trails  
**Decision:** ❌ Rejected (complex state management)

### C. Full Pull Model (Chosen)
**Pros:** Single SSoT, clean bounded contexts, scalable, audit trail, testable  
**Cons:** 2-3 release deprecation cycle, backward compat layer needed  
**Decision:** ✅ Chosen (best long-term architecture)

---

## Consequences

### Positive
✅ **Cleaner Architecture** — Bounded contexts respected  
✅ **SSoT** — One source of truth for retention data  
✅ **Scalable** — Other apps (Gastos, etc.) can reuse Retencion without duplication  
✅ **Audit Trail** — Full history of withholding events + reversals  
✅ **No Breaking Changes** — Backward compatible via @property + serializers  
✅ **Testable** — 59 comprehensive tests + CI/CD safety net  

### Negative
❌ **Deprecation Cycle** — 2-3 releases before fields removed  
❌ **@property Overhead** — Extra query per Factura read (mitigated by serializer caching)  
❌ **API Call Overhead** — Bridge endpoint adds HTTP roundtrip (negligible in internal API)  
❌ **Learning Curve** — Developers must understand Pull Model pattern  

---

## Migration Strategy

### Automatic Data Migration (Management Command)
```bash
# Dry-run: validate without committing
python manage.py migrate_retenciones --dry-run

# Execute: create Retencion records from Factura fields
python manage.py migrate_retenciones

# Rollback: delete migrated records if needed
python manage.py migrate_retenciones --rollback
```

### Rollback Plan
1. If issues detected: `python manage.py migrate_retenciones --rollback`
2. Fields remain on model until v3.9.0 (safe recovery window)
3. If critical: can stay on v3.7.0 (no breaking changes until v3.9.0)

---

## Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| **All tests passing** | 59 new + existing | ✅ |
| **No API breaking changes** | Same JSON contract | ✅ |
| **Data integrity** | 100% values migrated | ✅ |
| **Deprecation warnings** | Fields marked [DEPRECATED v3.7.1] | ✅ |
| **Rollback tested** | `--rollback` works | ✅ |
| **Documentation** | ADR + CLAUDE.md + tests | ✅ |

---

## Related Decisions

- **ADR-002 (Future):** Multi-source Pull Model (other apps like Gastos)
- **FASE 10:** Remove deprecated fields (v3.9.0 timeline)
- **AGENTS.md §18:** Bounded Context enforcement rules

---

## References

- `CLAUDE.md` → "Accounting integration" section
- `AGENTS.md` → "§18 Bounded Context" rules
- `MEMORIA.md` → `migration_retenciones_status.md` (implementation timeline)
- Test files:
  - `apps/tenant/contabilidad/tests/test_retenciones_service.py` (14 tests)
  - `apps/tenant/contabilidad/tests/test_retenciones_api.py` (18 tests)
  - `apps/tenant/facturas/tests/test_retenciones_backward_compat.py` (27 tests)
- Models: `apps/tenant/contabilidad/models.py` (Retencion, ConfiguracionRetenciones)
- Service: `apps/tenant/contabilidad/services/retenciones_service.py` (static methods)
- Bridge: `apps/tenant/facturas/services/business_service.py` (obtener_retenciones_desde_cliente)
- Migration: `apps/tenant/contabilidad/migrations/0007_migrate_retenciones_from_facturas.py`
- Management Command: `apps/tenant/contabilidad/management/commands/migrate_retenciones.py`

---

## Sign-off

- ✅ **Architect:** steven-zdt (2026-05-13)
- ✅ **Testing:** 59 tests, all passing
- ✅ **Deployed:** v3.7.1 (pending production roll-out)
