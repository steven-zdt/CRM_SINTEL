"""
Selectores para Cotizaciones v2.62.0 - Zero Waste Queries.
"""
from django.db.models import Q

from apps.tenant.clientes.models import Cliente
from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion
from apps.tenant.cotizaciones.models import Cotizacion

LIST_FIELDS = (
    "id", "uuid", "numero_cotizacion", "codigo_unico", "tipo_cotizacion",
    "estado", "fecha_emision", "fecha_vencimiento",
    "total_con_impuestos", "empresa_id", "created_at",
    "sede_id",  # DT-SEDE-04: KPI por sede
)

LIST_FK_FIELDS = (
    "cliente__razon_social", "cliente__nombre_comercial",
)

_SEDE_LIST_TRAVERSALS = (
    "sede__nombre",
)

DETAIL_FIELDS = (
    "id", "uuid", "numero_cotizacion", "codigo_unico", "fecha_emision",
    "fecha_vencimiento", "estado", "tipo_cotizacion", "iva_porcentaje",
    "porcentaje_aiu_admin", "porcentaje_aiu_imprevistos", "porcentaje_aiu_utilidad",
    "total_con_impuestos", "empresa_id", "created_at", "updated_at",
    "dias_totales", "dias_infraestructura", "dias_instalacion", "dias_configuracion", "dias_pruebas",
    "cliente_id", "configuracion_id",
    "sede_id",  # DT-SEDE-04
)

DETAIL_FK_FIELDS = (
    "cliente__razon_social", "cliente__nombre_comercial",
    "cliente__numero_documento", "cliente__uuid", "configuracion__id", "configuracion__uuid",
)

_SEDE_DETAIL_TRAVERSALS = (
    "sede__nombre", "sede__uuid",
)

class CotizacionSelector:
    @staticmethod
    def get_list(empresa_id, search=None, estado=None, cliente=None, sede_ids=None):
        """
        [OSF Fase F7] `sede_ids=None` (default) no restringe por sede -
        comportamiento identico al de antes de esta fase. El 100% de las
        Cotizaciones reales tiene sede=NULL hoy (verificado empiricamente,
        el campo era puramente informativo, DT-SEDE-04) - un registro sin
        sede queda visible para todos los alcances (filtro NULL-safe), para
        no ocultar datos existentes al activar el filtrado.
        """
        qs = Cotizacion.objects.filter(
            empresa_id=empresa_id
        ).select_related(
            'cliente', 'sede'
        ).only(*LIST_FIELDS, *LIST_FK_FIELDS, *_SEDE_LIST_TRAVERSALS)

        if sede_ids is not None:
            qs = qs.filter(Q(sede_id__isnull=True) | Q(sede_id__in=sede_ids))
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
    def get_detail(_cotizacion_id, empresa_id, sede_ids=None):
        """Returns base queryset filtered by empresa_id (DRF get_object applies uuid filter).

        [OSF Fase F13] `sede_ids=None` (default) no restringe - mismo
        criterio NULL-safe de F7 (get_list). Antes de esta fase, retrieve/
        update/exportar-pdf/render-offcanvas-*/recalcular en CotizacionViewSet
        solo filtraban por empresa_id (via get_qs_detail() sin sede_ids) -
        mismo gap que F11/F13(gastos) encontraron y corrigieron.
        """
        qs = Cotizacion.objects.filter(
            empresa_id=empresa_id
        ).select_related(
            'cliente', 'configuracion', 'sede'
        ).prefetch_related('items').only(
            *DETAIL_FIELDS, *DETAIL_FK_FIELDS, *_SEDE_DETAIL_TRAVERSALS
        )
        if sede_ids is not None:
            qs = qs.filter(Q(sede_id__isnull=True) | Q(sede_id__in=sede_ids))
        return qs

    @staticmethod
    def get_detail_by_uuid(uuid, empresa_id, sede_ids=None):
        """[OSF Fase F13] `sede_ids=None` (default) no restringe - mismo
        criterio NULL-safe. Usado directamente por `ui_views.py` (paginas de
        editor/detalle fuera del ViewSet DRF) y por `CotizacionBridge`
        (facturas, F9 - ese consumidor ya hace su propio chequeo NULL-safe
        post-fetch, no pasa `sede_ids` aqui, comportamiento sin cambios)."""
        qs = Cotizacion.objects.filter(
            empresa_id=empresa_id, uuid=uuid
        ).select_related(
            'cliente', 'configuracion', 'sede'
        ).prefetch_related('items').only(
            *DETAIL_FIELDS, *DETAIL_FK_FIELDS, *_SEDE_DETAIL_TRAVERSALS
        )
        if sede_ids is not None:
            qs = qs.filter(Q(sede_id__isnull=True) | Q(sede_id__in=sede_ids))
        return qs

    @staticmethod
    def get_clientes_activos(empresa_id):
        return Cliente.objects.filter(
            empresa_id=empresa_id,
            activo=True
        ).only('id', 'uuid', 'razon_social').order_by('razon_social')

    @staticmethod
    def get_configuraciones_activas(empresa_id):
        return ConfiguracionCotizacion.objects.filter(
            empresa_id=empresa_id,
            es_activo=True
        ).only('id', 'uuid', 'nombre_configuracion').order_by('nombre_configuracion')

    @staticmethod
    def get_configuracion_by_id(config_id, empresa_id):
        return ConfiguracionCotizacion.objects.filter(
            empresa_id=empresa_id, pk=config_id
        ).only(
            'id', 'uuid', 'nombre_configuracion', 'es_activo', 'dias_validez',
            'prefijo_secuencia', 'sufijo_secuencia', 'semilla_inicial', 'ultimo_numero'
        ).first()

    @staticmethod
    def get_configuracion_by_uuid(uuid, empresa_id):
        return ConfiguracionCotizacion.objects.filter(
            empresa_id=empresa_id, uuid=uuid
        ).only(
            'id', 'uuid', 'nombre_configuracion', 'es_activo', 'dias_validez',
            'prefijo_secuencia', 'sufijo_secuencia', 'semilla_inicial', 'ultimo_numero'
        ).first()

    @staticmethod
    def get_configuraciones_lista_completa(empresa_id):
        return ConfiguracionCotizacion.objects.filter(
            empresa_id=empresa_id
        ).only(
            'id', 'uuid', 'nombre_configuracion', 'es_activo', 'dias_validez',
            'prefijo_secuencia', 'sufijo_secuencia', 'ultimo_numero'
        ).order_by('-es_activo', 'nombre_configuracion')
