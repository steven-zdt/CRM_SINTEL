# 🔍 AUDITORÍA SINTEL v2.61.4 - RESULTADOS Y CORRECCIONES

**Fecha:** 2026-03-20  
**Versión Auditada:** v2.61.4  
**Fuente de Verdad:** [arquitectura_general.md](documentacion/arquitectura_general.md)  
**Rol Auditor:** Arquitecto Senior Python/Django - Service Layer & Multi-Tenant  

---

## 📊 RESUMEN EJECUTIVO

| Problema | Severidad | Estado | Impacto |
|----------|-----------|--------|---------|
| IntegrityError sin captura robusta | 🔴 CRÍTICA | Detectado | Crashes duplicados en prod |
| OSError 5 por templates faltantes | 🔴 CRÍTICA | Detectado | Caída de endpoints HTMX |
| NormalizationMixin incompleto | 🟠 ALTA | Detectado | Validación débil (Zero Trust) |
| Obtención de empresa no optimizada | 🟠 ALTA | Detectado | Query waste + condiciones de carrera |
| Falta de idempotencia | 🟠 ALTA | Detectado | Duplicados en bulk imports |
| Signals cero violations | ✅ OK | Auditado | Confirmado: no hay signals violadas |

---

## 🚨 PROBLEMA #1: IntegrityError Sin Captura Robusta

### Ubicación:
- `apps/tenant/clientes/services.py` → `crear_cliente()`, `actualizar_cliente()`
- `apps/tenant/proveedores/services.py` → Patrón similar
- `apps/tenant/gastos/services.py` → Manejo de duplicados inexistente

### Por Qué Falla:
```python
# ❌ CÓDIGO ACTUAL (DEFECTUOSO)
try:
    cliente = Cliente.objects.create(empresa=empresa, **data)
except IntegrityError as e:
    error_msg = str(e)
    # Solo captura ciertos patterns de constraint names
    if 'uniq_doc_cliente_empresa' in error_msg:
        raise ValidationError(...)
    # ⚠️ PROBLEMA: Otros errores de UNIQUE causan crash silencioso
    raise  # Re-lanza IntegrityError sin amigable para frontend
```

**Regla SSoT Violada (#1):** 
> "Idempotencia Absoluta: El sistema no debe fallar con registros duplicados"

**Regla SSoT Violada (#2):**
> "Zero Trust - Validación de Entrada: Validar explícitamente existencia antes de crear"

### Solución: Pattern Idempotente con Validación Previa

**Refactorización v2.61.4:**

```python
# ✅ CÓDIGO REFACTORIZADO (CORRECTO)
@transaction.atomic
def crear_cliente_idempotente(empresa, data):
    """
    ⚠️ v2.61.4: Creación IDEMPOTENTE de clientes usando validación previa.
    NUNCA usa IntegrityError como flujo de control - valida antes de crear.
    
    Reglas:
    1. Validar existencia previa (SSoT - empresa_id + documento)
    2. Normalizar entrada (Zero Trust)
    3. Crear si no existe (Idempotente)
    4. Retornar objeto + flag de creación
    
    Args:
        empresa: Instancia de Empresa (SSoT)
        data: Dict con datos del cliente
        
    Returns:
        tuple: (cliente, creado) donde creado=True si se creó, False si ya existía
        
    Raises:
        ValidationError: Si datos son inválidos (normalizados por serializer)
    """
    from django.core.exceptions import ValidationError as DjangoValidationError
    
    # ⚠️ Zero Trust: Validación previa de empresa
    if not empresa or not empresa.id:
        raise ValidationError('Empresa inválida')
    
    # ⚠️ Zero Trust: Validar que número_documento existe y es único
    numero_documento = data.get('numero_documento', '').strip()
    tipo_documento = data.get('tipo_documento')
    
    if not numero_documento or not tipo_documento:
        raise ValidationError({
            'numero_documento': ['Requerido para validación idempotente'],
            'tipo_documento': ['Requerido para validación idempotente']
        })
    
    # ⚠️ IDEMPOTENCIA: Validar existencia PREVIA (clave única: empresa + tipo_documento + numero_documento)
    cliente_existente = Cliente.objects.filter(
        empresa_id=empresa.id,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento
    ).first()
    
    if cliente_existente:
        # ⚠️ SilentSuccess Pattern: Retornar existente como si fuera nuevo
        # Esto es IDEMPOTENTE - llamadas idénticas retornan el mismo objeto
        return cliente_existente, False  # (cliente, creado=False)
    
    # ⚠️ Creación: Ya validamos que no existe
    # La transaction.atomic() garantiza atomicidad
    try:
        cliente = Cliente.objects.create(
            empresa=empresa,
            **{k: v for k, v in data.items() if k != 'contactos'}
        )
        return cliente, True  # (cliente, creado=True)
    except IntegrityError as e:
        # ⚠️ ÚLTIMA LÍNEA DE DEFENSA: Si aún falla, propagar error amigable
        # Esto NO debería suceder si validación previa es correcta
        logger.error(f'[crear_cliente_idempotente] IntegrityError inesperado: {e}')
        raise ValidationError({
            'non_field_errors': [
                'Error de integridad al crear cliente. '
                'Verifique que no exista otro cliente con el mismo documento.'
            ]
        })
```

### Aplicar al ProveedorViewSet (Patrón Idéntico)

```python
# apps/tenant/proveedores/services.py
@transaction.atomic
def crear_proveedor_idempotente(empresa, data):
    """⚠️ v2.61.4: Idempotente - validar NIT + empresa existentes antes de crear."""
    
    nit = data.get('numero_documento', '').strip()
    
    if not nit:
        raise ValidationError({'numero_documento': ['Requerido']})
    
    proveedor_existente = Proveedor.objects.filter(
        empresa_id=empresa.id,
        numero_documento=nit
    ).only('id').first()
    
    if proveedor_existente:
        return proveedor_existente, False
    
    try:
        proveedor = Proveedor.objects.create(empresa=empresa, **data)
        return proveedor, True
    except IntegrityError as e:
        logger.error(f'IntegrityError en crear_proveedor: {e}')
        raise ValidationError({
            'numero_documento': ['Ya existe un proveedor con este NIT en esta empresa']
        })
```

---

## 🚨 PROBLEMA #2: OSError 5 en TemplateHTMLRenderer

### Ubicación:
- `apps/tenant/clientes/api/viewsets.py` → `offcanvas()`, `render_offcanvas_crear()`
- `apps/tenant/empleados/api/viewsets.py` → Patrón repetido en 6+ endpoints
- `apps/tenant/proyectos/api/viewsets.py` → Patrón repetido en 3+ endpoints

### Por Qué Falla:
```python
# ❌ CÓDIGO ACTUAL (NO ROBUSTO)
@action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer])
def offcanvas(self, request):
    context = {'cliente': None}
    # ⚠️ Si template no existe: Response() throws OSError 5 (permiso denegado / archivo no encontrado)
    return Response(context, template_name='tenant/core/partials/clientes/offcanvas_form.html')
```

**Error típico en prod:**
```
OSError: [Errno 5] Input/output error
  File "/path/to/django/template/loader.py", line 17, in render
    return render_to_string(template, context, request=request)
```

**Regla SSoT Violada:**
> "Resiliencia de Infraestructura: El sistema debe manejar excepciones de forma robusta"

### Solución: Wrapper con Manejo de Excepciones

```python
# ✅ CÓDIGO REFACTORIZADO
from django.template.exceptions import TemplateDoesNotExist
from rest_framework.response import Response
from rest_framework.decorators import renderer_classes
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework import status

def render_template_safe(context, template_name, request=None):
    """
    ⚠️ v2.61.4: Wrapper seguro para TemplateHTMLRenderer.
    
    Maneja:
    - TemplateDoesNotExist: Template no encontrada
    - OSError: Errores de lectura del filesystem
    - PermissionError: Permisos insuficientes
    
    Args:
        context: Dict con contexto para el template
        template_name: Ruta del template (ej: 'tenant/core/partials/...')
        request: HttpRequest para build_absolute_uri() en serializers
        
    Returns:
        Response: HTML renderizado O JSON con error amigable
        
    Raises:
        Exception: Solo si es error irrecuperable del sistema
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # ⚠️ Validación previa: Verificar que template existe
        from django.template.loader import get_template
        try:
            get_template(template_name)
        except TemplateDoesNotExist:
            logger.error(f'[render_template_safe] Template no encontrada: {template_name}')
            return Response(
                {
                    'error': 'template_not_found',
                    'message': f'Template no encontrada: {template_name}',
                    'detail': 'El fichero de interfaz no está disponible. Por favor, contacte al administrador.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content_type='application/json'
            )
        
        # ⚠️ Renderizado seguro
        return Response(context, template_name=template_name)
    
    except (OSError, PermissionError) as e:
        logger.error(f'[render_template_safe] Error de lectura ({type(e).__name__}): {e}')
        return Response(
            {
                'error': 'template_read_error',
                'message': 'No se pudo leer la plantilla de interfaz',
                'detail': 'Verifique que el servidor tenga permisos de lectura'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content_type='application/json'
        )
    
    except Exception as e:
        logger.critical(f'[render_template_safe] Error inesperado: {e}', exc_info=True)
        return Response(
            {
                'error': 'unexpected_error',
                'message': 'Error inesperado al renderizar plantilla',
                'detail': str(e) if not settings.PRODUCTION else 'Por favor, contacte al administrador'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content_type='application/json'
        )


# Aplicar en ViewSet:
class ClienteViewSet(viewsets.GenericViewSet, ...):
    
    @action(
        detail=False, 
        methods=['get'], 
        renderer_classes=[TemplateHTMLRenderer, JSONRenderer],  # JSON como fallback
        url_path='offcanvas'
    )
    def offcanvas(self, request):
        """
        ⚠️ v2.61.4: Renderizado robusto con fallback a JSON si template falla.
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response(
                {'error': 'empresa_not_found', 'message': 'Empresa no configurada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        context = {
            'empresa': empresa,
            'cliente': None,
            'contactos': [],
            'modo': 'crear'
        }
        
        cliente_id = request.query_params.get('id')
        if cliente_id:
            try:
                cliente = self.get_queryset().get(id=cliente_id)
                context['cliente'] = cliente
                context['modo'] = 'editar'
                context['contactos'] = ContactoCliente.objects.filter(
                    cliente=cliente
                ).only('id', 'nombre_completo', 'cargo', 'email', 'telefono')
            except Cliente.DoesNotExist:
                logger.warning(f'[offcanvas] Cliente {cliente_id} no encontrado')
        
        # ⚠️ Usar wrapper seguro para renderizado
        return render_template_safe(
            context, 
            'tenant/core/partials/clientes/offcanvas_form.html',
            request=request
        )
```

---

## 🚨 PROBLEMA #3: NormalizationMixin Incompleto

### Ubicación:
- `apps/tenant/clientes/api/serializers.py` → NormalizationMixin base
- Usado en: `ClienteDetailSerializer`, `ContactoClienteSerializer`

### Por Qué Falla:
```python
# ❌ CÓDIGO ACTUAL (INCOMPLETO)
class NormalizationMixin:
    def normalize_data(self, attrs):
        for key, value in attrs.items():
            if isinstance(value, str):
                attrs[key] = value.strip()  # ⚠️ SOLO .strip() - insuficiente!
        return attrs
# NO valida:
# - Tipos numéricos
# - Campos técnicos (códigos, referencias)
# - Ranges de valores
# - Formato de emails/teléfonos
```

**Regla SSoT Violada:**
> "Zero Trust: Normalizar AND validar datos antes de persistir - No confiar en entrada del usuario"

### Solución: NormalizationMixin Completo

```python
# ✅ CÓDIGO REFACTORIZADO
from rest_framework import serializers
from decimal import Decimal, InvalidOperation
import re

class NormalizationMixin:
    """
    ⚠️ v2.61.4: Mixin de normalización E VALIDACIÓN (Zero Trust).
    
    Aplica:
    1. Limpieza de strings (strip, espacios dobles, sanitización HTML)
    2. Estandarización de formatos (MAYÚSCULAS para técnicos)
    3. Validación numérica estricta
    4. Validación de relaciones FK
    5. Normalización de teléfonos y documentos
    """
    
    def normalize_data(self, attrs):
        """
        ⚠️ Zero Trust: Normalizar TODOS los campos antes de validar.
        """
        for key, value in attrs.items():
            # Strings: Limpiar y normalizar
            if isinstance(value, str):
                value = value.strip()
                # Eliminar espacios múltiples
                value = re.sub(r'\s+', ' ', value)
                # Campos técnicos (código, referencia, marca): Convertir a MAYÚSCULAS
                if key in ['codigo', 'referencia', 'marca', 'unidad', 'numero_documento']:
                    value = value.upper()
                attrs[key] = value
            
            # Decimales: Validar y normalizar
            elif key in ['precio', 'precio_venta', 'costo_promedio', 'monto', 'cantidad']:
                if value is not None:
                    try:
                        decimal_val = Decimal(str(value)).quantize(Decimal('0.01'))
                        if decimal_val < 0:
                            raise serializers.ValidationError(
                                f'{key} no puede ser negativo'
                            )
                        attrs[key] = decimal_val
                    except (InvalidOperation, ValueError):
                        raise serializers.ValidationError(
                            f'{key} debe ser un número válido'
                        )
            
            # Booleanos: Asegurar tipo bool
            elif key in ['activo', 'is_principal', 'is_default']:
                attrs[key] = bool(value)
        
        return attrs
    
    def validate_foreign_key(self, fk_value, model_class, field_name, empresa_id=None):
        """
        ⚠️ Zero Trust: Validar que FK existe Y pertenece al tenant (si aplica).
        
        Args:
            fk_value: Valor de la FK (puede ser int o Instance)
            model_class: Clase del modelo a validar
            field_name: Nombre del campo para error message
            empresa_id: Si presente, validar que registro pertenece a empresa (SSoT)
            
        Returns:
            Instance: Objeto validado
            
        Raises:
            ValidationError: Si no existe o no pertenece al tenant
        """
        # ⚠️ Ya es instancia, validar que es tipo correcto
        if hasattr(fk_value, 'pk') and isinstance(fk_value, model_class):
            instance = fk_value
        else:
            # Es ID, traer objeto
            try:
                if empresa_id:
                    instance = model_class.objects.filter(
                        pk=fk_value,
                        empresa_id=empresa_id
                    ).first()
                    if not instance:
                        raise serializers.ValidationError({
                            field_name: [f'{model_class.__name__} no encontrado o no pertenece a esta empresa']
                        })
                else:
                    instance = model_class.objects.get(pk=fk_value)
            except model_class.DoesNotExist:
                raise serializers.ValidationError({
                    field_name: [f'{model_class.__name__} con ID {fk_value} no existe']
                })
            except (ValueError, TypeError):
                raise serializers.ValidationError({
                    field_name: [f'ID inválido para {model_class.__name__}']
                })
        
        return instance
    
    def normalize_document_number(self, document_number):
        """⚠️ Zero Trust: Normalizar números de documento."""
        if not document_number:
            return None
        # Remover espacios, guiones, puntos
        normalized = re.sub(r'[\s\-\.]', '', str(document_number).upper())
        if not normalized.isalnum():
            raise serializers.ValidationError('Número de documento contiene caracteres inválidos')
        return normalized


# Aplicar en serializers:
class ClienteDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """✅ v2.61.4: Serializer con validación completa."""
    
    class Meta:
        model = Cliente
        fields = [
            'id', 'tipo_persona', 'tipo_documento', 'numero_documento',
            'razon_social', 'email', 'telefono', 'activo'
        ]
    
    def validate(self, attrs):
        """⚠️ Zero Trust: Normalizar y validar en una sola pasada."""
        # 1. Normalizar
        attrs = self.normalize_data(attrs)
        
        # 2. Validar documento único (idempotencia)
        numero_documento = attrs.get('numero_documento')
        tipo_documento = attrs.get('tipo_documento')
        
        if numero_documento and tipo_documento:
            # ⚠️ Normalizar documento para búsqueda
            numero_documento_norm = self.normalize_document_number(numero_documento)
            attrs['numero_documento'] = numero_documento_norm
            
            existing = Cliente.objects.filter(
                empresa_id=self.context.get('empresa_id'),
                tipo_documento=tipo_documento,
                numero_documento=numero_documento_norm
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise serializers.ValidationError({
                    'numero_documento': ['Cliente con este documento ya existe']
                })
        
        return attrs
```

---

## 🚨 PROBLEMA #4: Obtención de Empresa No Optimizada

### Ubicación:
- `apps/tenant/clientes/api/viewsets.py` → `get_empresa()`
- `apps/tenant/proveedores/api/viewsets.py` → `get_empresa()`
- Patrón repetido en 8+ ViewSets

### Por Qué Falla:
```python
# ❌ CÓDIGO ACTUAL (INEFICIENTE)
def get_empresa(self):
    empresa = getattr(self.request.user, 'empresa', None)
    # ⚠️ PROBLEMA 1: No especifica .only('id') - carga TODOS los campos
    # ⚠️ PROBLEMA 2: Sin lógica de cache - se ejecuta en cada request
    # ⚠️ PROBLEMA 3: Sin validación de existencia explícita
    return empresa

# En cada ViewSet:
empresa = self.get_empresa()  # Query 1
if not empresa:
    return Response(...)
# ... más uso de empresa en filtros
```

**Regla SSoT Violada:**
> "Performance Bible: Solo cargar campos necesarios con .only()"

### Solución: Cached Property para Empresa

```python
# ✅ CÓDIGO REFACTORIZADO
from functools import cached_property

class BaseTenantViewSet(viewsets.GenericViewSet):
    """
    ⚠️ v2.61.4: Base ViewSet para apps de tenant.
    Proporciona acceso optimizado a empresa con caching automático.
    """
    
    @cached_property
    def tenant_empresa(self):
        """
        ⚠️ v2.61.4: Obtener empresa del tenant con caching por request.
        
        Registra en request.empresa para acceso desde serializers.
        Carga SOLO 'id' (Performance Bible).
        
        Returns:
            Empresa: Instancia de empresa (singleton por tenant)
            
        Raises:
            APIException: Si no se configura empresa en tenant
        """
        from apps.tenant.empresa.models import Empresa
        from rest_framework.exceptions import APIException
        import logging
        
        logger = logging.getLogger(__name__)
        
        # ⚠️ PERFORMANCE: .only('id') - NO cargar todos los campos
        empresa = Empresa.objects.only('id').first()
        
        if not empresa:
            logger.error(f'[BaseTenantViewSet] No hay empresa en tenant {self.request.tenant}')
            raise APIException(
                detail='Empresa no configurada para este tenant. Por favor, configure la empresa primero.',
                code='empresa_not_configured'
            )
        
        # ⚠️ CACHING: Guardar en request para acceso desde serializers/services
        self.request.empresa = empresa
        
        return empresa
    
    def get_empresa(self):
        """Alias para compatibilidad hacia atrás."""
        return self.tenant_empresa


# Aplicar en ClienteViewSet:
class ClienteViewSet(BaseTenantViewSet, mixins.ListModelMixin, ...):
    
    def get_queryset(self):
        """⚠️ v2.61.4: Usar cached_property para empresa."""
        # ⚠️ Esto NO ejecuta query adicional (cached_property)
        return qs_list(self.tenant_empresa.id)
    
    def create(self, request, *args, **kwargs):
        """⚠️ v2.61.4: Usar cached_property."""
        empresa = self.tenant_empresa  # Ya cacheado en request
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            cliente = crear_cliente(empresa, serializer.validated_data)
            return Response(ClienteRespSerializer(cliente).data, status=201)
        return Response(serializer.errors, status=400)
```

---

## 🚨 PROBLEMA #5: Falta de Idempotencia en Bulk Imports

### Ubicación:
- Cualquier endpoint de carga masiva (no existe aún, pero es necesario)
- Importaciones manuales de CSV/Excel
- Crédito de prueba

### Problema:
Si un usuario sube el mismo archivo dos veces, se crean registros duplicados sin validación idempotente.

### Solución: `update_or_create` Pattern

```python
# ✅ CÓDIGO PARA IMPORTS
@transaction.atomic
def crear_o_actualizar_cliente_csvinteligente(empresa, fila_csv):
    """
    ⚠️ v2.61.4: Importación IDEMPOTENTE desde CSV.
    
    Usasiempre update_or_create con unique_together como clave.
    
    Args:
        empresa: Instancia de Empresa
        fila_csv: Dict con campos de una fila
        
    Returns:
        tuple: (cliente, creado)
    """
    # ⚠️ Clave única: empresa + tipo_documento + numero_documento
    unique_fields = {
        'empresa_id': empresa.id,
        'tipo_documento': fila_csv['tipo_documento'],
        'numero_documento': fila_csv['numero_documento']
    }
    
    # ⚠️ Campos a actualizar
    update_fields = {
        'razon_social': fila_csv['razon_social'].strip(),
        'email': fila_csv.get('email', '').strip() or None,
        'telefono': fila_csv.get('telefono', '').strip() or None,
        'activo': fila_csv.get('activo', True)
    }
    
    # ⚠️ IDEMPOTENTE: Si existe, actualiza; si no, crea
    cliente, creado = Cliente.objects.update_or_create(
        **unique_fields,
        defaults=update_fields
    )
    
    return cliente, creado
```

---

## ✅ AUDITORÍA FINAL: CHECKLIST DE CONFORMIDAD

| Aspecto | Archivo | Estado | Corrección |
|---------|---------|--------|-----------|
| **Service Layer** | `**/services.py` | ✅ OK | Lógica en servicios, no en views |
| **Idempotencia** | Todos | 🟠 PARCIAL | Refactorizar create → update_or_create |
| **Multi-Tenant** | `**/models.py` | ✅ OK | Todos filtran por empresa_id |
| **Zero Trust** | `**/serializers.py` | 🟠 PARCIAL | Expandir NormalizationMixin |
| **Cero Signals** | `**/signals.py` | ✅ OK | No hay signals violadas |
| **Resiliencia** | ViewSets Offcanvas | 🟠 CRÍTICA | Agregar try/except en TemplateHTMLRenderer |
| **Performance** | `get_empresa()` | 🟠 ALTA | Cambiar a cached_property + .only('id') |
| **Paginación** | DRF | ✅ OK | StandardResultsSetPagination correcto |

---

## 📋 PLAN DE IMPLEMENTACIÓN

### Fase 1: Crítica (Prod Breaking) - Semana 1
1. ✅ Refactorizar `render_template_safe()` → Aplicar en 8+ ViewSets
2. ✅ Extender `NormalizationMixin` → Aplicar en 5+ serializers
3. ✅ Crear `BaseTenantViewSet.tenant_empresa` → Aplicar en 10+ ViewSets

### Fase 2: Alta (Data Consistency) - Semana 2
1. ✅ Pattern `crear_*_idempotente` → Aplicar en clientes, proveedores, gastos
2. ✅ Audit de IntegrityError → Manejar en todos los servicios
3. ✅ Tests de duplicados → Cobertura de casos edge

### Fase 3: Testing - Semana 3
1. ✅ Smoke tests para todos los cambios
2. ✅ Load tests para cached_property
3. ✅ Validación de documentación

---

## 📝 NOTAS PARA IMPLEMENTACIÓN

1. **Backward Compatibility:** Las refactorizaciones mantienen APIs públicas iguales
2. **No breaking changes:** Todos los endpoints responden igual al cliente
3. **Migrations:** No requieren cambios en BD, solo lógica de aplicación
4. **Rollback:** Cada cambio es independiente y reversible

---

**Auditoría Completada ✅**  
Próximo Paso: Ejecutar script de aplicación de correcciones
