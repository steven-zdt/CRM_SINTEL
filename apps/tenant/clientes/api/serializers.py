from rest_framework import serializers
from apps.tenant.clientes.models import Cliente, ContactoCliente

class ClienteListSerializer(serializers.ModelSerializer):
    """
    ⚠️ v2.40: Serializer optimizado para listas (Tabulator).
    Solo incluye campos estrictamente necesarios para la tabla del frontend.
    """
    tipo_documento_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)
    tipo_persona_display = serializers.CharField(source='get_tipo_persona_display', read_only=True)
    regimen_tributario_display = serializers.CharField(source='get_regimen_tributario_display', read_only=True)
    
    class Meta:
        model = Cliente
        fields = [
            'id', 
            'tipo_persona', 'tipo_persona_display',
            'tipo_documento', 'tipo_documento_display', 
            'numero_documento', 
            'razon_social', 
            'nombre_comercial',
            'regimen_tributario', 'regimen_tributario_display',
            'email', 
            'telefono',
            'ciudad',
            'activo'
        ]
        read_only_fields = ['id', 'tipo_documento_display', 'tipo_persona_display', 'regimen_tributario_display']


class ContactoClienteSerializer(serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer para Contactos de Cliente (CRUD independiente).
    Permite crear/actualizar/eliminar contactos asociados a un cliente.
    
    ⚠️ Zero Trust: Valida que el email no se repita en el mismo cliente (unique_together).
    ⚠️ v2.60: Optimizado para grid global (Directorio de Contactos) con campos de lectura del cliente.
    """
    cliente_nombre = serializers.SerializerMethodField()
    cliente_documento = serializers.SerializerMethodField()
    
    def get_cliente_nombre(self, obj):
        """Obtener razon_social del cliente de forma segura."""
        try:
            # Verificar que obj existe y tiene el atributo cliente
            if not obj:
                return None
            cliente = getattr(obj, 'cliente', None)
            if cliente:
                # Intentar acceder a razon_social
                razon_social = getattr(cliente, 'razon_social', None)
                return razon_social if razon_social else None
        except (AttributeError, Exception) as e:
            # Si hay algún error al acceder al cliente, retornar None
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'[ContactoClienteSerializer.get_cliente_nombre] Error accediendo a cliente: {str(e)}')
        return None
    
    def get_cliente_documento(self, obj):
        """Obtener numero_documento del cliente de forma segura."""
        try:
            # Verificar que obj existe y tiene el atributo cliente
            if not obj:
                return None
            cliente = getattr(obj, 'cliente', None)
            if cliente:
                # Intentar acceder a numero_documento
                numero_documento = getattr(cliente, 'numero_documento', None)
                return numero_documento if numero_documento else None
        except (AttributeError, Exception) as e:
            # Si hay algún error al acceder al cliente, retornar None
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'[ContactoClienteSerializer.get_cliente_documento] Error accediendo a cliente: {str(e)}')
        return None
    
    class Meta:
        model = ContactoCliente
        fields = [
            'id',
            'cliente',
            'cliente_nombre',
            'cliente_documento',
            'nombre_completo',
            'cargo',
            'email',
            'telefono',
            'activo',
            'is_principal'
        ]
        read_only_fields = ['id', 'cliente_nombre', 'cliente_documento']
    
    def validate(self, attrs):
        """
        ⚠️ Zero Trust: Validar unique_together (cliente + email) antes de guardar.
        """
        email = attrs.get('email')
        cliente = attrs.get('cliente') or (self.instance.cliente if self.instance else None)
        
        if email and cliente:
            # Verificar si ya existe otro contacto con el mismo email en el mismo cliente
            existing = ContactoCliente.objects.filter(
                cliente=cliente,
                email=email
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise serializers.ValidationError({
                    'email': ['Ya existe un contacto con este email para este cliente.']
                })
        
        return attrs


class ClienteDetailSerializer(serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer completo para detalle/edición de Clientes.
    Incluye todos los campos del modelo excepto empresa (SSoT) y timestamps.
    Soporta creación/actualización de contactos asociados.
    """
    # ⚠️ v2.60: Contactos anidados - read_only para lectura, write_only para escritura
    contactos = ContactoClienteSerializer(many=True, required=False, read_only=False)
    
    class Meta:
        model = Cliente
        fields = [
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
            'contactos'  # ⚠️ v2.60: Array de contactos
        ]
        read_only_fields = ['id']
    
    def to_representation(self, instance):
        """
        ⚠️ v2.60: Sobrescribir para incluir contactos en la representación (GET).
        """
        representation = super().to_representation(instance)
        # Cargar contactos usando .only() para optimización
        contactos = ContactoCliente.objects.filter(cliente=instance).only(
            'id', 'nombre_completo', 'cargo', 'email', 'telefono', 'activo', 'is_principal'
        )
        representation['contactos'] = ContactoClienteSerializer(contactos, many=True).data
        return representation