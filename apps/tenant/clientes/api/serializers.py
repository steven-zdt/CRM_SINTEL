from rest_framework import serializers
from apps.tenant.clientes.models import Cliente, ContactoCliente

class NormalizationMixin:
    """
    Mixin para normalización de datos de entrada (Zero Trust).
    """
    def normalize_data(self, attrs):
        for key, value in attrs.items():
            if isinstance(value, str):
                attrs[key] = value.strip()
        return attrs

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


class ContactoClienteSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer para Contactos de Cliente (CRUD independiente).
    ⚠️ v2.61: Campo id explícito y forzado para preservarlo en actualizaciones anidadas.
    ⚠️ v2.61: Integración con NormalizationMixin para Zero Trust.
    """
    # CRÍTICO: required=False y allow_null=True obliga a DRF a retener el ID en validated_data
    id = serializers.IntegerField(required=False, allow_null=True) 
    cliente = serializers.PrimaryKeyRelatedField(queryset=Cliente.objects.all(), required=False)
    
    def get_cliente_nombre(self, obj):
        return obj.cliente.razon_social if obj.cliente else None

    def get_cliente_documento(self, obj):
        return obj.cliente.numero_documento if obj.cliente else None

    class Meta:
        model = ContactoCliente
        fields = ['id', 'cliente', 'nombre_completo', 'cargo', 'email', 'telefono', 'activo', 'is_principal', 'cliente_nombre', 'cliente_documento']

    def validate(self, attrs):
        """Validar unique_together (cliente + email) solo si es operación unitaria."""
        # Aplicar normalización (Zero Trust)
        attrs = self.normalize_data(attrs)
        
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


class ClienteDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer completo para detalle/edición de Clientes.
    Soporta creación/actualización sincrónica de contactos asociados.
    ⚠️ v2.61: Integración con NormalizationMixin para Zero Trust.
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
    
    def validate(self, attrs):
        """Normalizar datos (Zero Trust)."""
        attrs = self.normalize_data(attrs)
        return attrs
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # La lógica de carga de contactos se movió al ViewSet (prefetch_related)
        if hasattr(instance, 'contactos_prefetched'):
            contactos = instance.contactos_prefetched
            representation['contactos'] = ContactoClienteSerializer(contactos, many=True).data
        else:
            # Fallback en caso de que no se haya precargado
            contactos = instance.contactos.all().order_by('-is_principal', 'nombre_completo')
            representation['contactos'] = ContactoClienteSerializer(contactos, many=True).data
        return representation