# MEDIA_MIGRATION — Fases 16, 17, 34

## `media/` (Fase 16)

**No es un volumen Docker** -- bind-mount directo (`.:/app` en
`docker-compose.yaml`) al filesystem del host. Vive en
`C:\Users\steve\OneDrive\Documents\crm_sintel\media\`, ya sincronizado
continuamente por OneDrive (no es una copia point-in-time manual, es
sync continuo -- ventaja real para este entorno, pero **no sustituye**
un backup versionado con checksum verificable en un punto exacto en
el tiempo).

- 165 archivos, 279.89 MB (`documentos_soporte/`, `empleados/`, y
  subcarpetas por tipo de documento).
- Manifiesto SHA256 completo generado 2026-08-31:
  `backups/migration_20260831/MEDIA_SHA256SUMS.txt` (165 líneas, ruta
  relativa + hash por archivo).

Verificación de integridad en TARGET (tras copiar):

```powershell
Get-ChildItem -Recurse -File media | ForEach-Object {
    $h = Get-FileHash -Algorithm SHA256 $_.FullName
    $rel = $_.FullName.Substring((Resolve-Path .).Path.Length+1) -replace '\\','/'
    "$($h.Hash.ToLower())  $rel"
} | Compare-Object (Get-Content MEDIA_SHA256SUMS.txt)
# Sin diferencias = integridad confirmada
```

## `staticfiles/` (Fase 17)

18 MB, **generado**, no fuente. La arquitectura ya establece
(`Dockerfile` líneas 39-47) que `collectstatic` corre automáticamente
en cada build/arranque del contenedor `web`. Nginx sirve
`/static/` directamente desde `/app/staticfiles/` (bind-mount, mismo
mecanismo que `media/`).

**No se trata `staticfiles/` como fuente de verdad** -- la fuente real
es el código (`apps/**/static/`) + `nginx/nginx.conf`. En el TARGET,
`staticfiles/` se regenera automáticamente al construir/arrancar
`web` -- no requiere copiarse ni verificarse por checksum, solo
confirmar que `collectstatic` corrió sin error (Fase 35, parte del
smoke test post-restore).

## Documentos críticos de muestra (Fase 34, para cuando exista TARGET)

Al validar en un TARGET real, abrir al menos 1 archivo de cada tipo
presente (`documentos_soporte/`, `empleados/`) para confirmar que no
solo el tamaño/checksum coincide, sino que el archivo es legible
(un PDF corrupto puede tener el tamaño correcto y aun así estar dañado
si la copia truncó el stream a mitad de transferencia) -- **no
ejecutado en esta pasada** porque no existe TARGET; queda como paso
explícito en `POST_MIGRATION_VALIDATION.md`.
