from rest_framework import serializers
from ..models import Producto, Servicio
from ..configuracion.models import ConfiguracionCotizacion

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'
        read_only_fields = ('uuid', 'empresa', 'created_at', 'updated_at')

class ServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = '__all__'
        read_only_fields = ('uuid', 'empresa', 'created_at', 'updated_at')

class ConfiguracionCotizacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionCotizacion
        fields = '__all__'
        read_only_fields = ('empresa', 'created_at', 'updated_at')
