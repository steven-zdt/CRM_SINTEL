# Matriz de Datos Requeridos — Maestros Empresariales SINTEL

**Fecha:** 2026-08-27. Verificado contra modelos reales (`apps/tenant/*/models.py`),
no inventado por intuición. Clasificación: REQUIRED (obligatorio a nivel de BD/
modelo, sin `blank=True`) / CONDITIONAL (obligatorio solo en un escenario) /
OPTIONAL (`blank=True`) / NOT_REQUIRED (no existe el campo).

## Cliente (`apps/tenant/clientes/models.py`)

| Dato | Obligatorio | Evidencia | Impacto si falta |
|---|---|---|---|
| `tipo_persona` | REQUIRED | sin `blank=True` | — |
| `tipo_documento` + `numero_documento` | REQUIRED, y **único por empresa** | `UniqueConstraint(empresa, tipo_documento, numero_documento)` | Sin esto, no se puede identificar el tercero ante DIAN |
| `razon_social` | REQUIRED | sin `blank=True` | — |
| `nombre_comercial` | OPTIONAL | `blank=True` | — |
| `regimen_tributario` | REQUIRED (campo), pero **sin lógica que lo use** | choices, sin `blank=True`; ninguna regla downstream verificada que aplique lógica distinta según su valor | Dato capturado pero descriptivo, no accionable hoy (ver `TAX_COMPLIANCE_MATRIX.md` §9) |
| `es_retenedor`/`aplica_retefuente`/`aplica_reteica`/`aplica_reteiva` + porcentajes | OPTIONAL (default `False`/`0`) | `default=False` | Sin esto, el cliente simplemente no es tratado como agente retenedor — comportamiento por defecto seguro |
| `email`/`telefono`/`direccion`/`ciudad` | OPTIONAL | `blank=True` en los 4 | Sin contacto, el cliente sigue siendo transaccionable pero sin datos de comunicación |
| `activo` | REQUIRED (con default) | `default=True` | Controla si el cliente puede recibir nuevas transacciones (no confirmado el enforcement exacto) |
| Municipio DIAN (código oficial) | **NOT_REQUIRED — no existe el campo** | Solo hay `ciudad` (texto libre, no catálogo de municipios DIAN) | Si se requiere reportar municipio DIAN estandarizado, el dato no existe hoy en forma estructurada |

## Proveedor (`apps/tenant/proveedores/models.py`)

| Dato | Obligatorio | Evidencia | Impacto si falta |
|---|---|---|---|
| `tipo_documento`+`numero_documento` | REQUIRED, único por empresa (mismo patrón que Cliente) | `UniqueConstraint` | Igual que Cliente |
| `digito_verificacion` | Presente como campo — obligatoriedad exacta no verificada en este pase | `models.py:78` | DV de NIT es relevante para validación DIAN; no se confirmó si el sistema lo calcula/valida automáticamente |
| `razon_social` | REQUIRED | sin `blank=True` | — |
| `regimen_tributario` | REQUIRED (campo) | igual que Cliente | Mismo comentario — descriptivo, no accionable |
| `actividad_economica_ciiu` | Presente como campo | `models.py:99` | **Dato relevante para ReteICA real** (que depende de actividad económica) — existe a nivel de captura pero `contabilidad.ConfiguracionRetenciones` no lo consume automáticamente (confirmado en `TAX_COMPLIANCE_MATRIX.md` §3) — oportunidad real, no un bug |
| `responsable_iva`/`gran_contribuyente`/`autoretenedor` | OPTIONAL con defaults sensatos | `default=True`/`False`/`False` | Autodeclarados, sin validación contra RUT/DIAN real |
| `es_retenedor` + flags/porcentajes | OPTIONAL | igual patrón que Cliente | — |
| `banco`/`tipo_cuenta`/`numero_cuenta` | OPTIONAL | `blank=True` en los 3 | Sin esto, no se puede automatizar el pago — requeriría captura manual en Bancos |
| `plazo_pago_dias` | Presente | `models.py:152` | Relevante para calendario de CxP/tesorería |

## Producto / Servicio (`apps/tenant/inventario/models.py`)

Ya auditado en profundidad en la misión de modernización de Inventario de esta
misma sesión (`docs/inventario/INVENTARIO_BASELINE.md`). Resumen: `codigo`+`nombre`
REQUIRED y únicos por empresa (`UniqueConstraint(Lower('codigo'), empresa)`);
`categoria` OPTIONAL (`SET_NULL`); `stock_actual`/`costo_promedio` son
DERIVED — nunca se capturan directamente, se calculan (`stock_actual` vía
Kardex) o se declaran estáticos por decisión (`costo_promedio`).

**Duplicación de concepto confirmada, no una fuente de verdad única:**
`cotizaciones` tiene su propio `Producto`/`Servicio` (línea de cotización,
texto libre) que NO es el mismo dato que `inventario.Producto`/`Servicio` —
confirmado en la misión de Cotizaciones de esta sesión: el picker de ítems de
Cotización no consume el catálogo de Inventario. Documentado como
desconexión real, no un bug (ver `BUSINESS_GAP_MATRIX.md`).

## Empleado / Contrato (`apps/tenant/empleados/models.py`)

Datos mínimos para nómina, ya verificados con cita normativa en
`documentacion/audits/apps/APP_empleados_NORMATIVE_MATRIX.md` (FASE M): tipo
de contrato (determina si aplica auxilio de transporte y prestaciones
sociales — `PRESTACION` las excluye explícitamente), salario base/IBC,
jornada. No se re-verificó campo por campo el modelo completo en esta sesión
(fuera de alcance re-auditar una app ya cubierta en profundidad).

## Cuenta Contable (`apps/tenant/contabilidad/models.py`)

`CuentaContable` (PUC) — poblada por `seed_cuentas_puc_pymes.py`.
`ConfiguracionRetenciones` requiere: `tipo_tercero`, `nit` (o `None` para
default), `naturaleza`, `empresa_id`, tarifa, y FK a `CuentaContable` de
destino — confirmado como la única fuente real de tarifas de retención
(ver `TAX_COMPLIANCE_MATRIX.md` §2).

## Regla aplicada en esta matriz

No se agregó ningún campo nuevo "para completar la tabla" — cada fila cita
el modelo real. Donde un dato razonable para un ERP colombiano (ej. código de
municipio DIAN estandarizado) no existe, se reporta como `NOT_REQUIRED —
campo ausente`, no se inventa como si ya existiera.
