# APP_contabilidad_NORMATIVE_MATRIX — Matriz normativa colombiana

Parte de `documentacion/audits/apps/APP_contabilidad_AUDIT.md` (FASE M).
**Cierra el ciclo de verificacion de retenciones** iniciado en
`clientes`/`proveedores`/`gastos`: aqui vive la implementacion real
(`RetencionesService`), ya referenciada por 4 apps distintas.

## `RetencionesService` — verificado

`services/retenciones_service.py`:

- `obtener_retenciones_desde_tercero(nit, tipo_tercero, naturaleza,
  empresa_id)` (verificado, ver linea 34-74 del archivo): busca
  `ConfiguracionRetenciones` especifica por `(tipo_tercero, nit,
  naturaleza, empresa_id)`, con fallback a un default
  `(tipo_tercero, nit=None, naturaleza, empresa_id)`, y retorna ceros
  si no existe ninguna configuracion. **Zero-Trust**: `empresa_id`
  obligatorio, lanza `ValueError` si falta.
- `calcular_monto_retencion(tipo, porcentaje, base)` (verificado
  linea por linea): formula simple y correcta `monto = base *
  porcentaje / 100`, con guard de porcentaje/base en cero.

`models.py:ConfiguracionRetenciones` (verificado linea por linea):
tabla real de configuracion **por tenant, por tercero (NIT especifico
u override default), por tipo de retencion, por naturaleza de
transaccion**, con FK a `CuentaContable` (asiento donde se registra),
`UniqueConstraint` sobre la combinacion completa (solo si `activa`).
**Las tarifas NO estan hardcodeadas en el codigo** -- son datos de
configuracion que cada tenant/contador debe cargar segun su perfil
fiscal real (correcto: las tarifas de Retefuente/ReteICA/ReteIVA
varian por concepto, municipio y periodo vigente en Colombia, un
hardcode en el codigo de aplicacion seria normativamente fragil e
imposible de mantener actualizado).

**Conclusion:** esto confirma y CIERRA el hallazgo iniciado en
`proveedores` (funciones dead-code con tarifas hardcodeadas 4%/0.966%)
y contrasta positivamente: la arquitectura real y correcta
(`contabilidad.RetencionesService` + `ConfiguracionRetenciones`) SI
sigue el patron correcto -- configuracion externa, no tarifas
hardcodeadas en logica de aplicacion.

## Pull Model — Extractores (`integracion/extractores/`)

4 extractores confirmados por nombre de archivo:
`extractores/facturas.py`, `extractores/gastos.py`,
`extractores/inventario.py`, `extractores/nomina.py` -- consistentes
con las integraciones ya confirmadas end-to-end en las auditorias de
`ventas` (F23, extractor F22 confirmado en tests), `gastos`
(RetencionesService), `inventario` (`get_movimientos_timeline()`),
`empleados` (extraccion de `Devengo`). No se revisaron linea por
linea en este pase (alcance de tiempo) -- el diseño Pull Model en si
ya fue validado indirectamente por las 13 apps auditadas previamente
que lo consumen sin encontrar contratos rotos.

## Matriz

| # | Obligacion | Sujeto obligado | Supuesto de hecho | Norma | Evidencia | Aplicabilidad |
|---|---|---|---|---|---|---|
| 1 | Configuracion de retenciones por tercero/naturaleza, no hardcodeada | Empresa (via su contador/administrador) | Toda transaccion con retencion aplicable | Estatuto Tributario (tarifas variables por concepto/municipio/periodo) | `models.py:ConfiguracionRetenciones` (verificado) | **OBLIGATORIO -- implementado correctamente**, arquitectura Pull Model centralizada y configurable |
| 2 | Plan Unico de Cuentas (PUC) colombiano como catalogo base | Empresa | Toda cuenta contable (`CuentaContable`) | Decreto 2650/1993 (PUC) y actualizaciones | `management/commands/seed_cuentas_puc_pymes.py` (comando de seed, confirma intencion de poblar PUC estandar) | **OBLIGATORIO** -- mecanismo de seed existe; no se verifico en este pase si el catalogo sembrado esta actualizado a la version PUC vigente (deferred) |
| 3 | Periodos contables (apertura/cierre) | Empresa | Todo asiento contable | Practica contable estandar, Codigo de Comercio | `models.py:PeriodoContable`, `seed_periodos_contables.py` | **OBLIGATORIO** -- mecanismo existe, no auditado en profundidad en este pase |
| 4 | Catalogo NIIF (`CatalogoMaestroNIIF`) | Empresa | Clasificacion contable segun normas NIIF/NIC aplicables a PYMES en Colombia | Decreto 3022/2013 (NIIF para PYMES) y relacionados | `models.py:CatalogoMaestroNIIF`, `poblar_catalogo_niif.py` | **OBLIGATORIO** -- mecanismo de seed existe, contenido no auditado en profundidad |

## Deferred

| # | Item | Prioridad |
|---|---|---|
| 1 | Contenido de los seeds (PUC, NIIF, periodos, reglas contables, tipos de comprobante) no verificado contra la version normativa vigente -- serian necesarios 5 comandos de seed revisados campo por campo, fuera del alcance de tiempo de esta auditoria de 16 apps | P2 (requiere validacion contable especializada, no solo de codigo) |
| 2 | Extractores del Pull Model (`facturas.py`, `gastos.py`, `inventario.py`, `nomina.py`) no revisados linea por linea en este pase -- validados indirectamente por las apps consumidoras | P3 |
