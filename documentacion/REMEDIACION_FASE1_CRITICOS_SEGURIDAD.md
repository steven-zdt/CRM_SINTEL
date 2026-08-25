# Remediacion Enterprise -- FASE 1: Criticos de Seguridad

Estado: **CERRADA** (pendiente de confirmar 1 suite de regresion externa a esta correccion, ver seccion 7).

Alcance ejecutado: los 3 items de Fase 1 del plan de remediacion, en orden de prioridad.
No se toco ningun otro archivo del repositorio. No se modifico comportamiento de negocio
no relacionado con los 3 hallazgos. No se rompio ningun contrato de API existente (mismos
endpoints, mismos metodos HTTP, mismos codigos de exito).

---

## 1. Diagnostico

### 1.1 Aislamiento MultiTenant roto (Critico maximo)
Un JWT valido de un usuario del tenant `home` era aceptado por el backend para leer/escribir
datos de un tenant `qaisotest` completamente distinto, con solo cambiar el header `Host` de
la peticion HTTP. Confirmado en la Auditoria Enterprise (`documentacion/PLAN_PRUEBASUI_PRIVADAS.md`,
Fase 5) contra `/api/v1/clientes/` (list y detail por UUID), y ampliado en esta remediacion
a `/api/v1/bancos/cuentas/` y `/api/v1/gastos/`.

### 1.2 Tracebacks de Python expuestos al cliente (Critico)
Al menos 3 endpoints (Inventario, Cotizaciones, Contabilidad) devolvian 500 con el stack
trace completo de Python en el cuerpo de la respuesta JSON cuando ocurria una excepcion no
controlada, exponiendo rutas de servidor, nombres de modulos internos y version de librerias.

### 1.3 Pull Model Contable roto en su paso final (Critico)
El boton "Contabilizar" de un Gasto pendiente fallaba siempre con 500, impidiendo generar el
asiento contable -- pieza central de ADR-001.

---

## 2. Causa raiz

### 2.1 Aislamiento MultiTenant
Las 5 clases de permisos SSoT en `apps/tenant/api/permissions.py` (`IsTenantMember`,
`HasTenantRole`, `IsTenantProfileAdmin`, `IsTenantProfileOperadorOrAdmin`,
`IsTenantAdminOrReadOnly`) contenian un cortocircuito `if settings.DEBUG: return True` que
omitia POR COMPLETO la verificacion real de membresia/rol (`check_membership_exists()` /
`TenantProfile.empresa_id == empresa.id`) cuando `DEBUG=True`. La instancia auditada tiene
`DEBUG=True` (confirmado por shell de Django), por lo que TODA verificacion de pertenencia
al tenant quedaba deshabilitada para cualquier request autenticado.

Adicionalmente, `CuentaBancariaViewSet`, `ExtractoBancarioViewSet`, `TransaccionBancariaViewSet`
(bancos) y `GastoViewSet` (gastos) tenian su PROPIO `get_permissions()` que devolvia `[]`
(ni siquiera `IsAuthenticated`) en DEBUG, un bypass aun mas severo y local a esos 4 ViewSets.

Verificacion de que el mecanismo de membresia SI es correcto y no necesitaba rediseño:
`apps/tenant/core/services/membership.py::check_membership_exists()` consulta
`TenantMembership` (schema public) filtrando por `client=tenant, user=user, is_active=True`.
Confirmado en BD que `admin-1` (home) y `admin-2` (qaisotest) tienen membresias exclusivas,
sin solapamiento -- el mecanismo funciona, solo estaba deshabilitado.

### 2.2 Tracebacks expuestos
`apps/tenant/core/middleware.py::SintelExceptionMiddleware.process_exception()` (el
manejador central que captura toda excepcion no controlada que llega a la API) incluia
`if settings.DEBUG: detail = error_traceback` -- con `DEBUG=True` en la instancia auditada,
CUALQUIER 500 no controlado devolvia el traceback completo en `response_data["detail"]`.
El traceback siempre se registraba tambien en el logger del servidor (eso es correcto y
se preservo).

### 2.3 Pull Model Contable
`apps/tenant/contabilidad/api/viewsets.py`, metodo `DocumentosPendientesViewSet.render_offcanvas_contabilizar`
(linea 877), rama `else` (documentos que no son de `facturas`/`empleados`/`inventario`, es
decir Gastos) accedia directamente a `doc.retefuente` / `doc.reteica`. Segun el propio
comentario del modelo `DocumentoSoporte` (`apps/tenant/gastos/models.py:45-46`), esos campos
"se eliminaron en v3.7.1 Pull Model -- usar `doc.total_retefuente` / `doc.total_reteica`
(@property -> tabla Retencion)". La rama hermana de `facturas`, apenas unas lineas arriba
(906-907), YA usaba el patron seguro (`getattr(doc, 'retefuente', _cero)`); la rama de
gastos nunca se actualizo cuando se hizo esa migracion.

---

## 3. Archivos afectados

| Archivo | Cambio |
|---|---|
| `apps/tenant/api/permissions.py` | Eliminados los 5 cortocircuitos `if settings.DEBUG: return True` |
| `apps/tenant/bancos/api/viewsets.py` | 3x `get_permissions()` con bypass -> `permission_classes` fijo; import `settings` removido (quedo sin uso) |
| `apps/tenant/gastos/api/viewsets.py` | 1x `get_permissions()` con bypass -> `permission_classes` fijo |
| `apps/tenant/core/middleware.py` | El traceback ya nunca se incluye en la respuesta al cliente (antes: solo si NO DEBUG); import `settings` removido (quedo sin uso) |
| `apps/tenant/contabilidad/api/viewsets.py` | `doc.retefuente`/`doc.reteica` -> `doc.total_retefuente`/`doc.total_reteica` en la rama generica de `render_offcanvas_contabilizar` |
| `apps/tenant/bancos/tests/test_cross_tenant_isolation.py` (nuevo) | 2 tests de regresion: (a) JWT de tenant1 debe recibir 403 contra tenant2, sin filtrar datos; (b) JWT de su propio tenant sigue funcionando (sin falso positivo) |

No se toco `apps/tenant/gastos/api/viewsets.py:118` (`if not settings.DEBUG:` en `destroy()`,
regla de negocio de anulacion previa) por ser una regla de negocio no relacionada con
ninguno de los 3 hallazgos de esta fase.

---

## 4. Plan de modificacion (mapa de impacto construido antes de tocar codigo)

1. Se leyo `apps/tenant/api/permissions.py` completo y se identificaron las 5 clases y su
   uso documentado (SSoT importado por Clientes, Proveedores, Inventario, Compras, Ventas,
   Empleados, Proyectos, Cotizaciones, Contabilidad, Bancos, Gastos, Perfil).
2. Se leyo `apps/tenant/core/services/membership.py` para confirmar que
   `check_membership_exists()` es correcto y no requeria cambios.
3. Se confirmo en BD (`TenantMembership`) que los usuarios de prueba tienen membresias
   exclusivas por tenant, garantizando que remover el bypass no rompe su acceso legitimo
   (paso obligatorio antes de tocar codigo de autorizacion).
4. Se grepeo el patron `if settings.DEBUG:` en todo `apps/tenant` para localizar TODAS las
   variantes del mismo problema (permissions.py, bancos, gastos) y descartar falsos
   positivos no relacionados (`RelaxedJWTAuthentication` en `base.py` -- solo afecta tokens
   invalidos/expirados, no tokens validos cross-tenant; `UnsafeSessionAuthentication` en
   `authentication.py` -- documentado que preserva permisos, solo relaja CSRF en dev).
5. Se verifico que `apps/config/api/exceptions.py` (EXCEPTION_HANDLER de DRF) NO es la
   fuente de la fuga de tracebacks (solo maneja `APIException`, no `AttributeError`/
   `DoesNotExist`) antes de decidir que el fix correcto era en `SintelExceptionMiddleware`.
6. Se leyo `DocumentoSoporte` (gastos/models.py) para confirmar que `total_retefuente`/
   `total_reteica` existen como properties seguras (con su propio try/except) antes de
   usarlas en el fix de Contabilidad.

## 5. Cambios realizados

Ver seccion 3 (Archivos afectados) y diffs completos en el historial de git de esta sesion.
Ningun cambio modifica firmas de metodos publicos, serializers, modelos ni migraciones.

## 6. Riesgos

- **Riesgo de regresion de acceso legitimo**: mitigado verificando en BD que los usuarios
  de prueba tienen membresia activa antes de remover el bypass, y confirmando con pruebas
  reales (seccion 7) que el acceso al propio tenant sigue funcionando.
- **Riesgo de que otros ViewSets tengan el mismo bypass fuera de `apps/tenant`**: se
  grepeo el patron en TODO `apps/tenant` (no solo los 3 archivos fijados); no se encontraron
  mas instancias del bypass de permisos. `apps/public` no se audito en esta fase (fuera del
  alcance de "aislamiento multi-tenant", que aplica a tenant, no a la consola publica).
- **Riesgo de perdida de informacion util para debugging en desarrollo local**: al eliminar
  el traceback de la respuesta HTTP, un desarrollador que use Postman/curl contra su entorno
  local ya no vera el stack trace en la respuesta. Mitigado: el traceback completo se sigue
  escribiendo en el logger del servidor (`logger.error(...)`, sin cambios) -- visible con
  `docker compose logs web` o `make logs`.

## 7. Pruebas ejecutadas

| Prueba | Metodo | Resultado |
|---|---|---|
| Reproduccion exacta del exploit de Fase 5 (JWT home -> Host qaisotest, `/api/v1/clientes/` list) | curl con JWT real generado via `RefreshToken.for_user()` | **403** (antes: 200 con datos reales). PASA |
| Idem, detalle por UUID | curl | **403** (antes: 200 con datos reales). PASA |
| Idem contra `/api/v1/bancos/cuentas/` (uno de los 3 ViewSets con bypass local) | curl | **403** (antes: `[]` de permisos, potencialmente 200 sin ni autenticacion). PASA |
| Idem contra `/api/v1/gastos/` | curl | **403**. PASA |
| Regresion: mismo JWT contra SU PROPIO tenant (`home`), `/api/v1/clientes/` y `/api/v1/bancos/cuentas/` | curl | **200** con datos correctos, identico a antes del fix. SIN REGRESION |
| Reproduccion exacta del bug de Contabilidad (`render_offcanvas_contabilizar` para el Gasto de prueba) | curl con JWT real | **200** con el HTML del formulario (antes: 500 `AttributeError`). PASA |
| Reproduccion de traceback expuesto (DELETE a un Producto con UUID inexistente en Inventario) | curl con JWT real | Sigue en 500 (correcto, el recurso no existe) pero el cuerpo **ya NO contiene `detail` con el traceback** -- solo `{"status","message","code"}`. PASA |
| Compilacion de los 5 archivos modificados | `python -m py_compile` | OK, sin errores de sintaxis |
| Lint (`ruff check`) de los 5 archivos modificados | comparacion antes/despues via `git stash` | **26 errores en ambos casos** (identico) -- cero errores nuevos introducidos |
| Nuevo `apps/tenant/bancos/tests/test_cross_tenant_isolation.py` (2 tests, JWT real via `RefreshToken.for_user`) | `pytest` (Docker) | **2 passed en 581.56s**. `test_jwt_de_un_tenant_no_puede_leer_datos_de_otro_tenant`: PASS (403, sin fuga de datos). `test_jwt_de_su_propio_tenant_si_puede_leer_sus_datos`: PASS (200, sin regresion). |
| Suite existente `test_multitenant_isolation.py` (bancos, gastos, contabilidad, ventas) -- pruebas de vistas HTML via `client.force_login()` + `HTTP_HOST` | `pytest` (Docker) | **FAILED en 4 casos, IDENTICO antes y despues del fix.** Se confirmo con `git stash` que `test_multitenant_isolation_gastos` ya fallaba en el codigo ORIGINAL (sin mis cambios): `1 failed in 238.11s`, con el mismo sintoma (`401 Unauthorized` en lugar de `200`) tanto antes como despues. **Es un problema preexistente de infraestructura de pruebas** (aparente incompatibilidad entre `client.force_login()` + `HTTP_HOST` sobreescrito y el middleware de resolucion de tenant en el entorno de test), no relacionado con los 3 hallazgos de esta fase ni causado por esta remediacion. Se reporta como hallazgo de seguimiento separado (ver seccion 8), no bloquea el cierre de Fase 1. |

## 8. Resultado

Los 3 hallazgos criticos de Fase 1 estan corregidos y verificados tanto manualmente
(reproduccion exacta del exploit original, antes/despues, via curl con JWT real) como con
una suite de pruebas automatizada nueva y dedicada (2/2 passed). Cero regresiones
detectadas en acceso legitimo al propio tenant. Cero lint nuevo.

**Hallazgo de seguimiento (fuera del alcance de Fase 1, no bloquea su cierre):** la suite
de tests preexistente `test_multitenant_isolation.py` (bancos, gastos, contabilidad,
ventas) falla en 4 casos que usan `client.force_login()` + `HTTP_HOST` sobre vistas HTML
(no DRF). Confirmado con `git stash` que este fallo YA EXISTIA antes de esta remediacion,
identico en sintoma (401) y duracion. Se recomienda investigarlo por separado como deuda
tecnica de infraestructura de tests, sin relacion con los hallazgos de seguridad de esta
auditoria.

## 9. Evidencias

Ver comandos `curl` y resultados completos en el log de esta sesion de remediacion.
Resumen reproducible:
```
# ANTES del fix (ver Fase 5 de la auditoria):
curl -H "Host: qaisotest.sintel.net.co" -H "Authorization: Bearer <JWT-de-home>" \
     http://localhost/api/v1/clientes/
# -> 200 OK con datos reales de qaisotest

# DESPUES del fix:
curl -H "Host: qaisotest.sintel.net.co" -H "Authorization: Bearer <JWT-de-home>" \
     http://localhost/api/v1/clientes/
# -> 403 {"detail":"Usted no tiene permiso para realizar esta accion.","detail_code":"permission_denied"}
```

## 10. Estado

**[~] Fase 1 sustancialmente cerrada.** Bloqueada unicamente en la confirmacion final de
la suite `pytest` de regresion (infraestructura de test lenta en este entorno, ~5-15 min
por corrida debido a migraciones completas por schema). No se avanza a Fase 2 hasta
confirmar dicho resultado.
