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

---

## 8. Actualización PROVEEDORES-02 (2026-09-15) — Representante obligatorio + fix real de CxP

Verificado con evidencia real: `pytest apps/tenant/proveedores/tests` — **53 passed, 0 failed**
(Docker, 33m58s), `manage.py check`/`makemigrations --check` limpios. Sin migraciones nuevas (todo
el cambio vive en `services/`, `api/`, frontend).

### 8.1 Creación de Proveedor — ahora exige Representante

```
POST /api/v1/proveedores/ {tipo_persona, ..., representante: {...}}
   ↓ ProveedorViewSet.create() — extrae request.data['representante'] y request.user.tenant_profile
   ↓ ProveedorBusinessService.crear_proveedor(empresa_id, data, representante_data, usuario)
        (ahora @transaction.atomic)
        ├─ tipo_persona=JURIDICA → representante_data OBLIGATORIO
        │    (numero_documento + nombre_completo) — sin esto, 400 ANTES de tocar la BD
        ├─ tipo_persona=NATURAL  → autogenera el representante principal desde `usuario`
        │    (TenantProfile/User: nombre, email, teléfono, cargo) — solo pide numero/tipo de
        │    documento, dato que el sistema no posee para ningun usuario
        └─ crea Proveedor + Representante(es_principal=True) en la MISMA transaccion
   ↓ RepresentanteCRUDService().create(empresa_id, proveedor.id, rep_payload)
```

`exigir_representante=False` (parametro nuevo, opcional) preserva el comportamiento histórico para
callers automatizados sin usuario/representante disponibles —
`resolver_o_crear_desde_factura_compra()` lo usa explícitamente (sin llamadores en vivo hoy, solo
`backfill_proveedores_facturas_compra.py`).

### 8.2 Un solo Representante principal — reforzado en creación/edición

`RepresentanteBusinessService.crear_representante()`/`actualizar_representante()`: crear o editar
un representante con `es_principal=True` degrada automáticamente cualquier OTRO principal existente
del mismo proveedor, en la misma transacción (antes solo había guard al *eliminar* el último
principal, ninguno al *crear* uno nuevo — dos representantes podían quedar `es_principal=True`
simultáneamente).

### 8.3 Cuentas por Pagar — fix real: "Abonar" no funcionaba sobre filas de origen Factura

**Hallazgo (no documentado en PROVEEDORES-01):** el listado unificado (§4 arriba) muestra
Facturas(COMPRA) como fuente PRIMARIA — la inmensa mayoría de las filas del listado real. Pero
`registrar_abono()`/`render_offcanvas()` solo buscaban por UUID en el modelo `CuentasPagar`, y
ninguna Factura tiene una `CuentasPagar` vinculada hasta su primer abono. Resultado: el botón
"Abono" fallaba con 400 sobre el caso más común, y el offcanvas de gestión leía
`cuentas_pagar.proveedor_nombre` (atributo que no existe en el modelo — es `proveedor.razon_social`)
mostrando el proveedor siempre vacío.

```
POST /api/v1/proveedores/cuentas-pagar/{uuid}/registrar-abono/  (uuid puede ser de Factura o de CuentasPagar)
   ↓ CuentasPagarBusinessService.registrar_abono()
   ↓ resolver_cuenta_pagar(uuid, empresa_id)
        ├─ CuentasPagar.objects.filter(uuid=...) → si existe, la usa directo
        └─ si no existe: _materializar_desde_factura(empresa_id, uuid)
             → Factura.objects.filter(uuid=..., naturaleza='COMPRA') (debe existir y tener proveedor_uuid)
             → CuentasPagar.objects.get_or_create(empresa, proveedor, numero_factura=factura.numero,
                   defaults={factura_uuid: factura.uuid, valor_total: factura.total, ...})
             → idempotente, mismo patron que registrar_cuenta_pagar() (bridge Compras→CxP)
   ↓ select_for_update() + valida monto + save() (igual que antes)
```

**Consecuencia manejada:** una vez materializada, `CuentasPagarSelector.qs_list_unificado()` debe
dejar de leer `Factura.estado_pago`/`total` crudo para esa fila (quedaría desactualizado — Facturas
nunca se escribe desde aquí) y usar la `CuentasPagar` recién vinculada como fuente autoritativa de
`valor_pagado`/`saldo`/`estado_pago`. Esto YA está resuelto en el selector (ver §4 actualizado
abajo) — sin este segundo fix, el abono se registraría correctamente pero desaparecería de la
tabla en la siguiente carga.

**Detalle de solo lectura** (`retrieve()`/`render_offcanvas()` sin `?modo=ver`... con `?modo=ver`):
usan `CuentasPagarSelector.resolver_fila_por_uuid()` — misma normalización, pero SIN escribir en BD
(un GET nunca debe materializar nada).

### 8.4 Cuentas por Pagar — DELETE (antes NOT_APPLICABLE, ahora restringido)

```
DELETE /api/v1/proveedores/cuentas-pagar/{uuid}/
   ↓ CuentasPagarBusinessService.eliminar_cuenta_pagar(uuid, empresa_id)
        ├─ factura_uuid IS NOT NULL  → 400 (la obligación real sigue en Facturas, no se puede
        │                              "eliminar" solo el registro de seguimiento de pagos)
        ├─ valor_pagado > 0          → 400 (preserva historial financiero)
        └─ factura_uuid IS NULL Y valor_pagado == 0 → hard delete permitido
```

No se introdujo un estado `ANULADA` nuevo — decisión explícita para mantener mínima la máquina de
estados de `CuentasPagar` (`SIN_PAGO`/`PARCIAL`/`PAGADA`, sin `VENCIDA`/`ANULADA`, ya fijada en
PROVEEDORES-01). Tampoco se agregó `PATCH` genérico — sigue sin edición arbitraria de una obligación
de pago, solo `registrar-abono` y ahora `DELETE` restringido mutan el registro.

### 8.5 Frontend — Directorio, Cuentas por Pagar y Compras

- **Directorio** (`tables.py::ProveedorTable`, `proveedores_list.html`): columnas nuevas Tipo
  (badge Jurídica/Natural), Régimen (+ badge retenedor), Contacto (email/tel/ciudad) — mismo estilo
  que `clientes/tables.py::ClienteTable`. Filtros chips (Todos/Jurídicas/Naturales/
  Retenedores/Activos/Inactivos) + botón refrescar. Acciones ampliadas a Ver/Editar/
  Representantes/Eliminar (antes solo Editar/Eliminar).
- **Cuentas por Pagar** (`proveedores_list.html`, `cuentas_pagar_list.js`): el `<select>` de estado
  se reemplazó por chips (Todas/Sin Pago/Parcial/Pagadas/Vencidas), igual que Clientes/Cartera.
  Barra de KPIs en vivo (Pendiente/Vencida/Pagado histórico) conectada al endpoint
  `dashboard-kpis` ya existente. Acciones de fila: Ver (siempre), Abonar (si no PAGADA), Eliminar
  (solo si `puede_eliminar`, ver §8.4).
- **Creación de Proveedor** (`offcanvas_form.html`, `proveedores_form.js`): sección "Representante"
  nueva, condicional por `tipo_persona` — solo visible al crear (nunca al editar).
- **Compras** (`apps/tenant/compras/templates/tenant/compras/compras_list.html`, mismo patrón):
  "Órdenes de Compra" y "Plantillas de Numeración" pasan de 2 cards siempre visibles y apiladas a
  un menú de pestañas (nav-pills) — clic en cada menú muestra su lista. Sin cambios de backend.
