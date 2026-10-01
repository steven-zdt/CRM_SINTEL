# ADK_DOMAIN_INVENTORY — Fase 1 (Inventario de Dominios)

**Fecha:** 2026-09-22
**Fuente:** `PLAN_MAESTRO_INTEGRACION_GOOGLE_ADK_ASISTENTE_IA_SINTEL.md` §59
**Depende de:** `docs/adk/ADK_BASELINE.md` (Fase 0)

STATUS FASE 1: **PASS**.

Todos los dominios de negocio siguen el mismo patrón FSD (`models.py` → `services/selectors.py` → `services/business_service.py` → `api/viewsets.py`), confirmado archivo por archivo (no asumido). Las columnas READ/VALIDATE/WRITE listan las tools **ya registradas** en `apps/services/ai/tools/` — nombre real de la tool tal como aparece en `AIToolRegistry.tool_metadata()`, no una tool propuesta.

## Matriz de dominios

| Dominio | Modelo principal | Selector | Service | READ tools | VALIDATE tools | WRITE tools |
|---|---|---|---|---|---|---|
| clientes | `Cliente` | `services/selectors.py` | `services/business_service.py` | `buscar_cliente` (SAFE_READ) | `validar_cliente` (SAFE_READ) | — |
| proveedores | `Proveedor` | `services/selectors.py` | `services/business_service.py` | `buscar_proveedor` (SAFE_READ) | `validar_proveedor` (SAFE_READ) | — |
| facturas | `Factura` | `services/selectors.py` | `services/business_service.py` | `consultar_factura` (SAFE_READ) | — | — |
| ventas | `Venta` | `services/selectors.py` | `services/business_service.py` | `consultar_venta` (SAFE_READ) | — | — |
| compras | `OrdenCompra` | `services/selectors.py` | `services/business_service.py` | `consultar_compra` (SAFE_READ) | `validar_compra` (SAFE_READ) | — |
| cotizaciones | `Cotizacion` | `services/selectors.py` | `services/business_service.py` | `consultar_cotizacion` (SAFE_READ) | `validar_cotizacion` (SAFE_READ) | — |
| inventario | `Producto` | `services/selectors.py` | `services/business_service.py` | `buscar_producto` (SAFE_READ) | `validar_producto` (SAFE_READ) | — |
| gastos | `DocumentoSoporte` | `services/selectors.py` | `services/business_service.py` | `consultar_gasto` (SAFE_READ) | `validar_gasto` (SAFE_READ) | — |
| empleados | `Empleado` | `services/selectors.py` | `services/business_service.py` | `buscar_empleado` (**SENSITIVE_READ**) | — | — |
| proyectos | `Proyecto` | `services/selectors.py` | `services/business_service.py` | `consultar_proyecto` (SAFE_READ) | — | — |
| bancos | `CuentaBancaria` | `services/selectors.py` | `services/business_service.py` | `consultar_cuenta_bancaria` (**SENSITIVE_READ**) | — | — |
| contabilidad | `AsientoContable` | `services/selectors.py` | `services/business_service.py` | — | — | — (tiene `sugerir_asiento_contable`, kind=**SUGGEST**, SENSITIVE_READ — no encaja en READ/VALIDATE/WRITE, ver nota) |
| platform/EKG (no es un dominio de negocio) | — (grafo de código estático) | — | — | `ai_project_map` (SAFE_READ) | — | — |
| ai_knowledge (no es un dominio de negocio) | `AIKnowledgeChunk` | `retrieval_service.py` | — (solo lectura, sin business_service) | `buscar_conocimiento` (SAFE_READ, requiere además `AI_RETRIEVAL_ENABLED`) | — | — |

**Totales:** 12 dominios de negocio del plan, todos con al menos 1 tool `READ` real. 6 dominios con `VALIDATE` real (clientes, proveedores, compras, cotizaciones, inventario, gastos). 0 dominios con `WRITE`. 1 dominio (contabilidad) con `SUGGEST` en vez de `READ` puro — su `sugerir_asiento_contable` es la única tool de este tipo en todo el registro (ver `docs/ai/AI_RELEASE_GATE.md` "AI-05 = BLOQUEADO POR DISEÑO": no hay más lógica de sugerencia pura que envolver hoy).

## Dominios deliberadamente sin tool (verificado, no un olvido)

- **impuestos / reporting**: `DEFERRED` formalmente desde AI-03 (ver `docs/ai/AI_TOOL_REGISTRY.md` "Cierre formal de AI-03") — decisión explícita anterior a este plan, no deuda técnica nueva.
- **empresa / perfil**: apps de configuración/plataforma, no dominios operativos con flujo "crear/editar registro" — el plan de ADK no las menciona en su §21 (router por dominio), coherente con no tener tools hoy.

## `ventas`: por qué no tiene `VALIDATE` (relevante para la Fase 3/9 del plan de ADK)

Investigado y descartado explícitamente en una misión anterior (no en esta sesión): `VentaDetailSerializer` no tiene un `validate()` propio verificable — envolverlo tal cual solo validaría campos superficiales, no reglas de negocio reales (posiblemente ligadas a la máquina de estados Venta↔Factura). Se prefirió no implementar una tool engañosa. El plan de ADK, en su Fase 9 (§67, migración por app, orden: Clientes→Proveedores→Inventario→Cotizaciones→**Ventas**→Facturas...), debe tratar este caso con el mismo criterio: no crear `validar_venta` como wrapper superficial solo para completar la matriz.

## `facturas`/`empleados`/`bancos`/`contabilidad`: por qué no tienen `VALIDATE`

- `facturas`: dominio de solo-lectura/import desde el punto de vista de tools IA (la escritura real ocurre vía UBL/XML, no por formulario libre).
- `empleados`/`bancos`: mismo criterio — sin una función `validate()` de negocio aislada y segura de envolver hoy.
- `contabilidad`: el Asistente Contable (`sugerir_lineas_asiento_ia`) ya valida internamente antes de sugerir (revalida contra `CuentaContable` real del tenant) — envolver una `VALIDATE` aparte sería redundante.

## Riesgo (`ToolRisk`) — ya clasificado, no pendiente

El plan de ADK (§11) pide niveles de riesgo READ/LOW_WRITE/MEDIUM_WRITE/HIGH_WRITE. El sistema real ya tiene una clasificación equivalente y más granular vía `ToolRisk` (`SAFE_READ`/`SENSITIVE_READ`/`SAFE_WRITE`/`SENSITIVE_WRITE`/`HIGH_RISK`, `apps/services/ai/tools/base.py`), aplicada tool por tool (`empleados`/`bancos`/`contabilidad` ya marcadas `SENSITIVE_READ`, ver `docs/ai/AI_SECURITY_MODEL.md`). ADK no necesita inventar su propio esquema de riesgo — debe leer este.

## Conclusión de Fase 1

```
FASE 1 — INVENTARIO DE DOMINIOS = PASS
```

Matriz completa, sin dominios sin auditar. Continúa en `docs/adk/ADK_STATUS.md` (tracker global) y queda pendiente la Fase 2 (Mapa de Conocimiento) y Fase 3 (Tool Contract), ambas documentales, antes del primer cambio de código real (Fase 4 — ADK Spike), que requiere la decisión de LLM/proveedor señalada en `ADK_BASELINE.md`.
