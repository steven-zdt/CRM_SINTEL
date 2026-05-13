import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import Q

from ..models import Servicio

logger = logging.getLogger(__name__)

SERVICIO_LIST_FIELDS = ('id', 'uuid', 'empresa_id', 'nombre', 'precio_venta', 'activo', 'created_at')
SERVICIO_DETAIL_FIELDS = SERVICIO_LIST_FIELDS

class ServicioSelector:
    @staticmethod
    def get_list(empresa_id, search=None, activo=None):
        qs = Servicio.objects.filter(empresa_id=empresa_id)
        if search:
            qs = qs.filter(nombre__icontains=search)
        if activo is not None:
            qs = qs.filter(activo=activo)
        return qs.only(*SERVICIO_LIST_FIELDS).order_by('-created_at')

    @staticmethod
    def get_detail(empresa_id, pk=None, uuid=None):
        if uuid:
            return Servicio.objects.filter(empresa_id=empresa_id, uuid=uuid).only(*SERVICIO_DETAIL_FIELDS).first()
        return Servicio.objects.filter(empresa_id=empresa_id, pk=pk).only(*SERVICIO_DETAIL_FIELDS).first()

class ServicioCRUDService:
    @staticmethod
    @transaction.atomic
    def crear(empresa_id, data):
        return Servicio.objects.create(empresa_id=empresa_id, **data)

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

class ServicioBusinessService:
    @staticmethod
    def registrar(empresa_id, data, instance=None):
        if instance:
            return ServicioCRUDService.actualizar(instance, data)
        return ServicioCRUDService.crear(empresa_id, data)

class ServicioServiceMixin:
    @property
    def selector_class(self):
        return ServicioSelector

    @property
    def business_service_class(self):
        return ServicioBusinessService

    def get_qs_list(self):
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search')
        return self.selector_class.get_list(empresa_id, search=search)

    def get_qs_detail(self):
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_list(empresa_id)

    def service_crear_servicio(self, serializer):
        empresa_id = self.get_empresa_id()
        return self.business_service_class.registrar(empresa_id, serializer.validated_data)

    def service_actualizar_servicio(self, instance, serializer):
        empresa_id = self.get_empresa_id()
        return self.business_service_class.registrar(empresa_id, serializer.validated_data, instance=instance)
