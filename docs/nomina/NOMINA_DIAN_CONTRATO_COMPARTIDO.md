# Nómina — Contrato Compartido DIAN (FASE NÓMINA-03)

**Fecha:** 2026-08-24. **Estado:** `NOMINA-03 = COMPLETED_WITH_DEFERRED`.

Ejecuta el plan de `NOMINA_DIAN_AUDIT.md` §6, con dos decisiones tomadas
por el usuario antes de implementar (ver AskUserQuestion de esta fase):
ubicación del código compartido y tratamiento del transporte SOAP.

---

## 1. Refactor ejecutado

**Movidos (sin cambiar su lógica) de `apps/tenant/facturas/services/dian/`
a `apps/tenant/core/dian/` (nuevo subpaquete, terreno neutral):**

- `XadesSignerService` — idéntico byte a byte al original. Sigue operando
  sobre `bytes` XML genéricos vía el marcador `<ext:UBLExtension/>`, sin
  conocer Invoice ni NominaIndividual.
- `AttachedDocumentService` — **único cambio de comportamiento**:
  `build()` ahora acepta `document_type: str = "Invoice"` (antes
  hardcodeado). El default preserva exactamente el XML que ya generaba
  para Factura Electrónica; `empleados` podrá llamarlo con
  `document_type="NominaIndividual"` cuando construya su propio pipeline
  (fuera de alcance de esta fase — ver `NOMINA_DIAN_AUDIT.md` §4).

**Quedan específicos de Factura, sin moverse** (confirmado en la
auditoría: fórmula/estructura acopladas a Invoice):

- `CufeService` (`facturas/services/dian/cufe.py`)
- `UBL21BuilderService` (`facturas/services/dian/ubl21_builder.py`)

**Hallazgo de la auditoría confirmado durante la implementación:**
`apps/tenant/ventas/services/business_service.py` ya importaba
`XadesSignerService`/`AttachedDocumentService` directamente desde
`facturas.services.dian.*` (acoplamiento cruzado `ventas → facturas` no
documentado antes de `NOMINA_DIAN_AUDIT.md`). Se actualizó ese único punto
de consumo para importar desde `apps.tenant.core.dian` — mismo
comportamiento, ahora sin depender de internals de `facturas`.

**Compatibilidad hacia atrás:** `facturas/services/dian/__init__.py`
re-exporta `XadesSignerService`/`AttachedDocumentService` desde la nueva
ubicación, así que cualquier código que hiciera
`from apps.tenant.facturas.services.dian import XadesSignerService` sigue
funcionando sin cambios.

### Archivos tocados

| Archivo | Cambio |
|---|---|
| `apps/tenant/core/dian/__init__.py` | **Nuevo** |
| `apps/tenant/core/dian/xades_signer.py` | **Nuevo** (movido, sin cambios de lógica) |
| `apps/tenant/core/dian/attached_document.py` | **Nuevo** (movido + `document_type` parametrizable) |
| `apps/tenant/facturas/services/dian/xades_signer.py` | **Eliminado** |
| `apps/tenant/facturas/services/dian/attached_document.py` | **Eliminado** |
| `apps/tenant/facturas/services/dian/__init__.py` | Re-exporta desde `core.dian` en vez de definir localmente |
| `apps/tenant/ventas/services/business_service.py` | Import actualizado a `apps.tenant.core.dian` |

---

## 2. Transporte SOAP hacia la DIAN — DEFERRED (BLOCKED_SAFE)

**Decisión del usuario:** diferir, mismo criterio que el resto de
bloqueadores normativos de esta misión (DIAN XML UBL, PILA — ver
`NOMINA_FLUJO_EMPRESARIAL.md` §5).

**Por qué no se construyó:** el proyecto no tiene hoy (ni para Factura ni
para Nómina, confirmado en `NOMINA_DIAN_AUDIT.md` §1) ninguna
implementación del transporte real hacia el webservice DIAN, y no hay
acceso verificado a WSDL/credenciales de habilitación en este entorno.
Construir un cliente SOAP "de memoria" a partir de conocimiento general
del estándar arriesga producir código que compila y parece completo pero
tiene detalles incorrectos (nombres de operación, estructura del sobre,
manejo real de códigos de respuesta) que solo se detectarían contra el
ambiente de habilitación real — el mismo riesgo que ya llevó a diferir la
firma XAdES real y el XML DIAN completo en fases anteriores de esta
misión.

**Qué se necesita para desbloquear:** WSDL real del servicio de
transmisión DIAN (Factura y/o Nómina), credenciales de habilitación, y
confirmación del usuario del mecanismo exacto (síncrono `SendBillSync` vs.
asíncrono, manejo de reintentos, timeout). Ninguno de estos es un problema
de arquitectura de código — el refactor de §1 ya deja `core.dian` como el
lugar correcto para que ese cliente viva una sola vez cuando se
desbloquee, sin duplicarlo entre `facturas` y `empleados`.

---

## 3. Verificación realizada

- `manage.py check`: 0 issues.
- Grep de todo el repo confirmando cero referencias residuales a
  `facturas.services.dian.xades_signer` / `.attached_document` (los dos
  módulos eliminados) — solo quedan referencias al paquete `cufe`/
  `ubl21_builder`, que no se movieron.
- Regresión dirigida: `test_scope_ventas_facturas_f10.py` (único test que
  ejercita el pipeline `venta → DTO DIAN → CUFE/XML/firma/AttachedDocument
  → Factura`) — ver resultado en el commit de esta fase.
- No se ejecutó la suite completa (regla de escalado progresivo,
  CLAUDE.md §Testing — cambio acotado a 2 servicios movidos + 2 puntos de
  import actualizados, no transversal).

---

## 4. Estado formal

**`NOMINA-03 = COMPLETED_WITH_DEFERRED`**

Contrato compartido (signer + wrapper AttachedDocument genérico) completo,
verificado, y ubicado correctamente en terreno neutral (`apps/tenant/core/dian/`)
sin crear ciclos `facturas ↔ empleados`. Transporte SOAP real diferido
explícitamente como bloqueador de infraestructura/negocio (no de
arquitectura) — documentado con lo que se necesita para desbloquear, no
simplemente marcado "pendiente".

Siguiente fase: **NÓMINA-04 — Estados reales de transmisión** (según el
plan del usuario), que puede avanzar sin depender del transporte SOAP en
sí (los estados `PENDIENTE/ACEPTADO/RECHAZADO` de `TransmisionNominaDIAN`
ya existen; falta definir cómo se actualizan ante una respuesta real, lo
cual sigue bloqueado por el mismo motivo de §2 hasta tener el transporte).
