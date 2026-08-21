# APP_gastos_NORMATIVE_MATRIX — Matriz normativa colombiana

Parte de `documentacion/audits/apps/APP_gastos_AUDIT.md` (FASE M).

## HALLAZGO PRINCIPAL: resuelve el P1 pendiente de `proveedores`

La auditoria de `proveedores` (app 6/16) dejo un hallazgo P1 abierto:
`ProveedorBusinessService.obtener_configuracion_retenciones()`/
`calcular_componentes_retencion()` estaban documentadas como el flujo
SSoT para calcular retenciones al crear un gasto, pero sin ningun
consumidor real confirmado -- se registro como CONTRACT_DRIFT
pendiente de resolver "con evidencia completa al auditar gastos".

**Resuelto con evidencia directa del codigo de `gastos`:**
`GastoBusinessService.procesar_gasto()` (`business_service.py:189-200`)
**NO llama a nada de `proveedores`** -- llama a
`apps.tenant.contabilidad.services.retenciones_service.RetencionesService.
obtener_retenciones_desde_tercero(nit=proveedor.numero_documento,
tipo_tercero='PROVEEDOR', naturaleza='COMPRA', empresa_id=empresa.id)`,
seguido de `RetencionesService.calcular_monto_retencion()` para cada
tipo (RETEFUENTE/RETEICA/RETEIVA). Es una **tercera implementacion,
independiente y mas madura**, que vive en `contabilidad` -- confirmado
que consulta configuracion por `(tipo_tercero, nit, naturaleza,
empresa_id)` con fallback a un default, NO lee directamente los campos
`aplica_retefuente`/`retefuente_porcentaje` del modelo `Proveedor`.

**Conclusion:** las funciones de `proveedores` (`obtener_configuracion_
retenciones`/`calcular_componentes_retencion`) son **DEAD_CONFIRMED
real** (no solo "desconectadas de gastos" como se sospechaba, sino
**superseded por una arquitectura Pull Model correctamente
centralizada en `contabilidad`**, coherente con ADR-001). El
mecanismo real ya funciona; no hay gap funcional en `gastos`.
**Downgrade de prioridad: P1 -> P3** (limpieza de codigo muerto en
`proveedores`, no un riesgo de calculo incorrecto -- se actualiza el
registro en `APP_proveedores_AUDIT.md`/`APP_AUDIT_MASTER_STATUS.md`
en esta misma sesion, sin reabrir ni volver a testear la app
`proveedores` -- es solo una correccion de documentacion/prioridad, no
un cambio de codigo en esa app).

Evidencia adicional: migraciones `0011`/`0017` de `gastos` agregaron
`retefuente_porcentaje`/`reteica_porcentaje` directamente en
`DocumentoSoporte`; migracion `0021_remove_deprecated_retencion_
fields.py` los elimino -- confirma que el equipo ya migro
deliberadamente DESDE guardar porcentajes en el documento HACIA el
Pull Model puro (leer de `contabilidad.Retencion` via
`documento_origen_app='gastos'`), el mismo patron de "desacoplamiento
contable" ya visto en `inventario`/`clientes`/`empleados`.

## Matriz

| # | Obligacion | Sujeto obligado | Supuesto de hecho | Norma | Evidencia | Aplicabilidad |
|---|---|---|---|---|---|---|
| 1 | Retencion en la fuente (Retefuente) al pagar/causar un gasto a un proveedor | Empresa (agente retenedor) | Todo `DocumentoSoporte` con proveedor no autorretenedor | Delegado a `contabilidad.RetencionesService` (config por tercero+naturaleza+empresa) | `business_service.py:189-200` | **OBLIGATORIO** -- mecanismo Pull Model correctamente centralizado, confirmado funcional. Validacion de tarifas especificas por concepto/UVT queda fuera del alcance de `gastos` (responsabilidad de `contabilidad`, a auditar en esa app -- ver app 15/16) |
| 2 | ReteICA / ReteIVA en documentos soporte | Empresa (agente retenedor) | Igual a #1 | Igual a #1 | `business_service.py:189-200` | **OBLIGATORIO** -- mismo mecanismo |
| 3 | Numeracion de Documento Soporte dentro de rango DIAN autorizado | Empresa (emisor del documento soporte) | Todo `DocumentoSoporte` | Normativa DIAN de documento soporte (adquisiciones a no obligados a facturar) | `models.py` (`ResolucionDIAN`), `business_service.py:126` (DSV resolucion) | **OBLIGATORIO** -- mismo patron `select_for_update()`/rango visto en `empleados.ResolucionDIAN`, `ventas.ResolucionFacturacion`, `compras.PlantillaOrdenCompra` |
| 4 | Categorizacion contable del gasto (PUC) | Empresa | Todo `DocumentoSoporte` | Desacoplamiento contable (mig. eliminando `cuenta_*_uuid` de `gastos`, migraciones 0013-0015/0020) -- Contabilidad es la unica propietaria del mapeo PUC | `choices/categoria_contable.py`, migraciones 0013/0014/0015/0020 | **OBLIGATORIO** -- confirmado desacoplado correctamente, consistente con el patron ya visto en `inventario` (v3.10.2, mismo desacoplamiento) |

## Deferred

Ninguno nuevo para `gastos` en si (el mecanismo real funciona
correctamente). Ver `APP_proveedores_AUDIT.md` para el cierre del
item P1 (reclasificado a P3, informativo, sin accion de codigo en
esta sesion).
