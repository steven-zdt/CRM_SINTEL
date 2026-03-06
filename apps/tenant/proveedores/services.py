"""
Service Layer para la app proveedores v2.40.

⚠️ PERFORMANCE BIBLE:
- PROHIBIDO objects.all(): Siempre filtrar por empresa_id (SSoT)
- PROHIBIDO SELECT *: Solo campos que usa el Serializer
- ELIMINACIÓN DE N+1: Usar select_related() para ForeignKey
- Conteo Eficiente: Usar .exists() en lugar de len() o .count() > 0
"""
from django.db import transaction, IntegrityError
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from .models import Proveedor

# ⚠️ v2.40: LIST_FIELDS y DETAIL_FIELDS alineados con modelo actual
LIST_FIELDS = (
    "id",
    "tipo_persona",  # Para get_tipo_persona_display()
    "tipo_documento",  # Para get_tipo_documento_display()
    "numero_documento",
    "digito_verificacion",
    "razon_social",
    "nombre_comercial",
    "regimen_tributario",  # Para get_regimen_tributario_display()
    "email_contacto",
    "telefono_contacto",
    "ciudad",
    "activo",
)

DETAIL_FIELDS = (
    "id",
    "tipo_persona",
    "tipo_documento",
    "numero_documento",
    "digito_verificacion",
    "razon_social",
    "nombre_comercial",
    "regimen_tributario",
    "actividad_economica_ciiu",
    "responsable_iva",
    "gran_contribuyente",
    "autoretenedor",
    "email_contacto",
    "telefono_contacto",
    "direccion",
    "ciudad",
    "plazo_pago_dias",
    "banco",
    "tipo_cuenta",
    "numero_cuenta",
    "activo",
    "observaciones",
    "created_at",
    "updated_at",
)


def qs_list(empresa_id, search=None):
    """
    ⚠️ v2.40: Retorna listado optimizado para Tabulator (Zero Waste).
    
    ⚠️ PERFORMANCE BIBLE:
    - PROHIBIDO objects.all(): Siempre filtrar por empresa_id (SSoT)
    - PROHIBIDO SELECT *: Solo campos que usa ProveedorListSerializer
    - Campos display (get_*_display) son métodos Python, no necesitan estar en .only()
    
    Args:
        empresa_id: ID de la empresa (SSoT)
        search: Término de búsqueda opcional
        
    Returns:
        QuerySet optimizado con only() para campos visibles en tabla
    """
    # ⚠️ CRÍTICO: Siempre filtrar por empresa (SSoT) - PROHIBIDO .all()
    qs = Proveedor.objects.filter(empresa_id=empresa_id).only(*LIST_FIELDS).order_by('razon_social')
    
    if search:
        qs = qs.filter(
            Q(razon_social__icontains=search) | 
            Q(numero_documento__icontains=search) |
            Q(email_contacto__icontains=search) |
            Q(nombre_comercial__icontains=search)
        )
    
    return qs


def qs_detail(empresa_id, pk):
    """
    ⚠️ v2.40: Retorna detalle completo para edición (Zero Waste).
    
    ⚠️ PERFORMANCE BIBLE:
    - Siempre filtrar por empresa_id (SSoT)
    - No usa select_related() porque ProveedorDetailSerializer no accede a relaciones
    
    Args:
        empresa_id: ID de la empresa (SSoT)
        pk: ID del proveedor
        
    Returns:
        Proveedor o None si no existe
    """
    # ⚠️ CRÍTICO: Siempre filtrar por empresa (SSoT) - PROHIBIDO .all()
    return Proveedor.objects.filter(empresa_id=empresa_id, pk=pk).first()


@transaction.atomic
def crear_proveedor(empresa_id, data):
    """
    ⚠️ v2.60: Crea un proveedor con Zero Trust.
    
    Args:
        empresa_id: ID de la empresa del tenant (Zero Trust)
        data: Dict con datos del proveedor
        
    Returns:
        Proveedor creado
        
    Raises:
        ValidationError: Si el documento ya existe (restricción única) o la empresa no existe
    """
    # ⚠️ ZERO TRUST: Validar que la empresa exista y pertenezca al tenant
    from apps.tenant.empresa.models import Empresa
    empresa = Empresa.objects.only('id').filter(pk=empresa_id).first()
    if not empresa:
        raise ValidationError(f"La empresa con ID {empresa_id} no existe o no pertenece a este tenant.")
    
    try:
        return Proveedor.objects.create(empresa_id=empresa_id, **data)
    except IntegrityError as e:
        # ⚠️ CRÍTICO: Capturar IntegrityError de restricción única
        # La restricción uniq_proveedor_empresa valida: empresa + tipo_documento + numero_documento
        error_msg = str(e)
        if 'uniq_proveedor_empresa' in error_msg or 'UNIQUE constraint' in error_msg:
            raise ValidationError({
                'numero_documento': [
                    'Ya existe un proveedor registrado con este tipo y número de documento en esta empresa.'
                ]
            })
        # Re-lanzar otros IntegrityError sin modificar
        raise


@transaction.atomic
def actualizar_proveedor(proveedor_id, empresa_id, data):
    """
    ⚠️ v2.60: Actualiza datos del proveedor con Zero Trust.
    
    Args:
        proveedor_id: ID del proveedor a actualizar
        empresa_id: ID de la empresa del tenant (Zero Trust)
        data: Dict con campos a actualizar
        
    Returns:
        Proveedor actualizado
        
    Raises:
        ValidationError: Si el proveedor no existe, no pertenece al tenant, o el documento ya existe
    """
    # ⚠️ ZERO TRUST: Validar que el proveedor pertenezca al tenant
    proveedor = Proveedor.objects.filter(pk=proveedor_id, empresa_id=empresa_id).first()
    if not proveedor:
        raise ValidationError(f"El proveedor con ID {proveedor_id} no existe o no pertenece a este tenant.")
    
    try:
        for key, value in data.items():
            setattr(proveedor, key, value)
        proveedor.save()
        return proveedor
    except IntegrityError as e:
        # ⚠️ CRÍTICO: Capturar IntegrityError de restricción única
        # La restricción uniq_proveedor_empresa valida: empresa + tipo_documento + numero_documento
        error_msg = str(e)
        if 'uniq_proveedor_empresa' in error_msg or 'UNIQUE constraint' in error_msg:
            raise ValidationError({
                'numero_documento': [
                    'Ya existe un proveedor registrado con este tipo y número de documento en esta empresa.'
                ]
            })
        # Re-lanzar otros IntegrityError sin modificar
        raise
