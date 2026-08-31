# DNS_MIGRATION — Fase 21

Inventario únicamente (Fase 21 lo exige explícito: **NO cambiar DNS
todavía**). Detalle completo con evidencia en
`docs/network/LAN_MULTI_TENANT_FINAL_REPORT.md` (misión previa de esta
misma sesión) -- no se duplica aquí, se referencia.

## Dominio público real: `sintel.net.co`

Registrado en Cloudflare, proxied. Resuelve (vía DNS público, `1.1.1.1`
verificado independientemente del router) a IPs anycast de Cloudflare
(`104.21.26.232`, `172.67.168.148`, + IPv6). Tráfico real vía
Cloudflare Tunnel (`cloudflared`, túnel confirmado conectado y
autenticado, ver `cloudflared/config.yml`: ingress `sintel.net.co` →
`http://nginx:80`).

## Wildcard `*.sintel.net.co` -- NO operativo (confirmado dos veces, dos rutas distintas)

1. **Vía Cloudflare** (`cloudflared/config.yml` ya tiene la regla de
   ingress `*.sintel.net.co → http://nginx:80`, pero el registro DNS
   CNAME wildcard nunca se creó en el dashboard de Cloudflare --
   confirmado consultando `1.1.1.1` directamente: NXDOMAIN).
2. **Vía DNS interno LAN** (la arquitectura documentada en
   `documentacion/INFRA_RED_LOCAL_MULTI_TENANT.md` asume un Windows
   Server con zona DNS interna -- no operativo hoy, DNS primario real
   de este host es el router, `192.168.2.1`, que no conoce esa zona).

## Dominios de tenant actuales (Fase 12, tabla `Domain`)

`sintel.net.co` (public), `home.sintel.net.co`, `qaisotest.sintel.net.co`,
`qa-verify-20260831090942.sintel.net.co`, `admin.sintel.net.co` -- los 4
privados resuelven hoy solo vía entradas manuales en el hosts file de
esta máquina (`127.0.0.1` o `192.168.2.17` según el caso), no vía DNS
real. Ver `docs/network/LAN_MULTI_TENANT_FINAL_REPORT.md` para el
detalle exacto por dominio.

## Implicación para la migración

Migrar el servidor **no resuelve por sí solo** el problema del wildcard
DNS -- son independientes. El TARGET, sin importar su IP, seguirá
necesitando la misma remediación de DNS ya documentada (zona wildcard
real, sea vía Cloudflare completando el registro CNAME faltante, o vía
un DNS interno LAN real) antes de que "cambiar DNS" (Fase 56) tenga
algo real que apuntar al TARGET.
