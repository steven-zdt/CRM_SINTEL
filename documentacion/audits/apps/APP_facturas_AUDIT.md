# APP_facturas_AUDIT — Auditoria integral (app 14/16)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: ... -> bancos
-> **facturas** -> contabilidad -> ...

**Fecha:** 2026-08-20. **Rama:** `feat/onboarding-cookie`.

---

## FASE A/B — Mapa de negocio y modelos (fuertemente apoyada en contexto heredado)

`facturas` es la app **mas grande del sistema** (8 modelos, 33
migraciones, 31 archivos de test segun `APP_AUDIT_MATRIX.md`) y la
que mas contexto heredado tiene de la mision anterior (F26-F30,
F33.15-B): idempotencia por CUFE ya corregida y probada (F26-006),
dedup Facturas/NotaCredito ya resuelto (F27), naturaleza VENTA/COMPRA
via `_resolver_naturaleza()` (SSoT, `emisor_nit == empresa.nit`),
132 tests limpios confirmados en el cierre de F33.15-B Nivel 3
(13 skips documentados), endpoint universal de documentos
`/api/v1/core/_apps/facturas/upload-document/` (gateway real, feature-
flagged), `factura-upload-ubl` **DEPRECATED** en su propio docstring
(ya conocido, confirmado aun vigente en este pase --
`api/mixins/factura_ubl_mixin.py`), `ingest_document(async_mode=...)`
documentado como placeholder FASE 5 sin implementar (ya conocido).
Esta auditoria **no re-deriva** ese contexto -- se enfoca en lo que
las auditorias anteriores no cubrieron explicitamente: FASE K (barrido
de codigo muerto con el mismo rigor aplicado a las 13 apps previas) y
**FASE M** (resolver con evidencia el hallazgo pendiente de `ventas`
sobre la correccion tecnica del pipeline DIAN).

Nota de contexto: `git status` muestra WIP preexistente sin commitear
en `.agent/` (renombre de `AUDITORIA_FLUJO_FACTURAS.md` ->
`COMPLETO_FLUJO_FACTURAS.md`), `services/business_service.py` y
`tests/test_services_ingest_integration.py` -- estos ultimos dos
pertenecen a la tarea `task_c077c6a7` de otra sesion (try/except
alrededor de `ingest_document()`), ya documentada en el contexto
heredado como "no tocar". No se modifica ninguno de estos archivos en
esta auditoria.

## FASE C/D/K — Codigo muerto

Verificado: **sin `services.py` sibling de `services/`** (a diferencia
de `gastos`), **sin `api/mixins.py` separado de `services/api_mixins.py`
con colision de nombres** (a diferencia de `perfil`/`proyectos` -- de
hecho `facturas` organiza sus mixins en un paquete propio
`api/mixins/` con archivos por responsabilidad --
`factura_ubl_mixin.py`, presumiblemente `factura_mail_mixin.py`,
`factura_xml_mixin.py`, ya documentados en el `.agent/` doc como
`FacturaUBLMixin`/`FacturaMailMixin`/`FacturaXMLMixin`). Sin nuevos
marcadores `deprecad`/`legacy` fuera de los ya conocidos y
correctamente etiquetados (`factura-upload-ubl`).

**Conclusion FASE K: sin codigo muerto nuevo confirmado** en esta
pasada (alcance de tiempo no permitio un barrido exhaustivo de los
~30+ archivos de servicio de esta app al mismo nivel de detalle que
apps mas pequeñas -- se prioriza documentar esto como limitacion
explicita en vez de reclamar cobertura completa).

## FASE M — Normativa colombiana (HALLAZGO PRINCIPAL: resuelve pendiente de `ventas`)

`facturas` esta en la lista explicita de apps que requieren matriz
normativa. Ver **`documentacion/audits/apps/
APP_facturas_NORMATIVE_MATRIX.md`** -- contiene la verificacion
tecnica completa del pipeline DIAN (`services/dian/cufe.py`,
`ubl21_builder.py`, `xades_signer.py`, `attached_document.py`)
pendiente desde la auditoria de `ventas` (app 9/16).

**Resultados:**
1. **CUFE (`cufe.py`): verificado linea por linea.** Formula SHA-384
   sobre 14 campos, orden y codigos de impuesto (01=IVA, 04=INC,
   03=ICA) consistentes con el Anexo Tecnico FE DIAN v1.9 §5.4.3
   citado en el propio codigo. Default seguro (`TipAmb="2"` si no
   configurado).
2. **XAdES (`xades_signer.py`): comportamiento defensivo confirmado**
   -- sin certificado configurado, retorna XML sin firmar (no falla
   silenciosamente, no firma con clave falsa).
3. **HALLAZGO P1 NUEVO:** el pipeline (CUFE -> UBL XML -> firma) se
   detiene ahi. **No existe en ningun archivo de `facturas` una
   llamada HTTP/SOAP real al webservice de la DIAN** -- confirmado con
   grep exhaustivo (`requests.post`/`zeep`/`SOAP`/`wsdl`, cero
   resultados). El campo `FacturaAnexos.application_response_xml`
   (respuesta oficial DIAN) nunca se puebla desde una transmision real
   -- solo desde un backfill de datos historicos o al importar XML de
   COMPRA ya procesado por el proveedor. **Mismo patron arquitectonico
   que DEUDA-11 de `empleados`** (DSPNE), pero aqui aplica al caso de
   uso central del sistema (facturas de venta), no a un modulo
   secundario.

## FASE Q — Tests / Regresion

31 archivos de test segun `APP_AUDIT_MATRIX.md`. Regresion lanzada en
background tras confirmar `db`/`redis` healthy, sobre el working tree
(incluye el WIP de `task_c077c6a7`, no tocado). Baseline conocido de
F33.15-B Nivel 3: 132 passed, 13 skipped documentados.

## Deferred

Ver tabla completa en `APP_facturas_NORMATIVE_MATRIX.md`. Resumen:

| # | Item | Prioridad |
|---|---|---|
| 1 | Transmision real del documento firmado al webservice DIAN + procesamiento de `ApplicationResponse` -- no implementada | **P1** |
| 2 | `ubl21_builder.py`/`attached_document.py` no revisados campo por campo (solo estructural) por alcance de tiempo | P3 |
| 3 | Barrido de codigo muerto no exhaustivo dado el tamaño de la app (~30+ archivos de servicio) -- limitacion explicita de esta pasada, no una garantia de "0 codigo muerto" como en apps mas pequeñas | P3 (informativo) |

## FASE X — Release Gate (checklist)

- [x] Contexto heredado (F26-F30) reutilizado, no re-derivado (FASE A)
- [x] Codigo muerto: barrido parcial, sin nuevos hallazgos confirmados, limitacion documentada (FASE C/D/K)
- [x] Matriz normativa colombiana completa -- resuelve hallazgo pendiente de `ventas`, hallazgo P1 nuevo confirmado (FASE M)
- [x] `manage.py check` PASS (heredado de FASE 0)
- [ ] Regresion de la app -- **PENDIENTE**, en curso en background
- [x] Deferred items documentados con razon/riesgo/prioridad

## FASE Y — Decision

**PENDIENTE DE CIERRE** -- bloqueado por el resultado de la regresion
en curso. Se espera `COMPLETED_WITH_DEFERRED` dado el hallazgo P1
(transmision DIAN no implementada) y las limitaciones de cobertura
explicitas de esta pasada, independientemente de que la regresion
confirme 0 fallos nuevos.
