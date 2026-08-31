# SOURCE_HOST_INVENTORY — Fase 1

Levantamiento real, 2026-08-31.

## Sistema operativo

- Microsoft Windows 11 Pro, versión `10.0.26200`, 64 bits.
- Docker corre vía Docker Desktop (backend WSL2/Hyper-V), no Linux nativo.

## CPU / RAM

- CPU: Intel(R) Core(TM) i5-10400T @ 2.00GHz, 6 núcleos físicos, 12 lógicos.
- RAM total: 12,387,684 KB (~11.8 GB). RAM libre en el momento del
  levantamiento: 1,443,692 KB (~1.4 GB) -- **uso alto**, considerar al
  dimensionar el TARGET (no dimensionar el TARGET igual a lo observado
  bajo presión de memoria en un momento puntual de dev).

## Disco

| Unidad | Usado | Libre |
|---|---|---|
| C: | ~100 GB | ~137 GB |
| D: | ~0.6 GB | ~931 GB |
| X:/Y: | ~202 GB | ~751 GB (unidades de red/virtuales) |

## Red

- Interfaz Ethernet: IP estática `192.168.2.17` (reasignada 2026-08-31,
  ver `docs/network/LAN_MULTI_TENANT_FINAL_REPORT.md` para el porqué).
  MAC `E4-A8-DF-9C-F8-4D`.
- Interfaz Wi-Fi: `192.168.2.197` (DHCP), MAC `14-5A-FC-31-19-77`.
- DNS configurado: `192.168.2.1` (router) -- el wildcard DNS interno
  `*.sintel.net.co` NO está operativo (hallazgo ya documentado).

## Docker

```
Docker Desktop 4.84.0 (234817)
Engine: 29.6.2 (API 1.55)
containerd: v2.2.5
runc: 1.3.6
Docker Compose: v5.3.1
```

## Repositorio

- Directorio de trabajo: `C:\Users\steve\OneDrive\Documents\crm_sintel`
  -- **sincronizado por OneDrive** (relevante para `media/`/`staticfiles/`,
  ver `MEDIA_MIGRATION.md`).
- Branch: `feat/onboarding-cookie`.
- HEAD: `6d1d94f3ec5b1a8a7443d26e46d003b4e2e5740f`.
- Working tree al momento de este levantamiento: cambios sin commitear
  en `apps/public/core/middleware.py`, `apps/public/tenants/services/
  deletion_service.py`, `tests/public/tenants/test_hard_delete_tenant.py`,
  `notas.txt` -- **pertenecen a 2 sesiones paralelas activas en este
  mismo entorno** (`crm-sintel-a4`, `crm-sintel-06`), no a esta misión.
  Un archivo nuevo sin trackear: `apps/public/core/tests/
  test_csrf_trusted_origin_middleware.py` (misma causa).

**Implicación real para la migración (Fase 24):** cualquier paquete de
migración de código debe decidir explícitamente si esos cambios en
progreso de las sesiones paralelas se incluyen o no -- no se pierden
por accidente, pero tampoco se asume su inclusión automática sin que
esas sesiones terminen su propio trabajo.
