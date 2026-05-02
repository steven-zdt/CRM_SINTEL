"""
WARNING: DEPRECATED v2.40: Este archivo está deprecado.

Use CuentaContableViewSet.datatables() y AsientoContableViewSet.datatables() actions en su lugar.
Este archivo será removido en v2.41.

Endpoints DataTables server-side para Contabilidad.

WARNING: v2.37: Usa LIST_FIELDS y qs_list() del service.
Usa DataTableSpec/DataTableServer según Arquitectura v2.37.
"""

from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.shared.datatable import DataTableServer, DataTableSpec
from apps.tenant.contabilidad.api.serializers import (
    AsientoContableListSerializer,
    CuentaContableListSerializer,
)
from apps.tenant.contabilidad.services.services import (
    qs_asiento_list,
    qs_cuenta_list,
)


@api_view(['POST'])
@authentication_classes([JWTAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def cuentas_contables_dt(request: Request):
    """
    Endpoint DataTables server-side para listado de cuentas contables.
    POST /api/v1/dt/cuentas-contables/
    Retorna JSON DataTables: { draw, recordsTotal, recordsFiltered, data }
    
    WARNING: v2.37: Usa CUENTA_LIST_FIELDS y qs_cuenta_list() del service.
    """
    base_qs = qs_cuenta_list()
    
    spec = DataTableSpec(
        fields_map={
            0: "codigo",
            1: "nombre",
            2: "tipo",
            3: "activa",
            4: "created_at",
        },
        search_fields=[
            "codigo",
            "nombre",
        ],
        base_qs=base_qs,
        serializer=CuentaContableListSerializer,
    )
    
    return DataTableServer(spec).handle(request)


@api_view(['POST'])
@authentication_classes([JWTAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def asientos_contables_dt(request: Request):
    """
    Endpoint DataTables server-side para listado de asientos contables.
    POST /api/v1/dt/asientos-contables/
    Retorna JSON DataTables: { draw, recordsTotal, recordsFiltered, data }
    
    WARNING: v2.37: Usa ASIENTO_LIST_FIELDS y qs_asiento_list() del service.
    """
    base_qs = qs_asiento_list()
    
    def extra_filter(req, qs):
        data = req.data if hasattr(req, 'data') else {}
        
        if estado := data.get('estado'):
            qs = qs.filter(estado=estado)
        
        if fecha_desde := data.get('fecha__gte'):
            qs = qs.filter(fecha__gte=fecha_desde)
        
        if fecha_hasta := data.get('fecha__lte'):
            qs = qs.filter(fecha__lte=fecha_hasta)
        
        return qs
    
    spec = DataTableSpec(
        fields_map={
            0: "numero",
            1: "fecha",
            2: "descripcion",
            3: "estado",
            4: "total_debe",
            5: "total_haber",
        },
        search_fields=[
            "numero",
            "descripcion",
        ],
        base_qs=base_qs,
        serializer=AsientoContableListSerializer,
        extra_filter=extra_filter,
    )
    
    return DataTableServer(spec).handle(request)
