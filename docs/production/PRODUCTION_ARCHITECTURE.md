# PRODUCTION_ARCHITECTURE

Arquitectura real (no aspiracional) — ver `docs/production/PRODUCTION_BASELINE.md`
para el detalle completo con evidencia.

```
Internet
   │
   ▼
cloudflared (Cloudflare Tunnel) — expone el servicio sin IP pública directa
   │
   ▼
nginx (reverse proxy, volumen nginx_certs para TLS)
   │
   ▼
web (Django + DRF, Gunicorn/runserver)
   │
   ├──► db (PostgreSQL 16, schema-per-tenant via django-tenants)
   ├──► redis (cache + broker Celery)
   ├──► neo4j (EKG — grafo de dependencias/impacto, tools.ekg)
   │
celery (worker: colas high_priority,default — SIN beat/scheduler)
```

**Multi-tenancy:** resolución por hostname → `TenantMainMiddleware`
(django-tenants) → schema PostgreSQL. `TenantSecurityMiddleware`
(`apps/public/tenants/middleware.py`) aplica el enforcement real de
`is_active`/trial (ver `docs/console/TENANT_LIFECYCLE.md`) en cada
request, antes de cualquier vista.

**No existe orquestador (k8s/ECS)** — la unidad de despliegue es
`docker compose`. No se debe implementar blue/green vía Kubernetes solo
para satisfacer un checklist genérico (per instrucción explícita del
plan) — ver `DEPLOYMENT_RUNBOOK.md` para la estrategia real compatible
con Compose.
