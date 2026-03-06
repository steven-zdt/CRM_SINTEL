"""
Endpoints DataTables (server-side) para catálogos de impuestos.

Retornan JSON en formato DataTables server-side:
{
    "draw": 1,
    "recordsTotal": 100,
    "recordsFiltered": 50,
    "data": [[...], [...]]
}

Referencia: https://datatables.net/manual/server-side
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.utils import timezone
from apps.public.impuestos.models import (
    TipoImpuesto,
    TarifaIVA,
    ConceptoRetencion,
    CodigoTributario,
    ActividadEconomica,
    NormaTributaria,
)


class BaseDataTablesView(APIView):
    """Base para vistas DataTables (formato estándar server-side)."""
    permission_classes = [permissions.IsAuthenticated]
    model = None
    columns = []
    
    def get_queryset(self):
        """Retorna el queryset base."""
        if self.model:
            return self.model.objects.all()
        return None
    
    def get_filtered_queryset(self, queryset, search_value):
        """Aplica búsqueda al queryset."""
        if not search_value or not queryset:
            return queryset
        
        # Búsqueda simple: buscar en campos de texto
        # Puedes personalizar según el modelo
        return queryset
    
    def format_row(self, obj):
        """Formatea un objeto como fila para DataTables."""
        # Debe retornar una lista con valores en el orden de columns
        return []
    
    def get(self, request):
        """
        Retorna datos en formato DataTables server-side.
        
        Parámetros esperados:
        - draw: Contador de request (DataTables lo envía automáticamente)
        - start: Offset (paginación)
        - length: Tamaño de página
        - search[value]: Valor de búsqueda
        """
        queryset = self.get_queryset()
        if not queryset:
            return Response({"error": "Model not configured"}, status=400)
        
        # Parámetros de DataTables
        draw = int(request.GET.get("draw", 1))
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 25))
        search_value = request.GET.get("search[value]", "").strip()
        
        # Aplicar búsqueda
        filtered_qs = self.get_filtered_queryset(queryset, search_value)
        
        # Contar totales
        records_total = queryset.count()
        records_filtered = filtered_qs.count()
        
        # Paginación y ordenamiento
        # DataTables envía order[0][column] y order[0][dir]
        order_column = int(request.GET.get("order[0][column]", 0))
        order_dir = request.GET.get("order[0][dir]", "asc")
        
        # Aplicar orden (por ahora usar id por defecto)
        if order_dir == "desc":
            filtered_qs = filtered_qs.order_by("-id")
        else:
            filtered_qs = filtered_qs.order_by("id")
        
        # Paginar
        end = start + length
        page_qs = filtered_qs[start:end]
        
        # Formatear datos
        data = [self.format_row(obj) for obj in page_qs]
        
        return Response({
            "draw": draw,
            "recordsTotal": records_total,
            "recordsFiltered": records_filtered,
            "data": data,
        })


class TipoImpuestoDataTablesView(BaseDataTablesView):
    """Endpoint DataTables para TipoImpuesto."""
    model = TipoImpuesto
    columns = ["id", "codigo", "nombre", "activo", "fecha_vigencia"]
    
    def get_filtered_queryset(self, queryset, search_value):
        if search_value:
            return queryset.filter(
                codigo__icontains=search_value
            ) | queryset.filter(
                nombre__icontains=search_value
            ) | queryset.filter(
                descripcion__icontains=search_value
            )
        return queryset
    
    def format_row(self, obj):
        return [
            obj.id,
            obj.codigo,
            obj.nombre,
            "✓" if obj.activo else "✗",
            obj.fecha_vigencia.strftime("%Y-%m-%d") if obj.fecha_vigencia else "",
        ]


class TarifaIVADataTablesView(BaseDataTablesView):
    """Endpoint DataTables para TarifaIVA."""
    model = TarifaIVA
    columns = ["id", "codigo", "nombre", "porcentaje", "activo"]
    
    def get_filtered_queryset(self, queryset, search_value):
        if search_value:
            return queryset.filter(
                codigo__icontains=search_value
            ) | queryset.filter(
                nombre__icontains=search_value
            )
        return queryset
    
    def format_row(self, obj):
        return [
            obj.id,
            obj.codigo,
            obj.nombre,
            f"{obj.porcentaje}%" if obj.porcentaje else "",
            "✓" if obj.activo else "✗",
        ]


class ConceptoRetencionDataTablesView(BaseDataTablesView):
    """Endpoint DataTables para ConceptoRetencion."""
    model = ConceptoRetencion
    columns = ["id", "codigo", "nombre", "tipo_retencion", "activo"]
    
    def get_filtered_queryset(self, queryset, search_value):
        if search_value:
            return queryset.filter(
                codigo__icontains=search_value
            ) | queryset.filter(
                nombre__icontains=search_value
            )
        return queryset
    
    def format_row(self, obj):
        return [
            obj.id,
            obj.codigo,
            obj.nombre,
            obj.get_tipo_retencion_display() if hasattr(obj, 'get_tipo_retencion_display') else obj.tipo_retencion,
            "✓" if obj.activo else "✗",
        ]


class CodigoTributarioDataTablesView(BaseDataTablesView):
    """Endpoint DataTables para CodigoTributario."""
    model = CodigoTributario
    columns = ["id", "codigo", "nombre", "tipo", "activo"]
    
    def get_filtered_queryset(self, queryset, search_value):
        if search_value:
            return queryset.filter(
                codigo__icontains=search_value
            ) | queryset.filter(
                nombre__icontains=search_value
            ) | queryset.filter(
                tipo__icontains=search_value
            )
        return queryset
    
    def format_row(self, obj):
        return [
            obj.id,
            obj.codigo,
            obj.nombre,
            obj.tipo,
            "✓" if obj.activo else "✗",
        ]


class ActividadEconomicaDataTablesView(BaseDataTablesView):
    """Endpoint DataTables para ActividadEconomica."""
    model = ActividadEconomica
    columns = ["id", "codigo", "nombre", "activo"]
    
    def get_filtered_queryset(self, queryset, search_value):
        if search_value:
            return queryset.filter(
                codigo__icontains=search_value
            ) | queryset.filter(
                nombre__icontains=search_value
            )
        return queryset
    
    def format_row(self, obj):
        return [
            obj.id,
            obj.codigo,
            obj.nombre,
            "✓" if obj.activo else "✗",
        ]
