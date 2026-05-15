"""
FacturaCRUDService — Acceso a datos y persistencia para Facturas.

Responsabilidad única: Operaciones DML (Create/Delete) y acceso a QuerySets.
No contiene lógica de negocio compleja — delega la validación a BusinessService.

Reglas SINTEL v3.5:
- Todos los métodos son @staticmethod.
- Operaciones de escritura envueltas en @transaction.atomic.
- Zero-Trust: El ViewSet filtra por empresa_id antes de llamar a este servicio.
"""

import logging
from typing import Any, Iterable

from django.db import transaction, IntegrityError
from django.db.models import ProtectedError
from django.utils import timezone

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, FacturaAnexos, ItemFactura
from apps.tenant.facturas.services.selectors import FacturaSelectors

logger = logging.getLogger(__name__)


class FacturaCRUDService:
    """
    Servicio para operaciones CRUD de Facturas.
    """

    @staticmethod
    def qs_list(search: str | None = None):
        """Retorna el QuerySet para listados (vía Selectors)."""
        return FacturaSelectors.qs_list(search=search)

    @staticmethod
    def qs_detail():
        """Retorna el QuerySet para detalle (vía Selectors)."""
        return FacturaSelectors.qs_detail()

    @staticmethod
    @transaction.atomic
    def crear(factura_data: dict[str, Any], anexos_data: dict[str, Any] | None = None) -> Factura:
        """
        Persistencia básica de Factura y Anexos.
        """
        empresa = factura_data.get("empresa")
        if not empresa:
            empresa = Empresa.objects.first()
            factura_data["empresa"] = empresa

        factura = Factura.objects.create(**factura_data)

        if anexos_data:
            FacturaAnexos.objects.update_or_create(
                factura=factura,
                defaults={
                    "empresa": factura.empresa,
                    **anexos_data
                },
            )

        return factura

    @staticmethod
    @transaction.atomic
    def eliminar(factura: Factura) -> None:
        """
        Elimina una factura y sus registros relacionados (v2.95).
        """
        # Eliminar nota de crédito asociada primero (OneToOne PROTECT workaround)
        # Usar la relación inversa "nota_credito" definida en el modelo
        if hasattr(factura, 'nota_credito') and factura.nota_credito:
            try:
                factura.nota_credito.delete()
            except Exception as e:
                logger.warning(f"Error al eliminar NotaCredito: {str(e)}")

        # Anexos se eliminan por cascada o manualmente por seguridad
        try:
            anexos = FacturaAnexos.objects.get(factura=factura)
            anexos.delete()
        except FacturaAnexos.DoesNotExist:
            pass

        # Items se eliminan por CASCADE en el modelo
        factura.delete()
        logger.info(f"Factura {factura.numero} eliminada exitosamente.")

    @staticmethod
    @transaction.atomic
    def actualizar(factura: Factura, update_data: dict[str, Any]) -> Factura:
        """
        Actualiza campos específicos de una factura.
        
        # WARNING: SINTEL v3.5: Persistencia transaccional.
        """
        for field, value in update_data.items():
            setattr(factura, field, value)
        
        # SINTEL v3.5: Forzar timestamp de actualización
        if hasattr(factura, 'updated_at'):
            factura.save(update_fields=list(update_data.keys()) + ['updated_at'])
        else:
            factura.save(update_fields=list(update_data.keys()))
            
        return factura
