# TARGET_REQUIREMENTS

Requisitos mínimos reales para un servidor TARGET, derivados de la
auditoría real de SOURCE (no genéricos).

## Software

- Docker Engine + Docker Compose v2+ (SOURCE usa Compose `v5.3.1` --
  cualquier versión reciente compatible con la sintaxis de
  `docker-compose.yaml` de este repo sirve, no se requiere la misma
  versión exacta).
- Sistema operativo: indiferente para Docker en sí, pero si el TARGET
  es Windows, replicar la lección real de esta sesión --
  `postgresql-client` del `Dockerfile` debe fijarse a la misma versión
  major que el `postgres:16-alpine` del compose (ya corregido en el
  `Dockerfile` de este repo vía PGDG, ver `IMAGE_MANIFEST.md`) --
  irrelevante si el host es Linux/Windows, el fix ya vive en el
  `Dockerfile`, no en el host.

## Recursos mínimos (derivados del uso real observado en SOURCE)

- RAM: SOURCE usa activamente varios GB con el stack completo
  arriba (7 servicios) más el propio Windows -- recomendado 8 GB+
  dedicados solo al stack Docker en el TARGET, más margen para el SO
  si el TARGET también es multipropósito.
- Disco: imágenes (~4.5 GB combinadas sin contar build cache) +
  volúmenes actuales (~720 MB) + `media/` (280 MB) + crecimiento
  esperado -- 20 GB libres como piso razonable, no ajustado.
- CPU: sin requisito estricto identificado en esta auditoría (el stack
  no mostró saturación de CPU en el levantamiento).

## Red

- Puertos 80/443 disponibles y sin conflicto con otro servicio del
  host (lección real de esta sesión: un servidor con IP duplicada en
  la LAN hace que Nginx nunca reciba el tráfico aunque esté
  perfectamente configurado -- verificar con `arp -a` que la IP
  elegida para el TARGET esté realmente libre ANTES de asignarla,
  igual que se hizo para `192.168.2.17` en SOURCE).
- Si el TARGET expone directamente el puerto de Django (`8000`) a
  cualquier interfaz que no sea loopback, es una regresión respecto al
  fix ya aplicado en SOURCE (`docker-compose.yaml`, `web: ports:
  127.0.0.1:8000:8000`) -- Nginx debe ser el único punto de entrada.
- `db`/`redis`/`neo4j` nunca expuestos más allá de `127.0.0.1` en el
  TARGET (mismo patrón ya verificado en SOURCE).

## DNS/TLS (prerequisito, no bloqueante para preparar TARGET pero sí para el cutover real)

Ver `DNS_MIGRATION.md`/`TLS_MIGRATION.md` -- el wildcard DNS interno
no está operativo hoy independientemente de dónde viva el servidor;
resolverlo es un prerequisito de infraestructura separado de "tener un
TARGET", no algo que la migración en sí resuelva.

## Secretos

`.env` completo (nombres en `SECRETS_MATRIX.md`) provisto por un canal
seguro, con `DJANGO_SECRET_KEY`/`JWT_SECRET_KEY` **regenerados** para
el TARGET (no reusar los de SOURCE -- ver `SECRETS_MATRIX.md`).
