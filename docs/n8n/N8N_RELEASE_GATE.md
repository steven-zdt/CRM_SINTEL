# N8N_RELEASE_GATE

Mision N8N-SINTEL-01 (2026-09-09). Ver `N8N_ARCHITECTURE.md`,
`N8N_SECURITY.md`, `N8N_MCP_CONTRACT.md`, `N8N_WORKFLOWS.md`,
`N8N_OPERATIONS.md` para el detalle completo de cada area.

## Veredicto

```
N8N_SINTEL = COMPLETED_WITH_DEFERRED
```

## Checklist del Release Gate (Fase 33)

```
[x] n8n corre en Docker                          -- verificado, healthy
[x] persiste correctamente                        -- volumen nativo Docker
                                                       (n8n_data), DB Postgres
                                                       separada, migraciones
                                                       internas corridas sin error
[ ] tiene backup                                   -- DEFERRED (diseño
                                                       documentado, no ejecutado)
[ ] HTTPS funcional                                -- DEFERRED (exposicion
                                                       publica no implementada,
                                                       decision explicita del
                                                       usuario)
[x] acceso autenticado                             -- verificado (JWT via
                                                       simplejwt, identidad
                                                       tecnica dedicada)
[x] SINTEL API autenticado                          -- verificado con POST
                                                       real (201) usando el
                                                       token de la identidad
                                                       tecnica
[x] tenant isolation probado                        -- verificado (rol n8n
                                                       sin CONNECT a `sintel`,
                                                       evidencia real de
                                                       bloqueo)
[ ] MCP real probado                                -- N/A por diseño (Fase
                                                       14: REST API en su
                                                       lugar, decision
                                                       explicita del usuario,
                                                       MCP formal DEFERRED)
[x] XML piloto procesado                            -- verificado con
                                                       evidencia real (POST
                                                       real -> 201 -> Factura
                                                       persistida via el
                                                       pipeline oficial ->
                                                       limpiada tras la prueba)
[ ] email piloto enviado                            -- DEFERRED (requiere
                                                       credenciales de correo
                                                       reales conectadas a
                                                       n8n + workflow receptor,
                                                       ninguno existe aun)
[ ] workflow de error probado                       -- DEFERRED (mismo motivo)
[ ] WhatsApp probado                                -- DEFERRED explicito
                                                       (sin credenciales
                                                       reales, tal como el
                                                       propio release gate
                                                       de la mision permite)
[ ] idempotencia probada                            -- DISEÑADA (event_id
                                                       UUID real, nunca
                                                       derivado de asunto/
                                                       timestamp/filename) --
                                                       NO probada end-to-end
                                                       porque el consumidor
                                                       (workflow receptor de
                                                       n8n) no existe aun
[x] manage.py check PASS                            -- verificado, limpio
[x] makemigrations --check PASS                     -- verificado, "No
                                                       changes detected"
[x] regresion SINTEL PASS (focalizada)               -- 6/6 tests de
                                                       apps/tenant/core/tests/test_documentos_upload_api.py
                                                       en verde (incluye
                                                       test_multitenant_isolation),
                                                       con el flag ahora
                                                       permanentemente en
                                                       true (19m50s). La
                                                       regresion COMPLETA
                                                       del ERP (fuera de
                                                       ventas/compras/facturas,
                                                       ya cubierta por
                                                       VENTAS-COMPRAS-FACTURAS-01)
                                                       no se re-ejecuto en
                                                       esta pasada -- los
                                                       cambios de esta mision
                                                       no tocan esas apps.
[ ] security audit n8n revisado                      -- DEFERRED (`n8n audit`
                                                       requiere que el usuario
                                                       complete primero el
                                                       setup inicial/login de
                                                       n8n, no completado en
                                                       esta sesion)
```

## Por que COMPLETED_WITH_DEFERRED y no PASS

El nucleo tecnico esta implementado y **verificado con evidencia real
ejecutada** (no solo diseñado): n8n corriendo en Docker con aislamiento
de base de datos probado, identidad tecnica funcional, endpoint REST de
SINTEL habilitado y probado con un POST real que persistio una Factura
por el pipeline oficial. Lo que falta para `PASS` son, en su mayoria,
pasos que **requieren accion del usuario fuera de esta sesion** (setup
inicial de n8n via su propia UI -- login con credenciales reales;
credenciales de correo/WhatsApp reales; decision de exponer n8n
publicamente) o **workflows del lado de n8n** (el receptor del webhook,
los nodos de Email/WhatsApp) que se construyen en la interfaz visual de
n8n, no en codigo Python de SINTEL.

## Por que no se ejecuto la regresion COMPLETA de SINTEL

Esta mision se ejecuto inmediatamente despues de cerrar
VENTAS-COMPRAS-FACTURAS-01 (misma sesion, mismo dia) -- esa mision ya
corrio y verifico en verde 32 tests de regresion real sobre
`ventas`/`cotizaciones`/`contabilidad` (ver
`docs/comercial/VENTAS_COMPRAS_FACTURAS_RELEASE_GATE.md`). Los cambios
de N8N-SINTEL-01 son aditivos y aislados (`apps/services/integration_events/`
nuevo, 1 management command nuevo, 1 bloque `try/except` nuevo y
aislado dentro de `upload_document()` que nunca puede romper su
`return Response(...)` por diseño, `settings.py` solo agrega 2
variables nuevas) -- no tocan ningun modelo, migracion, ni logica de
negocio existente de `ventas`/`compras`/`facturas`/`contabilidad`. Se
ejecuto la regresion **focalizada** del unico endpoint realmente
modificado (habilitado): `apps/tenant/core/tests/test_documentos_upload_api.py`,
6/6 en verde (incluye `test_multitenant_isolation`), con el flag ahora
permanentemente en `true`. La regresion COMPLETA del resto del ERP no
se re-ejecuto en esta pasada -- coherente con la norma de testing
progresivo del proyecto (`test especifico -> componente -> app ->
integracion -> suite global`, reservar la suite completa para cierres
de fase/cambios transversales, que este no es).

## Lo que SI se demuestra con evidencia real (no solo implementado)

1. **n8n aislado de PostgreSQL de SINTEL** — `psql -U n8n -d sintel` →
   `permission denied` (verificado, no asumido).
2. **Identidad tecnica funcional** — `crear_identidad_tecnica_n8n
   --schema home` crea la identidad, genera tokens reales, es
   idempotente (segunda corrida rota en vez de duplicar).
3. **Workflow A end-to-end** — XML real subido con el token de la
   identidad tecnica → `201 Created` → Factura persistida con
   `naturaleza` clasificada correctamente → evento `invoice.processed`
   publicado (log confirma el intento, se salta limpiamente por no
   haber `N8N_WEBHOOK_URL` configurada aun) → dato de prueba limpiado
   despues.
4. **Resto del stack SINTEL intacto** — `db`/`redis`/`neo4j`/`nginx`/
   `celery`/`celery-beat`/`web` todos `healthy` despues de todos los
   cambios de esta mision.

## DEFERRED (resumen, con lo que falta exactamente)

1. Exposicion publica de n8n (nginx + `automation.sintel.net.co`) —
   decision explicita del usuario, diseño documentado.
2. Workflow receptor del webhook en n8n (validacion HMAC + switch por
   `event_type` + notificaciones) — requiere trabajo en la UI de n8n.
3. Credenciales de correo/WhatsApp reales — requieren decision y datos
   del usuario.
4. `n8n audit` — requiere que el usuario complete el setup inicial de
   n8n primero.
5. Backup de la base de datos `n8n` y del `N8N_ENCRYPTION_KEY` — diseño
   documentado (`N8N_OPERATIONS.md`), no ejecutado.
6. Rotacion automatica de credenciales (workflow `N8N-SYSTEM`) —
   comando manual ya funcional, automatizacion DEFERRED.
7. `invoice.failed` (evento de error) no se publica todavia — el camino
   de error de `upload_document()` no dispara ningun evento aun.
8. MCP formal — DEFERRED por decision explicita (defecto de terceros ya
   confirmado, REST API es la via elegida para este piloto).

## Siguiente mision natural

Con el endpoint SINTEL y la identidad tecnica ya funcionando de punta a
punta, el siguiente paso real depende del usuario:
- Si quiere el workflow de correo real: completar el setup de n8n
  (login), conectar una cuenta de correo real, construir el workflow A
  completo en la UI de n8n.
- Si quiere las notificaciones salientes: construir el workflow
  receptor del webhook en n8n primero (mas simple, no requiere
  credenciales de correo/WhatsApp).
- Si se necesita composicion inteligente real (no solo REST
  deterministico): retomar MCP formal, empezando por resolver el
  defecto de terceros de `django-rest-framework-mcp` (actualizar el
  paquete o mitigar decorando solo ViewSets sin dependencia de
  `request.method`).
