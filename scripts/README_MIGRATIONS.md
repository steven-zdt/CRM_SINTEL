# Scripts de Migración de Tenants

## Wrapper Seguro: `safe_migrate_tenants.sh`

Script bash que ejecuta migraciones de tenants de forma segura, evitando el error común de pasar `all` como argumento a `--tenant`.

### Uso

```bash
# Migrar todos los tenants (default)
./scripts/safe_migrate_tenants.sh

# Migrar un tenant específico
TENANTS=mi_empresa ./scripts/safe_migrate_tenants.sh
./scripts/safe_migrate_tenants.sh mi_empresa
```

### Variables de Entorno

- `TENANTS`: Controla qué tenants migrar
  - `all` (default): Migra todos los tenants usando `migrate_schemas --tenant --fake-initial`
  - `<schema_name>`: Migra un tenant específico usando `migrate_schemas --schema=<schema_name> --fake-initial`

### Comportamiento

- **TENANTS=all**: Ejecuta `python manage.py migrate_schemas --tenant --fake-initial`
  - ⚠️ **IMPORTANTE**: NO pasa `all` como argumento, solo usa `--tenant` (flag booleano)
  
- **TENANTS=<schema>**: Ejecuta `python manage.py migrate_schemas --schema=<schema> --fake-initial`

### Integración en Entrypoint

El `entrypoint.sh` usa este wrapper automáticamente:

```bash
TENANTS="${TENANTS:-all}"
if [ "$TENANTS" = "all" ]; then
    python manage.py migrate_schemas --tenant --fake-initial
else
    python manage.py migrate_schemas --schema="$TENANTS" --fake-initial
fi
```

## Scripts Corregidos

### `apply_tenant_migrations.sh`

Script para aplicar migraciones manualmente. **Corregido** para usar `--tenant` sin `all`.

**Antes (incorrecto)**:
```bash
python manage.py migrate_schemas --tenant=all
```

**Después (correcto)**:
```bash
python manage.py migrate_schemas --tenant --fake-initial
```

### `apply_tenant_migrations.ps1`

Versión PowerShell del script anterior. **Corregido** de la misma forma.

## Tests

Los tests verifican que:

1. **No se pase `all` como argumento** después de `--tenant`
2. **La construcción de argumentos** sea correcta según `TENANTS`
3. **Los mensajes de log** contengan las frases esperadas

Ejecutar tests:
```bash
pytest tests/public/tenants/test_migrate_invocation_shape.py -v
pytest tests/tenant/core/smoke/test_boot_sequence_no_bad_args.py -v
```

## Referencias

- Documentación oficial de django-tenants: https://django-tenants.readthedocs.io/
- Arquitectura SINTEL: `documentacion/arquitectura_general.md`
