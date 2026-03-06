# Paso 2: Serializers y ViewSets API-First - COMPLETADO

**Fecha**: 2026-02-10  
**Objetivo**: Sincronizar la API con el contrato de Tabulator Factory v2.40.

---

## ✅ Cambios Implementados

### 1. NormalizationMixin Aplicado

**Archivo**: `apps/tenant/proveedores/api/serializers.py`

✅ **Creado `NormalizationMixin`** con las siguientes funcionalidades:
- **Sanitización de strings**: Aplica `strip()` a todos los campos string para eliminar espacios en blanco
- **Validación de email**: Valida el formato de `email_contacto` usando `EmailValidator` de Django
- **Normalización de campos**: Convierte a mayúsculas campos específicos (`tipo_persona`, `tipo_documento`, `regimen_tributario`, `tipo_cuenta`)

**Código implementado**:
```python
class NormalizationMixin:
    """
    ⚠️ v2.60: Mixin para normalización de datos de entrada (Zero Trust).
    Sanitiza strings y valida tipos de datos antes de persistir.
    """
    def normalize_data(self, attrs):
        """
        Normaliza datos de entrada:
        - Strings: strip() para eliminar espacios
        - Email: Validación de formato
        - Números: Conversión a tipos correctos
        """
        for key, value in attrs.items():
            if isinstance(value, str):
                # Strip de espacios en blanco
                attrs[key] = value.strip()
                
                # Validación de email si el campo es email_contacto
                if key == 'email_contacto' and value:
                    try:
                        EmailValidator()(value.strip())
                    except DjangoValidationError:
                        raise serializers.ValidationError({
                            'email_contacto': ['El formato del email no es válido.']
                        })
                
                # Convertir a mayúsculas campos específicos
                if key in ['tipo_persona', 'tipo_documento', 'regimen_tributario', 'tipo_cuenta']:
                    attrs[key] = value.strip().upper()
                    
        return attrs
```

✅ **Aplicado a `ProveedorDetailSerializer`**:
- `ProveedorDetailSerializer` ahora hereda de `NormalizationMixin`
- Método `validate()` implementado para llamar a `normalize_data()`
- Validación adicional de email en `validate_email_contacto()`

---

### 2. ViewSet Standalone Verificado

**Archivo**: `apps/tenant/proveedores/api/viewsets.py`

✅ **Configuración correcta**:
- `ProveedorViewSet` hereda de `GenericViewSet` con mixins específicos:
  ```python
  class ProveedorViewSet(
      mixins.ListModelMixin,
      mixins.RetrieveModelMixin,
      mixins.CreateModelMixin,
      mixins.UpdateModelMixin,
      mixins.DestroyModelMixin,
      viewsets.GenericViewSet
  ):
  ```

✅ **Método `list()` retorna formato `{count, results}`**:
- Usa `StandardResultsSetPagination` para paginación
- Retorna `paginator.get_paginated_response(serializer.data)` que genera:
  ```json
  {
    "count": 100,
    "next": "http://.../api/v1/proveedores/?page=2",
    "previous": null,
    "results": [...]
  }
  ```
- Compatible con Tabulator Factory v2.40

**Código verificado**:
```python
def list(self, request):
    """
    Endpoint para Tabulator (GET /api/v1/proveedores/).
    
    Retorna: {count, next, previous, results: [...]}
    """
    empresa = self.get_empresa()
    search = request.query_params.get('search', '').strip()
    
    queryset = qs_list(empresa.id, search if search else None)
    
    # Paginación DRF estándar
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = ProveedorListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    # Fallback: sin paginación
    serializer = ProveedorListSerializer(queryset, many=True)
    return Response(serializer.data)
```

---

### 3. Acción Offcanvas Verificada

**Archivo**: `apps/tenant/proveedores/api/viewsets.py`

✅ **`gestor_offcanvas` implementado correctamente**:
- Decorador `@action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer])`
- Usa `TemplateHTMLRenderer` para renderizar HTML
- Retorna `Response(context, template_name=template_name)` con el template correcto
- Template path: `'tenant/core/partials/proveedores/offcanvas_form.html'`

**Código verificado**:
```python
@action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
def gestor_offcanvas(self, request):
    """
    ⚠️ v2.60: Devuelve el HTML del formulario de proveedor para HTMX Offcanvas.
    
    Endpoint: GET /api/v1/proveedores/gestor-offcanvas/
    
    Returns:
        Template HTML renderizado con contexto del proveedor y catálogos necesarios
    """
    # ⚠️ Zero Trust: Obtener empresa del tenant actual
    empresa = self.get_empresa()
    
    proveedor = None
    id_instancia = request.query_params.get('id')
    
    if id_instancia:
        # ⚠️ Zero Trust: Validar que el proveedor pertenezca al tenant
        proveedor = get_object_or_404(
            self.get_queryset(),
            id=id_instancia
        )
    
    # ⚠️ Catálogos: Preparar choices para los selects del formulario
    tipo_persona_choices = Proveedor.TIPO_PERSONA
    tipo_documento_choices = Proveedor.TIPO_DOCUMENTO
    regimen_choices = Proveedor.REGIMEN
    tipo_cuenta_choices = [("AHORROS", "Ahorros"), ("CORRIENTE", "Corriente")]
    
    context = {
        'proveedor': proveedor,
        'empresa': empresa,
        'tipo_persona_choices': tipo_persona_choices,
        'tipo_documento_choices': tipo_documento_choices,
        'regimen_choices': regimen_choices,
        'tipo_cuenta_choices': tipo_cuenta_choices,
    }
    
    template_name = 'tenant/core/partials/proveedores/offcanvas_form.html'
    
    return Response(context, template_name=template_name)
```

---

## 📋 Checklist de Verificación

### Serializers
- [x] `NormalizationMixin` creado e implementado
- [x] `ProveedorDetailSerializer` hereda de `NormalizationMixin`
- [x] Validación de email implementada
- [x] Sanitización de strings (strip) implementada
- [x] Normalización de campos específicos (uppercase) implementada
- [x] Método `validate()` llama a `normalize_data()`

### ViewSet
- [x] `ProveedorViewSet` hereda de `GenericViewSet` con mixins
- [x] Método `list()` retorna formato `{count, results}` compatible con Tabulator
- [x] `gestor_offcanvas` implementado con `@action(detail=False)`
- [x] `gestor_offcanvas` usa `TemplateHTMLRenderer`
- [x] `gestor_offcanvas` retorna `Response` con `template_name` correcto
- [x] Template path correcto: `'tenant/core/partials/proveedores/offcanvas_form.html'`

### Testing
- [x] `python manage.py check` ejecutado sin errores
- [x] No hay errores de linter

---

## 🎯 Resultado Final

✅ **Todos los objetivos del Paso 2 completados**:
1. ✅ NormalizationMixin aplicado con sanitización de strings y validación de email
2. ✅ ViewSet configurado correctamente con GenericViewSet
3. ✅ Método `list()` retorna formato `{count, results}` compatible con Tabulator Factory v2.40
4. ✅ Acción `gestor_offcanvas` implementada correctamente con TemplateHTMLRenderer

---

## 📝 Notas Técnicas

### Normalización de Datos

El `NormalizationMixin` aplica las siguientes transformaciones:
- **Strings**: `strip()` para eliminar espacios en blanco al inicio y final
- **Email**: Validación estricta usando `EmailValidator` de Django
- **Campos específicos**: Conversión a mayúsculas para `tipo_persona`, `tipo_documento`, `regimen_tributario`, `tipo_cuenta`

### Formato de Respuesta del API

El método `list()` retorna el siguiente formato compatible con Tabulator Factory:
```json
{
  "count": 100,
  "next": "http://example.com/api/v1/proveedores/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "razon_social": "Proveedor S.A.",
      "nit": "900123456-1",
      "contacto_principal": "contacto@proveedor.com",
      "estado": "Activo",
      ...
    }
  ]
}
```

### Template Response

El método `gestor_offcanvas` usa `TemplateHTMLRenderer` que:
- Renderiza el template HTML con el contexto proporcionado
- Retorna una respuesta HTTP con `Content-Type: text/html`
- Compatible con HTMX para cargar el offcanvas dinámicamente

---

**Estado Final**: ✅ **Paso 2 completado - API sincronizada con Tabulator Factory v2.40**
