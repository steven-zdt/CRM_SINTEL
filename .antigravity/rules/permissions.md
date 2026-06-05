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
- **Zero-Hardcoding (§29):** PROHIBIDO escribir nombres propios de tenants de produccion (`'home'`, `'cliente'`, `'putito'`, `'tupapi'`) como strings literales en scripts, tests o management commands. Usar patrones ORM dinamicos o placeholders `{schema_name}`.

## Comandos de Validacion Zero-Hardcoding Autorizados (§29 AGENTS.md)

```bash
# Scan de violaciones — debe retornar 0 lineas antes de cerrar cualquier tarea
grep -rn "'home'\|'cliente'\|'putito'\|'tupapi'\|home\.sintel\.com\|cliente\.sintel\.com" \
    apps/ tests/ scripts/ scratch/ --include="*.py" \
    | grep -v "__pycache__\|migration\|assertNotIn\|\.sintel\.local\|{schema\|schema_name='public'"

# Listar tenants activos dinamicamente (patron canonico)
python manage.py shell -c \
    "from apps.public.tenants.models import Client; \
     [print(c.schema_name) for c in Client.objects.exclude(schema_name='public').filter(is_active=True)]"
```
