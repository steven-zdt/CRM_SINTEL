"""
⚠️ DEPRECATED v2.40: Este archivo está deprecado.

Use CuentaContableViewSet.datatables() y AsientoContableViewSet.datatables() actions en su lugar.
Este archivo será removido en v2.41.

Endpoints DataTables server-side para Contabilidad.

⚠️ v2.37: Usa LIST_FIELDS y qs_list() del service.
Usa DataTableSpec/DataTableServer según Arquitectura v2.37.
"""

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.request import Request
from apps.shared.datatable import DataTableSpec, DataTableServer
from apps.tenant.contabilidad.api.serializers import (
    CuentaContableListSerializer,
    AsientoContableListSerializer,
)
# Importar directamente desde services.py para evitar circularidad
import importlib.util
from pathlib import Path
import sys

services_py_path = Path(__file__).parent.parent / 'services.py'
if services_py_path.exists():
    module_name = 'apps.tenant.contabilidad.services_module'
    if module_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(module_name, services_py_path)
        services_module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = services_module
        spec.loader.exec_module(services_module)
    else:
        services_module = sys.modules[module_name]
    
    CUENTA_LIST_FIELDS = services_module.CUENTA_LIST_FIELDS
    qs_cuenta_list = services_module.qs_cuenta_list
    ASIENTO_LIST_FIELDS = services_module.ASIENTO_LIST_FIELDS
    qs_asiento_list = services_module.qs_asiento_list
else:
    raise ImportError(f"No se pudo cargar services.py desde {services_py_path}")


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def cuentas_contables_dt(request: Request):
    """
    Endpoint DataTables server-side para listado de cuentas contables.
    POST /api/v1/dt/cuentas-contables/
    Retorna JSON DataTables: { draw, recordsTotal, recordsFiltered, data }
    
    ⚠️ v2.37: Usa CUENTA_LIST_FIELDS y qs_cuenta_list() del service.
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
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def asientos_contables_dt(request: Request):
    """
    Endpoint DataTables server-side para listado de asientos contables.
    POST /api/v1/dt/asientos-contables/
    Retorna JSON DataTables: { draw, recordsTotal, recordsFiltered, data }
    
    ⚠️ v2.37: Usa ASIENTO_LIST_FIELDS y qs_asiento_list() del service.
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
