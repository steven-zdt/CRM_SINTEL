# POST_MIGRATION_VALIDATION — Fases 30-51

Checklist a ejecutar contra un TARGET real cuando exista. **No
ejecutado en esta pasada** (sin TARGET) -- preparado con los comandos
reales ya verificados en SOURCE durante esta sesión, no genéricos.

## Datos (Fase 30-34)

```
[ ] manage.py migrate                    -- sin errores
[ ] manage.py showmigrations             -- todo aplicado, sin huerfanos
[ ] Conteo de filas SOURCE vs TARGET      -- por tabla, no solo totales
    (ver tablas nucleo en DATABASE_MIGRATION.md como punto de partida)
[ ] SHA256SUMS.txt de los .dump           -- coincide con el backup real
[ ] Muestra de relaciones (Fase 33)       -- sin huerfanos:
    Tenant<->Domain, Tenant<->Membership, Factura<->Venta,
    Venta<->Cliente, Compra<->Proveedor, Movimiento<->Producto,
    Asiento<->Documento, Pago<->Documento
[ ] media/ -- Compare-Object contra MEDIA_SHA256SUMS.txt, 0 diferencias
[ ] Abrir 1 XML, 1 PDF, 1 imagen de muestra -- legibles, no truncados
[ ] collectstatic corre sin error en TARGET
```

## Settings de producción (Fase 36)

```
[ ] DEBUG=False
[ ] ALLOWED_HOSTS -- lista explicita del dominio/IP real de TARGET,
    nunca '*', nunca 'localhost' en un endpoint publico
[ ] CSRF_TRUSTED_ORIGINS -- dominio real de TARGET
[ ] CORS -- mismo criterio
[ ] SECURE_* settings -- correr:
    docker compose exec web python manage.py production_readiness
    (framework ya construido, reutilizar tal cual contra TARGET)
```

## Multi-tenant (Fase 37-38)

```
[ ] Crear Tenant A y Tenant B de prueba en TARGET
[ ] Login por hostname en cada uno -- redirige al tenant correcto
[ ] A nunca lee B: UI, API, DB (schema separado por diseno --
    confirmar con un curl -H "Host: A" y otro -H "Host: B", comparar
    contenido, mismo metodo ya usado en la mision LAN de esta sesion)
[ ] User Context correcto tras login (id, email, tenant coinciden)
```

## Celery/Redis (Fase 39)

```
[ ] docker compose exec web celery -A config inspect ping
[ ] Encolar una tarea de prueba real, confirmar ejecucion en logs de celery
[ ] Confirmar (again) que no hay celery-beat -- si se agrega en TARGET,
    documentarlo como cambio de arquitectura respecto a SOURCE, no
    asumirlo silenciosamente
```

## Onboarding / lifecycle (Fase 41-42)

```
[ ] Crear un tenant de prueba end-to-end (mismo mecanismo ya usado
    varias veces esta sesion: crear_tenant_con_owner)
[ ] Verificar Client, Domain, schema, Membership, Empresa, Perfil
[ ] Un tenant con trial EXPIRED sigue bloqueado en TARGET
    (TenantSecurityMiddleware.reconcile_tenant_lifecycle, ya auditado
    y verificado como check automatizado TEN-03)
```

## Facturación / Contabilidad / Bancos / Reporting (Fase 43-46)

```
[ ] 1 factura existente: XML, CUFE, estado y relaciones coinciden
    SOURCE vs TARGET
[ ] DIAN real no operativo -- mock/TEST se conserva explicito
    (FISCAL-01, ya clasificado EXTERNAL_DEPENDENCY, no fingir PASS)
[ ] Asientos: debe = haber (query de balance, no solo conteo de filas)
[ ] Bancos: movimientos y conciliaciones referencian documentos reales
[ ] 1 reporte del dashboard: comparar SOURCE vs TARGET con los mismos
    datos de entrada
```

## Health y red (Fase 48-50)

```
[ ] docker compose ps -- todos HEALTHY, no solo "Up"
[ ] /health responde 200 en TARGET
[ ] nginx healthcheck usa 127.0.0.1 explicito (fix ya aplicado en
    este repo, DEVOPS-M3 -- preservar, no revertir)
[ ] Desde un cliente real: DNS, HTTP, HTTPS resuelven al TARGET
[ ] Si TARGET esta en LAN: PostgreSQL/Redis/Celery siguen SIN exponer
    a la LAN (mismo patron ya verificado en SOURCE: 127.0.0.1 only)
```

## Performance (Fase 51)

```
[ ] Login, resolucion de tenant, dashboard, API, reportes --
    comparar tiempos SOURCE vs TARGET (no buscar igualdad exacta,
    buscar regresiones obvias -- 10x mas lento es una señal real,
    5% de diferencia no lo es)
```
