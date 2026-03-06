# Hard Reset - App Cotizaciones v2.60

**Fecha**: 2024-12-19  
**Objetivo**: Eliminar todas las tablas históricas y crear una nueva migración inicial limpia

## ✅ Tareas Completadas

### 1. Corrección de Importaciones
- ✅ Corregida importación de `ConfiguracionCotizacion` en `admin.py`
  - Cambiado de `from .models import ConfiguracionCotizacion` 
  - A `from .configuracion.models import ConfiguracionCotizacion`

### 2. Corrección de Referencias de Modelos
- ✅ Corregida referencia a `Cliente` en `models.py`
  - Cambiado de `'clientes.Cliente'` 
  - A `'tenant_clientes.Cliente'` (referencia lazy correcta)

### 3. Nueva Migración Inicial
- ✅ Creada migración `0001_initial_v2_60.py`
  - Modelos incluidos:
    - `ConfiguracionCotizacion` (desde `configuracion/models.py`)
    - `Cotizacion`
    - `Producto`
    - `Servicio`
    - `CotizacionItem`

## 📋 Próximos Pasos (Ejecutar Manualmente)

### Paso 1: Eliminar Tablas de la Base de Datos

**Opción A: Usando SQL directo (Recomendado)**

Ejecutar el script SQL en el esquema del tenant correspondiente:

```sql
-- Conectarse al esquema del tenant (ej: sintel_com)
SET search_path TO sintel_com;

-- Eliminar tablas en orden (respetando dependencias)
DROP TABLE IF EXISTS "tenant_cotizaciones_item" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_documento" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_configuracion" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_producto" CASCADE;
DROP TABLE IF EXISTS "tenant_cotizaciones_servicio" CASCADE;

-- Eliminar registros de migraciones de Django
DELETE FROM "django_migrations" WHERE app = 'tenant_cotizaciones';
```

**Opción B: Usando psql**

```bash
psql -h localhost -U postgres -d crm_sintel -c "
SET search_path TO sintel_com;
DROP TABLE IF EXISTS tenant_cotizaciones_item CASCADE;
DROP TABLE IF EXISTS tenant_cotizaciones_documento CASCADE;
DROP TABLE IF EXISTS tenant_cotizaciones_configuracion CASCADE;
DROP TABLE IF EXISTS tenant_cotizaciones_producto CASCADE;
DROP TABLE IF EXISTS tenant_cotizaciones_servicio CASCADE;
DELETE FROM django_migrations WHERE app = 'tenant_cotizaciones';
"
```

**Opción C: Usando el script Python (requiere conexión a BD)**

```bash
python scripts/hard_reset_cotizaciones.py
```

### Paso 2: Aplicar Nueva Migración

Una vez eliminadas las tablas, aplicar la nueva migración:

```bash
python manage.py migrate tenant_cotizaciones
```

### Paso 3: Verificar

Verificar que las tablas se crearon correctamente:

```sql
SELECT 
    table_name 
FROM 
    information_schema.tables 
WHERE 
    table_schema = current_schema()
    AND table_name LIKE 'tenant_cotizaciones%'
ORDER BY table_name;
```

Debería mostrar:
- `tenant_cotizaciones_configuracion`
- `tenant_cotizaciones_documento`
- `tenant_cotizaciones_item`
- `tenant_cotizaciones_producto`
- `tenant_cotizaciones_servicio`

## 📁 Archivos Creados/Modificados

### Migraciones
- ✅ `apps/tenant/cotizaciones/migrations/0001_initial_v2_60.py` (NUEVO)

### Scripts
- ✅ `scripts/hard_reset_cotizaciones.py` (Script Python para eliminación)
- ✅ `scripts/hard_reset_cotizaciones.sql` (Script SQL para eliminación)

### Modelos
- ✅ `apps/tenant/cotizaciones/models.py` (Corregida referencia a Cliente)
- ✅ `apps/tenant/cotizaciones/admin.py` (Corregida importación de ConfiguracionCotizacion)

## ⚠️ Advertencias

1. **Pérdida de Datos**: Este proceso elimina TODAS las tablas y datos de cotizaciones. Asegúrate de tener un backup si necesitas preservar datos.

2. **Esquema Específico**: El script SQL debe ejecutarse en el esquema del tenant correcto. No ejecutar en el esquema `public`.

3. **Dependencias**: Asegúrate de que la app `tenant_clientes` esté instalada y tenga migraciones aplicadas antes de aplicar la nueva migración de cotizaciones.

4. **Orden de Ejecución**: 
   - Primero eliminar tablas
   - Luego aplicar nueva migración
   - No hacer `migrate` antes de eliminar las tablas (causará errores)

## 🎯 Resultado Esperado

Después de completar los pasos:
- ✅ Todas las tablas antiguas eliminadas
- ✅ Nueva migración `0001_initial_v2_60.py` aplicada
- ✅ Tablas creadas con estructura v2.60
- ✅ Sin conflictos de migraciones históricas
- ✅ Base de datos limpia y lista para desarrollo

## 📝 Notas Técnicas

### Estructura de Tablas v2.60

1. **tenant_cotizaciones_configuracion**
   - Perfiles de configuración (tipo_plantilla, parámetros AIU, etc.)

2. **tenant_cotizaciones_documento** (Cotizacion)
   - Documentos de cotización con DNA dinámico
   - Referencia opcional a Cliente (resiliente)

3. **tenant_cotizaciones_item** (CotizacionItem)
   - Items de cotización con snapshot inmutable
   - Ordenamiento por campo `orden`

4. **tenant_cotizaciones_producto**
   - Catálogo de productos (STS)

5. **tenant_cotizaciones_servicio**
   - Catálogo de servicios

### Cambios en v2.60

- Modelo simplificado y desacoplado
- Referencias resilientes (SET_NULL en lugar de CASCADE)
- Campo `orden` en CotizacionItem para mantener secuencia
- ConfiguracionCotizacion separado en módulo `configuracion/`

---

**Última Actualización**: 2024-12-19  
**Versión**: DNA Dinámico v2.60
