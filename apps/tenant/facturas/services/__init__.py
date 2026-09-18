"""
Facturas Services Package — Punto de entrada SSoT.

Expone explicitamente todos los simbolos publicos del Service Layer.
Prohibido usar wildcard imports (from .modulo import *).

Incluye wrappers de compatibilidad para tests y management commands
que usan la API funcional de nivel de modulo (pre-refactorizacion v3.10).
"""

import re
from typing import Any

from .api_mixins import FacturaServiceMixin
from .business_service import FacturaBusinessService, FacturaInterAppAPI, FacturaService
from .crud_service import FacturaCRUDService
from .selectors import (
    DETAIL_FIELDS,
    LIST_FIELDS,
    ClienteBridge,
    FacturaSelectors,
    ProveedorBridge,
)

# ---------------------------------------------------------------------------
# [COMPAT] Wrappers funcionales de compatibilidad para tests y management cmds.
# Delegan a los metodos estaticos del Service Layer actual.
# No usar desde ViewSets — usar FacturaBusinessService directamente.
# ---------------------------------------------------------------------------

# Campos que pertenecen a FacturaAnexos (se separan del payload de Factura)
_ANEXOS_FIELDS = frozenset({"ubl_xml", "application_response_xml"})


def _norm_nit(value: str | None) -> str | None:
    """
    Normaliza un NIT para comparacion semantica.

    Reglas:
    - Retorna None si el valor es None, vacio o solo espacios.
    - Elimina puntos, guiones y espacios.
    - Elimina ceros a la izquierda.
    - Un NIT colombiano tiene 9 digitos; si el resultado tiene mas de 9,
      se recorta a los primeros 9 (elimina DV concatenado o ceros).
    - Convierte a mayusculas (para NITs alfanumericos).
    """
    if not value or not str(value).strip():
        return None

    normalized = str(value).strip().upper()
    # Eliminar separadores comunes
    normalized = re.sub(r'[\.\-\s]', '', normalized)

    if not normalized:
        return None

    # Para NITs puramente numericos: recortar a 9 digitos (estandar colombiano)
    if re.match(r'^\d+$', normalized):
        # Eliminar ceros a la izquierda
        normalized = str(int(normalized))
        # Truncar al NIT sin DV (primeros 9 digitos)
        if len(normalized) > 9:
            normalized = normalized[:9]

    return normalized if normalized else None


def _determinar_naturaleza(emisor_nit: str | None, empresa_nit: str | None) -> str:
    """
    Determina si la factura es VENTA o COMPRA.

    - VENTA: cuando el emisor_nit (normalizado) == empresa_nit (normalizado).
    - COMPRA: en cualquier otro caso (incluye None) -- este wrapper de
      compatibilidad NUNCA retorna None/"Revisar" (a diferencia de
      FacturaBusinessService._resolver_naturaleza()), para no cambiar el
      contrato de sus 2 callers reales (management commands
      backfill_naturaleza_facturas.py, fix_naturaleza_inconsistent.py) sin
      decision explicita del usuario sobre reclasificar datos existentes.

    FACTURAS-UI-CRONO-01 FASE 2: este docstring YA decia "Delega a
    FacturaBusinessService._resolver_naturaleza()" pero el codigo
    reimplementaba su propia comparacion con _norm_nit() (funcion de
    normalizacion DISTINTA a same_nit()/clean_nit() usada por la
    persistencia real) -- duplicacion real de la regla de negocio,
    confirmada porque _norm_nit() y same_nit() pueden divergir en NITs
    con caracteres no estandar. Corregido para delegar de verdad.
    """
    from apps.tenant.facturas.models import Factura

    naturaleza = FacturaBusinessService._resolver_naturaleza(emisor_nit, None, empresa_nit)
    return naturaleza or Factura.Naturaleza.COMPRA


def _split_factura_payload(data: dict | None) -> tuple[dict, dict]:
    """
    Separa un payload combinado en (factura_data, anexos_data).

    Los campos en _ANEXOS_FIELDS van a anexos_data; el resto a factura_data.
    Retorna ({}, {}) si data es None o vacio.
    """
    if not data:
        return {}, {}

    factura_data = {k: v for k, v in data.items() if k not in _ANEXOS_FIELDS}
    anexos_data = {k: v for k, v in data.items() if k in _ANEXOS_FIELDS}
    return factura_data, anexos_data


def crear_factura(factura_data: dict[str, Any], items_data: list | None = None) -> Any:
    """
    [COMPAT] Crea una Factura con sus Anexos desde un payload combinado.

    Separa los campos de FacturaAnexos del payload principal y delega
    a FacturaCRUDService.crear() para la persistencia transaccional.

    Args:
        factura_data: Dict con campos de Factura y opcionalmente campos de Anexos.
        items_data: Lista de items (no procesados en esta capa; se ignoran si vacia).

    Returns:
        Instancia de Factura persistida.
    """
    # No mutar el original
    payload = dict(factura_data)
    _, anexos_data = _split_factura_payload(payload)
    # Limpiar campos de anexos del payload principal
    for field in _ANEXOS_FIELDS:
        payload.pop(field, None)

    return FacturaCRUDService.crear(payload, anexos_data if anexos_data else None)


def importar_ubl(
    file_bytes: bytes,
    preview: bool = False,
    filename: str = 'ubl.xml',
    **kwargs: Any,
) -> tuple[dict, int]:
    """
    [COMPAT] Importa un documento UBL XML y retorna (payload, http_code).

    Delega a FacturaBusinessService.importar_documento() como SSoT.

    Args:
        file_bytes: Contenido del XML en bytes.
        preview: Si True, retorna DTO sin persistir.
        filename: Nombre de archivo para el pipeline universal.

    Returns:
        Tuple (dict respuesta, codigo HTTP).
    """
    return FacturaBusinessService.importar_documento(
        file_bytes,
        filename=filename,
        preview=preview,
        async_mode=False,
        **kwargs,
    )


def importar_ubl_sync(file_bytes: bytes, filename: str = 'ubl.xml') -> tuple[dict, int]:
    """
    [COMPAT] Importa un XML UBL de forma sincrona y retorna (payload, http_code).

    Alias directo de importar_ubl(preview=False).
    Delega a FacturaBusinessService.importar_documento().
    """
    return FacturaBusinessService.importar_documento(
        file_bytes,
        filename=filename,
        preview=False,
        async_mode=False,
    )


def materializar_factura_desde_result(result: dict, empresa_id: int | None = None) -> tuple[dict, int]:
    """
    [COMPAT] Materializa una Factura desde un resultado de preview.

    Delega a FacturaBusinessService.materializar_desde_result().

    Args:
        result: Payload devuelto por importar_ubl(preview=True).
        empresa_id: ID de empresa para DSV (opcional en este wrapper).

    Returns:
        Tuple (dict respuesta, codigo HTTP).
    """
    return FacturaBusinessService.materializar_desde_result(result, empresa_id=empresa_id)


# [v3.10.0] Inter-App API — acceso sin restriccion empresa_id para apps de negocio
# Uso: from apps.tenant.facturas.services import FacturaInterAppAPI
# API abierto para lectura — ver clase en business_service.py §FacturaInterAppAPI

# Expuesto adicionalmente para que el test de integracion pueda parcharlo:
# apps.tenant.facturas.services.ingest_ubl_sync
try:
    from apps.services.document_ingest.ingest_service import ingest_document as ingest_ubl_sync  # noqa: F401
except ImportError:
    ingest_ubl_sync = None  # type: ignore[assignment]
