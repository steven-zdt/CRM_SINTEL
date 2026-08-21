# APP_bancos_NORMATIVE_MATRIX — Matriz normativa colombiana

Parte de `documentacion/audits/apps/APP_bancos_AUDIT.md` (FASE M).

## Alcance real de `bancos`

`apps/tenant/bancos` es un modulo de **conciliacion bancaria**:
registro de cuentas propias, importacion ETL de extractos Excel,
vinculacion (soft-reference UUID) de cada transaccion con
Factura/Proveedor/Cliente. **No calcula impuestos, no calcula
retenciones, no genera documentos fiscales.** Confirmado con grep
repo-wide: cero referencias a retefuente/reteica/reteiva/retencion en
todo el modulo.

## Matriz

| # | Obligacion | Sujeto obligado | Supuesto de hecho | Norma | Evidencia | Aplicabilidad |
|---|---|---|---|---|---|---|
| 1 | Conservacion de soportes contables/bancarios (extractos, conciliaciones) | Empresa (comerciante) | Todo `ExtractoBancario` importado | Codigo de Comercio (Colombia), art. 28 y 60 -- obligacion general de conservar libros y papeles de comercio (plazo usualmente referenciado como 10 anios) -- **sin articulo especifico citado en codigo, y correctamente asi**: es una politica de retencion de datos a nivel de infraestructura/backup, no logica de aplicacion | `models.py` (`ExtractoBancario.archivo_s3`, sin logica de expiracion/purga automatica encontrada) | **REQUIERE_VALIDACION organizacional, NO_APLICA a nivel de codigo de esta app** -- la conservacion de datos es responsabilidad de la politica de retencion/backup de la infraestructura (fuera del alcance de una auditoria de codigo de aplicacion), no una regla que `bancos` deba implementar en su propia logica de negocio |
| 2 | Trazabilidad de la conciliacion (quien concilio, con que documento, cuando) | Empresa (control interno) | Toda `TransaccionBancaria.conciliado=True` | Buenas practicas de control interno contable -- no una norma DIAN/legal especifica | `models.py` (`notas_conciliacion`, `factura_uuid`/`proveedor_uuid`/`cliente_uuid`), `created_at`/`updated_at` heredados de `SintelTenantBaseModel` | **OBLIGATORIO (control interno)** -- implementado correctamente: soft-references con trazabilidad, campo de notas libre para justificacion |
| 3 | Integridad del saldo importado (saldo_inicial/saldo_final vs suma de transacciones) | Empresa | Todo `ExtractoBancario` procesado | Sin norma legal especifica -- es una validacion de integridad de datos, no normativa | `models.py` (`saldo_inicial`, `saldo_final`) | **NO_APLICA normativa** -- pertenece a FASE E/F (ORM/integridad de datos), no a FASE M. Nota informativa: no se verifico en este pase si existe una validacion automatica de que `saldo_final = saldo_inicial + sum(valor)` -- deferred de baja prioridad si no existe, ver Deferred |

## Conclusion FASE M

`bancos` no genera hallazgos normativos de alta prioridad -- es un
modulo de conciliacion/ETL, no de calculo tributario. El unico punto
de atencion es informal (verificar si existe validacion de
consistencia de saldos, ver Deferred).

**Deferred:**

| # | Item | Prioridad |
|---|---|---|
| 1 | No se verifico en este pase si `ExtractoBancarioBusinessService.procesar_archivo_extracto()` valida que `saldo_final` coincida con `saldo_inicial + sum(transacciones.valor)` tras el ETL -- si no existe, seria una validacion de integridad de datos util (no normativa) | P3 |
