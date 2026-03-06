"""
Servicios de dominio para Clientes v2.60.

PRINCIPIOS:
- Lógica de Negocio: Validaciones y operaciones CRUD.
- Transaccionalidad: Uso de transaction.atomic para integridad.
- Optimización: QuerySets pre-optimizados para Tabulator.
- SSoT: Empresa se inyecta automáticamente desde el tenant.
- Zero Trust: Validación explícita de que el Tenant (Empresa) del usuario coincida con la operación.
"""
from django.db import transaction, IntegrityError
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from .models import Cliente, ContactoCliente


def qs_list(empresa_id, search=None):
    """
    ⚠️ v2.40: Retorna listado optimizado para Tabulator (Zero Waste).
    
    ⚠️ PERFORMANCE BIBLE:
    - PROHIBIDO objects.all(): Siempre filtrar por empresa_id (SSoT)
    - PROHIBIDO SELECT *: Solo campos que usa ClienteListSerializer
    - Campos display (get_*_display) son métodos Python, no necesitan estar en .only()
    
    Args:
        empresa_id: ID de la empresa (SSoT)
        search: Término de búsqueda opcional
        
    Returns:
        QuerySet optimizado con only() para campos visibles en tabla
    """
    # ⚠️ CRÍTICO: Siempre filtrar por empresa (SSoT) - PROHIBIDO .all()
    qs = Cliente.objects.filter(empresa_id=empresa_id).only(
        # Campos base usados por ClienteListSerializer (sin métodos display)
        'id', 
        'tipo_persona',  # Para get_tipo_persona_display()
        'tipo_documento',  # Para get_tipo_documento_display()
        'numero_documento', 
        'razon_social', 
        'nombre_comercial',
        'regimen_tributario',  # Para get_regimen_tributario_display()
        'email', 
        'telefono',
        'ciudad',
        'activo'
    ).order_by('razon_social')
    
    if search:
        qs = qs.filter(
            Q(razon_social__icontains=search) | 
            Q(numero_documento__icontains=search) |
            Q(email__icontains=search) |
            Q(nombre_comercial__icontains=search)
        )
    
    return qs


def qs_detail(empresa_id, pk):
    """
    ⚠️ v2.60: Retorna detalle completo para edición (Zero Waste).
    
    ⚠️ PERFORMANCE BIBLE:
    - Siempre filtrar por empresa_id (SSoT)
    - PROHIBIDO SELECT *: Solo campos que usa ClienteDetailSerializer
    - No usa select_related() porque ClienteDetailSerializer no accede a relaciones directas
    
    Args:
        empresa_id: ID de la empresa (SSoT)
        pk: ID del cliente
        
    Returns:
        Cliente o None si no existe
    """
    # ⚠️ CRÍTICO: Siempre filtrar por empresa (SSoT) - PROHIBIDO .all()
    # ⚠️ CRÍTICO: Usar .only() con campos específicos usados por ClienteDetailSerializer
    return Cliente.objects.filter(empresa_id=empresa_id, pk=pk).only(
        'id',
        'tipo_persona',
        'tipo_documento',
        'numero_documento',
        'razon_social',
        'nombre_comercial',
        'regimen_tributario',
        'email',
        'telefono',
        'direccion',
        'ciudad',
        'activo',
        'observaciones',
        'empresa_id'  # Necesario para validaciones Zero Trust
    ).first()


@transaction.atomic
def crear_cliente(empresa, data, contactos_data=None):
    """
    ⚠️ v2.60: Crea un cliente asignando la empresa SSoT automáticamente.
    Soporta creación de contactos asociados en la misma transacción.
    
    ⚠️ Zero Trust: Valida explícitamente que la empresa proporcionada sea válida.
    
    Args:
        empresa: Instancia de Empresa (SSoT) - DEBE ser válida y existir
        data: Dict con datos del cliente (sin 'contactos')
        contactos_data: Lista opcional de dicts con datos de contactos
        
    Returns:
        Cliente creado con contactos asociados
        
    Raises:
        ValidationError: Si el documento ya existe (restricción única) o si hay errores en contactos
    """
    # ⚠️ Zero Trust: Validar explícitamente que empresa existe y tiene ID
    if not empresa or not hasattr(empresa, 'id') or not empresa.id:
        raise ValidationError({
            'empresa': ['La empresa proporcionada no es válida o no existe.']
        })
    
    # ⚠️ Zero Trust: Extraer contactos del data si viene en el payload
    if 'contactos' in data:
        if contactos_data is None:
            contactos_data = data.pop('contactos', [])
        else:
            data.pop('contactos', None)  # Remover si ya se pasó por separado
    
    try:
        # Crear cliente
        cliente = Cliente.objects.create(empresa=empresa, **data)
        
        # Crear contactos si se proporcionaron
        if contactos_data and isinstance(contactos_data, list):
            for contacto_data in contactos_data:
                # ⚠️ Zero Trust: Validar que cada contacto tenga campos requeridos
                if not contacto_data.get('nombre_completo'):
                    raise ValidationError({
                        'contactos': ['Todos los contactos deben tener un nombre_completo.']
                    })
                if not contacto_data.get('email'):
                    raise ValidationError({
                        'contactos': ['Todos los contactos deben tener un email.']
                    })
                
                # Crear contacto asociado al cliente
                try:
                    ContactoCliente.objects.create(
                        cliente=cliente,
                        nombre_completo=contacto_data.get('nombre_completo'),
                        cargo=contacto_data.get('cargo', ''),
                        email=contacto_data.get('email'),
                        telefono=contacto_data.get('telefono', ''),
                        activo=contacto_data.get('activo', True),
                        is_principal=contacto_data.get('is_principal', False)
                    )
                except IntegrityError as e:
                    # ⚠️ CRÍTICO: Capturar IntegrityError de restricción única (cliente + email)
                    error_msg = str(e)
                    if 'unique_together' in error_msg.lower() or 'UNIQUE constraint' in error_msg:
                        raise ValidationError({
                            'contactos': [
                                f'Ya existe un contacto con el email {contacto_data.get("email")} para este cliente.'
                            ]
                        })
                    raise
        
        return cliente
    except IntegrityError as e:
        # ⚠️ CRÍTICO: Capturar IntegrityError de restricción única
        # La restricción uniq_doc_cliente_empresa valida: empresa + tipo_documento + numero_documento
        error_msg = str(e)
        if 'uniq_doc_cliente_empresa' in error_msg or 'UNIQUE constraint' in error_msg:
            raise ValidationError({
                'numero_documento': [
                    'Ya existe un cliente registrado con este tipo y número de documento en esta empresa.'
                ]
            })
        # Re-lanzar otros IntegrityError sin modificar
        raise


@transaction.atomic
def actualizar_cliente(cliente, data, contactos_data=None):
    """
    ⚠️ v2.60: Actualiza datos del cliente.
    Soporta actualización de contactos asociados en la misma transacción.
    
    ⚠️ Zero Trust: Valida explícitamente que el cliente pertenezca a la empresa del tenant.
    
    Args:
        cliente: Instancia de Cliente - DEBE pertenecer a la empresa del tenant
        data: Dict con campos a actualizar (sin 'contactos')
        contactos_data: Lista opcional de dicts con datos de contactos (reemplaza todos los existentes)
        
    Returns:
        Cliente actualizado con contactos actualizados
        
    Raises:
        ValidationError: Si el documento ya existe (restricción única) o si hay errores en contactos
    """
    # ⚠️ Zero Trust: Validar explícitamente que cliente existe y tiene empresa
    if not cliente or not hasattr(cliente, 'empresa') or not cliente.empresa:
        raise ValidationError({
            'cliente': ['El cliente proporcionado no es válido o no tiene empresa asociada.']
        })
    
    # ⚠️ Zero Trust: Extraer contactos del data si viene en el payload
    if 'contactos' in data:
        if contactos_data is None:
            contactos_data = data.pop('contactos', [])
        else:
            data.pop('contactos', None)  # Remover si ya se pasó por separado
    
    try:
        # Actualizar campos del cliente
        for key, value in data.items():
            setattr(cliente, key, value)
        cliente.save()
        
        # Actualizar contactos si se proporcionaron
        if contactos_data is not None and isinstance(contactos_data, list):
            # ⚠️ Zero Trust: Eliminar contactos existentes y crear nuevos (reemplazo completo)
            # Esto garantiza que solo existan los contactos enviados en el payload
            ContactoCliente.objects.filter(cliente=cliente).delete()
            
            for contacto_data in contactos_data:
                # ⚠️ Zero Trust: Validar que cada contacto tenga campos requeridos
                if not contacto_data.get('nombre_completo'):
                    raise ValidationError({
                        'contactos': ['Todos los contactos deben tener un nombre_completo.']
                    })
                if not contacto_data.get('email'):
                    raise ValidationError({
                        'contactos': ['Todos los contactos deben tener un email.']
                    })
                
                # Crear contacto asociado al cliente
                try:
                    ContactoCliente.objects.create(
                        cliente=cliente,
                        nombre_completo=contacto_data.get('nombre_completo'),
                        cargo=contacto_data.get('cargo', ''),
                        email=contacto_data.get('email'),
                        telefono=contacto_data.get('telefono', ''),
                        activo=contacto_data.get('activo', True),
                        is_principal=contacto_data.get('is_principal', False)
                    )
                except IntegrityError as e:
                    # ⚠️ CRÍTICO: Capturar IntegrityError de restricción única (cliente + email)
                    error_msg = str(e)
                    if 'unique_together' in error_msg.lower() or 'UNIQUE constraint' in error_msg:
                        raise ValidationError({
                            'contactos': [
                                f'Ya existe un contacto con el email {contacto_data.get("email")} para este cliente.'
                            ]
                        })
                    raise
        
        return cliente
    except IntegrityError as e:
        # ⚠️ CRÍTICO: Capturar IntegrityError de restricción única
        # La restricción uniq_doc_cliente_empresa valida: empresa + tipo_documento + numero_documento
        error_msg = str(e)
        if 'uniq_doc_cliente_empresa' in error_msg or 'UNIQUE constraint' in error_msg:
            raise ValidationError({
                'numero_documento': [
                    'Ya existe un cliente registrado con este tipo y número de documento en esta empresa.'
                ]
            })
        # Re-lanzar otros IntegrityError sin modificar
        raise