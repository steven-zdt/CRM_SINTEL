# Task Plan — Integración Contable SINTEL v3.6

**Última actualización:** 2026-05-08 (v3.7 — post-correcciones On-Demand)
**Referencia:** `PLAN_INTEGRACION_CONTABLE.md` v3.7 + `AUDITORIA_COMPLETA_CONTABILIDAD.md` v3.7

## Estado global

| Track | Descripción | Estado |
|-------|-------------|--------|
| **Pista A — Manual On-Demand** | UI pendientes + asignación manual PUC | ✅ Operativo |
| **Pista B — ETL Automático** | Extractores Pull Model por app | 🔨 En progreso (Fases 1-2 completas) |

---

## Pista A — Manual On-Demand

### A.0 — Infraestructura On-Demand
- [x] DTO `LineaManual` y `ComprobanteManualDTO` (con `tipo_comprobante_id`) en `integracion/dtos.py`
- [x] Selectors pendientes en `services/selectors.py`: facturas, gastos, nominas, inventario + `get_documento_pendiente()`
- [x] `APP_ORIGEN_PREFIJOS` + `filtrar_cuentas_por_app_origen()` en `services/selectors.py`
- [x] `ContabilidadCRUDService.crear_asiento_manual()` — `documento_origen_*`, `tipo_comprobante_ref_id`, totales correctos
- [x] `ContabilidadBusinessService.contabilizar_documento_manual()` — valida `TipoComprobante`, numero via `obtener_siguiente_numero()`
- [x] `ContabilizarManualInputSerializer` con `tipo_comprobante_id` requerido
- [x] `CuentaContableViewSet.get_queryset()` — acepta `?app_origen=` y filtra por prefijos PUC
- [x] `DocumentosPendientesViewSet` — `ReglaContable` importado, `TipoComprobante` + `sugerencias_puc` en contexto
- [x] Registro en `api/urls.py` → `GET/POST /api/v1/contabilidad/pendientes/`
- [x] Template `pendientes_list.html` — filtro FACTURA/GASTO/NOMINA/INVENTARIO
- [x] Template `pendiente_offcanvas_contabilizar.html` — select TipoComprobante, preview número, SUGERENCIAS
- [x] JS `pendiente_list.js` — `TabulatorFactory.create()`, `clearFilter(false)`, `TIPO_BADGE` completo
- [x] Offcanvas JS `buscarCuenta` — inyecta `&app_origen=${APP_LABEL}`
- [x] Subtab `#subtab-pendientes` en `workspace.html`
- [x] Seed `TipoComprobante` (6 tipos: CE/RC/GN/ND/NC/NOM) en home + cliente
- [x] Seed `CuentaContable` nivel-6 (54 cuentas desde CatalogoMaestroNIIF) en home + cliente
- [x] Fix `NameError: ReglaContable` en `viewsets.py` (import faltante → 500 resuelto)
- [x] Verificado: 4 facturas + 1 gasto pendientes, flujo completo funcional

### A.1 — Extensión Pista A a nuevas apps
Contrato ahora de **5 pasos** (ver `PLAN_INTEGRACION_CONTABLE.md §3`): incluye registro en `APP_ORIGEN_PREFIJOS`.

| App | Modelo | Estado |
|-----|--------|--------|
| `facturas` | `Factura` | ✅ Operativo |
| `gastos` | `DocumentoSoporte` | ✅ Operativo |
| `empleados` | `Devengo` | ✅ Operativo |
| `inventario` | `MovimientoInventario` | ✅ Operativo |

---

## Pista B — ETL Automático

### B.0 — Setup & Arquitectura
- [x] Estructura `integracion/extractores/` con `__init__.py`
- [x] `AbstractExtractor` en `base.py` (extraer_pendientes + contabilizar_pendientes)
- [x] Orquestador `ejecutar_integracion_completa()` en `ContabilidadBusinessService`
- [x] `Contabilizador` y `TransaccionEconomica` DTO verificados

### B.1 — Extractor Gastos (`integracion/extractores/gastos.py`)
- [x] Implementado `ExtractorGastos`
- [x] Fix concepto default `GASTO_GENERAL` (era `COMPRA_GASTO_GENERAL` — no existía en seed)
- [x] Fix N+1: subquery exclusion (2 queries totales)
- [x] Fix `.only()`: campos `numero_documento`, `observaciones` añadidos
- [x] **Validación final con DocumentoSoporte reales** — ejecutado y verificado (mapeo DTO correcto)
- [ ] Pruebas unitarias

### B.2 — Extractor Inventario (`integracion/extractores/inventario.py`)
- [x] Implementado `ExtractorInventario`
- [x] Fix crítico: método `extraer_pendientes()` implementado (faltaba → `TypeError`)
- [x] Fix N+1: subquery exclusion
- [ ] **Validación final con MovimientoInventario reales**
- [ ] Pruebas unitarias

### B.3 — Extractor Facturas (`integracion/extractores/facturas.py`)
- [x] Modelo `Factura` con retenciones verificado (campos existentes en v2.62)
- [x] `ExtractorFacturas` implementado con Notas de Crédito
- [x] Fix conceptos: `VENTA_PRODUCTO`→`INGRESO_PRINCIPAL`, `CXC_CLIENTE`→`CXC`, etc.
- [x] Fix NC compra: `TipoTransaccion.VENTA_NOTA_CREDITO` → `COMPRA_NOTA_CREDITO` (nuevo enum)
- [x] `COMPRA_NOTA_CREDITO` añadido a `TipoTransaccion` en `dtos.py`
- [x] Reglas seed para `COMPRA_NOTA_CREDITO` en `seed_reglas_contables.py`
- [x] Fix N+1: 2 subqueries de exclusión
- [x] Idempotencia NC: protección en `FacturaBusinessService.guardar_desde_dto`
- [ ] **Validación final con suite de pruebas** (bloqueado por DB locks en Windows — pendiente reinicio)
- [ ] Pruebas unitarias

### B.4 — Extractor Nómina (`integracion/extractores/nomina.py`)
- [x] Implementado `ExtractorNomina` (basado en `Devengo`)
- [x] Conceptos `OTROS_DEVENGOS` y `PRESTAMOS_EMPLEADO` añadidos a `seed_reglas_contables.py`
- [x] Registrado en `extractores/__init__.py`
- [ ] **Provisiones patronales (NOMINA_PROVISION)** — calcular desde `TarifaImpuesto` en el extractor
- [ ] Pruebas unitarias

### B.5 — Infraestructura de ejecución
- [x] `TipoComprobante` modelo implementado (plantillas de asientos)
- [x] Catálogo NIIF poblado — 124 cuentas en todos los schemas
- [x] `seed_reglas_contables` command disponible
- [x] **Ejecutar `seed_reglas_contables` en schemas productivos** (Ejecutado en `home`)
- [ ] Tarea Celery periódica para ejecución automática del ETL
- [ ] Endpoint manual de trigger ETL (admin/staff)

### B.6 — Simplificación NIIF Mipymes
- [x] Búsqueda inteligente PUC implementada (buscador live en offcanvas cuentas + offcanvas contabilizar)
- [x] `CatalogoMaestroNIIF` con 124 cuentas NIIF PYMES Colombia
- [ ] Wizard de Cierre Mensual/Anual simplificado
- [ ] Reportes financieros: Balance General, Estado de Resultados (P&G)
- [ ] Dashboard de cumplimiento contable (saldos por periodo)

---

---

## Pista C — Asistente IA Contable

### C.0 — Infraestructura Agentes IA (v3.8)
- [x] `anthropic>=0.40.0` añadido a `requirements.txt`
- [x] `AsistenteIAInputSerializer` en `api/serializers.py` — valida app_label, modelo, documento_id, montos, tercero
- [x] `ContabilidadBusinessService.sugerir_lineas_asiento_ia()` — orquestador IA + validación DSV cuentas nivel-6
- [x] `DocumentosPendientesViewSet.asistente_ia()` — `POST /api/v1/contabilidad/pendientes/asistente-ia/` con `IsTenantMember`
- [x] Botón "Diligenciar con IA" en `pendiente_offcanvas_contabilizar.html` (junto a "Agregar Línea")
- [x] JS `diligenciarConIA()` — POST al endpoint, inyecta lineas via `agregarLinea()`, manejo de errores
- [x] Vars JS del contexto financiero (`DOC_SUBTOTAL`, `DOC_IMPUESTOS`, `DOC_TOTAL`, `DOC_TERCERO_*`)
- [x] Sección `[AI-AGENTS] 20.` en `AGENTS.md` — routing agents, prompt canónico, compliance rules
- [ ] `ANTHROPIC_API_KEY` configurada en `.env` / Docker Compose del servidor
- [ ] Test golden path: offcanvas → Diligenciar con IA → revisión → Generar Asiento
- [ ] Test error handling: API key ausente → 400 descriptivo
- [ ] Test cuadratura IA: si Claude retorna asiento sin cuadrar → 400 bloqueado

---

## Pendientes críticos (próximo sprint)

| # | Acción | Pista | Prioridad | Estado |
|---|--------|-------|-----------|--------|
| 1 | Ejecutar `seed_reglas_contables` — habilita `sugerencias_puc` en offcanvas | B | Alta | ✅ Completado |
| 2 | Completar y validar `ExtractorGastos` end-to-end | B-F1 | Alta |
| 3 | Implementar `ExtractorInventario` completo | B-F2 | Alta |
| 4 | Provisiones patronales en `ExtractorNomina` (via `TarifaImpuesto`) | B-F4 | Media |
| 5 | Resolver DB locks Windows para pruebas unitarias | B | Media |
| 6 | Tarea Celery ETL periódico | B-F5 | Baja |

---

## Decisiones de arquitectura

| Fecha | Decisión |
|-------|----------|
| 2026-05-08 | Pull Model (ETL Interno) para minimizar acoplamiento entre apps |
| 2026-05-08 | Inventario priorizado sobre Facturas (sin GAPs estructurales) |
| 2026-05-08 | NC integradas en `ExtractorFacturas` como reversiones (`COMPRA_NOTA_CREDITO`) |
| 2026-05-08 | Estabilización NC priorizada antes del extractor para garantizar trazabilidad |
| 2026-05-08 | Flujo "Document-First" (Siigo benchmark) — contador valida extracción, no digita |
| 2026-05-08 | **Arquitectura dual permanente**: Manual On-Demand + ETL automático coexisten |
| 2026-05-08 | Pista Manual usa `ComprobanteManualDTO` — no pasa por `ReglaContable` |
| 2026-05-08 | `TabulatorFactory.create()` obligatorio — cero `new Tabulator()` directos |

---

## Errores resueltos

| Error | Fase | Resolución |
|-------|------|------------|
| `IntegrityError` (pg_type) en tests | B.3 | Bloqueo infraestructura Windows/PostgreSQL — pendiente reinicio |
| 422 Duplicate NC | B.3 | Idempotencia en `FacturaBusinessService.guardar_desde_dto` |
| `NameError: TipoComprobanteListSerializer` | Global | Serializer movido antes de `AsientoContableDetailSerializer` |
| Catálogo NIIF vacío | A.0 | `poblar_catalogo_niif` fijado: `update_or_create` con empresa + todos los campos |
| `#grid-cuenta` vs `#grid-cuentas` | UI | Selector JS corregido en `cuenta_list.js` |
| `new Tabulator()` directo | A.0 | Migrado a `TabulatorFactory.create()` en `pendiente_list.js` |
| `UnicodeEncodeError` en `seed_reglas_contables` | Infra | Eliminados Unicode para compatibilidad Windows |
| `AttributeError: numero_documento` | B.1 | Property calculada removida de `.only()` en extractor |
| `TipoComprobante` vacío → botón disabled | A.0 | Seeded 6 tipos (CE/RC/GN/ND/NC/NOM) via shell |
| `CuentaContable nivel=6` = 0 → ValidationError | A.0 | Seeded 54 cuentas nivel-6 desde `CatalogoMaestroNIIF` |
| `NameError: ReglaContable` en `viewsets.py` | A.0 | Añadido al bloque de imports de `models` |
| `clearFilter()` borraba header filters de columnas | A (UI) | Cambiado a `clearFilter(false)` |
| Badge NOMINA/INVENTARIO sin estilo | A (UI) | Objeto `TIPO_BADGE` con clase por tipo en `pendiente_list.js` |
| Buscador cuentas sin contexto de app | A (UI) | `buscarCuenta` inyecta `&app_origen=${APP_LABEL}` |
| 500 en `render-offcanvas` (facturas) | A | Fix import `ReglaContable` → endpoint funcional |
