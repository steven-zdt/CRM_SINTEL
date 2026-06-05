from typing import List
import logging

from .base import AbstractExtractor
from ..dtos import TransaccionEconomica

logger = logging.getLogger(__name__)


class ExtractorInventario(AbstractExtractor):
    """
    Extractor legacy deshabilitado.

    La relacion contable de movimientos de inventario se centraliza en
    Inventario/Movimientos Recientes. Contabilidad no debe mapear Producto ni
    ActivoFijo directamente desde este extractor.
    """

    def extraer_pendientes(self) -> List[TransaccionEconomica]:
        """No extrae movimientos: el mapeo vive en Inventario."""
        logger.info(
            "[contabilidad:extractor_inventario] deshabilitado; empresa_id=%s",
            self.empresa_id,
        )
        return []
