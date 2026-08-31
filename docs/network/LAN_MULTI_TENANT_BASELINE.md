# LAN_MULTI_TENANT_BASELINE — Fase 0

Levantamiento real ejecutado 2026-08-31 sobre la máquina de desarrollo
actual (`Windows 11 Pro`, hostname de trabajo de este repo). Todo dato
aquí es observado directamente (comandos reales), no inferido de la
documentación existente.

## Documentación leída

- `AGENTS.md`, `documentacion/arquitectura_general.md`
- `documentacion/INFRA_RED_LOCAL_MULTI_TENANT.md` (2026-06-15,
  "IMPLEMENTADO" — **crítico para esta misión**, ver hallazgo principal)
- `config/settings.py` (`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_*`,
  `MIDDLEWARE`, `TENANT_DOMAIN_BASE`)
- `nginx/nginx.conf`, `docker-compose.yaml`
- `apps/public/tenants/middleware_urlconf.py` (`TenantSecurityAndURLConfMiddleware`)
- `apps/public/tenants/management/commands/ensure_tenant_dns.py`

## Hallazgo previo ya documentado (no descubierto por esta misión, confirmado por ella)

`INFRA_RED_LOCAL_MULTI_TENANT.md` describe una arquitectura completa
"IMPLEMENTADA" (2026-06-15) donde `192.168.2.15` es un **Windows Server
2022 Datacenter separado** corriendo Windows DNS Server (zona wildcard
`*.sintel.net.co`) + firewall dedicado. La sección de Troubleshooting
del mismo documento (fechada 2026-08-05, **anterior a esta misión**) ya
registra que esa arquitectura NO estaba operativa en el entorno de
desarrollo de ese momento, y que la IP real de la interfaz Ethernet de
la máquina de desarrollo había derivado a `192.168.2.200`. Esta misión
confirma en vivo (2026-08-31) que la situación cambió otra vez y de
forma más seria: ver Fase 1.

## Fase 1 — IP real del servidor

```
Get-NetAdapter | Select Name, Status, MacAddress
Get-NetIPAddress -AddressFamily IPv4 | Select InterfaceAlias, IPAddress, PrefixOrigin
```

| Interfaz | IP | Origen | Estado |
|---|---|---|---|
| Ethernet | `192.168.2.15` | **Manual (estática)** | Up |
| Wi-Fi | `192.168.2.197` | DHCP | Up |

MAC del adaptador Ethernet de esta máquina: `E4-A8-DF-9C-F8-4D`.
Gateway Ethernet: `192.168.2.2`. Gateway Wi-Fi: `192.168.2.1`.

**`192.168.2.15` SÍ está configurada como IP estática real en esta
máquina** — no es un dato desactualizado. El hallazgo real no es que la
IP esté mal escrita en la documentación, sino un conflicto de red activo
— ver Fase 13.

## Fase 2 — Puertos Docker

```
docker compose port nginx 80    → 0.0.0.0:80
docker compose port nginx 443   → 0.0.0.0:443
docker compose port web 8000    → 0.0.0.0:8000   [ANTES DEL FIX]
```

**Hallazgo real (corregido, ver `docker-compose.yaml`):** `web` (Django
`runserver`, servidor de desarrollo crudo) estaba publicado en
`0.0.0.0:8000`, alcanzable desde toda la LAN sin pasar por Nginx —
viola explícitamente la regla de esta misión ("No exponer Django 8000
públicamente si Nginx debe ser el punto de entrada"). `db`/`redis`/
`neo4j` ya estaban correctamente restringidos a `127.0.0.1`. Corregido
a `127.0.0.1:8000:8000` (mismo patrón que los otros servicios internos),
preservando acceso directo de depuración desde esta misma máquina.

## Fase 3 — Firewall del servidor (esta máquina)

```
Get-NetFirewallRule -DisplayName 'Docker Desktop Backend' | Get-NetFirewallPortFilter
→ Protocol=TCP/UDP, LocalPort=Any, Profile=Public
```

La regla "Docker Desktop Backend" permite entrada en **cualquier
puerto** que Docker publique, perfil `Public`. Antes del fix de Fase 2,
esto incluía el puerto 8000 sin filtrar. Tras el fix, sigue permitiendo
80/443 (correcto, Nginx) y ya no expone 8000 a la LAN (bindeado a
loopback, inalcanzable externamente sin importar el firewall).

**No existen** las reglas de firewall específicas `SINTEL - ...`
descritas en `INFRA_RED_LOCAL_MULTI_TENANT.md` (verificado con
`Get-NetFirewallRule | Where DisplayName -like '*SINTEL*'` → vacío) —
consistente con que esas reglas viven en el Windows Server 2022 real
descrito en ese documento, no en esta máquina de desarrollo.

## Fase 4 — DNS LAN

```
nslookup admin.sintel.net.co   → *** No existe el dominio (NXDOMAIN)
nslookup sintel.net.co         → resuelve a IPs públicas de Cloudflare
                                  (104.21.26.232, 172.67.168.148, ...)
Get-DnsClientServerAddress     → Ethernet: 192.168.2.1
                                  Wi-Fi: 192.168.2.1, 192.168.1.100
```

**Hallazgo crítico:** el wildcard DNS interno `*.sintel.net.co →
192.168.2.15` que la arquitectura documentada requiere **no está
operativo** desde ningún resolutor DNS que esta máquina usa
actualmente. El DNS primario real es `192.168.2.1` (el router/gateway),
no `192.168.2.15` — contradice la instrucción de configuración del
router en `INFRA_RED_LOCAL_MULTI_TENANT.md` ("Primary DNS:
192.168.2.15"). Ver `LAN_MULTI_TENANT_FINAL_REPORT.md` para el análisis
completo y las dos causas raíz reales.

## Fase 5-11 — Domain, ALLOWED_HOSTS, CSRF, CORS, Nginx, TenantMiddleware

Todo verificado en el código y en vivo — ver
`LAN_MULTI_TENANT_FINAL_REPORT.md` sección "Capa de aplicación (100%
verificada)" para el detalle punto por punto. Resumen: **la capa de
aplicación (Nginx, Django, TenantMiddleware, ALLOWED_HOSTS, CSRF, CORS,
resolución de tenant por hostname) funciona correctamente** — el
problema real está en las capas de red física/DNS, fuera del
repositorio de código.
