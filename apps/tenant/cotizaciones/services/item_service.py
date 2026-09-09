import logging
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from ..models import CotizacionItem

logger = logging.getLogger(__name__)

ITEM_LIST_FIELDS = ('id', 'uuid', 'empresa_id', 'cotizacion_id', 'tipo_item', 'producto_id',
                    'servicio_id', 'descripcion', 'marca', 'referencia', 'unidad',
                    'cantidad', 'costo_unitario', 'porcentaje_utilidad',
                    'precio_unitario_venta', 'subtotal_linea', 'orden')

class CotizacionItemSelector:
    @staticmethod
    def get_list(cotizacion_id, empresa_id):
        filters = {'empresa_id': empresa_id}
        if cotizacion_id:
            if '-' in str(cotizacion_id): # Probable UUID
                filters['cotizacion__uuid'] = cotizacion_id
            else:
                filters['cotizacion_id'] = cotizacion_id
        
        return CotizacionItem.objects.filter(**filters).only(*ITEM_LIST_FIELDS).order_by('orden')

    @staticmethod
    def get_detail(empresa_id, uuid=None, pk=None):
        if uuid:
            return CotizacionItem.objects.filter(
                empresa_id=empresa_id, uuid=uuid
            ).only(*ITEM_LIST_FIELDS).first()
        return CotizacionItem.objects.filter(
            empresa_id=empresa_id, pk=pk
        ).only(*ITEM_LIST_FIELDS).first()

class CotizacionItemCRUDService:
    @staticmethod
    @transaction.atomic
    def crear(empresa_id, data):
        return CotizacionItem.objects.create(empresa_id=empresa_id, **data)

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

class CotizacionItemBusinessService:
    HUNDRED = Decimal("100")
    MONEY_Q = Decimal("0.01")

    @staticmethod
    def _q(value):
        return value.quantize(CotizacionItemBusinessService.MONEY_Q, rounding=ROUND_HALF_UP)

    @staticmethod
    def calcular_precios(cantidad, costo_unitario, porcentaje_utilidad):
        factor = Decimal('1') + (porcentaje_utilidad / CotizacionItemBusinessService.HUNDRED)
        precio_venta = CotizacionItemBusinessService._q(costo_unitario * factor)
        subtotal = CotizacionItemBusinessService._q(cantidad * precio_venta)
        return precio_venta, subtotal

    @classmethod
    @transaction.atomic
    def registrar(cls, empresa_id, data, instance=None, recalcular=True):
        from .business_service import CotizacionService  # WARNING: IMPORT LAZY — circular: business_service imports CotizacionItemBusinessService from this module

        cantidad = Decimal(str(data.get('cantidad') or 0))
        costo = Decimal(str(data.get('costo_unitario') or 0))
        utilidad = Decimal(str(data.get('porcentaje_utilidad') or 0))

        precio_venta, subtotal = cls.calcular_precios(cantidad, costo, utilidad)

        data['precio_unitario_venta'] = precio_venta
        data['subtotal_linea'] = subtotal

        # Limpieza de datos antes de persistir
        data.pop('id', None)
        data.pop('uuid', None)

        if instance:
            # Asegurar que no cambiamos la cotizacion del item
            data.pop('cotizacion', None)
            item = CotizacionItemCRUDService.actualizar(instance, data)
        else:
            item = CotizacionItemCRUDService.crear(empresa_id, data)

        # recalcular=False: usado por CotizacionService._sync_items(), que ya
        # recalcula una sola vez al final del loop completo -- antes cada
        # item del loop disparaba su propio recalculo (2 SELECT + 1 UPDATE
        # cada uno) que se descartaba de inmediato, N+1 real (hallazgo real,
        # auditoria de modernizacion, 2026-08-27). El contrato para
        # CotizacionItemViewSet (item individual via API) no cambia --
        # sigue recalculando de inmediato por defecto.
        if recalcular:
            CotizacionService.calcular_totales(item.cotizacion_id, empresa_id)

        return item

    @classmethod
    @transaction.atomic
    def eliminar_item(cls, instance, recalcular=True):
        from .business_service import CotizacionService  # WARNING: IMPORT LAZY — circular
        cotizacion_id = instance.cotizacion_id
        empresa_id = instance.empresa_id
        CotizacionItemCRUDService.eliminar(instance)
        if recalcular:
            CotizacionService.calcular_totales(cotizacion_id, empresa_id)
        return True

class CotizacionItemServiceMixin:
    @property
    def selector_class(self):
        return CotizacionItemSelector

    @property
    def business_service_class(self):
        return CotizacionItemBusinessService

    def get_qs_list(self):
        empresa_id = self.get_empresa_id()
        cotizacion_id = self.request.query_params.get('cotizacion_id')
        return self.selector_class.get_list(cotizacion_id, empresa_id)

    def get_qs_detail(self):
        empresa_id = self.get_empresa_id()
        return CotizacionItem.objects.filter(empresa_id=empresa_id).only(*ITEM_LIST_FIELDS)

    def service_crear_item(self, serializer):
        empresa_id = self.get_empresa_id()
        return self.business_service_class.registrar(empresa_id, serializer.validated_data)

    def service_actualizar_item(self, instance, serializer):
        empresa_id = self.get_empresa_id()
        return self.business_service_class.registrar(empresa_id, serializer.validated_data, instance=instance)
