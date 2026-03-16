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
    ⚠️ v2.61: Campo id explícito y forzado para preservarlo en actualizaciones anidadas.
    """
    # CRÍTICO: required=False y allow_null=True obliga a DRF a retener el ID en validated_data
    id = serializers.IntegerField(required=False, allow_null=True) 
    cliente_nombre = serializers.SerializerMethodField()
    cliente_documento = serializers.SerializerMethodField()
    
    def get_cliente_nombre(self, obj):
        try:
            if not obj: return None
            cliente = getattr(obj, 'cliente', None)
            if cliente:
                razon_social = getattr(cliente, 'razon_social', None)
                return razon_social if razon_social else None
        except Exception as e:
            pass
        return None
    
    def get_cliente_documento(self, obj):
        try:
            if not obj: return None
            cliente = getattr(obj, 'cliente', None)
            if cliente:
                numero_documento = getattr(cliente, 'numero_documento', None)
                return numero_documento if numero_documento else None
        except Exception as e:
            pass
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
        read_only_fields = ['cliente_nombre', 'cliente_documento', 'cliente']
    
    def validate(self, attrs):
        """Validar unique_together (cliente + email) solo si es operación unitaria."""
        email = attrs.get('email')
        cliente = attrs.get('cliente')
        
        if not cliente and self.instance:
            cliente = self.instance.cliente
            
        if email and cliente:
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
    Soporta creación/actualización sincrónica de contactos asociados.
    """
    contactos = ContactoClienteSerializer(many=True, required=False)
    
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
            'contactos'
        ]
        read_only_fields = ['id']
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        contactos = ContactoCliente.objects.filter(cliente=instance).only(
            'id', 'nombre_completo', 'cargo', 'email', 'telefono', 'activo', 'is_principal'
        ).order_by('-is_principal', 'nombre_completo')
        representation['contactos'] = ContactoClienteSerializer(contactos, many=True).data
        return representation