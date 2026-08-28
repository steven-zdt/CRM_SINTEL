# Matriz de Cumplimiento Tributario — SINTEL ERP

**Fecha:** 2026-08-27. Auditor: análisis de código real, no asesoría legal.

**Advertencia obligatoria (no negociable):** esta matriz distingue explícitamente
dos columnas que NUNCA deben confundirse:

- **IMPLEMENTADO_TECNICAMENTE** = existe código que ejecuta un cálculo/mecanismo
  correspondiente a un concepto tributario, verificado por lectura de código real.
- **CUMPLIMIENTO_LEGAL_VERIFICADO** = un profesional contable/tributario colombiano
  confirmó, contra la fuente normativa oficial vigente, que ese cálculo es correcto
  para el régimen/actividad/período de un contribuyente real.

**Ninguna fila de esta matriz tiene `CUMPLIMIENTO_LEGAL_VERIFICADO = SI`.** Esta
sesión no tiene capacidad de validar contra fuentes DIAN/Ministerio del Trabajo
oficiales vigentes. Toda fila marca `PROFESSIONAL_REVIEW_REQUIRED` en esa columna
salvo que se indique lo contrario explícitamente.

Fuente de evidencia: lectura directa de código (citado archivo:línea donde
existe) + los 9 `documentacion/audits/apps/APP_*_NORMATIVE_MATRIX.md` (FASE M,
2026-08-21), verificados como vigentes salvo donde se indica DRIFT.

---

## 1. IVA (Impuesto sobre las Ventas)

| Campo | Detalle |
|---|---|
| Hecho generador | Venta de bienes/servicios gravados (`ItemVenta`/`ItemOrdenCompra`) |
| Base | Valor del ítem (`precio_unitario × cantidad`, antes de impuesto) |
| Tarifa | Campo `porcentaje_iva` — **entrada libre del usuario, sin validación contra tarifas vigentes (0%/5%/19%)**. Confirmado en `apps/tenant/ventas/services/business_service.py:331`, `apps/tenant/ventas/models.py:266`, `apps/tenant/compras/services/crud_service.py:133,203` |
| Naturaleza | Impuesto al consumo, trasladado al comprador |
| Documento | `Factura` (venta, real DIAN) / `OrdenCompra` (interno, no fiscal) |
| Origen | `ventas`/`compras` (captura) → `contabilidad` (registro vía Pull) |
| Cuenta | Resuelta por `contabilidad` vía `ReglaContable`, no hardcodeada en apps de negocio (confirmado, Pure Pull Model) |
| Declaración | No implementada (SINTEL no genera declaración de IVA) |
| Pago | Fuera de alcance de esta matriz (gestión de tesorería, no cálculo del impuesto) |
| Vencimiento | No implementado — sin calendario tributario en el sistema (ver §7) |
| Responsable | Empresa (contribuyente) |
| Fuente normativa | Estatuto Tributario — **sin artículo específico citado en código** |
| Vigencia | REGIMEN_NOT_VERIFIED — el sistema no distingue régimen del contribuyente para efectos de IVA |
| Estado de implementación | **IMPLEMENTADO_TECNICAMENTE: PARCIAL** — el campo existe y se traslada correctamente al documento, pero sin validación de tarifa. Mayor riesgo en `ventas` (factura DIAN real) que en `compras` (documento interno) |
| CUMPLIMIENTO_LEGAL_VERIFICADO | **NO — PROFESSIONAL_REVIEW_REQUIRED** |

## 2. Retención en la Fuente (Retefuente)

| Campo | Detalle |
|---|---|
| Hecho generador | Pago/abono en cuenta a un tercero (proveedor) sujeto de retención |
| Base | Valor del documento soporte/gasto sujeto a retención |
| Tarifa | **No hardcodeada** — configurable por tenant vía `ConfiguracionRetenciones` (`apps/tenant/contabilidad/models.py`), resuelta por `(tipo_tercero, nit, naturaleza, empresa_id)` con fallback a default. Confirmado en `apps/tenant/contabilidad/services/retenciones_service.py:34-74` |
| Naturaleza | Anticipo del impuesto de renta del tercero, retenido por el agente retenedor |
| Documento | `DocumentoSoporte` (gastos) |
| Origen | `gastos.GastoBusinessService.procesar_gasto()` (`business_service.py:189-200`) llama `contabilidad.RetencionesService` directamente — **mecanismo real, confirmado funcional** |
| Cuenta | FK a `CuentaContable` dentro de `ConfiguracionRetenciones` — configurable, no hardcodeada |
| Declaración | No implementada (SINTEL no genera formulario de retención) |
| Pago | Fuera de alcance (tesorería) |
| Vencimiento | No implementado (ver §7) |
| Responsable | Empresa (agente retenedor) |
| Fuente normativa | Estatuto Tributario — sin artículo específico citado en el mecanismo real (`contabilidad`) |
| Vigencia | REGIMEN_NOT_VERIFIED |
| Estado de implementación | **IMPLEMENTADO_TECNICAMENTE: SI, arquitectura correcta** — configuración externa por tenant, no tarifas fijas en código. Esta es la ÚNICA vía real de cálculo de retenciones en el sistema hoy |
| CUMPLIMIENTO_LEGAL_VERIFICADO | **NO — PROFESSIONAL_REVIEW_REQUIRED** (nadie verificó que las tarifas que un tenant configure sean las vigentes) |

**Nota de higiene — código muerto confirmado, no un gap funcional:**
`ProveedorBusinessService.obtener_configuracion_retenciones()`/
`calcular_componentes_retencion()` (`apps/tenant/proveedores/services/business_service.py:164-208`)
tienen tarifas hardcodeadas (Retefuente 4% plano, ReteICA 0.966% solo para
personas naturales) que **no se ejecutan en ningún flujo real** — confirmado
por `documentacion/audits/apps/APP_gastos_NORMATIVE_MATRIX.md`: `gastos` usa
el mecanismo real de `contabilidad`, no estas funciones. Candidato a
DEAD_CONFIRMED (limpieza de código, no urgente — no afecta cálculos reales).

**Gap real no cerrado por ninguna auditoría previa — dirección inversa de la retención:**
Ningún documento revisado confirma que SINTEL modele el caso en que **un
cliente actúa como agente retenedor y practica retención sobre lo que nos
paga** (Retefuente/ReteICA/ReteIVA descontados de la factura de venta que
emitimos). `Cliente.es_retenedor`/`aplica_retefuente` (`apps/tenant/clientes/models.py`)
existen como campos de configuración, pero ningún documento de evidencia
revisado confirma que `ventas`/`facturas` los use para calcular un menor
valor a cobrar o para registrar la retención que el cliente practicó.
**Marcado GAP, no confirmado con lectura de código propia en esta sesión —
requiere verificación dirigida** (ver `BUSINESS_GAP_MATRIX.md`).

## 3. ReteICA (Retención de Industria y Comercio)

| Campo | Detalle |
|---|---|
| Hecho generador | Igual a Retefuente, vía el mismo mecanismo `ConfiguracionRetenciones`/`RetencionesService` |
| Tarifa | Configurable por tenant — **correcto arquitectónicamente**, dado que la tarifa real de ReteICA en Colombia varía por municipio y actividad económica (CIIU), algo que un valor fijo en código nunca podría representar correctamente |
| Estado de implementación | **IMPLEMENTADO_TECNICAMENTE: SI** — mismo mecanismo que Retefuente (`gastos` → `contabilidad.RetencionesService`) |
| CUMPLIMIENTO_LEGAL_VERIFICADO | **NO — PROFESSIONAL_REVIEW_REQUIRED** (¿el tenant configuró la tarifa de SU municipio y actividad? el sistema no lo valida ni lo puede validar sin un catálogo municipal, que no existe) |

Misma nota de código muerto: `ProveedorBusinessService.calcular_componentes_retencion()`
tenía ReteICA hardcodeado a 0.966% solo para personas naturales (tarifa
simplificada e incorrecta como regla general — ReteICA depende de actividad/
municipio, no de tipo de persona) — confirmado no ejecutado en ningún flujo real.

## 4. ReteIVA

| Campo | Detalle |
|---|---|
| Estado de implementación | **IMPLEMENTADO_TECNICAMENTE: SI** — mismo mecanismo `ConfiguracionRetenciones`/`RetencionesService`, sin tarifa hardcodeada |
| CUMPLIMIENTO_LEGAL_VERIFICADO | **NO — PROFESSIONAL_REVIEW_REQUIRED** |

## 5. Facturación electrónica DIAN (CUFE / UBL 2.1 / XAdES / transmisión)

| Componente | Estado |
|---|---|
| CUFE (código único de facturación) | **IMPLEMENTADO_TECNICAMENTE: SI, verificado línea por línea** — `apps/tenant/facturas/services/dian/cufe.py`, SHA-384 sobre 14 campos, cita explícita "Anexo Técnico FE DIAN v1.9 §5.4.3" en docstring, orden de campos y códigos de impuesto (01=IVA, 04=INC, 03=ICA) consistentes con la estructura pública conocida del algoritmo |
| XML UBL 2.1 | **IMPLEMENTADO_TECNICAMENTE: SI** (revisión estructural, no campo-por-campo) — `ubl21_builder.py` (429 líneas) |
| Firma XAdES-EPES | **IMPLEMENTADO_TECNICAMENTE: SI** — `xades_signer.py`, cita "Anexo Técnico FE DIAN v1.9 §5.5". Fallback seguro: sin `settings.DIAN_CERT_P12` configurado, retorna XML sin firmar (modo borrador), nunca firma con clave falsa |
| **Transmisión real al webservice DIAN** | **IMPLEMENTADO_TECNICAMENTE: NO — GAP CONFIRMADO, CRÍTICO.** Grep exhaustivo (`requests.post`, `requests.Session`, `zeep`, `SOAP`, `wsdl`) en toda `apps/tenant/facturas/` → cero resultados de una llamada de red real a `dian.gov.co`. `FacturaAnexos.application_response_xml` solo se puebla desde un comando de backfill histórico o desde el parser de XML de facturas de COMPRA importadas (que ya traen la respuesta incluida) — **nunca desde una transmisión propia de venta** |
| **CUMPLIMIENTO_LEGAL_VERIFICADO como factura electrónica válida** | **NO. Sin transmisión real, ninguna factura emitida por SINTEL tiene validez legal como factura electrónica ante la DIAN**, independientemente de que el CUFE/XML/firma sean técnicamente correctos. Este es el hallazgo más crítico de toda la matriz — **EXTERNAL_DEPENDENCY** (requiere credenciales/certificado/WSDL DIAN reales para siquiera empezar a cerrarse) |

## 6. Nómina Electrónica DIAN (DSPNE)

| Componente | Estado |
|---|---|
| Separación conceptual (documento de nómina vs. transmisión electrónica) | **IMPLEMENTADO_TECNICAMENTE: SI** — `TransmisionNominaDIAN` es modelo separado de `Devengo`/`Contrato`, con `ResolucionDIAN`, consecutivo, CUNE |
| Deducciones de ley (salud 4%, pensión 4%, exclusión de auxilio de transporte) | **IMPLEMENTADO_TECNICAMENTE: SI, con cita normativa inline** (Ley 100/1993 arts. 204/20/30) — `apps/tenant/empleados/services/business_service.py:634,642,643` |
| Recargos (extra diurna +25%, nocturna +75%, nocturno ordinario +35%) | **IMPLEMENTADO_TECNICAMENTE: SI, con cita** (CST art. 168) — `business_service.py:645-650` |
| Jornada de referencia (Ley 2101/2021) | **IMPLEMENTADO_TECNICAMENTE: PARCIAL** — usa 42h/200h fijo, sin parametrizar el escalonamiento progresivo de la ley por fecha histórica del período. `PROFESSIONAL_REVIEW_REQUIRED` si el tenant tiene devengos retroactivos anteriores al escalón final |
| Límite de 2h/día en horas extra (CST art. 168) | **REQUIERE_VALIDACION** — existe guard de tope mensual agregado (80h/tipo, 200h/mes), no se confirmó si hay guard diario explícito |
| Prima, cesantías, intereses sobre cesantías, vacaciones | **IMPLEMENTADO_TECNICAMENTE: SI, formulas correctas** (`business_service.py:791,792,795,798`) pero **sin cita normativa inline** (a diferencia de las deducciones) — brecha de trazabilidad documental, no de cálculo |
| **Transmisión XML real a DIAN (DSPNE)** | **IMPLEMENTADO_TECNICAMENTE: NO — GAP CONFIRMADO (DEUDA-11, abierta desde 2026-06-17).** `estado_dian` permanece `PENDIENTE` indefinidamente; `xml_enviado`/`xml_respuesta` nunca se pueblan desde una transmisión real. Mismo patrón que facturas (§5), aplicado a nómina — **EXTERNAL_DEPENDENCY** |

## 7. Calendario tributario / vencimientos

**No existe ningún mecanismo en el código** para vencimientos de declaración/pago
por obligación tributaria (IVA, Retefuente, ICA, renta) ni calendario por último
dígito de NIT. Confirmado por ausencia — ningún modelo `CalendarioTributario`/
`VencimientoFiscal` fue encontrado en ninguna de las auditorías previas ni en
esta sesión. **No se hardcodeó ninguna fecha** (correcto, per regla §41 del
prompt maestro: preferir un catálogo versionado a fechas fijas en código) — pero
tampoco existe el catálogo. **GAP** — si el negocio necesita esta capacidad,
requiere una decisión de producto nueva, no una corrección de bug.

## 8. Plan Único de Cuentas (PUC) y NIIF para PYMES

| Componente | Estado |
|---|---|
| PUC como catálogo base | **IMPLEMENTADO_TECNICAMENTE: SI** — `management/commands/seed_cuentas_puc_pymes.py` (comando de seed existe) |
| Catálogo NIIF (`CatalogoMaestroNIIF`) | **IMPLEMENTADO_TECNICAMENTE: SI** — modelo + comando de seed (`poblar_catalogo_niif.py`) |
| **Contenido de los seeds verificado contra la versión normativa vigente** | **NO VERIFICADO en ninguna auditoría previa ni en esta sesión** — requeriría revisar 5 comandos de seed campo por campo contra la fuente oficial (Decreto 2650/1993 y actualizaciones, Decreto 3022/2013). **PROFESSIONAL_REVIEW_REQUIRED** |
| No hardcodeo de PUC en apps de negocio | **CONFIRMADO** (Pure Pull Model) — `inventario`, `gastos`, `clientes`/`proveedores` fueron desacoplados explícitamente (migraciones que eliminan campos `cuenta_*_uuid`), `contabilidad` es la única propietaria del mapeo |

## 9. Clasificación de régimen del contribuyente

`Cliente.regimen_tributario` (choices: SIMPLE/ORDINARIO/NO_RESP) existe como
campo de captura, pero **ningún mecanismo del sistema aplica lógica distinta
según su valor** — es un dato descriptivo, no una regla activa. Clasificado
`REGIMEN_NOT_VERIFIED` en el sentido del prompt maestro §3: el sistema no
determina ni valida el régimen real del tenant/contribuyente para efectos de
qué reglas tributarias aplicarle.

---

## Resumen ejecutivo de esta matriz

| Área | IMPLEMENTADO_TECNICAMENTE | CUMPLIMIENTO_LEGAL_VERIFICADO |
|---|---|---|
| IVA | Parcial (sin validar tarifa) | NO |
| Retefuente/ReteICA/ReteIVA (gastos, CxP) | SI (arquitectura correcta) | NO |
| Retención practicada por cliente (CxC, dirección inversa) | **NO CONFIRMADO** — ver gap | NO |
| CUFE/UBL2.1/XAdES | SI | NO |
| Transmisión DIAN facturas | **NO — GAP CRÍTICO** | NO |
| Transmisión DIAN nómina (DSPNE) | **NO — GAP CRÍTICO** | NO |
| Deducciones/recargos de nómina | SI, con cita normativa | NO |
| PUC/NIIF (catálogo) | SI (existencia) | NO (contenido no verificado) |
| Calendario tributario/vencimientos | NO EXISTE | N/A |

**Ninguna fila de esta matriz puede usarse para afirmar que SINTEL "cumple
legalmente" con la normativa colombiana.** Representa únicamente qué
mecanismos técnicos existen, verificados contra código real.
