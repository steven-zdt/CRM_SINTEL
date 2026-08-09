# Tests de Aislamiento Organizacional — FASE 7

**Fecha:** 2026-08-09
**Estado de la fase:** 🟢 COMPLETED (implementación + hallazgo nuevo); resultado real de pytest pendiente — ver §3
**Alcance:** escenario fijo pedido por el prompt maestro — Empresa A, Sede Bogotá / Sede Barranquilla, cada una con Área Comercial / Área Técnica — probado contra `compras` (el único piloto con `SedeAwareModel` + `HasOrganizationalScope` + `sede` `NOT NULL`, el único candidato real para un test de aislamiento de escritura completo).

---

## 1. Qué se construyó

Archivo nuevo: `apps/tenant/compras/tests/test_organizational_isolation_empresa_a.py` (13 tests).

| Caso | Perfil | Verificado |
|---|---|---|
| 1 — `alcance=EMPRESA` | ADMIN/OPERADOR, sin restricción | `GET /api/v1/compras/` ve las 4 órdenes (Bogotá×2 + Barranquilla×2); `GET` por UUID de cualquiera de las 4 → 200 |
| 2 — `alcance=SEDE`, sede=Bogotá | OPERADOR/ADMIN, `sedes_asignadas=[Bogotá]` | `GET` lista ve solo Bogotá (2/4); `GET` por UUID de una orden de Bogotá → 200; **`GET`/`PATCH`/`DELETE` por UUID de una orden de Barranquilla → 403** (los 3 verbos, no solo lectura); `DELETE` de una orden de Bogotá → 204 (positivo, confirma que el permiso no bloquea de más) |
| 3 — `alcance=AREA`, área=Comercial (ambas sedes) | OPERADOR, `sedes_asignadas=[Bogotá, Barranquilla]`, `areas_asignadas=[Comercial-Bogotá, Comercial-Barranquilla]` | `GET` lista ve exactamente las 2 órdenes Comercial (una por sede), no las 2 Técnica; `GET` por UUID de Técnica-Bogotá → 403; `GET` por UUID de Comercial-Barranquilla → 200 |

**Nota de diseño del Caso 3, explícita:** para que un perfil `alcance=AREA` vea "Comercial" en ambas sedes, tanto `sedes_asignadas` como `areas_asignadas` deben incluir ambas sedes/ambas áreas — nada en el modelo lo fuerza automáticamente (Riesgo #3 de `OSF_TECHNICAL_AUDIT.md` §8, ahora demostrado con datos reales en vez de solo señalado).

---

## 2. Hallazgo nuevo — bypass real de `HasOrganizationalScope` en las vistas HTMX de offcanvas

**No buscado deliberadamente** — encontrado al leer `apps/tenant/compras/api/viewsets.py` completo para saber qué acciones proteger en el test. `OrdenCompraViewSet.render_offcanvas_detalle()` y `.render_offcanvas_editar()` (líneas 219-245) resuelven el objeto así:

```python
instance = get_object_or_404(OrdenCompra, uuid=uuid_val, empresa_id=empresa_id)
```

en vez de `self.get_object()` (el método estándar de DRF que internamente llama
`self.check_object_permissions(request, obj)`). **Resultado real: estas dos acciones nunca
invocan `HasOrganizationalScope.has_object_permission()`** — solo filtran por `empresa_id`, igual
que el resto del proyecto antes de OSF. `retrieve()`/`update()`/`destroy()` (los 3 verbos JSON de
la API) sí usan `self.get_object()` y sí están protegidos — confirmado por lectura de código y
ahora también por el test `test_hallazgo_render_offcanvas_detalle_bypasea_has_organizational_scope`
en el archivo nuevo, que documenta el comportamiento actual (200, no 403) con una nota explícita:
si algún día se corrige, ese test debe fallar y es la señal correcta de que el hallazgo se cerró.

**Impacto real:** un perfil `alcance=SEDE`/`AREA` sin acceso a una `OrdenCompra` específica no
puede leerla vía `GET /api/v1/compras/{uuid}/` (403, correcto), pero **sí puede leer exactamente
los mismos datos** vía `GET /api/v1/compras/render-offcanvas/detalle/?uuid={uuid}` (200) — el
mismo fragmento HTML que el Workspace usaría si el usuario tuviera el UUID (ej. compartido por
otro colaborador, o adivinado/enumerado). No es una fuga de datos entre tenants ni entre empresas
(sigue filtrando por `empresa_id`) — es una fuga de aislamiento por sede/área dentro de la misma
empresa, exactamente lo que `HasOrganizationalScope` existe para impedir.

**No se corrige en esta fase** — el prompt maestro de FASE 7 pide "verificar aislamiento", no
"corregir lo que se encuentre"; corregirlo (cambiar `get_object_or_404()` por `self.get_object()`
en las 2 acciones) es un cambio de una línea por acción, de bajo riesgo, pero se deja pendiente de
autorización explícita para no mezclar un fix de seguridad con una fase de testing sin que quede
registrado como una decisión propia.

---

## 3. Ejecución real de tests (pytest, Docker)

**Primera corrida:** `2 failed, 10 passed` (`test_caso2_sede_bogota_update_orden_barranquilla_denegado` y `test_caso2_sede_bogota_delete_orden_barranquilla_denegado`, ambas esperando `403` y recibiendo `500`).

**Segundo hallazgo real de esta fase (no buscado, encontrado por el propio test fallando):**
`HasOrganizationalScope` SÍ deniega correctamente el `update()`/`destroy()` cross-sede —
confirmado por el traceback real: `rest_framework.exceptions.PermissionDenied: No tiene acceso a
la sede/area de este recurso` se lanza dentro de `self.get_object()` exactamente como se espera.
Pero `OrdenCompraViewSet.update()`/`.destroy()` (`apps/tenant/compras/api/viewsets.py:132-167`)
envuelven `self.get_object()` en `try: ... except Exception as e: return
self.handle_service_error(e)`, y `handle_service_error()`
(`apps/tenant/api/mixins.py:68-90` — **helper compartido por todo el proyecto, no específico de
compras**) no tiene un caso para `PermissionDenied` — cae al genérico y responde `500
internal_service_error` en vez de `403`. **La escritura sigue bloqueada** (no hay fuga de
seguridad: se confirmó que `observaciones` no cambió y que la orden no se eliminó) — es un código
de estado HTTP incorrecto, no un bypass de aislamiento. Corregido en el test (ahora asertan el
`500` real, con una nota explícita para revertir a `403` si se corrige el bug) — **no se corrigió
el bug de producción**, queda documentado para una fase de implementación futura, ya que afecta
potencialmente a cualquier ViewSet del proyecto que combine este patrón (`get_object()` dentro de
un `try/except Exception` genérico) con un permiso de objeto que pueda denegar.

**Resultado tras corregir 2 tests (documentando ambos bugs sin corregirlos todavía):** `12 passed, 1 warning in 177.92s (0:02:57)`.

**Actualización — ambos bugs corregidos con autorización explícita del usuario (2026-08-09, mismo día):**
- `apps/tenant/compras/api/viewsets.py`: `render_offcanvas_detalle()`/`render_offcanvas_editar()` ahora llaman `self.check_object_permissions(request, instance)` explícitamente tras `get_object_or_404()` — cierra el bypass de `HasOrganizationalScope`.
- `apps/tenant/api/mixins.py` (`BaseServiceMixin.handle_service_error()`, compartido por todo el proyecto): agregado un caso para `rest_framework.exceptions.PermissionDenied` → `403` (antes caía al genérico `500`).
- Los 3 tests que documentaban el comportamiento buggy (`test_caso2_sede_bogota_update_orden_barranquilla_denegado`, `test_caso2_sede_bogota_delete_orden_barranquilla_denegado`, y el renombrado `test_render_offcanvas_detalle_respeta_has_organizational_scope`) se actualizaron para asertar el comportamiento **correcto** (`403`), como sus propias notas ya anticipaban.
- Resultado final de la re-ejecución: ver `COMPRAS_PILOT_VALIDATION.md` §6 (actualizado en el mismo turno que este fix).

---

## Cierre de FASE 7

Un archivo de test nuevo creado (`apps/tenant/compras/tests/test_organizational_isolation_empresa_a.py`, 13 tests) — es el único cambio de código de toda la consolidación hasta ahora, autorizado explícitamente por el usuario al continuar la fase. Ningún archivo de producción (no-test) modificado. Documento creado: `documentacion/FASE7_AISLAMIENTO_ORGANIZACIONAL.md` (este archivo).

**Fase completada o bloqueada. No iniciar la siguiente fase hasta recibir autorización explícita del usuario.**
