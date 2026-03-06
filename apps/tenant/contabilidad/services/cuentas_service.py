"""
Service Layer para CuentaContable (dominio Contabilidad).

⚠️ v2.60: Service Layer Pattern - Lógica de negocio del dominio Contabilidad.
- Sin signals: Toda la lógica es explícita
- Sin HTTP: Funciones puras que operan sobre modelos
- Multi-tenant: Transparente (django-tenants maneja el aislamiento por esquema)
- Validaciones: Código único, cuenta padre válida, tipo de cuenta válido
"""
from typing import Dict, Any, Optional
from django.db import transaction
from rest_framework.exceptions import ValidationError
from apps.tenant.contabilidad.models import CuentaContable
from apps.tenant.empresa.models import Empresa


@transaction.atomic
def create_cuenta(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea una nueva cuenta contable.
    
    ⚠️ v2.60: Service Layer Pattern - Lógica de negocio completa
    ⚠️ VALIDACIONES: Código único, tipo válido, cuenta padre válida
    
    Args:
        data: Diccionario con datos de la cuenta:
            {
                'codigo': str,
                'nombre': str,
                'tipo': str (ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO),
                'descripcion': str (opcional),
                'cuenta_padre': int (ID, opcional),
                'activa': bool,
                'empresa': int (ID, opcional - se obtiene automáticamente si no se proporciona)
            }
    
    Returns:
        dict: DTO con datos de la cuenta creada
    
    Raises:
        rest_framework.exceptions.ValidationError: Si los datos no son válidos
    """
    # Validar código único
    codigo = data.get('codigo', '').strip()
    if not codigo:
        raise ValidationError({
            'codigo': ['El campo "codigo" es requerido y no puede estar vacío.']
        })
    
    if len(codigo) > 20:
        raise ValidationError({
            'codigo': ['El campo "codigo" no puede exceder 20 caracteres.']
        })
    
    if CuentaContable.objects.filter(codigo=codigo).exists():
        raise ValidationError({
            'codigo': [f'Ya existe una cuenta con el código "{codigo}".']
        })
    
    # Validar nombre
    nombre = data.get('nombre', '').strip()
    if not nombre:
        raise ValidationError({
            'nombre': ['El campo "nombre" es requerido y no puede estar vacío.']
        })
    
    if len(nombre) > 200:
        raise ValidationError({
            'nombre': ['El campo "nombre" no puede exceder 200 caracteres.']
        })
    
    # Validar tipo
    tipo = data.get('tipo', '').strip()
    tipos_validos = ['ACTIVO', 'PASIVO', 'PATRIMONIO', 'INGRESO', 'GASTO']
    if tipo not in tipos_validos:
        raise ValidationError({
            'tipo': [f'El campo "tipo" debe ser uno de: {", ".join(tipos_validos)}.']
        })
    
    # Validar cuenta padre si se proporciona
    cuenta_padre_id = data.get('cuenta_padre')
    if cuenta_padre_id:
        try:
            cuenta_padre = CuentaContable.objects.get(id=cuenta_padre_id)
            # Validar que la cuenta padre no sea la misma cuenta (si se está editando)
            if 'id' in data and cuenta_padre_id == data['id']:
                raise ValidationError({
                    'cuenta_padre': ['Una cuenta no puede ser su propia cuenta padre.']
                })
        except CuentaContable.DoesNotExist:
            raise ValidationError({
                'cuenta_padre': [f'Cuenta padre con ID {cuenta_padre_id} no encontrada.']
            })
    
    # Obtener empresa (SSoT) - Singleton por tenant
    empresa_id = data.get('empresa')
    if not empresa_id:
        # Intentar obtener empresa del tenant actual (singleton)
        try:
            empresa = Empresa.objects.first()
            if not empresa:
                raise ValidationError({
                    'empresa': ['No se encontró una empresa para el tenant actual.']
                })
            data['empresa'] = empresa
        except Exception as e:
            raise ValidationError({
                'empresa': [f'No se pudo determinar la empresa para la cuenta: {str(e)}']
            })
    else:
        try:
            empresa = Empresa.objects.get(id=empresa_id)
            data['empresa'] = empresa
        except Empresa.DoesNotExist:
            raise ValidationError({
                'empresa': [f'Empresa con ID {empresa_id} no encontrada.']
            })
    
    # Crear cuenta
    cuenta = CuentaContable.objects.create(
        codigo=codigo,
        nombre=nombre,
        tipo=tipo,
        descripcion=data.get('descripcion', ''),
        cuenta_padre_id=cuenta_padre_id,
        activa=data.get('activa', True),
        empresa=empresa
    )
    
    return {
        'id': cuenta.id,
        'uuid': str(cuenta.uuid),
        'codigo': cuenta.codigo,
        'nombre': cuenta.nombre,
        'tipo': cuenta.tipo,
        'descripcion': cuenta.descripcion,
        'cuenta_padre': cuenta.cuenta_padre_id,
        'activa': cuenta.activa,
        'created_at': cuenta.created_at.isoformat() if cuenta.created_at else None,
    }


@transaction.atomic
def update_cuenta(cuenta_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza una cuenta contable existente.
    
    ⚠️ v2.60: Service Layer Pattern - Lógica de negocio completa
    ⚠️ VALIDACIONES: Código único (si se cambia), tipo válido, cuenta padre válida
    
    Args:
        cuenta_id: ID de la cuenta a actualizar
        data: Diccionario con datos a actualizar (parcial)
    
    Returns:
        dict: DTO con datos de la cuenta actualizada
    
    Raises:
        rest_framework.exceptions.ValidationError: Si los datos no son válidos
        CuentaContable.DoesNotExist: Si la cuenta no existe
    """
    try:
        cuenta = CuentaContable.objects.get(id=cuenta_id)
    except CuentaContable.DoesNotExist:
        raise ValidationError({
            'detail': [f'Cuenta contable con ID {cuenta_id} no encontrada.']
        })
    
    # Validar código único si se está cambiando
    if 'codigo' in data:
        codigo = data['codigo'].strip()
        if not codigo:
            raise ValidationError({
                'codigo': ['El campo "codigo" no puede estar vacío.']
            })
        
        if len(codigo) > 20:
            raise ValidationError({
                'codigo': ['El campo "codigo" no puede exceder 20 caracteres.']
            })
        
        # Verificar que no exista otra cuenta con el mismo código
        if CuentaContable.objects.filter(codigo=codigo).exclude(id=cuenta_id).exists():
            raise ValidationError({
                'codigo': [f'Ya existe otra cuenta con el código "{codigo}".']
            })
    
    # Validar nombre si se está cambiando
    if 'nombre' in data:
        nombre = data['nombre'].strip()
        if not nombre:
            raise ValidationError({
                'nombre': ['El campo "nombre" no puede estar vacío.']
            })
        
        if len(nombre) > 200:
            raise ValidationError({
                'nombre': ['El campo "nombre" no puede exceder 200 caracteres.']
            })
    
    # Validar tipo si se está cambiando
    if 'tipo' in data:
        tipo = data['tipo'].strip()
        tipos_validos = ['ACTIVO', 'PASIVO', 'PATRIMONIO', 'INGRESO', 'GASTO']
        if tipo not in tipos_validos:
            raise ValidationError({
                'tipo': [f'El campo "tipo" debe ser uno de: {", ".join(tipos_validos)}.']
            })
    
    # Validar cuenta padre si se está cambiando
    if 'cuenta_padre' in data:
        cuenta_padre_id = data['cuenta_padre']
        if cuenta_padre_id:
            try:
                cuenta_padre = CuentaContable.objects.get(id=cuenta_padre_id)
                # Validar que la cuenta padre no sea la misma cuenta
                if cuenta_padre_id == cuenta_id:
                    raise ValidationError({
                        'cuenta_padre': ['Una cuenta no puede ser su propia cuenta padre.']
                    })
            except CuentaContable.DoesNotExist:
                raise ValidationError({
                    'cuenta_padre': [f'Cuenta padre con ID {cuenta_padre_id} no encontrada.']
                })
    
    # Actualizar campos
    update_fields = []
    if 'codigo' in data:
        cuenta.codigo = data['codigo'].strip()
        update_fields.append('codigo')
    if 'nombre' in data:
        cuenta.nombre = data['nombre'].strip()
        update_fields.append('nombre')
    if 'tipo' in data:
        cuenta.tipo = data['tipo'].strip()
        update_fields.append('tipo')
    if 'descripcion' in data:
        cuenta.descripcion = data.get('descripcion', '')
        update_fields.append('descripcion')
    if 'cuenta_padre' in data:
        cuenta.cuenta_padre_id = data['cuenta_padre']
        update_fields.append('cuenta_padre')
    if 'activa' in data:
        cuenta.activa = data['activa']
        update_fields.append('activa')
    
    if update_fields:
        cuenta.save(update_fields=update_fields)
    
    return {
        'id': cuenta.id,
        'uuid': str(cuenta.uuid),
        'codigo': cuenta.codigo,
        'nombre': cuenta.nombre,
        'tipo': cuenta.tipo,
        'descripcion': cuenta.descripcion,
        'cuenta_padre': cuenta.cuenta_padre_id,
        'activa': cuenta.activa,
        'created_at': cuenta.created_at.isoformat() if cuenta.created_at else None,
    }


@transaction.atomic
def delete_cuenta(cuenta_id: int) -> None:
    """
    Elimina una cuenta contable.
    
    ⚠️ v2.60: Service Layer Pattern - Lógica de negocio completa
    ⚠️ VALIDACIONES: Verificar que no tenga cuentas hijas ni movimientos asociados
    
    Args:
        cuenta_id: ID de la cuenta a eliminar
    
    Raises:
        rest_framework.exceptions.ValidationError: Si la cuenta no puede ser eliminada
        CuentaContable.DoesNotExist: Si la cuenta no existe
    """
    try:
        cuenta = CuentaContable.objects.get(id=cuenta_id)
    except CuentaContable.DoesNotExist:
        raise ValidationError({
            'detail': [f'Cuenta contable con ID {cuenta_id} no encontrada.']
        })
    
    # Validar que no tenga cuentas hijas
    if cuenta.cuentas_hijas.exists():
        raise ValidationError({
            'detail': ['No se puede eliminar una cuenta que tiene cuentas hijas asociadas.']
        })
    
    # Validar que no tenga movimientos asociados
    from apps.tenant.contabilidad.models import MovimientoContable
    if MovimientoContable.objects.filter(cuenta=cuenta).exists():
        raise ValidationError({
            'detail': ['No se puede eliminar una cuenta que tiene movimientos contables asociados.']
        })
    
    cuenta.delete()
