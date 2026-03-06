# 📋 Comandos de Prueba para Tenants - v3.3

**Propósito:** Generar y analizar tenants privados con datos de prueba para análisis de comportamiento

---

## 🚀 Comando: `generar_tenants_prueba`

Genera múltiples tenants privados con datos de prueba.

### Uso Básico

```bash
# Crear 100 tenants sin datos
python manage.py generar_tenants_prueba --cantidad 100

# Crear 100 tenants CON datos de prueba
python manage.py generar_tenants_prueba --cantidad 100 --con-datos

# Crear 50 tenants empezando desde el 50
python manage.py generar_tenants_prueba --cantidad 50 --inicio 50 --con-datos

# Omitir tenants que ya existen
python manage.py generar_tenants_prueba --cantidad 100 --con-datos --skip-existing
```

### Parámetros

- `--cantidad N`: Cantidad de tenants a crear (default: 100)
- `--con-datos`: Poblar cada tenant con datos de prueba
- `--inicio N`: Número inicial para indexación (default: 1)
- `--skip-existing`: Omitir tenants que ya existen

### Datos Generados (con --con-datos)

Por cada tenant se crea:

1. **Empresa (singleton)**
   - Razón social única
   - NIT único
   - Datos fiscales completos

2. **Clientes (5-10)**
   - Personas naturales y jurídicas
   - Datos de contacto completos
   - Distribución aleatoria

3. **Productos (10-20)**
   - Códigos únicos por tenant
   - Precios variados
   - Marcas y referencias

4. **Servicios (5-10)**
   - Códigos únicos por tenant
   - Precios variados

5. **Cotizaciones (3-8)**
   - Asociadas a clientes aleatorios
   - Estados variados (BORRADOR, ENVIADA, ACEPTADA, RECHAZADA)
   - Fechas realistas

6. **Proyectos (2-5)**
   - Asociados a clientes aleatorios
   - Fases variadas (BORRADOR, INICIO, PLANEACION, EJECUCION, CIERRE)
   - Valores de contrato variados

### Ejemplo de Salida

```
🚀 Iniciando generación de 100 tenants...
================================================================================
⚠️  Modo CON DATOS activado - Esto puede tardar varios minutos

[1/100] Procesando: Tecnología Soluciones 001 S.A.S.
  ✅ Tenant creado: tecnologia-soluciones-001-sas
  📊 Datos: 7 clientes, 15 productos, 5 cotizaciones, 3 proyectos

[2/100] Procesando: Construcción Servicios 002 S.A.S.
  ✅ Tenant creado: construccion-servicios-002-sas
  📊 Datos: 8 clientes, 18 productos, 6 cotizaciones, 4 proyectos

...

================================================================================
📊 REPORTE FINAL
================================================================================
✅ Tenants creados: 100
⏭️  Tenants omitidos: 0
❌ Errores: 0
📊 Con datos: 100
📊 Sin datos: 0

📄 Estadísticas guardadas en: /path/to/tenants_prueba_stats.json
```

---

## 🔍 Comando: `analizar_tenants_prueba`

Analiza el comportamiento de tenants creados.

### Uso Básico

```bash
# Análisis completo (JSON + CSV)
python manage.py analizar_tenants_prueba

# Solo JSON
python manage.py analizar_tenants_prueba --formato json

# Solo CSV
python manage.py analizar_tenants_prueba --formato csv

# Solo tenants activos
python manage.py analizar_tenants_prueba --solo-activos

# Filtrar por schema
python manage.py analizar_tenants_prueba --filtro-schema "tecnologia"

# Guardar en directorio específico
python manage.py analizar_tenants_prueba --output-dir /path/to/reports
```

### Parámetros

- `--formato {json,csv,ambos}`: Formato de salida (default: ambos)
- `--output-dir PATH`: Directorio para guardar reportes (default: BASE_DIR)
- `--solo-activos`: Analizar solo tenants activos
- `--filtro-schema TEXT`: Filtrar por schema_name (contiene)

### Estadísticas Generadas

Por cada tenant:
- Schema name y nombre
- Dominio principal
- Estado (activo/inactivo)
- Empresa asociada
- Cantidad de clientes, productos, servicios, cotizaciones, proyectos
- Número de miembros
- Fecha de creación
- Última actividad

Agregadas:
- Total de tenants
- Tenants activos vs inactivos
- Totales de cada tipo de dato
- Total de miembros

### Ejemplo de Salida

```
🔍 Iniciando análisis de tenants...
================================================================================
📊 Analizando 100 tenants...
[1/100] Analizando: tecnologia-soluciones-001-sas
  ✅ Activo: 7 clientes, 5 cotizaciones, 3 proyectos
[2/100] Analizando: construccion-servicios-002-sas
  ✅ Activo: 8 clientes, 6 cotizaciones, 4 proyectos
...

================================================================================
📊 ESTADÍSTICAS AGREGADAS
================================================================================
Total tenants: 100
Tenants activos: 95
Tenants inactivos: 5
Total clientes: 750
Total productos: 1500
Total servicios: 750
Total cotizaciones: 550
Total proyectos: 350
Total miembros: 100

📄 Reporte JSON guardado en: /path/to/analisis_tenants_20241219_143022.json
📄 Reporte CSV guardado en: /path/to/analisis_tenants_20241219_143022.csv
```

---

## 📊 Formato de Reportes

### JSON

```json
{
  "estadisticas_agregadas": {
    "total_tenants": 100,
    "tenants_activos": 95,
    "tenants_inactivos": 5,
    "total_clientes": 750,
    "total_productos": 1500,
    "total_servicios": 750,
    "total_cotizaciones": 550,
    "total_proyectos": 350,
    "total_miembros": 100,
    "fecha_analisis": "2024-12-19T14:30:22Z"
  },
  "resultados": [
    {
      "schema_name": "tecnologia-soluciones-001-sas",
      "nombre": "Tecnología Soluciones 001 S.A.S.",
      "dominio": "tecnologia-soluciones-001-sas.localhost",
      "activo": true,
      "is_active": true,
      "on_trial": true,
      "empresa": "Tecnología Soluciones 001 S.A.S.",
      "clientes": 7,
      "productos": 15,
      "servicios": 8,
      "cotizaciones": 5,
      "proyectos": 3,
      "miembros": 1,
      "fecha_creacion": "2024-12-19T10:00:00Z",
      "ultima_actividad": "2024-12-19T14:00:00Z"
    },
    ...
  ],
  "errores": []
}
```

### CSV

Columnas:
- `schema_name`, `nombre`, `dominio`, `activo`, `is_active`, `on_trial`
- `empresa`, `clientes`, `productos`, `servicios`, `cotizaciones`, `proyectos`
- `miembros`, `fecha_creacion`, `ultima_actividad`, `paid_until`

---

## ⚠️ Notas Importantes

1. **Rendimiento:** Crear 100 tenants con datos puede tardar 10-30 minutos dependiendo del hardware
2. **Base de Datos:** Asegúrate de tener suficiente espacio en PostgreSQL
3. **Memoria:** El proceso puede consumir memoria significativa
4. **Transacciones:** Cada tenant se crea en una transacción atómica
5. **Errores:** Los errores se registran pero no detienen el proceso completo

---

## 🔧 Troubleshooting

### Error: "Usuario admin base no encontrado"
**Solución:** El comando crea automáticamente el usuario `admin.base@test.local` si no existe.

### Error: "Schema ya existe"
**Solución:** Usa `--skip-existing` para omitir tenants existentes.

### Error: "No se pudo crear dominio"
**Solución:** Verifica que `TENANT_DOMAIN_BASE` esté configurado en settings.

### Error: "Error poblando datos"
**Solución:** Verifica que las migraciones de tenant apps estén aplicadas.

---

## 📈 Casos de Uso

### 1. Análisis de Rendimiento
```bash
# Crear 100 tenants con datos
python manage.py generar_tenants_prueba --cantidad 100 --con-datos

# Analizar comportamiento
python manage.py analizar_tenants_prueba --solo-activos
```

### 2. Pruebas de Carga
```bash
# Crear tenants incrementales
python manage.py generar_tenants_prueba --cantidad 50 --inicio 1 --con-datos
python manage.py generar_tenants_prueba --cantidad 50 --inicio 51 --con-datos
```

### 3. Análisis de Uso
```bash
# Analizar y exportar a CSV para análisis externo
python manage.py analizar_tenants_prueba --formato csv --output-dir ./reports
```

---

**Última actualización:** 2024-12-19  
**Versión:** 3.3
