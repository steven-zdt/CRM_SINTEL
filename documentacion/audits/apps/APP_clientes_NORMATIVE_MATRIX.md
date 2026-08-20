# APP_clientes_NORMATIVE_MATRIX — Matriz normativa colombiana

Parte de `documentacion/audits/apps/APP_clientes_AUDIT.md` (FASE M).

## Hallazgo principal: `clientes` es solo configuracion, no calculo

A diferencia de `empleados` (que calcula deducciones/prestaciones
directamente en `business_service.py` con citas de articulo inline),
`apps/tenant/clientes` **no calcula retenciones**. El modelo `Cliente`
solo almacena la CONFIGURACION de si un cliente es sujeto de retencion
y a que tarifa (`es_retenedor`, `aplica_retefuente`/
`retefuente_porcentaje`, `aplica_reteica`/`reteica_porcentaje`,
`aplica_reteiva`/`reteiva_porcentaje`). Confirmado en
`business_service.py:_sanitize_retenciones()` (lineas 178-191): la
unica logica presente es Zero Trust -- si `es_retenedor=False`, fuerza
todos los flags/porcentajes a 0/False; si un flag individual es False,
fuerza su porcentaje a 0. **No hay calculo de retencion, no hay
validacion de tarifas contra la normativa DIAN vigente (UVT, cuantias
minimas, tarifas por concepto), no hay articulo citado.**

Segun el `.agent/AUDITORIA_FLUJO_CLIENTES.md` (linea 486, verificado):
*"Retenciones se delegan a `RetencionesService` (ADR-001). Clientes
solo guarda config (porcentajes)."* -- el calculo real, la validacion
de tarifas y la aplicabilidad normativa (cuantias minimas UVT, tipos
de concepto) vive en `apps/tenant/contabilidad` (Pull Model), **fuera
del alcance de esta app**. Se revisara con evidencia completa cuando
se audite `contabilidad` (app 15/16 de esta mision).

## Matriz (alcance de `clientes` unicamente)

| # | Obligacion | Sujeto obligado | Supuesto de hecho | Norma | Evidencia | Aplicabilidad |
|---|---|---|---|---|---|---|
| 1 | Identificacion tributaria por documento legal (NIT/CC/CE/PA) unico por empresa | Empresa (tenant) | Todo cliente registrado | Estatuto Tributario (identificacion de terceros) -- sin articulo especifico citado en codigo | `models.py` (`UniqueConstraint(empresa, tipo_documento, numero_documento)`) | **OBLIGATORIO** -- constraint DB, no solo convencion |
| 2 | Clasificacion de regimen tributario del cliente (SIMPLE/ORDINARIO/NO_RESP) | Empresa (tenant) | Todo cliente | Ley 2010/2019 (Regimen Simple de Tributacion) -- **REQUIERE_VALIDACION**: el codigo no cita el articulo/ley especifica para esta clasificacion, es un campo de choices sin logica normativa asociada visible en `clientes` | `models.py` campo `regimen_tributario` | **REQUIERE_VALIDACION** -- el campo existe y se usa como config downstream (posiblemente en contabilidad), pero esta app no valida ni aplica reglas segun el valor |
| 3 | Configuracion de agente retenedor y tarifas (Retefuente/ReteICA/ReteIVA) | Cliente (como cara del tercero) / Empresa (como agente retenedor potencial) | Cliente marcado `es_retenedor=True` | Delegado a `RetencionesService` en `contabilidad` (ADR-001) -- **fuera del alcance de esta app** | `business_service.py:_sanitize_retenciones()` | **NO_APLICA a esta app directamente** -- `clientes` solo persiste config con Zero Trust (limpieza de flags inconsistentes), no calcula ni valida tarifas contra normativa vigente. Ver auditoria de `contabilidad` (pendiente) para el hallazgo normativo real. |

## Conclusion FASE M

`clientes` no requiere items normativos propios adicionales mas alla
de la trazabilidad de que es un modulo de **configuracion**, no de
**calculo**. El deferred real (validacion de tarifas de retencion
contra normativa DIAN vigente) se registra aqui como puntero y se
resolvera con evidencia completa en la auditoria de `contabilidad`
(app 15/16), que es donde vive `RetencionesService`.

**Deferred:**

| # | Item | Prioridad |
|---|---|---|
| 1 | Validacion de tarifas Retefuente/ReteICA/ReteIVA contra normativa DIAN vigente -- pertenece a `contabilidad` (RetencionesService), no a `clientes`. Revisar cuando se audite esa app. | P3 para `clientes` (fuera de su alcance real) |
