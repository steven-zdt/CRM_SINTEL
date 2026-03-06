"""
Core API Views para Contabilidad (Cuentas, Asientos, Movimientos CRUD).

⚠️ v2.30: Core API como orquestador único de la UI privada.
- Cuentas: GET/POST /api/v1/core/contabilidad/cuentas/, PATCH/DELETE /api/v1/core/contabilidad/cuentas/{id}/
- Asientos: GET/POST /api/v1/core/contabilidad/asientos/, PATCH/DELETE /api/v1/core/contabilidad/asientos/{id}/, POST /api/v1/core/contabilidad/asientos/{id}/aprobar/
- Movimientos: GET/POST /api/v1/core/contabilidad/movimientos/, PATCH/DELETE /api/v1/core/contabilidad/movimientos/{id}/

⚠️ POLÍTICA:
- SessionAuthentication + CSRF (UI privada)
- IsAuthenticated; la membresía por tenant ya la valida el TenantAwareBackend
- JSON-only global (sin BrowsableAPIRenderer)
- Usa Core Service Adapter (apps/tenant/core/services/contabilidad_adapter)
- Paginación DRF siempre; filtros/orden whitelisteados
"""
import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication

logger = logging.getLogger(__name__)


# ============================================================================
# CUENTAS CONTABLES
# ============================================================================

class CoreContabilidadCuentasListCreateAPIView(APIView):
    """
    GET: Lista cuentas contables (paginado)
    POST: Crea una cuenta contable
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """
        GET /api/v1/core/contabilidad/cuentas/
        
        Lista cuentas contables (paginado).
        Query params: page, page_size, tipo, activa, cuenta_padre, search, ordering
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_cuentas_list
            
            # Extraer filtros de query params
            filters = {}
            if 'tipo' in request.query_params:
                filters['tipo'] = request.query_params['tipo']
            if 'activa' in request.query_params:
                filters['activa'] = request.query_params['activa'].lower() == 'true'
            if 'cuenta_padre' in request.query_params:
                filters['cuenta_padre'] = int(request.query_params['cuenta_padre'])
            if 'search' in request.query_params:
                filters['search'] = request.query_params['search']
            
            ordering = request.query_params.get('ordering')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            result = core_cuentas_list(filters=filters, ordering=ordering, page=page, page_size=page_size)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "CoreContabilidadCuentasListCreateAPIView GET: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al listar cuentas."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, *args, **kwargs):
        """
        POST /api/v1/core/contabilidad/cuentas/
        
        Crea una cuenta contable.
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_cuentas_create
            
            data = request.data.copy()
            result = core_cuentas_create(data)
            return Response(result, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "CoreContabilidadCuentasListCreateAPIView POST: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al crear la cuenta."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CoreContabilidadCuentaRetrieveUpdateDestroyAPIView(APIView):
    """
    GET: Obtiene una cuenta contable
    PATCH: Actualiza una cuenta contable
    DELETE: Elimina una cuenta contable
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, cuenta_id, *args, **kwargs):
        """
        GET /api/v1/core/contabilidad/cuentas/{id}/
        
        Obtiene una cuenta contable.
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_cuentas_list
            
            # Obtener la cuenta específica desde la lista
            result = core_cuentas_list(page=1, page_size=1000)  # Obtener todas para buscar
            cuenta = next((c for c in result['results'] if c['id'] == cuenta_id), None)
            
            if not cuenta:
                return Response(
                    {"detail": "Cuenta no encontrada."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(cuenta, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "CoreContabilidadCuentaRetrieveUpdateDestroyAPIView GET: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al obtener la cuenta."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, cuenta_id, *args, **kwargs):
        """
        PATCH /api/v1/core/contabilidad/cuentas/{id}/
        
        Actualiza una cuenta contable.
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_cuentas_update
            
            data = request.data.copy()
            result = core_cuentas_update(cuenta_id, data)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "CoreContabilidadCuentaRetrieveUpdateDestroyAPIView PATCH: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al actualizar la cuenta."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, cuenta_id, *args, **kwargs):
        """
        DELETE /api/v1/core/contabilidad/cuentas/{id}/
        
        Elimina una cuenta contable.
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_cuentas_delete
            
            core_cuentas_delete(cuenta_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(
                "CoreContabilidadCuentaRetrieveUpdateDestroyAPIView DELETE: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al eliminar la cuenta."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# ASIENTOS CONTABLES
# ============================================================================

class CoreContabilidadAsientosListCreateAPIView(APIView):
    """
    GET: Lista asientos contables (paginado)
    POST: Crea un asiento contable
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """
        GET /api/v1/core/contabilidad/asientos/
        
        Lista asientos contables (paginado).
        Query params: page, page_size, estado, fecha, search, ordering
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_asientos_list
            
            # Extraer filtros de query params
            filters = {}
            if 'estado' in request.query_params:
                filters['estado'] = request.query_params['estado']
            if 'fecha' in request.query_params:
                filters['fecha'] = request.query_params['fecha']
            if 'search' in request.query_params:
                filters['search'] = request.query_params['search']
            
            ordering = request.query_params.get('ordering')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            result = core_asientos_list(filters=filters, ordering=ordering, page=page, page_size=page_size)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "CoreContabilidadAsientosListCreateAPIView GET: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al listar asientos."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, *args, **kwargs):
        """
        POST /api/v1/core/contabilidad/asientos/
        
        Crea un asiento contable.
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_asientos_create
            
            data = request.data.copy()
            result = core_asientos_create(data)
            return Response(result, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "CoreContabilidadAsientosListCreateAPIView POST: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al crear el asiento."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CoreContabilidadAsientoRetrieveUpdateDestroyAPIView(APIView):
    """
    GET: Obtiene un asiento contable
    PATCH: Actualiza un asiento contable
    DELETE: Elimina un asiento contable
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, asiento_id, *args, **kwargs):
        """
        GET /api/v1/core/contabilidad/asientos/{id}/
        
        Obtiene un asiento contable.
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_asientos_list
            
            # Obtener el asiento específico desde la lista
            result = core_asientos_list(page=1, page_size=1000)  # Obtener todos para buscar
            asiento = next((a for a in result['results'] if a['id'] == asiento_id), None)
            
            if not asiento:
                return Response(
                    {"detail": "Asiento no encontrado."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(asiento, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "CoreContabilidadAsientoRetrieveUpdateDestroyAPIView GET: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al obtener el asiento."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, asiento_id, *args, **kwargs):
        """
        PATCH /api/v1/core/contabilidad/asientos/{id}/
        
        Actualiza un asiento contable.
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_asientos_update
            
            data = request.data.copy()
            result = core_asientos_update(asiento_id, data)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "CoreContabilidadAsientoRetrieveUpdateDestroyAPIView PATCH: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al actualizar el asiento."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, asiento_id, *args, **kwargs):
        """
        DELETE /api/v1/core/contabilidad/asientos/{id}/
        
        Elimina un asiento contable.
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_asientos_delete
            
            core_asientos_delete(asiento_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(
                "CoreContabilidadAsientoRetrieveUpdateDestroyAPIView DELETE: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al eliminar el asiento."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CoreContabilidadAsientoAprobarAPIView(APIView):
    """
    POST: Aprueba un asiento contable
    
    ⚠️ VALIDACIÓN: Un asiento solo puede ser aprobado si total_debe == total_haber.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, asiento_id, *args, **kwargs):
        """
        POST /api/v1/core/contabilidad/asientos/{id}/aprobar/
        
        Aprueba un asiento contable.
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_asientos_aprobar
            
            result = core_asientos_aprobar(asiento_id)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "CoreContabilidadAsientoAprobarAPIView POST: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al aprobar el asiento."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# MOVIMIENTOS CONTABLES
# ============================================================================

class CoreContabilidadMovimientosListCreateAPIView(APIView):
    """
    GET: Lista movimientos contables (paginado)
    POST: Crea un movimiento contable
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """
        GET /api/v1/core/contabilidad/movimientos/
        
        Lista movimientos contables (paginado).
        Query params: page, page_size, asiento, cuenta, search, ordering
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_movimientos_list
            
            # Extraer filtros de query params
            filters = {}
            if 'asiento' in request.query_params:
                filters['asiento'] = int(request.query_params['asiento'])
            if 'cuenta' in request.query_params:
                filters['cuenta'] = int(request.query_params['cuenta'])
            if 'search' in request.query_params:
                filters['search'] = request.query_params['search']
            
            ordering = request.query_params.get('ordering')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            result = core_movimientos_list(filters=filters, ordering=ordering, page=page, page_size=page_size)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "CoreContabilidadMovimientosListCreateAPIView GET: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al listar movimientos."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, *args, **kwargs):
        """
        POST /api/v1/core/contabilidad/movimientos/
        
        Crea un movimiento contable.
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_movimientos_create
            
            data = request.data.copy()
            result = core_movimientos_create(data)
            return Response(result, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "CoreContabilidadMovimientosListCreateAPIView POST: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al crear el movimiento."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CoreContabilidadMovimientoRetrieveUpdateDestroyAPIView(APIView):
    """
    GET: Obtiene un movimiento contable
    PATCH: Actualiza un movimiento contable
    DELETE: Elimina un movimiento contable
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, movimiento_id, *args, **kwargs):
        """
        GET /api/v1/core/contabilidad/movimientos/{id}/
        
        Obtiene un movimiento contable.
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_movimientos_list
            
            # Obtener el movimiento específico desde la lista
            result = core_movimientos_list(page=1, page_size=1000)  # Obtener todos para buscar
            movimiento = next((m for m in result['results'] if m['id'] == movimiento_id), None)
            
            if not movimiento:
                return Response(
                    {"detail": "Movimiento no encontrado."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(movimiento, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "CoreContabilidadMovimientoRetrieveUpdateDestroyAPIView GET: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al obtener el movimiento."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, movimiento_id, *args, **kwargs):
        """
        PATCH /api/v1/core/contabilidad/movimientos/{id}/
        
        Actualiza un movimiento contable.
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_movimientos_update
            
            data = request.data.copy()
            result = core_movimientos_update(movimiento_id, data)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "CoreContabilidadMovimientoRetrieveUpdateDestroyAPIView PATCH: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al actualizar el movimiento."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, movimiento_id, *args, **kwargs):
        """
        DELETE /api/v1/core/contabilidad/movimientos/{id}/
        
        Elimina un movimiento contable.
        """
        try:
            from apps.tenant.core.services.contabilidad_adapter import core_movimientos_delete
            
            core_movimientos_delete(movimiento_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(
                "CoreContabilidadMovimientoRetrieveUpdateDestroyAPIView DELETE: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al eliminar el movimiento."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
