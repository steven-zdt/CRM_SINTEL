"""
Helper server-side reutilizable para DataTables.

Centraliza parseo y validación de parámetros DataTables (draw/start/length/order/columns/search),
aplica whitelists de orden/búsqueda y devuelve el contrato DataTables estándar.

Referencias:
- DataTables server-side: https://datatables.net/manual/server-side
- Seguridad whitelist: https://webdevservices.in/secure-datatables-implementation/
"""
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any

from django.db.models import Q, QuerySet
from rest_framework import status
from rest_framework.response import Response


class DataTableSpec:
    """
    Especificación declarativa para un endpoint DataTables.
    
    Define qué columnas son ordenables/buscables y cómo se mapean a campos ORM.
    
    Args:
        fields_map: Mapeo de índice de columna (int) -> nombre de campo ORM permitido (whitelist)
        search_fields: Lista de campos ORM sobre los que aplicar búsqueda global (icontains)
        base_qs: QuerySet base (ya con only()/select_related()/prefetch_related() aplicados)
        serializer: Clase de serializador DRF para serializar 'data'
        extra_filter: Callable opcional (request, qs) -> qs (para filtros adicionales)
        
    Ejemplo:
        spec = DataTableSpec(
            fields_map={0: "id", 1: "name", 2: "domain", 3: "created_at"},
            search_fields=["name", "domain"],
            base_qs=Tenant.objects.only("id", "name", "domain", "created_at"),
            serializer=TenantListSerializer,
        )
    """
    
    def __init__(
        self,
        fields_map: Mapping[int, str],
        search_fields: Sequence[str],
        base_qs: QuerySet,
        serializer,
        extra_filter: Callable | None = None,
    ):
        self.fields_map = dict(fields_map)
        self.search_fields = list(search_fields)
        self.base_qs = base_qs
        self.serializer = serializer
        self.extra_filter = extra_filter


class DataTableServer:
    """
    Helper server-side para procesar requests DataTables.
    
    Lee parámetros desde request.data (POST), aplica búsqueda global y orden
    solo en campos whitelisted, pagina con slice [start:start+length] (estilo DataTables),
    y responde con el contrato estándar:
    
    {
        "draw": int,              # Echo del request (para sincronización)
        "recordsTotal": int,      # Total de registros (sin filtros)
        "recordsFiltered": int,   # Total después de búsqueda/filtros
        "data": List[dict]        # Datos serializados de la página actual
    }
    
    Referencias:
    - Contrato DataTables: https://datatables.net/manual/server-side
    - Seguridad whitelist: https://webdevservices.in/secure-datatables-implementation/
    """
    
    def __init__(self, spec: DataTableSpec):
        """
        Inicializa el helper con una especificación.
        
        Args:
            spec: DataTableSpec con la configuración del endpoint
        """
        self.spec = spec
    
    def _apply_search(self, qs: QuerySet, search_value: str) -> QuerySet:
        """
        Aplica búsqueda global sobre campos permitidos (whitelist).
        
        Args:
            qs: QuerySet base
            search_value: Valor de búsqueda (str, puede estar vacío)
            
        Returns:
            QuerySet filtrado con OR sobre search_fields
        """
        if not search_value or not self.spec.search_fields:
            return qs
        
        # Construye OR dinámico sobre campos permitidos
        query = Q()
        for field in self.spec.search_fields:
            query |= Q(**{f"{field}__icontains": search_value})
        
        return qs.filter(query)
    
    def _apply_order(self, qs: QuerySet, order_rules: Iterable[Mapping]) -> QuerySet:
        """
        Aplica orden solo sobre columnas whitelisted.
        
        Args:
            qs: QuerySet base
            order_rules: Lista de dicts con {"column": int, "dir": "asc"|"desc"}
            
        Returns:
            QuerySet ordenado (solo columnas permitidas)
        """
        if not order_rules:
            return qs
        
        ordering = []
        for rule in order_rules:
            try:
                idx = int(rule.get("column", 0))
            except (TypeError, ValueError):
                continue
            
            # Whitelist: solo campos permitidos
            field = self.spec.fields_map.get(idx)
            if not field:
                continue
            
            dir_val = rule.get("dir", "asc")
            if dir_val == "desc":
                field = f"-{field}"
            
            ordering.append(field)
        
        if ordering:
            return qs.order_by(*ordering)
        
        return qs
    
    def _parse_request(self, request) -> dict[str, Any]:
        """
        Parsea parámetros DataTables desde request.data (POST).
        
        DataTables envía:
        - draw: int (echo para sincronización)
        - start: int (offset para paginación)
        - length: int (tamaño de página)
        - search[value]: str (búsqueda global)
        - order[i][column]: int, order[i][dir]: "asc"|"desc" (reglas de orden)
        - columns[i][data]: str (nombre de columna, no usado en server-side)
        
        Returns:
            Dict con parámetros parseados
        """
        data = request.data if hasattr(request, 'data') else {}
        
        # Parámetros básicos
        draw = int(data.get("draw", 0))
        start = int(data.get("start", 0))
        length = int(data.get("length", 10))
        
        # Búsqueda global
        search = data.get("search", {})
        search_value = str(search.get("value", "")).strip() if isinstance(search, dict) else ""
        
        # Orden (puede haber múltiples reglas)
        order_rules = []
        order_data = data.get("order", [])
        if isinstance(order_data, list):
            for order_rule in order_data:
                if isinstance(order_rule, dict):
                    order_rules.append(order_rule)
        
        return {
            "draw": draw,
            "start": start,
            "length": length,
            "search_value": search_value,
            "order_rules": order_rules,
        }
    
    def handle(self, request) -> Response:
        """
        Procesa request DataTables y devuelve respuesta estándar.
        
        Flujo:
        1. Parsear parámetros del request
        2. Aplicar extra_filter si existe
        3. Contar recordsTotal (sin filtros de búsqueda)
        4. Aplicar búsqueda global
        5. Contar recordsFiltered (después de búsqueda)
        6. Aplicar orden
        7. Paginar [start:start+length]
        8. Serializar datos
        9. Responder con contrato DataTables
        
        Args:
            request: HttpRequest/Request con request.data (POST)
            
        Returns:
            Response con JSON: {draw, recordsTotal, recordsFiltered, data}
        """
        # 1. Parsear parámetros
        params = self._parse_request(request)
        
        # 2. QuerySet base (ya con only()/select_related()/prefetch_related())
        qs = self.spec.base_qs
        
        # 3. Aplicar extra_filter si existe (filtros adicionales del módulo)
        if self.spec.extra_filter:
            qs = self.spec.extra_filter(request, qs)
        
        # 4. Contar total sin búsqueda
        records_total = qs.count()
        
        # 5. Aplicar búsqueda global
        qs_filtered = self._apply_search(qs, params["search_value"])
        
        # 6. Contar después de búsqueda
        records_filtered = qs_filtered.count()
        
        # 7. Aplicar orden
        qs_ordered = self._apply_order(qs_filtered, params["order_rules"])
        
        # 8. Paginar (estilo DataTables: [start:start+length])
        start = params["start"]
        length = params["length"]
        qs_paginated = qs_ordered[start:start + length]
        
        # 9. Serializar datos
        serializer = self.spec.serializer(qs_paginated, many=True)
        
        # 10. Responder con contrato DataTables
        return Response(
            {
                "draw": params["draw"],
                "recordsTotal": records_total,
                "recordsFiltered": records_filtered,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
