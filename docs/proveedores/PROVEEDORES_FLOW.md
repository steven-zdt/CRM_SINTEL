# PROVEEDORES_FLOW — flujo real verificado (PROVEEDORES-01)

Complementa `PROVEEDORES_AUDIT.md`. Reemplaza los diagramas de
`.agent/docs/proveedores_flow_map.md` (v3.5.0), desactualizados desde que el
frontend migró de Tabulator a server-rendered (django-tables2+HTMX) y se
agregaron `Representante`/`CuentasPagar`.

Fecha: 2026-09-08. Verificado contra código real, no contra documentación
previa.

---

## 1. Navegación

```
/workspace/ (SPA de tabs)
  └─ #proveedores  →  {% include 'tenant/proveedores/proveedores_list.html' %}
       ├─ Tab "Directorio"        → server-rendered (django-tables2 + HTMX)
       ├─ Tab "Cuentas por Pagar" → server-rendered (django-tables2 + HTMX)
       └─ Tab "Representantes"    → Tabulator (directorio global consolidado)
```

## 2. Directorio de Proveedores (CRUD)

```
GET /ui/proveedores/tabla/ (HTMX, hx-trigger="load, proveedor-updated from:body")
   → ProveedorTablaView (django-tables2) → ProveedorSelector.get_list()
   → partials/tabla_proveedores.html

Nuevo / Editar / Ver
   → offcanvas_form.html (HTMX render-offcanvas/{crear,editar,detalle}/)
   → proveedores_form.js construye payload (saneo bool/numérico)
   → POST/PATCH /api/v1/proveedores/{uuid}/
   → ProveedorViewSet.create/update → ProveedorBusinessService.crear/actualizar_proveedor
   → DSV: empresa existe, documento único por empresa
   → ProveedorCRUDService (persistencia @transaction.atomic)
   → evento "proveedor-updated" → refresca la tabla
```

**Delete**: `DELETE /api/v1/proveedores/{uuid}/` → soft-delete (`activo=False`)
si tiene FKs dependientes (compras, CxP, representantes), hard-delete si no
tiene ninguna. Nunca rompe trazabilidad histórica.

## 3. Representante (dentro del detalle de Proveedor, y directorio global)

```
Dentro de offcanvas_form.html (modo detalle) → tab "Representantes"
   → partials/list_representantes.html (tabla HTML simple, no Tabulator)
   → GET /api/v1/proveedores/representantes/?proveedor_uuid={uuid}

Nuevo/Editar representante
   → offcanvas_representante_form.html (autocomplete de proveedor con chip,
     debounce 280ms sobre ?search=)
   → POST/PATCH /api/v1/proveedores/representantes/(:uuid/)
   → RepresentanteViewSet.create/update → RepresentanteBusinessService
   → DSV: empresa existe → proveedor pertenece a la empresa → documento único
     POR PROVEEDOR (no global — el mismo documento puede repetirse como
     representante de dos proveedores distintos)

Eliminar
   → DELETE /api/v1/proveedores/representantes/{uuid}/
   → RepresentanteBusinessService.eliminar_representante
   → Guard: rechaza (400) si es el único es_principal=True del proveedor
```

Directorio global (tab propio en `proveedores_list.html`, Tabulator):
`GET /api/v1/proveedores/representantes/` (sin `?proveedor_uuid`) lista todos
los representantes de la empresa.

## 4. Cuentas por Pagar

**Fuente del listado — dos orígenes fusionados, sin FK entre ellos:**

```
qs_list_unificado() (CuentasPagarSelector)
  ├─ Factura.objects.filter(naturaleza='COMPRA')       ← fuente PRIMARIA
  │    (proveedor_uuid soft-ref, resuelto/creado automáticamente al
  │     importar la factura XML si el NIT emisor no tiene Proveedor aún)
  └─ CuentasPagar sin factura_uuid                      ← CxP "sueltas"
       (creadas a mano, o por CuentasPagarBusinessService.registrar_cuenta_pagar
       al aprobar una Orden de Compra — bridge Compras→Proveedores)
```

```
GET /ui/proveedores/cuentas-pagar/tabla/ (HTMX)
   → CuentasPagarTablaView → CuentasPagarSelector.qs_list_unificado()
   → partials/tabla_cuentas_pagar.html

Registrar abono
   → offcanvas_cuentas_pagar.html
   → POST /api/v1/proveedores/cuentas-pagar/{uuid}/registrar-abono/
   → CuentasPagarBusinessService.registrar_abono
       - select_for_update (evita condición de carrera en abonos concurrentes)
       - rechaza monto <= 0 o monto > saldo pendiente
       - recalcula saldo/estado_pago en CuentasPagar.save()
       - estados: SIN_PAGO → PARCIAL → PAGADA (no existe VENCIDA/ANULADA)
```

**No hay `update`/`delete` genérico de una `CuentasPagar`** — por diseño,
solo se modifica vía abono (evita edición arbitraria de una obligación de
pago).

**Limitación conocida (documentada, no oculta):** una misma compra puede
generar obligación por los 2 caminos (Orden de Compra aprobada + Factura
real posterior) sin reconciliarse entre sí — ver H6 en `PROVEEDORES_AUDIT.md`.
Riesgo aceptado, no se implementa reconciliación automática en esta misión.

## 5. Proveedor → Compras → Facturas (documento vivo vs. fiscal)

```
OrdenCompra.proveedor  → FK directa + PROTECT (documento interno vivo,
                          siempre refleja el dato ACTUAL del proveedor)

Factura (naturaleza=COMPRA) → snapshot fiscal (emisor_nit, emisor_razon_social,
                          ...) + proveedor_uuid (soft-ref al maestro actual)
                          — preserva lo que decía el XML/DIAN en el momento
                          de emisión, navegable al proveedor vivo por separado
```

## 6. Retenciones — NO se calculan en Proveedores

```
Proveedor.retefuente_porcentaje / aplica_retefuente / etc.
   → capturables vía API pero READ-ONLY desde PROVEEDORES-01 (H2)
   → NINGÚN cálculo real los lee

Cálculo real de retenciones de una compra/gasto:
   apps/tenant/gastos, apps/tenant/facturas
      → contabilidad.RetencionesService.obtener_retenciones_desde_tercero(
            nit, tipo_tercero='PROVEEDOR', naturaleza='COMPRA', empresa_id)
      → contabilidad.ConfiguracionRetenciones (indexado por NIT, Pull Model
        ADR-001 — nunca por FK a Proveedor)
```

## 7. Permisos (binario, deliberado — ver H3)

```
Lectura (GET/list/retrieve)         → IsTenantMember (cualquier miembro activo)
Escritura (POST/PATCH/PUT/DELETE,
incluye registrar-abono = pagar)    → IsTenantAdminOrReadOnly (solo ADMIN)
```

Sin niveles intermedios (OPERADOR no puede crear/editar proveedores ni
representantes, ni registrar pagos). Confirmado como política deliberada,
no un gap.
