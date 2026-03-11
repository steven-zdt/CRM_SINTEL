"""Core API helpers (funcionales) para normalizar request payloads y respuestas.

⚠️ POLÍTICA:
- Sin lógica de negocio aquí.
- Solo utilidades puras/reutilizables para evitar duplicación (JSON vs multipart, paginación, errores).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict, Optional, Tuple

from django.http import QueryDict
from rest_framework import status
from rest_framework.response import Response


def coerce_request_data(request) -> Dict[str, Any]:
    """Normaliza request.data a dict plano.

    - JSONParser -> dict
    - FormParser/MultiPartParser -> QueryDict

    No valida contenido, solo lo convierte.
    """
    if not isinstance(getattr(request, "data", None), Mapping):
        return {}

    data = request.data
    if isinstance(data, QueryDict):
        out: Dict[str, Any] = data.dict()
    else:
        out = dict(data)

    # Campo de compatibilidad (FormData) que no debe contarse como dato de negocio.
    out.pop("csrfmiddlewaretoken", None)
    return out


def parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_pagination_params(request, *, default_page: int = 1, default_page_size: int = 20) -> Tuple[int, int]:
    """Extrae page y page_size en forma segura."""
    page = parse_int(getattr(request, "query_params", {}).get("page"), default_page)
    page_size = parse_int(getattr(request, "query_params", {}).get("page_size"), default_page_size)
    if page < 1:
        page = default_page
    if page_size < 1:
        page_size = default_page_size
    return page, page_size


def error_response(message: str, *, error: str = "bad_request", http_status: int = status.HTTP_400_BAD_REQUEST) -> Response:
    return Response({"error": error, "detail": message}, status=http_status)
