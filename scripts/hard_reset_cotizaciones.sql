-- ==========================================
-- HARD RESET - App Cotizaciones
-- ==========================================
-- Este script elimina todas las tablas de cotizaciones
-- y los registros de migraciones de Django.
-- 
-- USO: Ejecutar en el esquema del tenant correspondiente
-- ==========================================

-- Eliminar tablas en orden (respetando dependencias)
DROP TABLE IF EXISTS "tenant_cotizaciones_item" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_documento" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_configuracion" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_producto" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_servicio" CASCADE;

-- Eliminar registros de migraciones de Django
-- NOTA: Reemplazar 'schema_name' con el nombre del esquema actual
DELETE FROM "django_migrations" WHERE app = 'tenant_cotizaciones';

-- Verificar eliminación
SELECT 
    table_name 
FROM 
    information_schema.tables 
WHERE 
    table_schema = current_schema()
    AND table_name LIKE 'tenant_cotizaciones%';

-- Si no hay resultados, las tablas fueron eliminadas correctamente
