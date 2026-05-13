"""
CRUD Service para Gastos - Persistencia transaccional pura.

WARNING: SINTEL v2.62.0: Arquitectura Service Layer Modular.
- Este archivo contiene SOLO operaciones de persistencia (Create, Read, Update, Delete).
- Sin logica de negocio, solo acceso a datos con @transaction.atomic.
- Todas las funciones son @staticmethod.
"""
import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from django.db import transaction, models
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN


logger = logging.getLogger(__name__)


class ResolucionCRUDService:
    """Operaciones CRUD puras para ResolucionDIAN."""

    @staticmethod
    def _invalidar_cache_vigente(empresa_id: int) -> None:
        """Invalida cache de resolucion vigente para una empresa."""
        from django.core.cache import cache

        cache.delete(f"resolucion_vigente_{empresa_id}")

    @staticmethod
    @transaction.atomic
    def crear_resolucion(data: dict, empresa) -> ResolucionDIAN:
        """Crea una nueva resolucion DIAN."""
        # Validar unicidad de numero_resolucion por empresa
        numero = data.get('numero_resolucion')
        if ResolucionDIAN.objects.filter(
            empresa=empresa,
            numero_resolucion=numero
        ).exists():
            raise ValidationError(
                f"Ya existe una resolucion con numero {numero} para esta empresa"
            )

        resolucion = ResolucionDIAN(**data)
        resolucion.empresa = empresa
        resolucion.full_clean()
        resolucion.save()
        ResolucionCRUDService._invalidar_cache_vigente(empresa.id)
        
        logger.info(f"[ResolucionCRUD] Creada resolucion ID={resolucion.id}")
        return resolucion

    @staticmethod
    @transaction.atomic
    def desactivar_resolucion(resolucion: ResolucionDIAN) -> ResolucionDIAN:
        """Desactiva una resolucion (marca como no vigente)."""
        resolucion.vigente = False
        resolucion.save(update_fields=['vigente'])
        ResolucionCRUDService._invalidar_cache_vigente(resolucion.empresa_id)
        logger.info(f"[ResolucionCRUD] Desactivada resolucion ID={resolucion.id}")
        return resolucion

    @staticmethod
    def puede_eliminar(resolucion: ResolucionDIAN) -> bool:
        """Verifica si una resolucion puede ser eliminada."""
        return not DocumentoSoporte.objects.filter(
            resolucion_dian=resolucion
        ).exists()

    @staticmethod
    @transaction.atomic
    def eliminar_resolucion(resolucion: ResolucionDIAN):
        """Elimina una resolucion."""
        if not ResolucionCRUDService.puede_eliminar(resolucion):
            raise ValidationError(
                "No se puede eliminar la resolucion porque tiene documentos asociados"
            )

        resolucion_id = resolucion.id
        empresa_id = resolucion.empresa_id
        resolucion.delete()
        ResolucionCRUDService._invalidar_cache_vigente(empresa_id)
        logger.info(f"[ResolucionCRUD] Eliminada resolucion ID={resolucion_id}")


class DocumentoCRUDService:
    """Operaciones CRUD puras para DocumentoSoporte."""

    @staticmethod
    @transaction.atomic
    def crear_documento(data: dict, empresa, resolucion) -> DocumentoSoporte:
        """Crea un nuevo documento soporte con consecutivo."""
        # Obtener siguiente consecutivo de forma atomica
        consecutivo = DocumentoCRUDService._obtener_siguiente_consecutivo(resolucion)

        documento = DocumentoSoporte(
            empresa=empresa,
            resolucion_dian=resolucion,
            consecutivo=consecutivo,
            **data
        )
        documento.full_clean()
        documento.save()
        
        logger.info(
            f"[DocumentoCRUD] Creado documento ID={documento.id}, "
            f"consecutivo={consecutivo}"
        )
        return documento

    @staticmethod
    @transaction.atomic
    def anular_documento(documento: DocumentoSoporte, motivo: str = None, usuario: Any = None) -> DocumentoSoporte:
        """Marca un documento como anulado."""
        fecha_anulacion = timezone.now()
        DocumentoSoporte.objects.filter(pk=documento.pk).update(
            anulado=True,
            fecha_anulacion=fecha_anulacion,
            motivo_anulacion=motivo,
            usuario_anulacion=usuario,
            activo=False
        )
        logger.info(f"[DocumentoCRUD] Anulado documento ID={documento.id}")
        documento.refresh_from_db()
        return documento

    @staticmethod
    @transaction.atomic
    def desactivar_documento(documento: DocumentoSoporte) -> DocumentoSoporte:
        """Desactiva un documento (soft delete)."""
        DocumentoSoporte.objects.filter(pk=documento.pk).update(activo=False)
        logger.info(f"[DocumentoCRUD] Desactivado documento ID={documento.id}")
        documento.refresh_from_db()
        return documento

    @staticmethod
    @transaction.atomic
    def eliminar_documento(documento: DocumentoSoporte):
        """Elimina físicamente un documento."""
        doc_id = documento.id
        documento.delete()
        logger.info(f"[DocumentoCRUD] Eliminado físicamente documento ID={doc_id}")

    @staticmethod
    def _obtener_siguiente_consecutivo(resolucion: ResolucionDIAN) -> int:
        """Calcula el siguiente consecutivo atomicamente."""
        # Lock para evitar race conditions
        res_locked = ResolucionDIAN.objects.select_for_update().get(pk=resolucion.pk)

        ultimo = DocumentoSoporte.objects.filter(
            resolucion_dian=res_locked
        ).aggregate(max_val=models.Max('consecutivo'))['max_val']

        nuevo = (ultimo + 1) if ultimo else res_locked.rango_desde

        if nuevo > res_locked.rango_hasta:
            raise ValidationError(
                f"Rango de resolucion {res_locked.numero_resolucion} agotado"
            )

        # Verificar que no exista (doble verificacion)
        existe = DocumentoSoporte.objects.filter(
            resolucion_dian=res_locked,
            consecutivo=nuevo
        ).exists()

        if existe:
            raise ValidationError(
                f"El consecutivo {nuevo} ya existe para esta resolucion"
            )

        return nuevo
