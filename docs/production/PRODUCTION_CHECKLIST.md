# PRODUCTION_CHECKLIST

Checklist operativo por release. **Ejecutar `python manage.py
production_readiness` primero** — cubre automáticamente gran parte de
esta lista (Fase 4-7, 15, 44-45, 58 parcial). Lo que sigue es lo que el
comando NO puede verificar automáticamente (requiere infraestructura
real o juicio humano).

## Pre-release (manual, no automatizable)

- [ ] `DJANGO_SECRET_KEY` real generada y en el `.env`/secret manager
      del entorno de destino (NO el default `django-insecure-...`).
- [ ] `DEBUG=False` en el entorno de destino.
- [ ] Certificado TLS real cargado en el volumen `nginx_certs` (o
      gestionado por `cloudflared`) — verificar expiración.
- [ ] DNS del dominio de destino resuelve al servidor correcto.
- [ ] Backup tomado inmediatamente antes (ver `BACKUP_RESTORE_RUNBOOK.md`).

## Smoke tests post-deploy (Fase 36 — NO ejecutar la suite completa)

- [ ] `GET /health` → 200
- [ ] `GET /` (dominio público) → redirige apropiadamente
- [ ] Login real (staff, dominio público) → 200/302
- [ ] Login real (owner de un tenant existente, dominio del tenant) → 200
- [ ] `GET /console/tenants/` (staff autenticado) → 200, lista tenants reales
- [ ] Un CREATE/READ real en una entidad de negocio (ej. Cliente) dentro
      de un tenant de prueba
- [ ] Logout → sesión invalidada

## Flujos críticos de negocio (Fase 37 — un escenario controlado por flujo, en staging)

- [ ] Onboarding de tenant (ya cubierto extensamente en
      `docs/e2e/ONBOARDING_E2E_REPORT.md` — repetir en el entorno de
      destino real antes del primer release a ese entorno)
- [ ] Cliente → Cotización → Venta → Factura → IVA/Retención → Cobro → Banco → Contabilidad
- [ ] Proveedor → Compra → Recepción → Inventario → Factura de compra → Pago

**No ejecutado en esta pasada contra un ambiente real** — no existe
staging desplegado. Ver `docs/production/PRODUCTION_BASELINE.md`.

## Fiscal readiness (Fase 38-41)

- [ ] Clasificación DIAN: `EXTERNAL_DEPENDENCY` (confirmado, ver
      `docs/remediation/REM-EXT-01.md`) — NO declarar production-ready
      sin credenciales/certificado/WSDL reales.
- [ ] Clasificación DSPNE: `EXTERNAL_DEPENDENCY` (ver `REM-EXT-02.md`).
- [ ] Configuración fiscal por tenant (NIT, régimen, actividad
      económica) — no auditado exhaustivamente en esta pasada; cada
      tenant real debe verificarse individualmente antes de emitir
      documentos fiscales reales, no asumir un régimen único para todos.
- [ ] Retenciones: cálculo/contabilización ya verificados en
      `docs/remediation/REM-P0-03.md` (integridad de datos); conciliación
      bancaria real no verificada contra un banco real (fuera de alcance
      sin datos bancarios reales).

## Governance (Fase 52) — ejecutar antes de cada release

```bash
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py production_readiness
git diff --check
```
