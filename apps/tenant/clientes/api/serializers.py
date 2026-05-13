from rest_framework import serializers

from apps.tenant.api.utils import NormalizationMixin
from apps.tenant.clientes.models import Cliente, ContactoCliente

# # WARNING: v2.61.4: Importar NormalizationMixin expandido desde utils
# Incluye validación de strings, decimales, booleanos, documentos, teléfonos

class ClienteMiniSerializer(serializers.ModelSerializer):
    """
    Lightweight read-only serializer para uso nested en otros modulos.
    Uso: cotizaciones, proyectos, reportes - donde se necesita info minima del cliente
    sin cargar el serializer completo.
    """
    class Meta:
        model = Cliente
        fields = [
            'id',
            'numero_documento',
            'razon_social',
            'nombre_comercial',
            'email',
            'telefono',
        ]
        read_only_fields = fields


class ClienteListSerializer(serializers.ModelSerializer):
    """
    # WARNING: v2.40: Serializer optimizado para listas (Tabulator).
    Solo incluye campos estrictamente necesarios para la tabla del frontend.
    """
    tipo_documento_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)
    tipo_persona_display = serializers.CharField(source='get_tipo_persona_display', read_only=True)
    regimen_tributario_display = serializers.CharField(source='get_regimen_tributario_display', read_only=True)
    encargado = serializers.SerializerMethodField()

    def get_encargado(self, obj):
        principal = obj.contactos_prefetched[0] if hasattr(obj, 'contactos_prefetched') and obj.contactos_prefetched else None
        if principal:
            return {'nombre': principal.nombre_completo, 'email': principal.email}
        return None

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
            'es_retenedor',
            'aplica_retefuente', 'retefuente_porcentaje',
            'aplica_reteica', 'reteica_porcentaje',
            'aplica_reteiva', 'reteiva_porcentaje',
            'email',
            'telefono',
            'ciudad',
            'encargado',
            'activo'
        ]
        read_only_fields = ['id', 'tipo_documento_display', 'tipo_persona_display', 'regimen_tributario_display', 'encargado']


class ContactoClienteSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    # WARNING: v2.60: Serializer para Contactos de Cliente (CRUD independiente).
    # WARNING: v2.61: Campo id explícito y forzado para preservarlo en actualizaciones anidadas.
    # WARNING: v2.61: Integración con NormalizationMixin para Zero Trust.
    """
    # cliente es opcional en el serializer para soportar el patron de creacion anidada inicial:
    # al crear un cliente nuevo, el ID del padre aun no existe en el momento de validar el payload.
    # El service layer valida y asigna el cliente_id antes de persistir.
    # Para PATCH parcial DRF ignora required de todas formas cuando partial=True.
    cliente = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.only('id', 'empresa_id'),
        required=False,
        allow_null=True,
    )
    cliente_nombre = serializers.SerializerMethodField(read_only=True)
    cliente_documento = serializers.SerializerMethodField(read_only=True)
    
    def get_cliente_nombre(self, obj):
        return obj.cliente.razon_social if obj.cliente else None

    def get_cliente_documento(self, obj):
        return obj.cliente.numero_documento if obj.cliente else None

    class Meta:
        model = ContactoCliente
        fields = [
            'id',
            'cliente',
            'nombre_completo',
            'cargo',
            'email',
            'telefono',
            'activo',
            'is_principal',
            'cliente_nombre',
            'cliente_documento',
        ]

    def validate(self, attrs):
        # Normalize fields
        attrs = self.normalize_data(attrs)
        if attrs.get('email'):
            attrs['email'] = attrs['email'].strip().lower()
        if attrs.get('nombre_completo'):
            attrs['nombre_completo'] = attrs['nombre_completo'].strip()

        empresa_id = self.context.get('empresa_id')
        cliente = attrs.get('cliente') or (self.instance.cliente if self.instance else None)

        # Validate client belongs to this tenant
        if cliente and empresa_id and cliente.empresa_id != empresa_id:
            raise serializers.ValidationError({
                'cliente': ['El cliente especificado no pertenece a esta empresa.']
            })

        # Validate unique (cliente, email) on update to surface error early
        email = attrs.get('email')
        if email and cliente and self.instance:
            existing = ContactoCliente.objects.filter(
                cliente_id=cliente.id,
                empresa_id=empresa_id or cliente.empresa_id,
                email=email,
            ).exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError({
                    'email': ['Ya existe un contacto con este email para este cliente.']
                })

        return attrs


class ClienteDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    Serializer completo para detalle/edicion de Clientes.
    Contactos se gestionan de forma independiente via ContactoClienteViewSet.
    """

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
            'es_retenedor',
            'aplica_retefuente',
            'retefuente_porcentaje',
            'aplica_reteica',
            'reteica_porcentaje',
            'aplica_reteiva',
            'reteiva_porcentaje',
            'email',
            'telefono',
            'direccion',
            'ciudad',
            'activo',
            'observaciones',
            'cuenta_contable_uuid',
        ]
        read_only_fields = ['id']
    
    def validate(self, attrs):
        """
        # WARNING: v2.61.4: Validación completa (Zero Trust).
        
        1. Normalizar strings, números, booleanos
        2. Normalizar documento para búsqueda de duplicados
        3. Validar uniqueness: tipo_documento + numero_documento + empresa
        """
        # 1. Normalizar
        attrs = self.normalize_data(attrs)

        empresa_id = self.context.get('empresa_id')
        
        # 2. Validar documento único (idempotencia preventiva)
        numero_documento = attrs.get('numero_documento')
        tipo_documento = attrs.get('tipo_documento')
        
        if numero_documento and tipo_documento:
            # # WARNING: Normalizar documento para búsqueda (remover espacios, guiones)
            numero_documento_norm = self.normalize_document_number(numero_documento)
            attrs['numero_documento'] = numero_documento_norm
            
            # En create se permite idempotencia: el service layer hace upsert por documento.
            # En update sí validamos conflicto de unicidad excluyendo instancia actual.
            if empresa_id and self.instance is not None:
                existing = Cliente.objects.filter(
                    empresa_id=empresa_id,
                    tipo_documento=tipo_documento,
                    numero_documento=numero_documento_norm
                ).exclude(
                    pk=self.instance.pk if self.instance else None
                )
                
                if existing.exists():
                    raise serializers.ValidationError({
                        'numero_documento': [
                            f'Ya existe un cliente con el documento tipo {tipo_documento} número {numero_documento_norm} en esta empresa'
                        ]
                    })
        
        # 3. Validar campos técnicos están normalizados
        if 'nombre_comercial' in attrs and attrs['nombre_comercial']:
            attrs['nombre_comercial'] = attrs['nombre_comercial'].strip()
        
        if 'telefono' in attrs and attrs['telefono']:
            attrs['telefono'] = self.normalize_phone(attrs['telefono'])

        return attrs
