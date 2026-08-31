# DATABASE_MIGRATION — Fases 11, 12, 13, 14, 15

## Motor

PostgreSQL 16.14 (Alpine, `postgres:16-alpine`), backend
`django_tenants.postgresql_backend` (esquema-por-tenant, `TenantSyncRouter`).

## Catálogo de tenants (Fase 12)

| Client ID | schema | Domain(s) | Membresías | Activo |
|---|---|---|---|---|
| 1 | `public` | `sintel.net.co`, `localhost`, `127.0.0.1` | -- | sí |
| 3 | `home` | `home.sintel.net.co` | 1 | sí |
| 4 | `qaisotest` | `qaisotest.sintel.net.co` | 1 | sí |
| 10 | `qa_verify_20260831090942` | `qa-verify-20260831090942.sintel.net.co` | 1 | **no** (desactivado, misión E2E previa) |
| 14 | `admin` | `admin.sintel.net.co` | 2 (owner + `admin@sintel.com`, misión LAN previa) | sí |

Validado `schema ↔ tenant` y `domain ↔ tenant` -- 1:1 correcto en los
5 casos (sin dominios duplicados, sin schema huérfano; confirmado
contra `information_schema.schemata` real: exactamente 5 schemas no-
sistema, coincide con las 5 filas de `tenants_client`). No se
almacenan contraseñas en este documento.

## Conteo de tablas por schema (Fase 13)

`public`: 31 tablas (`SHARED_APPS`). Cada tenant: 79 tablas
(`TENANT_APPS`) -- idéntico en los 4 tenants, confirma que no hay
drift de migraciones entre schemas.

## Conteo de filas — tablas núcleo (muestra, Fase 13)

| Tabla | `public` | `home` | `admin` |
|---|---|---|---|
| `tenants_client` | 5 | -- | -- |
| `tenants_domain` | 7 | -- | -- |
| `tenants_tenantmembership` | 5 | -- | -- |
| `accounts_user` | 12 | -- | -- |
| `tenant_ventas_venta` | -- | 1 | 0 |
| `facturas_factura` | -- | 1 | 0 |
| `tenant_inventario_producto` | -- | 1 | 0 |
| `contabilidad_asientocontable` | -- | 3 | 0 |

Entorno de desarrollo con datos mínimos reales (no hay tenant de
producción con volumen real todavía) -- los conteos completos por
tabla y por tenant quedan en el propio backup (metadata JSON, ver
abajo), no se transcriben exhaustivamente aquí para evitar que este
documento quede desactualizado frente al dato real.

## Backup lógico real (Fase 14) — ejecutado 2026-08-31

```
python manage.py backup_all_tenants --output-dir /tmp/migration_backup_20260831_162439
-> 5/5 exitosos, 0 errores
```

| Schema | Archivo | Tamaño |
|---|---|---|
| `public` | `public_20260831_162446.dump` | 362,305 bytes |
| `home` | `home_20260831_162447.dump` | 1,157,324 bytes |
| `qaisotest` | `qaisotest_20260831_162447.dump` | 1,213,469 bytes |
| `qa_verify_20260831090942` | `qa_verify_20260831090942_20260831_162448.dump` | 1,286,736 bytes |
| `admin` | `admin_20260831_162449.dump` | 1,138,495 bytes |

Copiados fuera del contenedor (que es efímero, ver hallazgo de
`BAK-02`) a `backups/migration_20260831/` en el host -- **agregado a
`.gitignore`** (nunca deben llegar a git, contienen datos reales,
aunque sean de tenants QA). Formato `custom` (`pg_dump --format=custom
--compress=9`), restaurable con `pg_restore` -- mecanismo ya probado
end-to-end en `docs/production/BACKUP_RESTORE_RUNBOOK.md` (`BAK-02`,
incluyendo el fix real de versión de cliente `pg_dump`/`pg_restore`
encontrado en esa misión).

## Checksum (Fase 15)

`backups/migration_20260831/SHA256SUMS.txt` (5 líneas, formato
`sha256sum` estándar, generado con `Get-FileHash` de PowerShell, sin
BOM). Verificar en cualquier momento con:

```powershell
Get-FileHash -Algorithm SHA256 -Path *.dump | ForEach-Object { "$($_.Hash.ToLower())  $(Split-Path $_.Path -Leaf)" }
# comparar linea a linea contra SHA256SUMS.txt
```

## Backup físico adicional -- Neo4j (punto abierto)

`backup_tenant`/`backup_all_tenants` cubren **solo PostgreSQL**. La
base Neo4j (`crm_sintel_neo4j_data`, 543.5 MB, biblioteca tributaria
en `apps/public/impuestos/search`) no tiene un mecanismo de backup
lógico propio auditado en esta pasada -- queda como punto abierto en
`MIGRATION_RELEASE_GATE.md` (recomendación: `neo4j-admin database
dump`, ejecutar y verificar restore antes de declarar el release gate
completo).
