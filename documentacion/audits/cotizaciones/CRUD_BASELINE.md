# Cotizaciones — CRUD Baseline (FASE 0/1)

**Fecha:** 2026-08-26
**Método:** lectura directa de código real (`models.py`, `services/*.py`, `api/*.py`, `ui_views.py`, templates, JS, tests) + comparación contra `.agent/AUDITORIA_FLUJO_COMPLETO.md` y `.agent/docs/*.md`.

**Nota sobre la documentación existente:** `.agent/AUDITORIA_FLUJO_COMPLETO.md` (v3.10.3, 2026-05-25) describe correctamente la mayoría de la arquitectura actual. Sus docs hermanos en `.agent/docs/` (`cotizaciones_business_logic.md`, `cotizaciones_flow_map.md`) están **desactualizados**: mencionan campos que ya no existen en `ConfiguracionCotizacion` (`iva_porcentaje_default`, `aiu_*_default`, `tipo_cotizacion_default` — eliminados en el refactor v2.60 "User-Driven"), firma/imagen de perfil (no existen), y un `CotizacionPDFViewSet` que no existe (el PDF vive como `@action` dentro de `CotizacionViewSet`). Se tratan como aspiracionales, no como estado real, en el resto de esta auditoría.

---

## Inventario de modelos reales

| Modelo | Clasificación | Propietario | Empresa | Sede/Área | UUID | Soft-delete |
|---|---|---|---|---|---|---|
| `Cotizacion` | CORE | Cotizaciones | sí (heredado) | `sede` opcional (informativo/KPI, DT-SEDE-04) | sí | **no existe** |
| `CotizacionItem` | CHILD | Cotizaciones | vía `cotizacion` | — | sí | no (CASCADE con cabecera) |
| `Producto` (propio) | CATALOG | Cotizaciones | sí | — | sí | `activo` (declarado, nunca usado para bloquear nada) |
| `Servicio` (propio) | CATALOG | Cotizaciones | sí | — | sí | `activo` (ídem) |
| `ConfiguracionCotizacion` | SUPPORT | Cotizaciones | sí | — | — | `es_activo` (múltiples activos permitidos a propósito) |

### Cotizacion — detalle
- `cliente`: FK real a `clientes.Cliente`, `SET_NULL, null=True, blank=True` — **opcional por diseño** (el admin tiene fallback "Sin cliente definido"; `get_cliente_for_empresa` trata `None` como caso válido).
- `configuracion`: FK a `ConfiguracionCotizacion`, `SET_NULL, null=True`.
- `sede`: FK opcional a `empresa.Sede`, puramente informativa.
- `numero_cotizacion`, `fecha_vencimiento`: obligatorios.
- `estado`: choices `BORRADOR / ENVIADA / ACEPTADA / CANCELADA`, default `BORRADOR`.
- Constraint: `unique_numero_cotizacion_por_perfil` sobre `(empresa, configuracion, numero_cotizacion)`.
- **Sin proyecto**: no existe ningún campo/FK a `proyectos` en el modelo — la guía de la misión lo suponía, el dominio real no lo tiene.
- **Sin moneda**: no hay campo de moneda — una sola moneda implícita.

### CotizacionItem — detalle
- FK `cotizacion` (`CASCADE`), `producto`/`servicio` FKs opcionales (`SET_NULL`) — **patrón Snapshot real**: `descripcion`, `marca`, `referencia`, `costo_unitario`, `precio_unitario_venta`, `subtotal_linea` se persisten en la fila, independientes del catálogo de origen.
- `tipo_item`: choices `PRODUCTO / MATERIAL / SERVICIO` — nota: `MATERIAL` no tiene FK de catálogo propia, es texto libre.

---

## Endpoints reales (API)

| Recurso | Método | Endpoint | Service Layer |
|---|---|---|---|
| Cotizacion | POST | `/api/v1/cotizaciones/` | `CotizacionService.crear_preforma()` |
| Cotizacion | GET (list) | `/api/v1/cotizaciones/` | `CotizacionSelector.get_list()` |
| Cotizacion | GET (detail) | `/api/v1/cotizaciones/{uuid}/` | `CotizacionSelector.get_detail_by_uuid()` |
| Cotizacion | PATCH/PUT | `/api/v1/cotizaciones/{uuid}/` | `CotizacionService.actualizar_cotizacion()` |
| Cotizacion | DELETE | `/api/v1/cotizaciones/{uuid}/` | **ninguno — DRF `ModelViewSet.destroy()` por defecto, hard-delete directo** |
| Cotizacion | GET | `/{uuid}/exportar-pdf/` | `CotizacionPDFExportService.generar_pdf_publico()` |
| CotizacionItem | POST/PATCH/DELETE | `/api/v1/cotizaciones/items/...` | `CotizacionItemBusinessService` (create/update/eliminar_item, recalcula cabecera) |
| Producto | POST/GET/PATCH | `/api/v1/cotizaciones/productos/` | `ProductoBusinessService.registrar()` |
| Producto | DELETE | `/api/v1/cotizaciones/productos/{uuid}/` | **ninguno — `destroy()` directo en el ViewSet, bypasea BusinessService** |
| Servicio | POST/GET/PATCH | `/api/v1/cotizaciones/servicios/` | `ServicioBusinessService.registrar()` (sin validación real) |
| Servicio | DELETE | `/api/v1/cotizaciones/servicios/{uuid}/` | **ninguno — mismo bypass que Producto** |
| ConfiguracionCotizacion | POST/GET/PATCH | `/api/v1/cotizaciones/configuracion/` | `ConfiguracionCotizacionBusinessService` |
| ConfiguracionCotizacion | DELETE | — | **sin `destroy()` — `ConfiguracionCRUDService.delete_configuracion()` es código muerto, nunca invocado** |

---

## Gaps confirmados (evidencia real, ver `CRUD_COMPLETE_REPORT.md` para el detalle completo y la disposición de cada uno)

1. **Bug latente:** `Cotizacion.fecha_emision` es `auto_now_add=True`, pero `_build_header_fields()` calcula un valor desde el payload que Django ignora silenciosamente en el INSERT — la fecha "elegida" por el usuario nunca se persiste.
2. **DELETE físico sin protección de trazabilidad:** borrar una `Cotizacion` referenciada por `Factura.cotizacion_uuid` no está bloqueado — deja al UUID de la Factura apuntando a un registro inexistente, sin error.
3. **`estado` editable vía PATCH genérico sin ninguna validación de transición** — no existe ninguna máquina de estados en el código (única asignación de `estado` en todo el árbol Python es el `BORRADOR` de creación).
4. **`ProductoViewSet`/`ServicioViewSet`/`ConfiguracionCotizacion` bypasean el Service Layer en DELETE** — `destroy()` por defecto de DRF, viola el flujo `ViewSet → ServiceMixin → BusinessService → CRUDService` documentado como obligatorio.
5. **TOCTOU en unicidad de `codigo` de Producto** — validación de aplicación (query + `ValueError`), sin constraint de BD ni `select_for_update`.
6. **Código muerto confirmado:** `CotizacionPDFExportService.generar_pdf_interno()` apunta a un template (`formato_interno.html`) que no existe en el filesystem — cero call-sites reales.
7. **Cobertura de tests delgada en el CRUD core:** sin tests de PATCH/UPDATE de Cotización, sin DELETE (ningún modelo), sin `CotizacionItemViewSet` vía API, sin `exportar_pdf`, sin negativos de DSV cross-empresa.

**Confirmado NO existe (evidencia negativa, no un gap a "arreglar" sino un hecho del dominio a documentar):**
- Conversión Cotización→Venta: `grep -rin "cotizacion" apps/tenant/ventas` → 0 resultados. Lo único real es un vínculo manual `Factura.cotizacion_uuid` (bridge de solo enlace, no de conversión, no copia items/totales, no es idempotente porque no crea nada).
- `Cotizacion.proyecto`: no existe.
- Máquina de estados: no existe ninguna transición con respaldo en código.

**Producto/Servicio propios — veredicto (FASE 8/9):** `DUPLICATE_CANDIDATE` con evidencia estructural real (mismo dominio conceptual que `inventario.Producto/Servicio`, sin FK/bridge/sincronización entre ambos catálogos), pero con un propósito diferenciado defendible: `cotizaciones.Producto/Servicio` son deliberadamente mínimos (sin stock/categoría/imagen), consistentes con la idea de "ítem especulativo de cotización" que puede no existir aún en el inventario formal. Consumidores fuera de `cotizaciones/` en todo el repo: solo 2 (scripts de generación de tenants de prueba, no lógica de negocio). **No se recomienda ni ejecuta ninguna migración/eliminación** — ver `CRUD_COMPLETE_REPORT.md` §Producto/Servicio para el razonamiento completo.

Ver `CRUD_COMPLETE_REPORT.md` para el detalle fase-por-fase completo (FASE 2-45) y `CRUD_MATRIX.md` para el veredicto final por modelo.
