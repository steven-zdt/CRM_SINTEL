# TLS_MIGRATION — Fase 22

Levantamiento real, 2026-08-31. **Ninguna clave privada en este
documento** -- solo metadata pública del certificado.

## Certificado actual (autofirmado, uso LAN)

```
Subject:  CN=*.sintel.com, O=Sintel, C=CO
Issuer:   CN=*.sintel.com, O=Sintel, C=CO  (autofirmado)
notBefore: 2026-08-05
notAfter:  2036-08-02   (10 años, sin riesgo de expiración a corto plazo)
SHA1 Fingerprint: 56:3C:C7:65:DF:4C:4B:01:20:CF:21:A2:C9:A3:D2:5E:52:56:FA:31
```

**Hallazgo real, no corregido en esta pasada (fuera del alcance de
"solo auditar", requiere decidir el dominio correcto antes de
regenerar):** el `CN`/`Subject` del certificado es `*.sintel.com`, NO
`*.sintel.net.co` -- el dominio real usado en todo el resto del stack
(`TENANT_DOMAIN_BASE`, `ALLOWED_HOSTS`, `Domain` de cada tenant). Un
navegador validando estrictamente el hostname contra el certificado
vería un mismatch de nombre además de la advertencia esperada de
"autofirmado" -- dos advertencias distintas, no una. Ver
`docs/network/LAN_MULTI_TENANT_FINAL_REPORT.md` para el contexto del
dominio real. Recomendado: regenerar el certificado con
`CN=*.sintel.net.co` (o el dominio real que se decida para el TARGET)
antes del cutover -- no se regeneró aquí para no invalidar el
certificado actualmente en uso por sesiones activas sin necesidad
real durante una auditoría.

## Almacenamiento

Volumen Docker `crm_sintel_nginx_certs` (`/etc/nginx/certs/`, 3 kB) --
**persiste entre rebuilds de la imagen `nginx`** (el entrypoint solo
genera un cert nuevo si no existe uno ya en el volumen, ver
`documentacion/INFRA_RED_LOCAL_MULTI_TENANT.md` sección "Certificado
SSL — Persistencia").

## Migración a TARGET

- **`.crt` (público):** copiar sin restricción --
  `docker compose cp nginx:/etc/nginx/certs/sintel.crt`.
- **`.key` (privado):** copiar únicamente por el mismo canal seguro
  recomendado en `SECRETS_MATRIX.md` -- nunca a este repo, nunca a
  chat, nunca a un documento de `docs/migration/`.
- Si se regenera el certificado con el CN correcto (recomendado, ver
  hallazgo arriba) en el TARGET directamente, no hace falta migrar la
  clave privada actual en absoluto -- opción más simple y más segura.
