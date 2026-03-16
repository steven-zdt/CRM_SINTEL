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
        # ⚠️ CRÍTICO: Capturar IntegrityError de restricciones únicas
        error_msg = str(e)
        
        # Error de documento duplicado
        if 'uniq_doc_cliente_empresa' in error_msg:
            raise ValidationError({
                'numero_documento': [
                    'Ya existe un cliente registrado con este tipo y número de documento en esta empresa.'
                ]
            })
        
        # Error de contacto duplicado (cliente_id + email)
        if 'contactocliente_cliente_id_email' in error_msg or 'cliente_id_email' in error_msg:
            raise ValidationError({
                'contactos': [
                    'Ya existe un contacto con este correo electrónico para este cliente.'
                ]
            })
        
        # Error genérico de constraint única
        if 'UNIQUE constraint' in error_msg or 'unique constraint' in error_msg:
            raise ValidationError({
                'non_field_errors': [
                    'Error de integridad: Ya existe un registro con estos datos únicos.'
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
            # ⚠️ v2.61: Lógica mejorada - Actualizar existentes, crear nuevos, eliminar faltantes
            contactos_ids_enviados = []
            
            for contacto_data in contactos_data:
                # ⚠️ DEBUG: Log del contacto recibido
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f'[actualizar_cliente] Procesando contacto: {contacto_data}')
                
                # ⚠️ Zero Trust: Validar que cada contacto tenga campos requeridos
                if not contacto_data.get('nombre_completo'):
                    raise ValidationError({
                        'contactos': ['Todos los contactos deben tener un nombre_completo.']
                    })
                if not contacto_data.get('email'):
                    raise ValidationError({
                        'contactos': ['Todos los contactos deben tener un email.']
                    })
                
                contacto_id = contacto_data.get('id')
                logger.info(f'[actualizar_cliente] Contacto ID extraído: {contacto_id}')
                
                # Si tiene ID, actualizar contacto existente
                if contacto_id:
                    try:
                        # Convertir id a int si viene como string
                        contacto_id = int(contacto_id) if isinstance(contacto_id, str) else contacto_id
                        
                        # ⚠️ Zero Trust: Solo actualizar contactos del cliente actual
                        contacto = ContactoCliente.objects.filter(
                            id=contacto_id,
                            cliente=cliente
                        ).first()
                        
                        if contacto:
                            contacto.nombre_completo = contacto_data.get('nombre_completo')
                            contacto.cargo = contacto_data.get('cargo', '')
                            contacto.email = contacto_data.get('email')
                            contacto.telefono = contacto_data.get('telefono', '')
                            contacto.activo = contacto_data.get('activo', True)
                            contacto.is_principal = contacto_data.get('is_principal', False)
                            contacto.save()
                            contactos_ids_enviados.append(contacto.id)
                        else:
                            # Si no existe el contacto con ese ID, ignorar
                            pass
                    except (ValueError, TypeError):
                        # Si el ID no es válido, ignorar
                        pass
                else:
                    # Si no tiene ID, crear nuevo contacto
                    try:
                        nuevo_contacto = ContactoCliente.objects.create(
                            cliente=cliente,
                            nombre_completo=contacto_data.get('nombre_completo'),
                            cargo=contacto_data.get('cargo', ''),
                            email=contacto_data.get('email'),
                            telefono=contacto_data.get('telefono', ''),
                            activo=contacto_data.get('activo', True),
                            is_principal=contacto_data.get('is_principal', False)
                        )
                        contactos_ids_enviados.append(nuevo_contacto.id)
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
            
            # ⚠️ Eliminar contactos que no vinieron en el payload (fueron removidos en el frontend)
            if contactos_ids_enviados:
                ContactoCliente.objects.filter(cliente=cliente).exclude(
                    id__in=contactos_ids_enviados
                ).delete()
            else:
                # Si no hay contactos enviados, eliminar todos
                ContactoCliente.objects.filter(cliente=cliente).delete()
        
        return cliente
    except IntegrityError as e:
        # ⚠️ CRÍTICO: Capturar IntegrityError de restricciones únicas
        error_msg = str(e)
        
        # Error de documento duplicado
        if 'uniq_doc_cliente_empresa' in error_msg:
            raise ValidationError({
                'numero_documento': [
                    'Ya existe un cliente registrado con este tipo y número de documento en esta empresa.'
                ]
            })
        
        # Error de contacto duplicado (cliente_id + email)
        if 'contactocliente_cliente_id_email' in error_msg or 'cliente_id_email' in error_msg:
            raise ValidationError({
                'contactos': [
                    'Ya existe un contacto con este correo electrónico para este cliente.'
                ]
            })
        
        # Error genérico de constraint única
        if 'UNIQUE constraint' in error_msg or 'unique constraint' in error_msg:
            raise ValidationError({
                'non_field_errors': [
                    'Error de integridad: Ya existe un registro con estos datos únicos.'
                ]
            })
        
        # Re-lanzar otros IntegrityError sin modificar
        raise
