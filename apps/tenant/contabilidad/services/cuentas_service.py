"""
Service Layer interno para CuentaContable (dominio Contabilidad).

⚠️ v2.30: Service Layer Pattern - Lógica de negocio del dominio Contabilidad.
- Sin signals: Toda la lógica es explícita
- Sin HTTP: Funciones puras que operan sobre modelos
- Multi-tenant: Transparente (django-tenants maneja el aislamiento por esquema)
- Validaciones: Estructura de código, unicidad por tenant
"""
from typing import Dict, Any, List, Optional
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q


def list_cuentas(
    filters: Optional[Dict[str, Any]] = None,
    ordering: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    Lista cuentas contables (paginado).
    
    Args:
        filters: Diccionario con filtros (tipo, activa, cuenta_padre, search)
        ordering: Campo de ordenamiento (codigo, nombre, tipo)
        page: Número de página (1-indexed)
        page_size: Tamaño de página
    
    Returns:
        dict: DTO con resultados paginados
    """
    from apps.tenant.contabilidad.models import CuentaContable
    
    qs = CuentaContable.objects.only(
        'id', 'codigo', 'nombre', 'tipo', 'activa', 'created_at'
    )
    
    # Aplicar filtros
    if filters:
        if 'tipo' in filters:
            qs = qs.filter(tipo=filters['tipo'])
        if 'activa' in filters:
            qs = qs.filter(activa=filters['activa'])
        if 'cuenta_padre' in filters:
            qs = qs.filter(cuenta_padre_id=filters['cuenta_padre'])
        if 'search' in filters:
            search = filters['search']
            qs = qs.filter(
                Q(codigo__icontains=search) |
                Q(nombre__icontains=search) |
                Q(descripcion__icontains=search)
            )
    
    # Aplicar ordenamiento (whitelist)
    ordering_fields = ['codigo', 'nombre', 'tipo', '-codigo', '-nombre', '-tipo']
    if ordering and ordering in ordering_fields:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by('codigo')
    
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)
    
    results = []
    for cuenta in page_obj:
        results.append({
            'id': cuenta.id,
            'codigo': cuenta.codigo,
            'nombre': cuenta.nombre,
            'tipo': cuenta.tipo,
            'activa': cuenta.activa,
            'created_at': cuenta.created_at.isoformat() if cuenta.created_at else None,
        })
    
    return {
        'count': paginator.count,
        'next': page_obj.next_page_number() if page_obj.has_next() else None,
        'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'results': results,
    }


@transaction.atomic
def create_cuenta(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea una cuenta contable.
    
    ⚠️ VALIDACIONES: Estructura de código, unicidad por tenant.
    
    Args:
        data: Diccionario con datos de la cuenta
    
    Returns:
        dict: DTO con datos de la cuenta creada
    
    Raises:
        ValueError: Si los datos no son válidos
    """
    from apps.tenant.contabilidad.models import CuentaContable
    
    # Validaciones
    if 'codigo' in data:
        codigo = data['codigo']
        if not isinstance(codigo, str) or len(codigo) > 20:
            raise ValueError("El campo 'codigo' debe ser una cadena de texto de máximo 20 caracteres.")
        if not codigo.strip():
            raise ValueError("El campo 'codigo' no puede estar vacío.")
        # Verificar unicidad
        if CuentaContable.objects.filter(codigo=codigo).exists():
            raise ValueError(f"Ya existe una cuenta con el código '{codigo}'.")
    
    if 'nombre' in data:
        nombre = data['nombre']
        if not isinstance(nombre, str) or len(nombre) > 200:
            raise ValueError("El campo 'nombre' debe ser una cadena de texto de máximo 200 caracteres.")
        if not nombre.strip():
            raise ValueError("El campo 'nombre' no puede estar vacío.")
    
    if 'tipo' in data:
        tipo = data['tipo']
        tipos_validos = ['ACTIVO', 'PASIVO', 'PATRIMONIO', 'INGRESO', 'GASTO']
        if tipo not in tipos_validos:
            raise ValueError(f"El campo 'tipo' debe ser uno de: {', '.join(tipos_validos)}.")
    
    cuenta = CuentaContable.objects.create(**data)
    
    return {
        'id': cuenta.id,
        'codigo': cuenta.codigo,
        'nombre': cuenta.nombre,
        'tipo': cuenta.tipo,
        'descripcion': cuenta.descripcion or '',
        'cuenta_padre': cuenta.cuenta_padre_id,
        'activa': cuenta.activa,
        'created_at': cuenta.created_at.isoformat() if cuenta.created_at else None,
    }


@transaction.atomic
def update_cuenta(cuenta_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza una cuenta contable.
    
    ⚠️ VALIDACIONES: Estructura de código, unicidad por tenant.
    
    Args:
        cuenta_id: ID de la cuenta
        data: Diccionario con campos a actualizar
    
    Returns:
        dict: DTO con datos de la cuenta actualizada
    
    Raises:
        ValueError: Si los datos no son válidos
        CuentaContable.DoesNotExist: Si la cuenta no existe
    """
    from apps.tenant.contabilidad.models import CuentaContable
    
    cuenta = CuentaContable.objects.get(id=cuenta_id)
    
    # Validaciones (mismas que create)
    if 'codigo' in data:
        codigo = data['codigo']
        if not isinstance(codigo, str) or len(codigo) > 20:
            raise ValueError("El campo 'codigo' debe ser una cadena de texto de máximo 20 caracteres.")
        if not codigo.strip():
            raise ValueError("El campo 'codigo' no puede estar vacío.")
        # Verificar unicidad (excluyendo la cuenta actual)
        if CuentaContable.objects.filter(codigo=codigo).exclude(id=cuenta_id).exists():
            raise ValueError(f"Ya existe otra cuenta con el código '{codigo}'.")
    
    campos_permitidos = ['codigo', 'nombre', 'tipo', 'descripcion', 'cuenta_padre', 'activa']
    update_fields = []
    for campo in campos_permitidos:
        if campo in data:
            setattr(cuenta, campo, data[campo])
            update_fields.append(campo)
    
    if update_fields:
        cuenta.save(update_fields=update_fields)
    
    return {
        'id': cuenta.id,
        'codigo': cuenta.codigo,
        'nombre': cuenta.nombre,
        'tipo': cuenta.tipo,
        'descripcion': cuenta.descripcion or '',
        'cuenta_padre': cuenta.cuenta_padre_id,
        'activa': cuenta.activa,
        'created_at': cuenta.created_at.isoformat() if cuenta.created_at else None,
    }


@transaction.atomic
def delete_cuenta(cuenta_id: int) -> None:
    """
    Elimina una cuenta contable.
    
    Args:
        cuenta_id: ID de la cuenta
    
    Raises:
        CuentaContable.DoesNotExist: Si la cuenta no existe
    """
    from apps.tenant.contabilidad.models import CuentaContable
    
    cuenta = CuentaContable.objects.get(id=cuenta_id)
    cuenta.delete()
