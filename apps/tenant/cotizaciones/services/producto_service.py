import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from ..models import Producto
from apps.tenant.api.utils import resolve_tenant_empresa

logger = logging.getLogger(__name__)

PRODUCTO_LIST_FIELDS = ('id', 'uuid', 'empresa_id', 'codigo', 'nombre', 'marca', 
                        'referencia', 'unidad', 'precio_venta', 'activo', 'created_at')
PRODUCTO_DETAIL_FIELDS = PRODUCTO_LIST_FIELDS

class ProductoSelector:
    @staticmethod
    def get_list(empresa_id, search=None, activo=None):
        qs = Producto.objects.filter(empresa_id=empresa_id)
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) | 
                Q(codigo__icontains=search) | 
                Q(marca__icontains=search) | 
                Q(referencia__icontains=search)
            )
        if activo is not None:
            qs = qs.filter(activo=activo)
        return qs.only(*PRODUCTO_LIST_FIELDS).order_by('-created_at')

    @staticmethod
    def get_detail(empresa_id, pk=None, uuid=None):
        if uuid:
            return Producto.objects.filter(empresa_id=empresa_id, uuid=uuid).only(*PRODUCTO_DETAIL_FIELDS).first()
        return Producto.objects.filter(empresa_id=empresa_id, pk=pk).only(*PRODUCTO_DETAIL_FIELDS).first()

class ProductoCRUDService:
    @staticmethod
    @transaction.atomic
    def crear(empresa_id, data):
        return Producto.objects.create(empresa_id=empresa_id, **data)

    @staticmethod
    @transaction.atomic
    def actualizar(instance, data):
        for attr, value in data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    @staticmethod
    @transaction.atomic
    def eliminar(instance):
        instance.delete()
        return True

class ProductoBusinessService:
    @staticmethod
    def registrar(empresa_id, data, instance=None):
        # DSV and logic
        codigo = data.get('codigo')
        if codigo:
            exists = Producto.objects.filter(empresa_id=empresa_id, codigo=codigo)
            if instance:
                exists = exists.exclude(pk=instance.pk)
            if exists.exists():
                raise ValueError(f"El código {codigo} ya está en uso.")
        
        if instance:
            return ProductoCRUDService.actualizar(instance, data)
        return ProductoCRUDService.crear(empresa_id, data)

class ProductoServiceMixin:
    @property
    def selector_class(self):
        return ProductoSelector

    @property
    def business_service_class(self):
        return ProductoBusinessService

    def get_qs_list(self):
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search')
        return self.selector_class.get_list(empresa_id, search=search)

    def get_qs_detail(self):
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_list(empresa_id)

    def service_crear_producto(self, serializer):
        empresa_id = self.get_empresa_id()
        return self.business_service_class.registrar(empresa_id, serializer.validated_data)

    def service_actualizar_producto(self, instance, serializer):
        empresa_id = self.get_empresa_id()
        return self.business_service_class.registrar(empresa_id, serializer.validated_data, instance=instance)
