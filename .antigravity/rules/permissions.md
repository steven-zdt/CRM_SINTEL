# Permisos y Comandos Autorizados

Antigravity adopta los permisos de ejecución establecidos para el proyecto.

## Comandos de Mantenimiento Autorizados
- `docker-compose restart *`
- `docker exec *`
- `git status`, `git diff *`, `git log *`

## Comandos de Django/Python Autorizados
- `python -m py_compile *` (Validación obligatoria)
- `python manage.py test *`
- `python manage.py migrate_schemas`
- `python manage.py seed_reglas_contables`
- `python manage.py backfill_asientos_gastos`
- `python manage.py collectstatic`

## Gestión de Archivos y Archivo
- Se permite el movimiento de reportes de auditoría y archivos temporales a la carpeta `_archive/` o `documentacion/_archive/`.

## Restricciones de Escritura
- Cualquier escritura en archivos que no sigan el patrón Service Layer o que afecten el esquema público requiere confirmación explícita.
