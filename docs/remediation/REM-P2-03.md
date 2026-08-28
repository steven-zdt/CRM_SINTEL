# REM-P2-03 — Régimen tributario de Cliente: ¿informativo u operativo?

**Estado:** VERIFIED (confirmado informativo, decisión documentada — no
requiere corrección de código)
**Prioridad:** P2
**App involucrada:** `clientes`
**Fecha:** 2026-08-28

## Investigación

Grep de todo `apps/tenant/` por usos condicionales reales de
`Cliente.regimen_tributario` (`if regimen_tributario ==`, `!=`, `in [...]`)
— los únicos resultados son:

- `apps/tenant/clientes/templates/tenant/clientes/offcanvas_editar_
  cliente.html:107-109` — pre-selección del `<option>` en el formulario
  (UI pura).
- `apps/tenant/clientes/tables.py:76` — `get_regimen_tributario_display()`
  para mostrar la etiqueta legible en la grilla (UI pura).

**Cero resultados** de lógica de negocio, cálculo fiscal, o validación que
ramifique según el valor de `Cliente.regimen_tributario`. (Los demás
matches del grep amplio de 68 archivos correspondían a
`Empresa.regimen_tributario` — un campo distinto, del propio tenant, no
del tercero — o a texto no relacionado.)

## Decisión

**Confirmado: es un dato puramente informativo/de captura**, consistente
con lo ya documentado en `documentacion/audits/apps/
APP_clientes_NORMATIVE_MATRIX.md` (2026-08-21): *"el campo existe y se usa
como config downstream (posiblemente en contabilidad), pero esta app no
valida ni aplica reglas segun el valor"* — esta investigación confirma que
tampoco `contabilidad` ni ninguna otra app lo consume para lógica real.

**No se implementa ningún cambio.** Mantenerlo como dato informativo es
correcto — no hay evidencia de que el negocio necesite reglas
diferenciadas por régimen del cliente hoy. Si en el futuro se necesita
(ej. aplicabilidad condicional de ciertas retenciones según régimen), es
una funcionalidad nueva con su propio alcance normativo a definir con
asesoría profesional (`PROFESSIONAL_REVIEW_REQUIRED` si se activa).

## Governance

N/A — sin cambio de código.
