# Findings — Integración Contable SINTEL v3.6

**Última actualización:** 2026-05-08 (v3.7)

---

## Descubrimientos e investigación

| Fecha | Hallazgo | Impacto |
|-------|---------|---------|
| 2026-05-08 | `PLAN_INTEGRACION_CONTABLE.md` v2.1 define Pull Model (ETL) para desacoplar contabilidad de apps origen | Arquitecturalmente correcto, minimiza breaking changes |
| 2026-05-08 | `gastos` e `inventario` no tienen GAPs de modelo — campos necesarios ya existen | Fases 1 y 2 ETL implementables sin migraciones |
| 2026-05-08 | `Factura` ya tiene `retefuente`, `reteica` en v2.62 — sin GAP para Fase 3 ETL | Fase 3 implementable sin migración adicional |
| 2026-05-08 | `CatalogoMaestroNIIF` tenía tabla pero estaba vacía — `poblar_catalogo_niif` no seteaba `nombre`/`nivel`/`naturaleza`/`empresa_id` | Fix: `update_or_create` con todos los campos. 124 cuentas pobladas. |
| 2026-05-08 | `TipoComprobanteListSerializer` definido después de ser referenciado → `NameError` en arranque | Fix: mover definición antes de `AsientoContableDetailSerializer` |
| 2026-05-08 | `cuenta_list.js` usaba `#grid-cuenta` pero template tiene `#grid-cuentas` → tabla nunca montaba | Fix: 4 selectores corregidos en JS |
| 2026-05-08 | `pendiente_list.js` usaba `new Tabulator()` directo — viola regla FSD "TabulatorFactory obligatorio" | Fix: migrado a `TabulatorFactory.create()`. Array response compatible con Caso 1 del factory. |
| 2026-05-08 | `TabulatorFactory.ajaxResponse` maneja arrays directos (Caso 1: `Array.isArray(response)`) | Endpoint `/pendientes/` puede retornar array plano sin paginación — compatible |
| 2026-05-08 | `AsientoContable.save()` sincroniza `total_debe = debe_total` — el CRUD legacy seteaba los campos legacy directamente causando que `save()` los sobreescribiera con 0 | Fix: `crear_asiento_manual()` setea `debe_total`/`haber_total` (campos primarios) y deja que `save()` sincronice los legacy |
| 2026-05-08 | `DocumentoSoporte.numero_documento` es `@property` que accede `resolucion_dian` — necesita `select_related('resolucion_dian')` | Fix: `qs_gastos_pendientes()` incluye `select_related('proveedor', 'resolucion_dian')` |
| 2026-05-08 | `Proveedor.numero_documento` es el campo NIT (no `nit`) | Usado correctamente en `DocumentosPendientesViewSet.list()` |
| 2026-05-08 | `SintelTenantBaseModel.save()` lanza `ValueError` si `empresa_id` es None — `poblar_catalogo_niif` hacía `get_or_create(codigo=codigo)` sin empresa | Fix: obtener `Empresa.objects.first()` antes del loop |
| 2026-05-08 | `TipoComprobante` vacío → select sin opciones → `comprobanteSeleccionado = false` → `btnGenerar` siempre disabled | Fix: seed 6 tipos (CE/RC/GN/ND/NC/NOM) via shell para todos los schemas |
| 2026-05-08 | `CuentaContable nivel=6 = 0` → `business_service._validar_cuentas_auxiliares()` rechazaba todo → ningún asiento podía crearse | Fix: seed 54 cuentas nivel-6 desde `CatalogoMaestroNIIF` via shell |
| 2026-05-08 | `ReglaContable` usada en `render_offcanvas_contabilizar` pero no importada en `viewsets.py` → `NameError` → 500 | Fix: añadido al bloque `from apps.tenant.contabilidad.models import (...)` |
| 2026-05-08 | `table.clearFilter()` sin argumento = `clearFilter(true)` en Tabulator → limpiaba también header filters de columnas | Fix: `clearFilter(false)` para preservar header filters de `numero` y `tercero_nombre` |
| 2026-05-08 | Dropdown de tipo solo tenía FACTURA/GASTO pero API devuelve NOMINA/INVENTARIO → datos ocultos al filtrar | Fix: opciones NOMINA/INVENTARIO añadidas a `pendientes_list.html` y `TIPO_BADGE` en JS |
| 2026-05-08 | Buscador de cuentas en offcanvas no filtraba por contexto de app → sugería cuentas irrelevantes | Fix: `APP_ORIGEN_PREFIJOS` + `filtrar_cuentas_por_app_origen()` en selectors + `?app_origen=` en JS |

| 2026-05-08 (v3.8) | `anthropic` no estaba en `requirements.txt` — la app no podía importar el SDK | Añadido `anthropic>=0.40.0,<1.0`; `ImportError` en el service retorna `HTTP 400` descriptivo |
| 2026-05-08 (v3.8) | `sugerir_lineas_asiento_ia` usa `filtrar_cuentas_por_app_origen` para acotar el prompt — sin esto Claude sugeriría cuentas no disponibles en el tenant | Fix by design: contexto de cuentas filtrado antes de construir el prompt |
| 2026-05-08 (v3.8) | Claude puede retornar markdown con ` ``` ` en el JSON — `json.loads()` fallaría | Fix: strip de bloques markdown antes de `json.loads()` |
| 2026-05-08 (v3.8) | Las líneas sugeridas por IA deben pasar DSV igual que el flujo manual — cuenta no nivel-6 o de otro tenant no puede colarse | Fix: validación `CuentaContable.filter(empresa_id, codigo, nivel=6)` por cada línea retornada |
| 2026-05-08 (v3.8) | Si IA retorna asiento sin cuadrar, frontend lo inyecta de igual forma — el usuario vería badge "Sin cuadrar" y podría ajustar | Diseño intencional: validación local de cuadratura sigue siendo el gate final para "Generar Asiento" |
| 2026-05-08 (exec) | `seed_reglas_contables` falla silenciosamente — intenta acceder a `empresa.nombre` pero el campo es `razon_social` | Ejecutado manual seed con 13 ReglaContable bases (VENTA_FACTURA, COMPRA_GASTO, NOMINA, INVENTARIO) |
| 2026-05-08 (fix) | `NameError: name 'Decimal' is not defined` en `render_offcanvas_contabilizar` linea 792 al llamar app_label='empleados' | Fix: añadido `from decimal import Decimal` en viewsets.py imports |
| 2026-05-08 (fix) | `KeyError: 'numero_actual'` en `get_documento_pendiente()` al llamar app_label='gastos' — campo no existe en `ResolucionDIAN` | Fix: cambiar `resolucion_dian__numero_actual` → `resolucion_dian__consecutivo` en selectors.py |

---

## Estado actual de módulos clave

### `contabilidad.integracion.contabilizador.Contabilizador`
- ✅ Verificado y funcional
- Maneja: idempotencia (`existe_asiento_para`), período (`_resolver_periodo`), persistencia atómica
- Único punto de entrada para flujo ETL automático

### `contabilidad.integracion.dtos`
- ✅ Completo
- `TransaccionEconomica`: flujo ETL automático
- `LineaManual` + `ComprobanteManualDTO`: flujo On-Demand manual (nuevo v3.6)

### `contabilidad.integracion.resolver.ResolverCuentas`
- ✅ Funcional
- Precedencia: `cuenta_hint` > `ReglaContable` > `ReglaContableNoDefinidaError`
- Cachea resultados por sesión
- **No usado en flujo manual** — usuario provee `cuenta_codigo` directamente

### `contabilidad.services.business_service.ContabilidadBusinessService`
- ✅ Completo
- Métodos ETL: `ejecutar_integracion_completa()` → orquesta todos los extractores
- Método manual: `contabilizar_documento_manual(empresa_id, dto)` → validación + CRUD
- Método catálogo: `buscar_catalogo_niif_por_tipo(tipo, search)` → buscador UI

### `contabilidad.services.crud_service.ContabilidadCRUDService`
- ✅ Completo
- `crear_asiento()`: flujo ETL/API directa (legacy, `factura_id` legacy en DB pero no en modelo)
- `crear_asiento_manual()`: flujo On-Demand (nuevo v3.6, soporta `documento_origen_*`, corrige sync totales)

### `contabilidad.api.viewsets.DocumentosPendientesViewSet`
- ✅ Operativo
- `GET /pendientes/`: merge de facturas + gastos + nominas + inventario pendientes
- `GET /pendientes/render-offcanvas/`: offcanvas HTMX — contexto incluye `TipoComprobante` + `sugerencias_puc`
- `POST /pendientes/contabilizar-manual/`: genera asiento con `TipoComprobante` y cuentas manuales

### `contabilidad.api.viewsets.CuentaContableViewSet`
- ✅ Operativo con filtro contextual
- `GET /cuentas-contables/?search=X&app_origen=Y`: filtra por prefijos PUC del `APP_ORIGEN_PREFIJOS[Y]`
- Sin `app_origen`: comportamiento original (todas las cuentas activas)

### `contabilidad.services.selectors.filtrar_cuentas_por_app_origen`
- ✅ Operativo
- Mapa `APP_ORIGEN_PREFIJOS`: facturas (20 prefijos), gastos (37), empleados (20), inventario (10)
- Cuentas nivel-6 disponibles por app: facturas=14, gastos=25, empleados=13, inventario=6

### Extractores ETL (`integracion/extractores/`)
- `ExtractorGastos`: ✅ Implementado — pendiente validación final
- `ExtractorInventario`: ✅ Implementado — pendiente validación final
- `ExtractorFacturas`: ✅ Implementado — pendiente pruebas (bloqueado por DB locks)
- `ExtractorNomina`: ✅ Implementado parcial — falta provisiones patronales

---

## Análisis de cobertura contable

### Cuentas PUC utilizadas (confirmadas en ReglaContable / uso manual)

| Clase | Grupo | Uso en sistema |
|-------|-------|---------------|
| 1 (Activo) | 1105-1110 (Caja/Bancos) | Recaudo (futuro) |
| 1 (Activo) | 1305 (Clientes) | Factura venta |
| 1 (Activo) | 1355 (Anticipos impuestos) | Retenciones a favor |
| 1 (Activo) | 1435 (Inventarios) | Inventario |
| 2 (Pasivo) | 2205 (Proveedores) | Compra gastos |
| 2 (Pasivo) | 2335 (C×P) | Gastos por pagar |
| 2 (Pasivo) | 2365-2368 (Retenciones) | Retefuente, ReteICA |
| 2 (Pasivo) | 2370 (Aportes nómina) | Seguridad social |
| 2 (Pasivo) | 2408 (IVA) | 240805 generado, 240810 descontable |
| 2 (Pasivo) | 25xx (Obligaciones laborales) | Provisiones nómina |
| 4 (Ingresos) | 4135 (Ventas) | Factura venta |
| 5 (Gastos) | 5105 (Personal) | Nómina |
| 5 (Gastos) | 51xx (Operativos) | Gastos compras |
| 6 (Costos) | 6135 (CMV) | Inventario ventas |

### GAPs de cobertura identificados

| GAP | Afecta | Plan |
|-----|--------|------|
| IVA descontable en gastos (240810) | `ExtractorGastos` | Fase 1b (migración `DocumentoSoporte`) |
| Recaudo cartera (1110/1305) | `facturas` | Módulo tesorería futuro |
| Provisiones patronales nómina | `ExtractorNomina` | Fase B.4 — calcular via `TarifaImpuesto` |
| Cierre contable (transfer 4,5,6→3) | Módulo cierre | Fase B.6 |

---

## Benchmark Siigo Contador (Mipymes Colombia)

| Feature | Siigo | SINTEL v3.6 |
|---------|-------|-------------|
| Causación automática | Documentos comerciales generan asiento sin intervención | ✅ `ExtractorFacturas` + `Contabilizador` |
| Causación manual asistida | Contador asigna cuentas desde lista de pendientes | ✅ `DocumentosPendientesViewSet` + offcanvas |
| Vínculo NC → Factura | NC creadas desde factura original para heredar CUFE | ✅ `FacturaBusinessService.vincular_nc` |
| Comprobantes contables | Plantillas pre-configuradas por tipo de documento | ✅ `TipoComprobante` modelo implementado |
| Búsqueda inteligente PUC | Sugerencia PUC en tiempo real | ✅ Buscador live en offcanvas (cuenta y pendientes) |
| Catálogo NIIF Colombia | 124+ cuentas estándar | ✅ `CatalogoMaestroNIIF` (124 cuentas) |
| Período contable y cierre | Cierre mensual bloquea ediciones | ✅ `PeriodoContable` con inmutabilidad |
| Cierre anual automático | Wizard que transfiere saldos 4,5,6 → 3 | ⏳ Pendiente (Fase B.6) |
| Reportes financieros | Balance General, P&G en tiempo real | ⏳ Pendiente (post-ETL estabilizado) |
| Dashboard cumplimiento | Estado DIAN + cierres visuales | ⏳ Pendiente (Fase B.6) |

---

## Decisiones técnicas documentadas

| Decisión | Justificación |
|----------|--------------|
| Pull Model (ETL Interno) | Cero acoplamiento apps origen ↔ contabilidad |
| Arquitectura dual permanente | Manual cubre edge cases y correcciones; ETL cubre volumen operativo |
| `ComprobanteManualDTO` no usa `ReglaContable` | Usuario es la fuente de verdad de las cuentas en flujo manual |
| `crear_asiento_manual()` separado del `crear_asiento()` legacy | Evita romper flujo existente; soporta `documento_origen_*` y `tipo_comprobante_ref_id` |
| `debe_total`/`haber_total` como campos primarios | `save()` sincroniza legacy — setear primarios garantiza consistencia |
| `TabulatorFactory.create()` obligatorio | Consistencia FSD; el factory maneja JWT, errores, paginación DRF |
| Catálogo NIIF 1 copia por tenant schema | django-tenants aísla por schema; cada tenant puede customizar |
| `APP_ORIGEN_PREFIJOS` en selectors.py (no en viewset) | Reutilizable por cualquier componente; SSoT para la lógica de contexto contable |
| Seed datos via shell en lugar de migración | `TipoComprobante` y `CuentaContable` son datos de negocio, no esquema; seed idempotente |
| `clearFilter(false)` para filtro tipo_doc | Preserva header filters de usuario en columnas `numero` y `tercero_nombre` |
