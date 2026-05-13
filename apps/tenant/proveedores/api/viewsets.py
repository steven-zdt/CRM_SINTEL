from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantMember, IsTenantAdminOrReadOnly
from apps.tenant.api.utils import render_template_safe, resolve_tenant_empresa
from apps.tenant.empresa.models import Empresa
from .mixins import ProveedorServiceMixin
from apps.tenant.proveedores.api.serializers import (
    ProveedorDetailSerializer,
    ProveedorListSerializer,
)
from apps.tenant.proveedores.models import Proveedor
from apps.config.api.pagination import StandardResultsSetPagination

class ProveedorViewSet(ProveedorServiceMixin, BaseTenantViewSet):
    """
    ViewSet para Proveedores v3.5 - Refactorizado a Service Layer (DSV Mixins).
    """
    queryset = Proveedor.objects.none()
    serializer_class = ProveedorDetailSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]

    def get_serializer_class(self):
        """Selecciona el serializer según la acción."""
        if self.action == 'list':
            return ProveedorListSerializer
        return ProveedorDetailSerializer
    
    def get_queryset(self):
        """Zero Trust - Filtra siempre por la empresa del tenant."""
        empresa = self.get_empresa()
        return Proveedor.objects.filter(empresa=empresa)

    def get_empresa(self):
        """Zero Trust - Obtiene la empresa del tenant actual via core helper."""
        return resolve_tenant_empresa(self.request, self)

    def list(self, request):
        """Endpoint para Tabulator (Selector Modular)."""
        empresa = self.get_empresa()
        search = request.query_params.get('search', '').strip()
        
        queryset = self.proveedor_selector.get_list(empresa.id, search if search else None)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ProveedorListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ProveedorListSerializer(queryset, many=True)
        return Response(serializer.data)

    def get_object(self):
        """
        Sobrescribe get_object para soportar lookup por uuid (v3.5 SSoT).
        Mantiene compatibilidad con PK si el uuid no es un UUID válido.
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs.get(lookup_url_kwarg)

        if not lookup_value:
            raise Http404("ID no proporcionado")

        # 1. Intentar por UUID si el valor parece uno (len > 10)
        if len(str(lookup_value)) > 10:
            obj = self.get_queryset().filter(uuid=lookup_value).first()
            if obj:
                return obj
        
        # 2. Fallback a PK (si es numérico)
        if str(lookup_value).isdigit():
            obj = self.get_queryset().filter(pk=lookup_value).first()
            if obj:
                return obj
                
        raise Http404("Proveedor no encontrado")
    
    def retrieve(self, request, *args, **kwargs):
        """Obtiene detalle de un proveedor."""
        proveedor = self.get_object()
        serializer = ProveedorDetailSerializer(proveedor)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Crea un proveedor delegando al Business Service."""
        empresa = self.get_empresa()
        serializer = ProveedorDetailSerializer(data=request.data)
        if serializer.is_valid():
            proveedor = self.proveedor_service.crear_proveedor(empresa.id, serializer.validated_data)
            return Response(
                ProveedorDetailSerializer(proveedor).data, 
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Actualiza un proveedor delegando al Business Service."""
        proveedor = self.get_object()
        serializer = ProveedorDetailSerializer(proveedor, data=request.data, partial=False)
        if serializer.is_valid():
            proveedor = self.proveedor_service.actualizar_proveedor(proveedor, serializer.validated_data)
            return Response(ProveedorDetailSerializer(proveedor).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial delegando al Business Service."""
        proveedor = self.get_object()
        serializer = ProveedorDetailSerializer(proveedor, data=request.data, partial=True)
        if serializer.is_valid():
            proveedor = self.proveedor_service.actualizar_proveedor(proveedor, serializer.validated_data)
            return Response(ProveedorDetailSerializer(proveedor).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Eliminación delegando lógica de protección al Business Service."""
        proveedor = self.get_object()
        try:
            self.proveedor_service.eliminar_proveedor(proveedor)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """Renderiza offcanvas de creación (FSD Compliant)."""
        return self.get_offcanvas_response(request, template_suffix='crear')

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request):
        """Renderiza offcanvas de edición (FSD Compliant)."""
        return self.get_offcanvas_response(request, template_suffix='editar')

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request):
        """Renderiza offcanvas en modo detalle (FSD Compliant)."""
        return self.get_offcanvas_response(request, template_suffix='detalle')

    def get_offcanvas_response(self, request, template_suffix='crear'):
        """Helper para renderizar el Offcanvas con el contexto NIIF."""
        empresa = self.get_empresa()
        proveedor = None
        id_instancia = request.query_params.get('id')
        
        if id_instancia:
            # v3.5.2: Priorizamos UUID para lookup seguro
            proveedor = self.proveedor_selector.get_by_uuid(empresa.id, id_instancia)
            if not proveedor and str(id_instancia).isdigit():
                # Fallback por PK para compatibilidad
                proveedor = self.proveedor_selector.get_by_id(empresa.id, id_instancia)
        
        from apps.tenant.proveedores.choices.niif_proveedores_choices import (
            PROVEEDORES_NIIF_CHOICES,
        )
        
        context = {
            'proveedor': proveedor,
            'empresa': empresa,
            'tipo_persona_choices': Proveedor.TIPO_PERSONA,
            'tipo_documento_choices': Proveedor.TIPO_DOCUMENTO,
            'regimen_choices': Proveedor.REGIMEN,
            'tipo_cuenta_choices': [("AHORROS", "Ahorros"), ("CORRIENTE", "Corriente")],
            'niif_choices': PROVEEDORES_NIIF_CHOICES,
            'modo_detalle': template_suffix == 'detalle',
        }
        
        # v3.5.2: Template universal unificado para evitar desincronización de IDs
        template_name = 'tenant/proveedores/offcanvas_form.html'
        return render_template_safe(context, template_name, request=request)
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """Alias para retrocompatibilidad."""
        return self.get_offcanvas_response(request, template_suffix='crear')
