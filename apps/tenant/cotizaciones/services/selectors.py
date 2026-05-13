"""
Selectores para Cotizaciones v2.62.0 - Zero Waste Queries.
"""
from django.db.models import Q

from apps.tenant.clientes.models import Cliente
from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion
from apps.tenant.cotizaciones.models import Cotizacion

LIST_FIELDS = (
    "id", "uuid", "numero_cotizacion", "estado", "fecha_emision", 
    "fecha_vencimiento", "total_con_impuestos", "empresa_id", "created_at",
)

LIST_FK_FIELDS = (
    "cliente__razon_social", "cliente__nombre_comercial",
)

DETAIL_FIELDS = (
    "id", "uuid", "numero_cotizacion", "codigo_unico", "fecha_emision", 
    "fecha_vencimiento", "estado", "tipo_cotizacion", "iva_porcentaje", 
    "porcentaje_aiu_admin", "porcentaje_aiu_imprevistos", "porcentaje_aiu_utilidad", 
    "total_con_impuestos", "empresa_id", "created_at", "updated_at",
)

DETAIL_FK_FIELDS = (
    "cliente__razon_social", "cliente__nombre_comercial", 
    "cliente__numero_documento", "configuracion__id",
)

class CotizacionSelector:
    @staticmethod
    def get_list(empresa_id, search=None, estado=None, cliente=None):
        qs = Cotizacion.objects.filter(
            empresa_id=empresa_id
        ).select_related('cliente').only(*LIST_FIELDS, *LIST_FK_FIELDS)

        if search:
            qs = qs.filter(
                Q(numero_cotizacion__icontains=search) |
                Q(cliente__razon_social__icontains=search)
            )
        if estado:
            qs = qs.filter(estado=estado)
        if cliente:
            qs = qs.filter(cliente_id=cliente)

        return qs.order_by('-created_at')

    @staticmethod
    def get_detail(cotizacion_id, empresa_id):
        qs = Cotizacion.objects.filter(
            empresa_id=empresa_id
        ).select_related(
            'cliente', 'configuracion'
        ).prefetch_related('items').only(
            *DETAIL_FIELDS, *DETAIL_FK_FIELDS
        )
        if cotizacion_id is None:
            return qs
        return qs.filter(id=cotizacion_id).first()

    @staticmethod
    def get_detail_by_uuid(uuid, empresa_id):
        return Cotizacion.objects.filter(
            empresa_id=empresa_id, uuid=uuid
        ).select_related('cliente', 'configuracion').prefetch_related('items').only(
            *DETAIL_FIELDS, *DETAIL_FK_FIELDS
        )

    @staticmethod
    def get_clientes_activos(empresa_id):
        return Cliente.objects.filter(
            empresa_id=empresa_id,
            activo=True
        ).only('id', 'razon_social').order_by('razon_social')

    @staticmethod
    def get_configuraciones_activas(empresa_id):
        return ConfiguracionCotizacion.objects.filter(
            empresa_id=empresa_id,
            es_activo=True
        ).only('id', 'nombre_configuracion').order_by('nombre_configuracion')

    @staticmethod
    def get_configuracion_by_id(config_id, empresa_id):
        return ConfiguracionCotizacion.objects.filter(
            empresa_id=empresa_id, pk=config_id
        ).only(
            'id', 'nombre_configuracion', 'es_activo', 'dias_validez',
            'prefijo_secuencia', 'sufijo_secuencia', 'semilla_inicial', 'ultimo_numero'
        ).first()

    @staticmethod
    def get_configuraciones_lista_completa(empresa_id):
        return ConfiguracionCotizacion.objects.filter(
            empresa_id=empresa_id
        ).only(
            'id', 'nombre_configuracion', 'es_activo', 'dias_validez',
            'prefijo_secuencia', 'sufijo_secuencia', 'ultimo_numero'
        ).order_by('-es_activo', 'nombre_configuracion')
