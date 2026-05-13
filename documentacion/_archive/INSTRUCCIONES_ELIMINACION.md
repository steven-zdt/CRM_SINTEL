# Instrucciones para Eliminar Tablas de Cotizaciones

## ⚠️ ADVERTENCIA
Este proceso elimina **TODAS** las tablas y datos de cotizaciones. Asegúrate de tener un backup si necesitas preservar datos.

## Método 1: Usando psql (Recomendado)

```bash
# Conectarse a la base de datos
psql -h localhost -U postgres -d crm_sintel

# Dentro de psql, ejecutar:
\c crm_sintel
SET search_path TO sintel_com;  -- Reemplazar 'sintel_com' con tu esquema

-- Eliminar tablas
DROP TABLE IF EXISTS "tenant_cotizaciones_item" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_documento" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_configuracion" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_producto" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_servicio" CASCADE;

-- Eliminar registros de migraciones
DELETE FROM "django_migrations" WHERE app = 'tenant_cotizaciones';

-- Verificar
SELECT table_name FROM information_schema.tables 
WHERE table_schema = current_schema() 
AND table_name LIKE 'tenant_cotizaciones%';
```

## Método 2: Ejecutar Script SQL Directo

```bash
# Ejecutar el script SQL directamente
psql -h localhost -U postgres -d crm_sintel -f scripts/ELIMINAR_TABLAS_COTIZACIONES.sql
```

**Nota**: Asegúrate de editar el script y cambiar `sintel_com` por el nombre de tu esquema de tenant.

## Método 3: Desde pgAdmin o DBeaver

1. Conectarse a la base de datos `crm_sintel`
2. Seleccionar el esquema del tenant (ej: `sintel_com`)
3. Abrir el archivo `scripts/ELIMINAR_TABLAS_COTIZACIONES.sql`
4. Editar la línea `SET search_path TO sintel_com;` con tu esquema
5. Ejecutar el script completo

## Método 4: Usando Python (si la BD está disponible)

```bash
python scripts/eliminar_tablas_cotizaciones.py
```

## Después de Eliminar

Una vez eliminadas las tablas, aplicar la nueva migración:

```bash
python manage.py migrate tenant_cotizaciones
```

## Verificación Final

Verificar que las tablas se crearon correctamente:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'sintel_com'  -- Reemplazar con tu esquema
AND table_name LIKE 'tenant_cotizaciones%'
ORDER BY table_name;
```

Debería mostrar:
- `tenant_cotizaciones_configuracion`
- `tenant_cotizaciones_documento`
- `tenant_cotizaciones_item`
- `tenant_cotizaciones_producto`
- `tenant_cotizaciones_servicio`
