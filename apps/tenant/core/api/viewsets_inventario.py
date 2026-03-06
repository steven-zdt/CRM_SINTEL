from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.conf import settings
# ⚠️ ESTÁNDAR v2.40: Importar servicios directamente desde la app de inventario (SSoT)
from apps.tenant.inventario.services import (
    calcular_stock,
    registrar_entrada,
)
from apps.tenant.inventario.models import Producto, Servicio
from apps.tenant.empresa.models import Empresa

# En dev: usar UnsafeSessionAuthentication si existe
try:
    from apps.tenant.api.authentication import UnsafeSessionAuthentication
    _UnsafeSessionAuthentication = UnsafeSessionAuthentication
except Exception:
    _UnsafeSessionAuthentication = None


class CoreInventarioViewSet(viewsets.ViewSet):
    """
    Orquestador de inventario para Workspace:
    - GET /api/v1/core/inventario/resumen/
    - GET /api/v1/core/inventario/catalogo/?search=&tipo=&activos=&limit=&offset=
    - GET /api/v1/core/inventario/stock/{id}/
    - POST /api/v1/core/inventario/entrada/ {catalogo, cantidad, costo_unitario?, referencia?}
    - POST /api/v1/core/inventario/vincular-venta/ {item_factura, catalogo, cantidad?, referencia?}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_authenticators(self):
        if settings.DEBUG and _UnsafeSessionAuthentication:
            return [_UnsafeSessionAuthentication()]
        return super().get_authenticators()

    @action(detail=False, methods=["get"], url_path="resumen")
    def resumen(self, request):
        """
        ⚠️ ESTÁNDAR v2.40: Resumen de inventario usando servicios directos de la app.
        Retorna estadísticas básicas de productos, servicios y activos.
        """
        from apps.tenant.inventario.services import (
            qs_producto_list, qs_servicio_list, qs_activo_list
        )
        empresa = Empresa.objects.first()
        if not empresa:
            return Response({"error": "No se encontró empresa"}, status=status.HTTP_400_BAD_REQUEST)
        
        productos = qs_producto_list().filter(empresa=empresa, activo=True)
        servicios = qs_servicio_list().filter(empresa=empresa, activo=True)
        activos = qs_activo_list().filter(empresa=empresa, activo=True)
        
        data = {
            "total_productos": productos.count(),
            "total_servicios": servicios.count(),
            "total_activos": activos.count(),
        }
        return Response(data)

    @action(detail=False, methods=["get"], url_path="catalogo")
    def catalogo(self, request):
        """
        ⚠️ ESTÁNDAR v2.40: Lista de catálogo (productos y servicios) usando servicios directos.
        Parámetros: search, tipo (PRODUCTO|SERVICIO), activos (true|false), limit, offset
        """
        from apps.tenant.inventario.services import (
            qs_producto_list, qs_servicio_list
        )
        search = request.query_params.get("search", "").strip()
        tipo = request.query_params.get("tipo", "").upper()
        activos_param = request.query_params.get("activos")
        limit = int(request.query_params.get("limit", 20))
        offset = int(request.query_params.get("offset", 0))
        
        empresa = Empresa.objects.first()
        if not empresa:
            return Response({"error": "No se encontró empresa"}, status=status.HTTP_400_BAD_REQUEST)
        
        items = []
        if not tipo or tipo == "PRODUCTO":
            qs = qs_producto_list().filter(empresa=empresa)
            if activos_param is not None:
                activos = str(activos_param).lower() in ("1", "true", "yes")
                qs = qs.filter(activo=activos)
            if search:
                qs = qs.filter(nombre__icontains=search)
            productos = qs[offset:offset+limit]
            for p in productos:
                items.append({"id": p.id, "nombre": p.nombre, "tipo": "PRODUCTO", "codigo": p.codigo})
        
        if not tipo or tipo == "SERVICIO":
            qs = qs_servicio_list().filter(empresa=empresa)
            if activos_param is not None:
                activos = str(activos_param).lower() in ("1", "true", "yes")
                qs = qs.filter(activo=activos)
            if search:
                qs = qs.filter(nombre__icontains=search)
            servicios = qs[offset:offset+limit]
            for s in servicios:
                items.append({"id": s.id, "nombre": s.nombre, "tipo": "SERVICIO", "codigo": s.codigo})
        
        return Response({"items": items, "count": len(items)})

    @action(detail=True, methods=["get"], url_path="stock")
    def stock(self, request, pk=None):
        """
        ⚠️ ESTÁNDAR v2.40: Obtiene stock de un producto usando servicios directos.
        """
        try:
            stock = calcular_stock(int(pk))
            return Response({"producto_id": int(pk), "stock": float(stock)})
        except Producto.DoesNotExist:
            return Response({"error": "Producto no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["post"], url_path="entrada")
    def entrada(self, request):
        """
        ⚠️ ESTÁNDAR v2.40: Registra entrada de producto usando servicios directos.
        Payload: { "producto": <id>, "cantidad": <decimal>, "costo_unitario": <decimal>, "referencia": <str> }
        """
        from decimal import Decimal
        payload = request.data
        producto_id = payload.get("producto") or payload.get("catalogo")  # Compatibilidad legacy
        if not producto_id:
            return Response({"error": "Falta 'producto' en el payload"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            mov = registrar_entrada(
                producto_id=int(producto_id),
                cantidad=Decimal(str(payload.get("cantidad", 0))),
                costo_unitario=Decimal(str(payload.get("costo_unitario", 0))) if payload.get("costo_unitario") else None,
                referencia=payload.get("referencia"),
                usuario=request.user if request.user and request.user.is_authenticated else None,
            )
            return Response({
                "id": mov.id,
                "producto_id": mov.producto_id,
                "cantidad": float(mov.cantidad),
                "tipo": mov.tipo,
            }, status=status.HTTP_201_CREATED)
        except Producto.DoesNotExist:
            return Response({"error": "Producto no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="vincular-venta")
    def vincular_venta(self, request):
        """
        ⚠️ ESTÁNDAR v2.40: Vincula venta con producto usando servicios directos.
        Payload: { "item_factura": <id>, "producto": <id>, "cantidad": <decimal>, "referencia": <str> }
        
        ⚠️ DEPRECADO: Esta funcionalidad está deshabilitada por acoplamiento prohibido.
        Las facturas son documentos históricos inmutables y no deben disparar side-effects síncronos acoplados.
        """
        # TODO: Refactorizar a evento asíncrono o materialización desde DTO
        # La vinculación de facturas con inventario debe hacerse mediante:
        # 1. Eventos asíncronos (Celery) cuando se guarda una factura
        # 2. Materialización desde DTO en lugar de side-effects síncronos
        # 3. Endpoint dedicado que no acople inventario con facturas directamente
        
        return Response({
            "error": "funcionalidad_deshabilitada",
            "message": "La vinculación directa de facturas con inventario está deshabilitada por arquitectura v2.40. "
                       "Las facturas son documentos históricos inmutables y no deben disparar side-effects síncronos acoplados. "
                       "Refactorizar a evento asíncrono o materialización desde DTO."
        }, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=False, methods=["post"], url_path="smoke/run", permission_classes=[IsAdminUser])
    def smoke_run(self, request):
        """
        ⚠️ ESTÁNDAR v2.40: Smoke tests deshabilitados - usar tests unitarios en su lugar.
        """
        if not settings.DEBUG:
            return Response({"detail": "Smoke tests solo disponibles en DEBUG."}, status=status.HTTP_403_FORBIDDEN)
        return Response({
            "success": False,
            "message": "Smoke tests deshabilitados. Usar tests unitarios en su lugar."
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
