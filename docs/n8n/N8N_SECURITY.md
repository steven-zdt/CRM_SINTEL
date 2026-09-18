# N8N_SECURITY — autenticacion, aislamiento, secretos

Mision N8N-SINTEL-01. Ver `N8N_ARCHITECTURE.md` para el diseño completo.

## 1. Aislamiento de base de datos (Fase 6/22) — verificado con evidencia real

- Rol Postgres dedicado `n8n`, sin `SUPERUSER`, sin ningun privilegio
  sobre la base `sintel`.
- `REVOKE CONNECT ON DATABASE sintel FROM PUBLIC` + `GRANT CONNECT ...
  TO sintel` — el rol `n8n` **no puede conectar** a la base de SINTEL
  (verificado: `psql -U n8n -d sintel` → `FATAL: permission denied for
  database "sintel"`, mientras que `psql -U sintel -d sintel` sigue
  funcionando normal).
- n8n nunca recibe `DATABASE_PASSWORD`/`DATABASE_USER` de SINTEL.

## 2. Identidad tecnica SINTEL -> n8n (Fase 13)

Mecanismo elegido: **JWT via el sistema ya existente** (simplejwt,
`SIMPLE_JWT` en `config/settings.py` — `ACCESS_TOKEN_LIFETIME=15min`,
`REFRESH_TOKEN_LIFETIME=7 dias`, `ROTATE_REFRESH_TOKENS=True`,
`BLACKLIST_AFTER_ROTATION=True`). No se crea un segundo mecanismo de
autenticacion (API key/OAuth2/mTLS evaluados y descartados por esta
razon: el proyecto ya tiene un sistema JWT maduro, con rotacion y
blacklist reales, reutilizarlo es mas seguro que inventar uno nuevo).

**Identidad dedicada, nunca un usuario humano:**
`manage.py crear_identidad_tecnica_n8n --schema <tenant>` crea (o
rota, si ya existe):
- Un `User` con `set_unusable_password()` (nunca puede hacer login por
  UI/password, solo via el JWT emitido por el comando) y
  `is_staff=False`/`is_superuser=False` (nunca accede al admin de
  Django).
- `TenantMembership(rol=ADMIN)` en el esquema `public`.
- `TenantProfile(rol=ADMIN)` en el esquema del tenant.
- Un par access/refresh token, impreso UNA sola vez (nunca persistido
  en texto plano del lado de SINTEL).

**Por que ADMIN:** el endpoint real que esta identidad necesita usar
(`upload-document`, ver mas abajo) exige
`[IsTenantMember, IsTenantAdminOrReadOnly]` -- regla YA existente del
ViewSet, no introducida por esta mision. Es mas privilegio del que un
"minimo privilegio" ideal pediria, mitigado por: (a) identidad separada
y revocable independientemente (`TenantMembership.is_active=False`
la desactiva sin borrar el usuario ni sus tokens ya emitidos, que
igual expiran/pueden blacklistearse); (b) auditable (logs de Django
muestran el `user_id` real de esta identidad en cada request, distinto
de cualquier usuario humano); (c) el endpoint solo permite
crear/actualizar Facturas via el pipeline oficial, nunca acceso
arbitrario a otros dominios.

**Rotacion:** el refresh token expira en 7 dias. Un workflow
`N8N-SYSTEM: rotar credenciales` (catalogo, ver `N8N_WORKFLOWS.md`)
debe re-ejecutar el comando antes de esa fecha y actualizar la
credencial guardada en n8n. **No implementado en esta pasada** (el
comando ya soporta rotacion idempotente -- ejecutarlo de nuevo no crea
una segunda identidad, solo emite un par nuevo) -- DEFERRED como
workflow automatico, el comando manual ya es 100% funcional.

**Revocacion:** `TenantMembership.is_active = False` para el usuario
tecnico corta el acceso de inmediato (mismo mecanismo que revoca acceso
de cualquier usuario humano — no se crea un segundo mecanismo de
revocacion).

## 3. Autenticacion SINTEL -> n8n (webhooks salientes, Fase 8/13)

Direccion opuesta: SINTEL llamando a n8n (para notificar eventos). n8n
no tiene un concepto de "usuario" para peticiones entrantes a un
Webhook node -- el mecanismo estandar de la industria (y el que usa
esta mision) es **webhook firmado** (HMAC-SHA256):

```python
X-Sintel-Signature: hmac_sha256(N8N_WEBHOOK_SECRET, body)
X-Sintel-Event-Id:   <uuid del evento>
X-Sintel-Event-Type: <ej. invoice.processed>
```

n8n debe validar la firma en su nodo Webhook (con un nodo Function/Code
que recalcule el HMAC y compare) antes de procesar cualquier payload --
**esto queda como paso de configuracion del workflow receptor en n8n,
DEFERRED** (requiere crear el workflow real en la UI de n8n, fuera del
alcance de codigo de esta mision).

`N8N_WEBHOOK_SECRET` generado (`.env`, no versionado) -- 32 bytes
aleatorios, mismo criterio que `N8N_ENCRYPTION_KEY`.

## 4. FEATURE_UPLOAD_DOCUMENT_ENDPOINT — decision de habilitarlo

`POST /api/v1/core/_apps/facturas/upload-document/` ya existia,
completamente construido y testeado (`apps/tenant/facturas/api/mixins/factura_ubl_mixin.py::upload_document`,
reutiliza el mismo pipeline que los demas endpoints de upload — "Ninguno
de los 3 endpoints de upload duplica el parser ni la persistencia —
todos convergen en `guardar_desde_dto()`", `docs/facturas/FACTURAS_HUB_BASELINE.md`)
pero deshabilitado por `FEATURE_UPLOAD_DOCUMENT_ENDPOINT=False`. Se
habilito (`.env`, `true`) porque:
1. No duplica ningun parser ni pipeline (cumple la Fase 14 de la
   mision: "n8n NO debe parsear por su cuenta la factura").
2. Ya protegido por Dual-Auth + `IsTenantAdminOrReadOnly` (no se abre
   un endpoint anonimo).
3. Es exactamente el endpoint que la Fase 14 pide para el Caso de Uso
   #1 ("REST API... para... uploads de archivos").

## 5. Que NUNCA se hizo (Fase 22, verificado)

```
[x] n8n nunca recibio credenciales DATABASE_* de SINTEL
[x] n8n nunca ejecuta SQL sobre tablas de SINTEL (rol sin CONNECT a `sintel`)
[x] No se replicaron modelos Django en n8n
[x] No se duplico el parser XML fiscal (upload-document reusa guardar_desde_dto())
[x] No se duplico DocumentDispatcher (n8n usa el endpoint HTTP, no el pipeline de mail)
[x] No se toco pgvector/embeddings/RetrievalService/AI-VECTOR (fuera de alcance, verificado sin cambios)
[x] AI_WRITE_ENABLED no se toco
[x] No se creo un segundo mecanismo de autenticacion (JWT ya existente, reutilizado)
[x] No se creo un segundo RBAC (TenantMembership/TenantProfile ya existentes, reutilizados)
```

## Riesgos conocidos, no mitigados en esta pasada (DEFERRED)

- El workflow receptor del webhook (validacion HMAC del lado de n8n) no
  esta creado — requiere trabajo en la UI de n8n, no en codigo SINTEL.
- La identidad tecnica tiene rol ADMIN (heredado del endpoint existente,
  no introducido por esta mision) — un rol mas granular requeriria
  cambiar los permisos del ViewSet real de Facturas, fuera del alcance
  minimo de esta mision.
- Exposicion publica de n8n (nginx + dominio) queda DEFERRED — ver
  `N8N_ARCHITECTURE.md`.
