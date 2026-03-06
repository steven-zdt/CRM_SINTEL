-- ==========================================
-- ELIMINACIÓN DE TABLAS - App Cotizaciones
-- ==========================================
-- INSTRUCCIONES:
-- 1. Conectarse al esquema del tenant (ej: sintel_com)
-- 2. Ejecutar este script completo
-- 3. Luego ejecutar: python manage.py migrate tenant_cotizaciones
-- ==========================================

-- IMPORTANTE: Reemplazar 'sintel_com' con el nombre del esquema de tu tenant
SET search_path TO sintel_com;

-- Eliminar tablas en orden (respetando dependencias)
-- Las tablas se eliminan en orden inverso de dependencias

DROP TABLE IF EXISTS "tenant_cotizaciones_item" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_documento" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_configuracion" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_producto" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_servicio" CASCADE;

-- Eliminar registros de migraciones de Django
DELETE FROM "django_migrations" WHERE app = 'tenant_cotizaciones';

-- Verificar eliminación (debe retornar 0 filas)
SELECT 
    table_name 
FROM 
    information_schema.tables 
WHERE 
    table_schema = current_schema()
    AND table_name LIKE 'tenant_cotizaciones%'
ORDER BY table_name;

-- Si la consulta anterior no retorna resultados, las tablas fueron eliminadas correctamente
-- Mensaje esperado: "0 filas retornadas"
