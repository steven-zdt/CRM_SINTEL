"""
ViewSets DRF para gastos (JSON-only).

⚠️ v2.40: INMUTABILIDAD ESTRICTA y SSoT Empresa.
- Los campos de listado usan prefijos 'ds_' alineados con GastoListSerializer.
- POST solo para crear nuevos gastos (Inmutabilidad legal).
- Acción 'anular' implementada para revertir efectos financieros.
"""
import logging
from decimal import Decimal
from rest_framework import viewsets, mixins, filters, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Max

from apps.tenant.api.permissions import IsTenantMember, IsTenantAdminOrReadOnly
from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.gastos.models import Gasto, ResolucionDIAN, DocumentoSoporte
from apps.tenant.gastos.services import (
    qs_list, 
    qs_detail, 
    get_gastos_summary, 
    obtener_resolucion_vigente,
    obtener_siguiente_numero_soporte, 
    normalize_document_number, 
    anular_gasto_service,
    desactivar_gasto_service,  # ⚠️ v2.40: Función para desactivar gasto
    qs_resolucion_list,
    qs_resolucion_detail,
    crear_resolucion,
    desactivar_resolucion,
    puede_eliminar_resolucion,
    calcular_retenciones  # ⚠️ v2.40: Función para calcular retenciones
)
from .serializers import (
    GastoListSerializer, GastoDetailSerializer, 
    ResolucionDIANCreateSerializer,  # ⚠️ v2.60: Serializer para crear resoluciones
    ResolucionDIANNestedSerializer,
    ResolucionDIANListSerializer,
    ResolucionDIANDetailSerializer
)

logger = logging.getLogger(__name__)

class GastoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet para gastos (v2.40).
    Prohíbe PUT/PATCH para garantizar integridad del Documento Soporte.
    
    ⚠️ CRÍTICO: El queryset debe estar definido en tiempo de clase para que DRF
    pueda registrar las rutas correctamente. Se sobrescribe en get_queryset()
    para optimización según la acción.
    """
    # ⚠️ CRÍTICO: queryset requerido por DRF para registro de rutas
    # Se usa get_queryset() para optimización, pero este debe existir
    # ⚠️ IMPORTANTE: Gasto.objects.all() es necesario para que DRF pueda registrar las rutas
    queryset = Gasto.objects.all()  # Base queryset para registro de rutas
    serializer_class = GastoDetailSerializer  # ⚠️ CRÍTICO: DRF necesita serializer_class para generar rutas (se sobrescribe en get_serializer_class())
    pagination_class = StandardResultsSetPagination  # ⚠️ v2.40: Paginación para Tabulator
    http_method_names = ['get', 'post', 'delete', 'head', 'options'] # Bloquea PUT/PATCH
    
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["periodo", "centro_costo", "categoria_contable"]
    search_fields = ["descripcion", "documento_soporte__vendedor_nombre", "documento_soporte__prefijo"]
    ordering_fields = ["documento_soporte__fecha", "documento_soporte__total"]
    ordering = ["-documento_soporte__fecha"]

    def get_queryset(self):
        """
        Usa las funciones del service layer para optimizar el QuerySet.
        
        ⚠️ CRÍTICO: Este método sobrescribe el queryset de clase para optimización.
        Si no hay acción definida (tiempo de registro), retorna queryset base.
        ⚠️ v2.40: Soporta búsqueda con parámetro ?search=
        
        ⚠️ CRÍTICO: INCLUYE TODOS LOS DOCUMENTOS (anulados y no anulados).
        - Los documentos anulados DEBEN aparecer en la lista para mantener la secuencia de consecutivos.
        - El consecutivo prevalece en la lista, incluso si el documento está anulado.
        - Solo el summary (get_gastos_summary) excluye documentos anulados del cálculo financiero.
        """
        # Si no hay acción (tiempo de registro de rutas), retornar queryset base
        if not hasattr(self, 'action') or self.action is None:
            return Gasto.objects.all()
        
        # Obtener parámetro de búsqueda
        search = self.request.query_params.get('search', None)
        
        if self.action == "list":
            # ⚠️ CRÍTICO: qs_list() NO filtra por anulado=False, incluye TODOS los documentos
            return qs_list(search=search)
        elif self.action == "retrieve":
            return qs_detail()
        else:
            # Fallback: queryset completo para otras acciones
            return Gasto.objects.all()

    def get_serializer_class(self):
        """Alineación v2.40: ListSerializer usa campos aplanados 'ds_'."""
        if self.action == "list":
            return GastoListSerializer
        return GastoDetailSerializer
    
    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/gastos/
        Lista paginada de gastos (Tabulator v2.40).
        Soporta ?search= para búsqueda y ?page= para paginación.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo Gasto con DocumentoSoporte.
        
        ⚠️ v2.40: Usa automáticamente la resolución vigente si no se proporciona.
        """
        try:
            from apps.tenant.empresa.models import Empresa
            from apps.tenant.gastos.models import DocumentoSoporte
            from django.db import transaction
            from decimal import Decimal
            
            # Obtener empresa del tenant (SSoT)
            empresa = Empresa.objects.first()
            if not empresa:
                return Response(
                    {
                        "error": "empresa_no_configurada",
                        "message": "No hay empresa configurada para este tenant.",
                        "missing_fields": ["empresa"]
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )
            
            # ⚠️ v2.60: Permitir que el usuario seleccione la resolución desde el formulario
            # Si viene resolucion_dian en el request, usarla; si no, usar la vigente por defecto
            data = request.data.copy()
            resolucion_id = data.get('resolucion_dian')
            
            if resolucion_id:
                # ⚠️ v2.60: Usuario seleccionó una resolución específica
                try:
                    resolucion = ResolucionDIAN.objects.filter(
                        empresa=empresa,
                        id=resolucion_id
                    ).first()
                    
                    if not resolucion:
                        return Response(
                            {
                                "error": "resolucion_no_encontrada",
                                "message": f"La resolución seleccionada (ID: {resolucion_id}) no existe o no pertenece a este tenant.",
                                "missing_fields": ["resolucion_dian"]
                            },
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY
                        )
                    
                    # Validar que la resolución esté dentro de fecha
                    if not resolucion.esta_dentro_de_fecha():
                        return Response(
                            {
                                "error": "resolucion_expirada",
                                "message": f"La resolución seleccionada está fuera de fecha. Fecha fin: {resolucion.fecha_fin}",
                                "missing_fields": ["resolucion_dian"]
                            },
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY
                        )
                except (ValueError, TypeError):
                    return Response(
                        {
                            "error": "resolucion_invalida",
                            "message": "El ID de resolución proporcionado no es válido.",
                            "missing_fields": ["resolucion_dian"]
                        },
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY
                    )
            else:
                # ⚠️ v2.60: Fallback - Usar resolución vigente automáticamente si no se proporciona
                resolucion = obtener_resolucion_vigente(empresa)
                if not resolucion:
                    # ⚠️ v2.60: Regla de Negocio - Retornar 422 con mensaje específico para Error Injector
                    return Response(
                        {
                            "error": "resolucion_no_configurada",
                            "message": "No hay resolución DIAN activa. Configure una resolución primero.",
                            "missing_fields": ["resolucion_dian"]
                        },
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY
                    )
            
            with transaction.atomic():
                # ⚠️ v2.60: Obtener siguiente consecutivo en transacción atómica (evita colisiones)
                # Si el usuario seleccionó una resolución específica, usar esa resolución para el consecutivo
                if resolucion_id:
                    # ⚠️ v2.60: Usar la resolución seleccionada para obtener el consecutivo
                    # Validar que la resolución tenga rango disponible con lock
                    resolucion_lock = ResolucionDIAN.objects.select_for_update().filter(
                        empresa=empresa,
                        id=resolucion.id
                    ).first()
                    
                    if not resolucion_lock:
                        return Response(
                            {
                                "error": "resolucion_no_encontrada",
                                "message": f"La resolución seleccionada no existe o no pertenece a este tenant.",
                                "missing_fields": ["resolucion_dian"]
                            },
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY
                        )
                    
                    # Obtener el máximo consecutivo de la resolución seleccionada
                    ultimo = DocumentoSoporte.objects.select_for_update().filter(
                        empresa=empresa,
                        resolucion_dian=resolucion_lock
                    ).aggregate(max_val=Max('consecutivo'))['max_val']
                    
                    nuevo_numero = (ultimo + 1) if ultimo else resolucion_lock.rango_desde
                    
                    if nuevo_numero > resolucion_lock.rango_hasta:
                        return Response(
                            {
                                "error": "rango_agotado",
                                "message": f"El rango de la resolución seleccionada se ha agotado. Rango disponible: {resolucion_lock.rango_desde}-{resolucion_lock.rango_hasta}",
                                "missing_fields": ["resolucion_dian"]
                            },
                            status=status.HTTP_409_CONFLICT
                        )
                    
                    # Validar que no exista ya este consecutivo
                    existe = DocumentoSoporte.objects.select_for_update().filter(
                        empresa=empresa,
                        resolucion_dian=resolucion_lock,
                        consecutivo=nuevo_numero
                    ).exists()
                    
                    if existe:
                        return Response(
                            {
                                "error": "consecutivo_duplicado",
                                "message": f"El consecutivo {nuevo_numero} ya existe para la resolución seleccionada.",
                                "missing_fields": ["resolucion_dian"]
                            },
                            status=status.HTTP_409_CONFLICT
                        )
                    
                    consecutivo = nuevo_numero
                    # Usar la resolución seleccionada
                    resolucion = resolucion_lock
                else:
                    # ⚠️ v2.60: Fallback - Usar la función existente que busca la resolución vigente
                    consecutivo = obtener_siguiente_numero_soporte(empresa)
                    # La resolución ya está asignada desde el bloque else anterior
                
                # ⚠️ v2.40: Obtener subtotal y porcentajes de retención
                subtotal = Decimal(str(data.get('subtotal', 0)))
                retefuente_porcentaje = data.get('retefuente_porcentaje', '0.00')
                reteica_porcentaje = data.get('reteica_porcentaje', '0.00')
                
                # ⚠️ v2.60: Validar campos obligatorios antes de calcular
                campos_faltantes = []
                if not subtotal or subtotal <= 0:
                    campos_faltantes.append('subtotal')
                if not retefuente_porcentaje:
                    campos_faltantes.append('retefuente_porcentaje')
                if not reteica_porcentaje:
                    campos_faltantes.append('reteica_porcentaje')
                if not data.get('fecha'):
                    campos_faltantes.append('fecha')
                if not data.get('vendedor_nit'):
                    campos_faltantes.append('vendedor_nit')
                if not data.get('vendedor_nombre'):
                    campos_faltantes.append('vendedor_nombre')
                if not data.get('categoria_contable'):
                    campos_faltantes.append('categoria_contable')
                if not data.get('periodo'):
                    campos_faltantes.append('periodo')
                
                if campos_faltantes:
                    return Response(
                        {
                            "error": "missing_required_fields",
                            "message": f"Faltan campos obligatorios: {', '.join(campos_faltantes)}",
                            "missing_fields": campos_faltantes
                        },
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY
                    )
                
                # ⚠️ v2.40: Calcular retenciones usando el service layer
                # ⚠️ v2.60: Esta función valida la fórmula Total = Subtotal - Retefuente - ReteICA
                retenciones = calcular_retenciones(subtotal, retefuente_porcentaje, reteica_porcentaje)
                
                # ⚠️ v2.60: VALIDACIÓN ADICIONAL DE FÓRMULA antes de persistir
                # Doble verificación para asegurar inmutabilidad
                total_calculado = subtotal - retenciones['retefuente'] - retenciones['reteica']
                diferencia = abs(retenciones['total'] - total_calculado)
                
                if diferencia > Decimal('0.01'):
                    return Response(
                        {
                            "error": "formula_validation_error",
                            "message": (
                                f"Error de validación: La fórmula Total = Subtotal - Retefuente - ReteICA no se cumple. "
                                f"Subtotal: {subtotal}, Retefuente: {retenciones['retefuente']}, "
                                f"ReteICA: {retenciones['reteica']}, Total calculado: {total_calculado}, "
                                f"Total esperado: {retenciones['total']}, Diferencia: {diferencia}"
                            ),
                            "missing_fields": ["subtotal", "retefuente_porcentaje", "reteica_porcentaje"]
                        },
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY
                    )
                
                # Crear DocumentoSoporte con valores calculados
                documento_soporte = DocumentoSoporte.objects.create(
                    empresa=empresa,
                    resolucion_dian=resolucion,
                    prefijo=resolucion.prefijo,
                    consecutivo=consecutivo,
                    fecha=data.get('fecha'),
                    vendedor_nit=data.get('vendedor_nit'),
                    vendedor_nombre=data.get('vendedor_nombre'),
                    vendedor_direccion=data.get('vendedor_direccion', ''),
                    vendedor_telefono=data.get('vendedor_telefono', ''),
                    numero_factura_proveedor=data.get('numero_factura_proveedor', ''),
                    subtotal=subtotal,
                    retefuente_porcentaje=retefuente_porcentaje,
                    retefuente=retenciones['retefuente'],
                    reteica_porcentaje=reteica_porcentaje,
                    reteica=retenciones['reteica'],
                    total=retenciones['total'],
                    adjunto=data.get('adjunto')
                )
                
                # ⚠️ v2.60: VALIDACIÓN POST-PERSISTENCIA - Verificar que el modelo validó correctamente
                # El modelo DocumentoSoporte tiene validación en clean() y save()
                documento_soporte.refresh_from_db()
                
                # Crear Gasto
                gasto = Gasto.objects.create(
                    empresa=empresa,
                    documento_soporte=documento_soporte,
                    periodo=data.get('periodo'),
                    centro_costo=data.get('centro_costo', ''),
                    categoria_contable=data.get('categoria_contable'),
                    descripcion=data.get('descripcion', ''),
                    observaciones=data.get('observaciones', '')
                )
                
                # ⚠️ v2.60: Contabilidad Invisible - Hook para materializar asiento automático
                # Si el gasto está activo y no anulado, crear asiento contable automáticamente
                if documento_soporte.activo and not documento_soporte.anulado:
                    try:
                        from apps.tenant.contabilidad.services.asientos_service import materializar_asiento_desde_gasto
                        materializar_asiento_desde_gasto(gasto)
                        logger.info(f"[gastos.viewset] Asiento contable materializado automáticamente para gasto {documento_soporte.numero_documento}")
                    except Exception as e:
                        # ⚠️ Aislamiento Gradual: No fallar la creación de gasto si falla la materialización del asiento
                        # El asiento se puede crear manualmente después
                        logger.warning(f"[gastos.viewset] Error al materializar asiento desde gasto {documento_soporte.numero_documento}: {str(e)}")
                        # No propagar el error - el gasto ya está guardado
                
                serializer = self.get_serializer(gasto)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
        except IntegrityError as e:
            # ⚠️ v2.60: Manejar errores de integridad (duplicados) para Error Injector
            logger.warning(f"Error de integridad al crear gasto: {e}", exc_info=True)
            error_message = "Error de integridad: El consecutivo o documento ya existe."
            
            # Intentar extraer información del error
            if 'unique_ds_resolucion_consecutivo' in str(e):
                error_message = "Ya existe un Documento Soporte con este consecutivo en esta resolución."
            elif 'unique_ds_vendedor_factura' in str(e):
                error_message = "Ya existe un Documento Soporte activo con este vendedor y número de factura."
            
            return Response(
                {
                    "error": "duplicate_error",
                    "message": error_message,
                    "missing_fields": ["consecutivo", "vendedor_nit", "numero_factura_proveedor"]
                },
                status=status.HTTP_409_CONFLICT
            )
                
        except ValidationError as e:
            # ⚠️ v2.60: Formatear ValidationError para Error Injector
            error_message = str(e)
            missing_fields = []
            
            # ⚠️ v2.60: Regla de Negocio - Si el consecutivo se agota, retornar 409 Conflict
            if "agotado" in error_message.lower() or ("rango" in error_message.lower() and "resolución" in error_message.lower()):
                return Response(
                    {
                        "error": "rango_agotado",
                        "message": f"El rango de consecutivos de la resolución se ha agotado. {error_message}",
                        "missing_fields": ["resolucion_dian"]
                    },
                    status=status.HTTP_409_CONFLICT
                )
            
            # ⚠️ v2.60: Detectar errores de resolución no configurada o no válida
            if "resolución" in error_message.lower() and ("no válida" in error_message.lower() or "expirada" in error_message.lower()):
                return Response(
                    {
                        "error": "resolucion_no_valida",
                        "message": error_message,
                        "missing_fields": ["resolucion_dian"]
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )
            
            # Si el ValidationError tiene un diccionario de errores, extraer campos
            if hasattr(e, 'error_dict'):
                missing_fields = list(e.error_dict.keys())
                if e.error_dict:
                    # Tomar el primer mensaje de error como mensaje principal
                    first_field = list(e.error_dict.keys())[0]
                    first_errors = e.error_dict[first_field]
                    if first_errors:
                        error_message = f"{first_field}: {first_errors[0]}"
            
            return Response(
                {
                    "error": "validacion_error",
                    "message": error_message,
                    "missing_fields": missing_fields if missing_fields else ["subtotal", "retefuente_porcentaje", "reteica_porcentaje"]
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.error(f"Error creando gasto: {e}", exc_info=True)
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"], url_path="desactivar")
    def desactivar(self, request, pk=None):
        """
        Acción para desactivar un gasto (v2.40).
        
        ⚠️ REGLA CRÍTICA: Paso previo obligatorio antes de anular.
        El documento debe estar desactivado para poder anularlo.
        """
        try:
            gasto = self.get_object()
            resultado = desactivar_gasto_service(gasto.id)
            return Response(resultado, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error desactivando gasto {pk}: {str(e)}")
            return Response({"detail": "Error interno al desactivar"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"], url_path="anular")
    def anular(self, request, pk=None):
        """
        Acción para anular un gasto (v2.40).
        
        ⚠️ REGLA CRÍTICA: Solo se puede anular si está desactivado (activo=False).
        Utiliza el service layer para garantizar atomicidad e inmutabilidad.
        """
        try:
            gasto = self.get_object()
            # ⚠️ REGLA: No se puede editar, solo anular a través del service
            resultado = anular_gasto_service(gasto.id)
            return Response(resultado, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error anulando gasto {pk}: {str(e)}")
            return Response({"detail": "Error interno al anular"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        Obtiene resumen financiero neto excluyendo documentos anulados.
        
        ⚠️ v2.40: REGLA CRÍTICA - Documentos con anulado=True => Valor 0.
        Solo suma documentos no anulados para mantener integridad contable.
        
        Returns:
            {
                "subtotal_neto": Decimal,
                "retenciones_neto": Decimal,  # Suma de retefuente + reteica
                "total_neto": Decimal,
                "cantidad": int
            }
        """
        try:
            # Obtener empresa del tenant (opcional, para filtrado futuro)
            empresa_id = None
            if hasattr(request.user, 'empresa_id'):
                empresa_id = request.user.empresa_id
            
            summary_data = get_gastos_summary(empresa_id=empresa_id)
            
            # Convertir Decimal a string para JSON (si es necesario)
            def decimal_to_str(d):
                if isinstance(d, dict):
                    return {k: str(v) if isinstance(v, Decimal) else v for k, v in d.items()}
                return d
            
            summary_serialized = decimal_to_str(summary_data)
            
            return Response(summary_serialized, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error calculando resumen de gastos: {e}", exc_info=True)
            return Response(
                {"error": "error_calculando_resumen", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"], url_path="resoluciones")
    def resoluciones(self, request):
        """
        Retorna todas las resoluciones DIAN disponibles para el formulario de creación.
        
        ⚠️ v2.60: Actualizado para retornar TODAS las resoluciones (no solo vigentes)
        para que el usuario pueda seleccionar entre todas las disponibles.
        """
        from apps.tenant.empresa.models import Empresa
        
        empresa = Empresa.objects.first()
        if not empresa:
            return Response(
                {"error": "empresa_no_configurada", "message": "No hay empresa configurada para este tenant."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # ⚠️ v2.60: Retornar TODAS las resoluciones de la empresa (no solo vigentes)
        resoluciones = ResolucionDIAN.objects.filter(empresa=empresa).order_by('-vigente', '-fecha_resolucion')
        serializer = ResolucionDIANNestedSerializer(resoluciones, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=["get"], url_path="resolucion-activa")
    def resolucion_activa(self, request):
        """
        Retorna la resolución DIAN vigente para la empresa del tenant.
        
        ⚠️ v2.40: SSoT - Solo una resolución vigente por empresa.
        Si no existe, retorna 404 para que el frontend abra el modal de configuración.
        """
        try:
            # Obtener empresa del tenant (SSoT)
            from apps.tenant.empresa.models import Empresa
            empresa = Empresa.objects.first()  # Singleton por tenant
            
            if not empresa:
                return Response(
                    {"error": "empresa_no_configurada", "message": "No hay empresa configurada para este tenant."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            resolucion = ResolucionDIAN.objects.filter(
                empresa=empresa,
                vigente=True
            ).first()
            
            if not resolucion:
                return Response(
                    {"error": "resolucion_no_configurada", "message": "No hay resolución DIAN configurada."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = ResolucionDIANNestedSerializer(resolucion)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error obteniendo resolución activa: {e}", exc_info=True)
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        Endpoint HTMX para cargar offcanvas de gastos (crear o detalle).
        
        ⚠️ v2.60: Feature-Sliced Architecture - Templates separados por acción
        - Modo creación: offcanvas_crear.html
        - Modo detalle: offcanvas_detalle.html
        
        Query params:
        - id: ID del gasto (opcional, si no se proporciona es modo creación)
        - mode: 'create' o 'detail' (opcional, si no se proporciona se infiere de 'id')
        
        Returns:
            Template HTML renderizado según el modo
        """
        gasto_id = request.query_params.get('id')
        mode = request.query_params.get('mode', 'create' if not gasto_id else 'detail')
        context = {}
        
        if mode == 'detail' and gasto_id:
            try:
                # Modo detalle: cargar gasto
                from apps.tenant.empresa.models import Empresa
                empresa = Empresa.objects.only('id').first()
                if not empresa:
                    context['error'] = "No se encontró la empresa (SSoT) configurada para este tenant."
                    return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html')
                
                # Zero Waste: only() carga solo lo necesario para el visualizador
                gasto = Gasto.objects.select_related('documento_soporte', 'documento_soporte__resolucion').filter(
                    documento_soporte__empresa=empresa,
                    id=gasto_id
                ).only(
                    'id',
                    'categoria_contable',
                    'centro_costo',
                    'descripcion',
                    'periodo',
                    'documento_soporte__prefijo',
                    'documento_soporte__consecutivo',
                    'documento_soporte__fecha',
                    'documento_soporte__vendedor_nombre',
                    'documento_soporte__vendedor_nit',
                    'documento_soporte__subtotal',
                    'documento_soporte__retefuente',
                    'documento_soporte__retefuente_porcentaje',
                    'documento_soporte__reteica',
                    'documento_soporte__reteica_porcentaje',
                    'documento_soporte__total',
                    'documento_soporte__activo',
                    'documento_soporte__anulado',
                ).first()
                
                if not gasto:
                    context['error'] = "Gasto no encontrado o no pertenece a este tenant."
                    return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html')
                
                context['gasto'] = gasto
                return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html')
                
            except Gasto.DoesNotExist:
                logger.warning(f"Gasto {gasto_id} no encontrado para Offcanvas.")
                context['error'] = "Gasto no encontrado."
                return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html', status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger.exception(f"Error al obtener gasto para Offcanvas: {e}")
                context['error'] = "No se pudo cargar el gasto."
                return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Modo creación
            context['gasto'] = None
            return Response(context, template_name='tenant/core/gastos/offcanvas_crear.html')
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de creación de gastos.
        
        ⚠️ v2.60: Feature-Sliced Architecture - Template dedicado para creación
        - GET /api/v1/gastos/render-offcanvas/crear/ → Modo creación
        
        Returns:
            Template HTML: tenant/core/gastos/offcanvas_crear.html
        """
        context = {'gasto': None}
        return Response(context, template_name='tenant/core/gastos/offcanvas_crear.html')
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/resolucion')
    def render_offcanvas_resolucion(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de configuración de resolución DIAN.
        
        ⚠️ v2.60: Feature-Sliced Architecture - Template dedicado para configuración
        - GET /api/v1/gastos/render-offcanvas/resolucion/ → Modo configuración
        
        Returns:
            Template HTML: tenant/core/gastos/offcanvas_resolucion.html
        """
        context = {}
        return Response(context, template_name='tenant/core/gastos/offcanvas_resolucion.html')
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de detalle de gastos.
        
        ⚠️ v2.60: Feature-Sliced Architecture - Template dedicado para detalle
        - GET /api/v1/gastos/render-offcanvas/detalle/?id=123 → Modo detalle
        
        Query params:
        - id: ID del gasto (requerido)
        
        Returns:
            Template HTML: tenant/core/gastos/offcanvas_detalle.html
        """
        gasto_id = request.query_params.get('id')
        context = {}
        
        if not gasto_id:
            context['error'] = "Se requiere el parámetro 'id' para el modo detalle."
            return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html', status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Modo detalle: cargar gasto
            from apps.tenant.empresa.models import Empresa
            empresa = Empresa.objects.only('id').first()
            if not empresa:
                context['error'] = "No se encontró la empresa (SSoT) configurada para este tenant."
                return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html')
            
            # Zero Waste: only() carga solo lo necesario para el visualizador
            gasto = Gasto.objects.select_related('documento_soporte', 'documento_soporte__resolucion').filter(
                documento_soporte__empresa=empresa,
                id=gasto_id
            ).only(
                'id',
                'categoria_contable',
                'centro_costo',
                'descripcion',
                'periodo',
                'documento_soporte__prefijo',
                'documento_soporte__consecutivo',
                'documento_soporte__fecha',
                'documento_soporte__vendedor_nombre',
                'documento_soporte__vendedor_nit',
                'documento_soporte__subtotal',
                'documento_soporte__retefuente',
                'documento_soporte__retefuente_porcentaje',
                'documento_soporte__reteica',
                'documento_soporte__reteica_porcentaje',
                'documento_soporte__total',
                'documento_soporte__activo',
                'documento_soporte__anulado',
            ).first()
            
            if not gasto:
                context['error'] = "Gasto no encontrado o no pertenece a este tenant."
                return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html')
            
            context['gasto'] = gasto
            return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html')
            
        except Gasto.DoesNotExist:
            logger.warning(f"Gasto {gasto_id} no encontrado para Offcanvas.")
            context['error'] = "Gasto no encontrado."
            return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html', status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Error al obtener gasto para Offcanvas: {e}")
            context['error'] = "No se pudo cargar el gasto."
            return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["post"], url_path="configurar-resolucion")
    def configurar_resolucion(self, request):
        """
        Crea o actualiza una resolución DIAN para la empresa del tenant.
        
        ⚠️ v2.60: CORRECCIÓN - Usa ResolucionDIANCreateSerializer para manejar valores de checkbox HTML.
        ⚠️ v2.40: SSoT - Solo una resolución vigente por empresa.
        Si se marca como vigente, desactiva automáticamente las anteriores.
        """
        try:
            from apps.tenant.empresa.models import Empresa
            from django.db import transaction
            from .serializers import ResolucionDIANCreateSerializer
            
            empresa = Empresa.objects.first()  # Singleton por tenant
            
            if not empresa:
                return Response(
                    {"error": "empresa_no_configurada", "message": "No hay empresa configurada para este tenant."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # ⚠️ v2.60: Usar serializer para validación y manejo de valores HTML
            data = request.data.copy()
            data['empresa'] = empresa.id
            
            # ⚠️ CORRECCIÓN: El serializer maneja el valor "on" del checkbox
            serializer = ResolucionDIANCreateSerializer(data=data)
            
            if not serializer.is_valid():
                # ⚠️ v2.60: Formatear errores para Error Injector
                error_details = {}
                for field, errors in serializer.errors.items():
                    error_details[field] = errors[0] if isinstance(errors, list) else str(errors)
                
                return Response(
                    {
                        "error": "validacion_error",
                        "message": "Error de validación en los datos proporcionados.",
                        "details": error_details,
                        "missing_fields": list(error_details.keys())
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )
            
            validated_data = serializer.validated_data
            vigente = validated_data.get('vigente', True)
            
            # ⚠️ v2.60: El serializer ya validó y parseó todos los campos
            fecha_resolucion = validated_data['fecha_resolucion']
            fecha_fin = validated_data['fecha_fin']
            
            with transaction.atomic():
                # Si se marca como vigente, desactivar las anteriores
                if vigente:
                    ResolucionDIAN.objects.filter(
                        empresa=empresa,
                        vigente=True
                    ).update(vigente=False)
                
                # ⚠️ v2.60: Crear nueva resolución usando datos validados del serializer
                resolucion = ResolucionDIAN(
                    empresa=empresa,
                    numero_resolucion=validated_data['numero_resolucion'],
                    prefijo=validated_data['prefijo'],
                    rango_desde=validated_data['rango_desde'],
                    rango_hasta=validated_data['rango_hasta'],
                    fecha_resolucion=fecha_resolucion,
                    fecha_inicio=fecha_resolucion,  # ⚠️ Usar fecha_resolucion como fecha_inicio
                    fecha_fin=fecha_fin,
                    clave_tecnica=validated_data.get('clave_tecnica', ''),
                    vigente=vigente
                )
                
                # ⚠️ VALIDACIÓN: Llamar a full_clean() para ejecutar clean() del modelo
                resolucion.full_clean()
                resolucion.save()
                
                serializer = ResolucionDIANNestedSerializer(resolucion)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
        except ValidationError as e:
            return Response(
                {"error": "validacion_error", "message": str(e), "details": e.message_dict if hasattr(e, 'message_dict') else None},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error configurando resolución: {e}", exc_info=True)
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResolucionDIANViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet para Resoluciones DIAN (v2.40).
    
    ⚠️ INMUTABILIDAD: Las resoluciones son documentos legales y no deben editarse.
    - Bloquea PUT/PATCH (update/partial_update)
    - Solo permite CREATE, LIST, RETRIEVE, DESTROY
    - En DESTROY: valida que no tenga Documentos de Soporte asociados
    
    ⚠️ REGLA CRÍTICA: Solo UNA resolución puede estar vigente por empresa.
    Si se crea una nueva como vigente, desactiva automáticamente las anteriores.
    
    ⚠️ SNAPSHOT INALTERABLE: Al desactivar o eliminar una resolución,
    los Documentos de Soporte conservan su número y prefijo originales.
    """
    queryset = ResolucionDIAN.objects.none()  # Se sobrescribe en get_queryset()
    serializer_class = ResolucionDIANDetailSerializer
    pagination_class = StandardResultsSetPagination
    http_method_names = ['get', 'post', 'delete', 'head', 'options']  # Bloquea PUT/PATCH
    
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero_resolucion', 'prefijo']
    ordering_fields = ['fecha_resolucion', 'vigente', 'created_at']
    ordering = ['-vigente', '-fecha_resolucion']
    
    def get_empresa(self):
        """
        Obtiene la empresa del tenant actual (SSoT).
        
        ⚠️ PERFORMANCE BIBLE: Usa .first() en lugar de .all()[0]
        Singleton pattern: Solo debe existir una empresa por tenant
        """
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            from rest_framework.exceptions import APIException
            raise APIException(detail='No se encontró empresa para este tenant')
        return empresa
    
    def get_queryset(self):
        """
        QuerySet optimizado según la acción.
        
        ⚠️ SSoT: Filtrado por empresa para aislamiento multi-tenant.
        """
        if not hasattr(self, 'action') or self.action is None:
            return ResolucionDIAN.objects.none()
        
        empresa = self.get_empresa()
        
        if self.action == "list":
            return qs_resolucion_list(empresa.id)
        elif self.action == "retrieve":
            return qs_resolucion_detail(empresa.id, self.kwargs.get('pk'))
        else:
            return ResolucionDIAN.objects.filter(empresa=empresa)
    
    def get_serializer_class(self):
        """Alineación v2.40: ListSerializer para listado, DetailSerializer para detalle."""
        if self.action == "list":
            return ResolucionDIANListSerializer
        return ResolucionDIANDetailSerializer
    
    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/resoluciones-dian/
        Lista paginada de resoluciones (Tabulator v2.40).
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """
        GET /api/v1/resoluciones-dian/{id}/
        Obtiene detalle de una resolución.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/resoluciones-dian/
        Crea una nueva resolución DIAN.
        
        ⚠️ REGLA CRÍTICA: Solo UNA resolución puede estar vigente por empresa.
        Si se marca como vigente, desactiva automáticamente las anteriores.
        """
        try:
            empresa = self.get_empresa()
            resultado = crear_resolucion(empresa, request.data)
            serializer = self.get_serializer(resultado)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(
                {"error": "validacion_error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creando resolución: {e}", exc_info=True)
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/v1/resoluciones-dian/{id}/
        Elimina una resolución DIAN.
        
        ⚠️ REGLA: No se puede eliminar si tiene Documentos de Soporte asociados.
        Los documentos deben conservar su referencia a la resolución (evidencia legal).
        """
        try:
            empresa = self.get_empresa()
            resolucion_id = self.kwargs.get('pk')
            
            # Validar que se puede eliminar
            puede_eliminar, mensaje = puede_eliminar_resolucion(empresa, resolucion_id)
            
            if not puede_eliminar:
                return Response(
                    {"error": "resolucion_en_uso", "message": mensaje},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Obtener y eliminar
            resolucion = qs_resolucion_detail(empresa.id, resolucion_id)
            if not resolucion:
                return Response(
                    {"error": "resolucion_no_encontrada", "message": "Resolución no encontrada."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            resolucion.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"Error eliminando resolución: {e}", exc_info=True)
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=["post"], url_path="desactivar")
    def desactivar(self, request, pk=None):
        """
        POST /api/v1/resoluciones-dian/{id}/desactivar/
        Desactiva una resolución DIAN (marca vigente=False).
        
        ⚠️ INMUTABILIDAD: El DocumentoSoporte conserva su número y prefijo originales
        (snapshot inalterable). La desactivación no afecta documentos ya generados.
        """
        try:
            empresa = self.get_empresa()
            resultado = desactivar_resolucion(empresa, pk)
            serializer = self.get_serializer(resultado)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(
                {"error": "validacion_error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error desactivando resolución {pk}: {str(e)}")
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=["get"], url_path="activa")
    def activa(self, request):
        """
        GET /api/v1/resoluciones-dian/activa/
        Retorna la resolución DIAN vigente para la empresa del tenant.
        
        ⚠️ v2.40: SSoT - Solo una resolución vigente por empresa.
        Si no existe, retorna 404 para que el frontend abra el modal de configuración.
        """
        try:
            empresa = self.get_empresa()
            resolucion = obtener_resolucion_vigente(empresa)
            
            if not resolucion:
                return Response(
                    {"error": "resolucion_no_configurada", "message": "No hay resolución DIAN configurada."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = ResolucionDIANNestedSerializer(resolucion)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error obteniendo resolución activa: {e}", exc_info=True)
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )