# Checklist de Wiring - Normativa DIAN (v2.30+)

## ✅ Verificaciones de Implementación

### 1. Modelos
- [x] `ContribuyenteTipo` creado en `apps/public/impuestos/models.py`
- [x] `RegimenRenta` creado en `apps/public/impuestos/models.py`
- [x] `ResponsabilidadRUT` creado en `apps/public/impuestos/models.py`
- [x] `PerfilTributario` creado en `apps/public/impuestos/models.py`
- [x] Migraciones creadas: `0002_add_normativa_dian_catalogos.py`

### 2. Serializers
- [x] `ContribuyenteTipoSerializer` en `apps/public/impuestos/api/serializers.py`
- [x] `RegimenRentaSerializer` en `apps/public/impuestos/api/serializers.py`
- [x] `ResponsabilidadRUTSerializer` en `apps/public/impuestos/api/serializers.py`
- [x] `PerfilTributarioSerializer` en `apps/public/impuestos/api/serializers.py` (con relaciones)

### 3. ViewSets
- [x] `ContribuyenteTipoViewSet` en `apps/public/impuestos/api/viewsets.py` (BaseReadWrite)
- [x] `RegimenRentaViewSet` en `apps/public/impuestos/api/viewsets.py` (BaseReadWrite)
- [x] `ResponsabilidadRUTViewSet` en `apps/public/impuestos/api/viewsets.py` (BaseReadWrite)
- [x] `PerfilTributarioViewSet` en `apps/public/impuestos/api/viewsets.py` (BaseReadWrite)
- [x] Permisos: GET AllowAny, POST/PUT/PATCH/DELETE IsAdminUser

### 4. URLs
- [x] ViewSets registrados en `VIEWSETS` de `apps/public/impuestos/api/viewsets.py`
- [x] Router automático en `apps/public/impuestos/api/urls.py`
- [x] Endpoints disponibles bajo `/api/public/v1/impuestos/...`

### 5. Admin
- [x] `ContribuyenteTipoAdmin` registrado
- [x] `RegimenRentaAdmin` registrado
- [x] `ResponsabilidadRUTAdmin` registrado
- [x] `PerfilTributarioAdmin` registrado (con filter_horizontal para responsabilidades)

### 6. Configuración DRF
- [x] `DEFAULT_RENDERER_CLASSES` = `['rest_framework.renderers.JSONRenderer']` (JSON-only)
- [x] Sin `BrowsableAPIRenderer` (API-First)

### 7. Pruebas
- [x] `tests/public/impuestos/test_normativa_dian_api.py` creado
- [x] Pruebas de lectura pública (GET AllowAny)
- [x] Pruebas de escritura restringida (POST requiere staff)
- [x] Pruebas de JSON-only (sin HTML)

## 🔍 Verificación de Endpoints

### Endpoints Públicos (GET AllowAny)
- `GET /api/public/v1/impuestos/contribuyentes-tipos/`
- `GET /api/public/v1/impuestos/contribuyentes-tipos/{id}/`
- `GET /api/public/v1/impuestos/regimenes-renta/`
- `GET /api/public/v1/impuestos/regimenes-renta/{id}/`
- `GET /api/public/v1/impuestos/responsabilidades-rut/`
- `GET /api/public/v1/impuestos/responsabilidades-rut/{id}/`
- `GET /api/public/v1/impuestos/perfiles-tributarios/`
- `GET /api/public/v1/impuestos/perfiles-tributarios/{id}/`

### Endpoints Restringidos (POST/PUT/PATCH/DELETE IsAdminUser)
- `POST /api/public/v1/impuestos/contribuyentes-tipos/` (requiere staff)
- `PUT /api/public/v1/impuestos/contribuyentes-tipos/{id}/` (requiere staff)
- `PATCH /api/public/v1/impuestos/contribuyentes-tipos/{id}/` (requiere staff)
- `DELETE /api/public/v1/impuestos/contribuyentes-tipos/{id}/` (requiere staff)
- (Mismo patrón para los otros modelos)

## 🧪 Comandos de Verificación

```bash
# 1. Verificar migraciones
python manage.py makemigrations impuestos --dry-run

# 2. Aplicar migraciones (esquema public)
python manage.py migrate_schemas --shared

# 3. Ejecutar pruebas de humo
pytest tests/public/impuestos/test_normativa_dian_api.py -v

# 4. Verificar endpoints (requiere servidor corriendo)
curl http://sintel.com/api/public/v1/impuestos/contribuyentes-tipos/
curl http://sintel.com/api/public/v1/impuestos/regimenes-renta/
curl http://sintel.com/api/public/v1/impuestos/responsabilidades-rut/
curl http://sintel.com/api/public/v1/impuestos/perfiles-tributarios/

# 5. Verificar admin (requiere login staff)
# http://sintel.com/admin/impuestos/contribuyentetipo/
# http://sintel.com/admin/impuestos/regimenrenta/
# http://sintel.com/admin/impuestos/responsabilidadrut/
# http://sintel.com/admin/impuestos/perfiltributario/
```

## 📝 Notas de Implementación

- **Política SSoT**: `apps/public/impuestos` es la única fuente de verdad para normativa DIAN
- **Permisos**: GET abierto, escritura solo staff/admin
- **JSON-only**: Todas las APIs retornan solo JSON (sin HTML)
- **Multi-tenant**: Los catálogos están en el esquema `public` y son compartidos por todos los tenants
- **Base Legal**: Los modelos incluyen campo `base_legal` para documentar la normativa de origen
