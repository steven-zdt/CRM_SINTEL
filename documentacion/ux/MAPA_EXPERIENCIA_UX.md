# Mapa de Experiencia UX — SINTEL ERP

**FASE 1 de la mision de transformacion UX/UI.** Consolida en un solo
documento el recorrido completo del usuario a traves del sistema y la
relacion real entre las 16 apps, construido sobre lo verificado en la
revision de FASE 0/2/3 y el recorrido app-por-app documentado en
`UX_MASTER_BASELINE.md`. No es un diseño nuevo: es el mapa de lo que
existe hoy, con los puntos de friccion ya encontrados senalados en su
lugar.

**Fecha:** 2026-08-21. **Fuente:** lectura directa de codigo
(templates, viewsets, `apps/tenant/contabilidad/services/selectors.py`
para las relaciones contables reales), no inferencia especulativa —
donde algo no se pudo verificar en esta sesion se marca explicitamente
como "por confirmar".

---

## 1. Entrada al sistema

```
sintel.net.co (publico, marketing)
        |
        v
apps.public.tenants — registro / activacion (token de un solo uso)
        |
        v
<empresa>.sintel.net.co/workspace/ — primer login
        |
        v
#workspace-welcome — checklist "Primeros pasos" (FASE 2, ya construido)
        |
        v
Navegacion normal por el sidebar (6 grupos, ver §2)
```

- El dominio publico (`apps/public/core.PublicIndexView`) y el flujo
  de registro/activacion (`apps/public/tenants`) viven en el schema
  `public`, fuera del `workspace` -- son la unica parte del sistema
  que un usuario ve ANTES de tener una `Empresa` creada.
- **Hallazgo abierto (FASE 0, no corregido):** `config/urls_public.py`
  registra `PublicIndexView` en la ruta raiz `''` antes que
  `apps.public.tenants.LandingPageView`, que tambien apunta a `''` --
  la segunda vista queda inalcanzable (shadowed). No se toco por no
  ser parte del alcance de las fases ya ejecutadas.
- Tras la activacion, el usuario aterriza directo en `/workspace/`
  -- no hay pantalla intermedia de "bienvenida" separada, el propio
  checklist de FASE 2 cumple ese rol dentro de la pantalla de
  bienvenida ya existente.
- El checklist verifica 6 senales reales via API (cuenta, empresa,
  equipo, clientes, proveedores, inventario) -- ver
  `UX_MASTER_BASELINE.md` §FASE 2 para el detalle exacto de que
  considera "completo" cada paso.

---

## 2. Estructura de navegacion (sidebar, 6 grupos)

Criterio unico aplicado a los 15 modulos (corregido en la revision de
esta sesion -- ver `UX_MASTER_BASELINE.md` §FASE 3.1):

| Grupo | Criterio | Modulos |
|---|---|---|
| Inicio | Vista general, no transaccional | Dashboard |
| Configuración | Administracion del tenant en si | Usuarios y roles, Mi empresa, Equipo |
| Relaciones | Contrapartes externas | Clientes, Proveedores |
| Comercial | Documentos de transaccion con esas contrapartes | Cotizaciones, Ventas, Compras |
| Operación | Recursos internos de ejecucion | Inventario, Proyectos, Gastos |
| Finanzas | Registro fiscal/contable formal | Facturas, Bancos, Contabilidad |

Todo vive en un unico shell SPA-like (`workspace.html`) -- cambiar de
modulo no recarga la pagina, solo alterna que `<section>` esta visible
(`workspace.js`, `showTab()`). El contexto de sede activa se muestra
en un selector propio del navbar superior (independiente del sidebar,
ya existente antes de esta mision).

---

## 3. Las 16 apps: que hacen y con que se conectan

### 3.1 Configuración

- **Usuarios y roles** (`perfil`) -- quien tiene acceso al tenant y
  con que rol (ADMIN/OPERADOR/VISOR). Un `TenantProfile` por persona,
  1:1 con su cuenta de usuario global. Rotulo corregido en esta sesion
  (antes decia "Mi perfil", prometia una pantalla personal que nunca
  existio).
- **Mi empresa** (`empresa`) -- datos fiscales/de contacto de la
  empresa (singleton, 1 solo registro por tenant), mas Sedes y Areas.
  Es el SSoT que Perfil, Empleados y (indirectamente, via Sedes)
  Inventario/Ventas/Compras consultan para ubicar a cada persona/
  transaccion en una sede/area concreta.
- **Equipo** (`empleados`) -- registro de personal: datos del
  empleado, contratos, nominas (devengos), liquidaciones,
  resoluciones DIAN de nomina electronica. Alimenta directamente
  Contabilidad (ver §4) para el gasto de nomina.

### 3.2 Relaciones

- **Clientes** -- directorio de clientes + contactos + cartera
  (cuentas por cobrar). La cartera se resume por cliente
  (`cartera_resumen`: pendiente/cobrada) pero las facturas que la
  generan viven en el modulo Facturas, no aqui.
- **Proveedores** -- directorio + representantes legales + cuentas
  por pagar (simetrico a Clientes, pero para el lado de compra).

### 3.3 Comercial

- **Cotizaciones** -- propuesta comercial a un Cliente, previa a la
  Venta. (Relacion Cotizacion -> Venta: por confirmar en el codigo,
  no verificada explicitamente en esta sesion.)
- **Ventas** -- la transaccion de venta en si (estados: Borrador,
  Facturada DIAN, Anulada). Genera salida de inventario
  (`VentaBusinessService._generar_salida_inventario()`, referenciado
  en trabajo previo de esta sesion) y es el origen de negocio de una
  Factura de venta.
- **Compras** -- ordenes de compra a un Proveedor. Tiene su propio
  sistema de plantillas de numeracion. Es el origen de negocio de una
  Factura de compra y de una entrada de inventario en la recepcion
  (`RecepcionCompraBusinessService.confirmar_recepcion()`,
  referenciado en trabajo previo de esta sesion).

### 3.4 Operación

- **Inventario** -- 5 sub-vistas: Categorias, Productos, Servicios,
  Activos Fijos, Movimientos (Kardex). Es el registro de existencias
  que Ventas/Compras mueven y que Contabilidad pulea via
  `KardexService`.
- **Proyectos** -- gestion de proyectos con logica de costos propia
  (tareas, costeo). Conectado a Inventario para consumo de material
  por proyecto (contenedor de offcanvas propio
  `offcanvas-container-inventario-proyecto`, distinto del generico de
  Inventario -- ver nota de colision de IDs en el codigo,
  `list_inventario.html`).
- **Gastos** -- registro de gastos operativos + resoluciones DIAN de
  gastos. No requiere necesariamente una Orden de Compra asociada
  (cubre gastos que no pasan por el flujo formal de Compras).

### 3.5 Finanzas

- **Facturas** -- el documento fiscal DIAN (factura electronica),
  cubre tanto ventas como compras (confirmado: la UI tiene tabs
  separados `venta`/`compra` dentro del mismo modulo). Se crea
  principalmente por **importacion de XML DIAN**
  (`FacturaBusinessService.guardar_desde_dto()`), no por captura
  manual -- el `NotaCreditoViewSet` incluso bloquea POST/PUT/PATCH
  explicitamente. Es el modulo mas complejo y fragil del sistema
  (ver hallazgo de offcanvas no corregido en
  `UX_MASTER_BASELINE.md` §FASE Facturas).
- **Bancos** -- cuentas bancarias + extractos (importables). Provee
  el lado de caja/tesoreria que concilia contra Facturas/Contabilidad.
- **Contabilidad** -- el libro mayor. Nunca recibe escrituras directas
  de otras apps (ADR-001, Pull Model): en cambio, **jala** datos de
  6 apps de origen reales (confirmado leyendo
  `APP_ORIGEN_PREFIJOS` en `apps/tenant/contabilidad/services/selectors.py`):
  `facturas`, `clientes`, `gastos`, `empleados`, `inventario`,
  `proveedores` -- cada una mapeada a un conjunto especifico de
  cuentas PUC. **Notese que `ventas` y `compras` NO estan en esa
  lista** -- su efecto contable llega indirectamente via Facturas
  (el documento fiscal) e Inventario (el movimiento de stock), no
  directamente. Esto es coherente con la separacion Comercial
  (negociacion) vs Finanzas (registro fiscal) que ya aplica el
  sidebar.

---

## 4. Flujos de negocio transversales (cruzan varias apps)

### 4.1 Ciclo de venta

```
Cliente (ya registrado, o se crea aqui)
   -> Cotizacion (opcional)
   -> Venta (Borrador)
   -> Factura DIAN importada/generada (venta pasa a "Facturada DIAN")
   -> Inventario: salida de stock
   -> Contabilidad: pulea desde Facturas + Inventario (ingreso, IVA, costo de venta, cartera)
   -> Cliente: cartera se actualiza (cuenta por cobrar)
   -> Bancos: al recibir el pago, se concilia contra el extracto
```

### 4.2 Ciclo de compra

```
Proveedor (ya registrado, o se crea aqui)
   -> Orden de Compra
   -> Recepcion de la orden -> entrada de Inventario
   -> Factura de compra (Facturas, tab "compra") o Gasto directo
   -> Contabilidad: pulea desde Facturas/Gastos + Inventario + Proveedores (costo, IVA descontable, cuenta por pagar)
   -> Proveedor: cuenta por pagar se actualiza
   -> Bancos: al pagar, se concilia contra el extracto
```

### 4.3 Ciclo de nomina

```
Empleado (Equipo) -> Contrato -> Devengo (nomina del periodo) -> Liquidacion (al terminar el contrato)
   -> Contabilidad: pulea directo desde Empleados (gasto de nomina + pasivos laborales, prefijos clase 25/51)
```

### 4.4 Devoluciones (Notas Credito) — gap conocido, no resuelto

Documentado en trabajo previo de esta sesion (plan
`linked-drifting-kitten`, no ejecutado aun): el mecanismo de
`ENTRADA_DEVOLUCION` en Inventario/Kardex ya existe y esta probado,
pero `NotaCredito` no tiene lineas (`ItemNotaCredito` no existe como
modelo), asi que una devolucion real hoy NO dispara un movimiento de
inventario automatico -- queda como documento de solo cabecera. Es un
gap de **backend/datos**, no de UI -- fuera del alcance de la mision
UX, pero relevante para entender por que "devolver un producto" no
tiene hoy un flujo visible en la interfaz.

---

## 5. Brechas y hallazgos conocidos (consolidado)

Todos ya documentados en detalle en `UX_MASTER_BASELINE.md`; aqui solo
el indice:

| Hallazgo | Estado | Seccion en UX_MASTER_BASELINE.md |
|---|---|---|
| `LandingPageView` inalcanzable (shadowed por `PublicIndexView`) | Abierto, no corregido | FASE 0 |
| Resaltado de item activo en sidebar roto (`.active` vs `aria-current`) | Corregido | FASE 3 |
| Sidebar sin agrupacion conceptual | Corregido | FASE 3 |
| Sin pantalla de onboarding/progreso inicial | Corregido (checklist) | FASE 2 |
| "Mi perfil" prometia pantalla personal, mostraba roster de equipo | Corregido (rotulo) | FASE Perfil |
| Badge "SSoT" expuesto al usuario | Corregido (eliminado) | FASE Empresa |
| "Operación" sin criterio propio de agrupacion | Corregido (dividido) | FASE 3.1 |
| Offcanvas duplicado/debilitado en Inventario y Proyectos | Corregido (consolidado) | FASE Inventario/Cotizaciones/Proyectos |
| Offcanvas duplicado en Facturas (`facturas_main.js`) | Abierto, deliberadamente no corregido (alto riesgo) | FASE Facturas |
| Offcanvas en Empleados (`devengo_editor.js`) | Revisado, descartado (workaround valido, no es bug) | FASE Empleados/Dashboard |
| Test `test_perfil_removed_from_sidebar` pasa vacio (selector desactualizado) | Abierto, no corregido (decision de producto) | FASE Perfil |
| Tests `test_hash_routing_still_works` / `test_workspace_contains_all_view_sections` fallan (arquitectura obsoleta que esperan) | Abierto, no corregido | FASE Perfil |
| Relacion Cotizacion -> Venta | Por confirmar (no verificado en codigo esta sesion) | -- |
| `ItemNotaCredito` no existe -- devoluciones sin movimiento de inventario automatico | Gap de backend, fuera de alcance UX | -- |

---

## 6. Que NO cubre este mapa (fuera de alcance de esta pasada)

- **Formularios individuales de creacion/edicion** (los offcanvas de
  "Nuevo Cliente", "Nueva Venta", etc.) -- esta pasada se centro en
  navegacion/listados, no en el contenido de cada formulario. Pendiente
  si se decide continuar esa fase.
- **Responsive/mobile** -- no evaluado visualmente en esta sesion (ver
  limitacion de la herramienta de navegador documentada en
  `UX_MASTER_BASELINE.md` §FASE 3, verificacion).
- **Accesibilidad mas alla de `aria-current`** -- no se hizo una
  auditoria de contraste, navegacion por teclado ni lectores de
  pantalla.
