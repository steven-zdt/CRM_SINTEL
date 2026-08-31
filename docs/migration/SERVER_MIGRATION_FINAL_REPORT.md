# SERVER_MIGRATION_FINAL_REPORT

**Fecha:** 2026-08-31. **SOURCE:** esta máquina (Windows 11 Pro,
`192.168.2.17`). **TARGET:** no existe -- ninguna infraestructura
provista para esta misión.

## Estado final

## **`SOURCE_AUDIT = READY_FOR_MIGRATION`** · **`MIGRATION = NOT_READY`** (no `BLOCKED_SAFE`: nada bloquea seguir auditando, solo falta un TARGET real para continuar)

No se declara `MIGRATION_READY = VERIFIED` -- eso exige un TARGET real
donde restaurar y validar (Fases 27-59 de la misión), que no existe en
este momento. Lo que sí se completó, con evidencia real y verificable,
es **todo lo que depende exclusivamente de SOURCE**: inventario
completo, backups reales con checksum, y los 14 documentos de
`docs/migration/` que sirven de base para ejecutar el resto en cuanto
exista un TARGET.

## Commit / versión auditada

Branch `feat/onboarding-cookie`, HEAD `6d1d94f3ec5b1a8a7443d26e46d003b4e2e5740f`.

## Imágenes (detalle: `IMAGE_MANIFEST.md`)

7 imágenes: 3 build-local (`web`, `celery`, `nginx`, reconstruibles
desde el `Dockerfile`/`nginx/nginx.conf` actuales) + 4 de registry
oficial fijadas por tag+digest (`postgres:16-alpine`,
`redis:7.2-alpine`, `neo4j:5.24-community`,
`cloudflare/cloudflared:2025.5.0`).

## Containers / volúmenes (detalle: `SERVER_MIGRATION_BASELINE.md`, `VOLUME_MAP.md`)

7 servicios, todos `healthy` al momento del levantamiento. 3 volúmenes
Docker críticos (`postgres_data` 174 MB, `neo4j_data` 544 MB,
`nginx_certs` 3 kB) + `media/`/`staticfiles/` como bind-mounts
directos al host (no volúmenes Docker).

## Base de datos (detalle: `DATABASE_MIGRATION.md`)

PostgreSQL 16.14, 5 schemas (public + 4 tenants). Backup lógico real
ejecutado: **5/5 exitoso, 0 errores**, checksums SHA256 generados,
copiado fuera del contenedor efímero a `backups/migration_20260831/`
(gitignored). Restore ya verificado end-to-end en la misión de
producción previa de esta misma sesión (`BAK-02`) -- mismo mecanismo,
no repetido innecesariamente aquí.

## Media (detalle: `MEDIA_MIGRATION.md`)

165 archivos, 279.89 MB, manifiesto SHA256 completo generado. Ya vive
en el filesystem del host, sincronizado por OneDrive de forma
continua.

## DNS (detalle: `DNS_MIGRATION.md`)

No modificado (regla explícita de la Fase 21). Wildcard `*.sintel.net.co`
confirmado NO operativo por dos rutas independientes (Cloudflare
público y DNS interno LAN) -- prerequisito independiente de la
migración, no resuelto por ella.

## TLS (detalle: `TLS_MIGRATION.md`)

Certificado autofirmado inventariado, válido hasta 2036. **Hallazgo
real:** `CN=*.sintel.com`, no `*.sintel.net.co` (el dominio real en
uso) -- mismatch de nombre además de la advertencia esperada de
autofirmado. No corregido en esta pasada (requiere decidir el dominio
final del TARGET primero).

## Tests / smoke

No ejecutados contra TARGET (no existe). Los smoke tests/checks
automatizados ya construidos en la misión de producción previa
(`apps/public/core/production_readiness/`) quedan documentados en
`CUTOVER_RUNBOOK.md`/`POST_MIGRATION_VALIDATION.md` como el primer
paso a correr en cuanto exista un TARGET -- reutilizables tal cual,
sin reescribirlos.

## Problemas encontrados y su estado

| Hallazgo | Estado |
|---|---|
| Volúmenes anónimos sin nombre declarado (2, tamaño menor) | Documentado, descartado deliberadamente de la migración (no forman parte del contrato oficial de `docker-compose.yaml`) |
| Neo4j sin mecanismo de backup lógico auditado | Documentado como punto abierto en `MIGRATION_RELEASE_GATE.md` -- no ejecutado en esta pasada |
| TLS cert con CN incorrecto (`*.sintel.com` vs `*.sintel.net.co`) | Documentado, no corregido (decisión de dominio pendiente) |
| `runserver` de Django en vez de un servidor WSGI de producción | Documentado como brecha real para un TARGET de producción -- no asumida resuelta |
| DNS wildcard interno no operativo | Ya documentado en misión previa (LAN), confirmado sin cambios aquí |

## Riesgos

- Migrar sin resolver el DNS wildcard deja al TARGET en el mismo
  estado de acceso limitado que SOURCE tiene hoy (solo alcanzable vía
  hosts file manual por cliente).
- Restaurar el volumen de Neo4j sin un backup lógico propio (copia
  cruda de volumen entre hosts con versiones distintas de Neo4j) es
  frágil -- mismo tipo de riesgo que ya se demostró real para Postgres
  en la misión `BAK-02` (incompatibilidad de versión de cliente).
- El certificado TLS con CN incorrecto, si se copia tal cual al
  TARGET, propaga el mismo mismatch -- mejor regenerarlo en el TARGET
  con el CN correcto que migrar la clave actual.

## Rollback

Trivial en este punto: SOURCE nunca se tocó de forma destructiva
(regla #1 de la misión, respetada íntegramente). Ver
`ROLLBACK_RUNBOOK.md` para el procedimiento completo una vez exista un
TARGET real y se ejecute un cutover.

## Estado final declarado

```
MIGRATION_READY = NOT_READY
SOURCE_AUDIT    = READY_FOR_MIGRATION
BACKUP          = VERIFIED (Postgres, 5/5 schemas, checksums generados)
RESTORE         = VERIFIED (mecanismo, misión BAK-02 previa)
TARGET          = NO_EXISTE
CUTOVER         = NO_EJECUTADO
```

## Siguiente paso real (no ejecutado, fuera del alcance de esta sesión)

Provisionar un TARGET real (servidor, VM, o instancia cloud) con los
requisitos de `TARGET_REQUIREMENTS.md`, y retomar desde `CUTOVER_RUNBOOK.md`
paso 3 en adelante -- todo lo anterior (backup, manifest, runbooks) ya
está listo y no necesita repetirse salvo que el estado de SOURCE
cambie sustancialmente antes de esa fecha (en cuyo caso, regenerar
solo el backup, no toda la auditoría).
