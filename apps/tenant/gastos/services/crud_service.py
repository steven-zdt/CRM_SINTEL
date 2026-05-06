"""
CRUD Service para Gastos - Persistencia transaccional pura.

WARNING: SINTEL v2.61.4: Arquitectura Service Layer Modular.
- Este archivo contiene SOLO operaciones de persistencia (Create, Read, Update, Delete).
- Sin lógica de negocio, solo acceso a datos con @transaction.atomic.
- Todas las funciones son @staticmethod.
"""
import logging
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.tenant.gastos.models import Gasto, ResolucionDIAN, DocumentoSoporte

logger = logging.getLogger(__name__)


class GastoCRUDService:
    """Operaciones CRUD puras para Gasto."""

    @staticmethod
    @transaction.atomic
    def crear_gasto(data: dict, empresa, documento_soporte=None) -> Gasto:
        """Crea un nuevo gasto."""
        gasto = Gasto.objects.create(
            empresa=empresa,
            documento_soporte=documento_soporte,
            **data
        )
        logger.info(f"[GastoCRUD] Creado gasto ID={gasto.id}")
        return gasto

    @staticmethod
    @transaction.atomic
    def anular_gasto(gasto: Gasto, motivo: str = None, usuario = None) -> Gasto:
        """Marca un gasto como anulado vía su documento soporte."""
        if not gasto.documento_soporte:
            raise ValidationError("El gasto no tiene documento soporte asociado")

        # Anular documento soporte (inmutabilidad contable)
        doc = gasto.documento_soporte
        doc.anulado = True
        doc.motivo_anulacion = motivo
        doc.usuario_anulacion = usuario
        doc.save(update_fields=['anulado', 'motivo_anulacion', 'usuario_anulacion'])

        logger.info(f"[GastoCRUD] Anulado gasto ID={gasto.id}")
        return gasto

    @staticmethod
    @transaction.atomic
    def desactivar_gasto(gasto: Gasto) -> Gasto:
        """Desactiva un gasto (soft delete)."""
        gasto.activo = False
        gasto.save(update_fields=['activo'])
        logger.info(f"[GastoCRUD] Desactivado gasto ID={gasto.id}")
        return gasto


class ResolucionCRUDService:
    """Operaciones CRUD puras para ResolucionDIAN."""

    @staticmethod
    @transaction.atomic
    def crear_resolucion(data: dict, empresa) -> ResolucionDIAN:
        """Crea una nueva resolución DIAN."""
        # Validar unicidad de numero_resolucion por empresa
        numero = data.get('numero_resolucion')
        if ResolucionDIAN.objects.filter(
            empresa=empresa,
            numero_resolucion=numero
        ).exists():
            raise ValidationError(
                f"Ya existe una resolución con número {numero} para esta empresa"
            )

        resolucion = ResolucionDIAN.objects.create(empresa=empresa, **data)
        logger.info(f"[ResolucionCRUD] Creada resolución ID={resolucion.id}")
        return resolucion

    @staticmethod
    @transaction.atomic
    def desactivar_resolucion(resolucion: ResolucionDIAN) -> ResolucionDIAN:
        """Desactiva una resolución (marca como no vigente)."""
        resolucion.vigente = False
        resolucion.save(update_fields=['vigente'])
        logger.info(f"[ResolucionCRUD] Desactivada resolución ID={resolucion.id}")
        return resolucion

    @staticmethod
    def puede_eliminar(resolucion: ResolucionDIAN) -> bool:
        """Verifica si una resolución puede ser eliminada."""
        # No se puede eliminar si tiene documentos asociados
        return not DocumentoSoporte.objects.filter(
            resolucion_dian=resolucion
        ).exists()

    @staticmethod
    @transaction.atomic
    def eliminar_resolucion(resolucion: ResolucionDIAN):
        """Elimina una resolución."""
        if not ResolucionCRUDService.puede_eliminar(resolucion):
            raise ValidationError(
                "No se puede eliminar la resolución porque tiene documentos asociados"
            )

        resolucion_id = resolucion.id
        resolucion.delete()
        logger.info(f"[ResolucionCRUD] Eliminada resolución ID={resolucion_id}")


class DocumentoCRUDService:
    """Operaciones CRUD puras para DocumentoSoporte."""

    @staticmethod
    @transaction.atomic
    def crear_documento(data: dict, empresa, resolucion) -> DocumentoSoporte:
        """Crea un nuevo documento soporte con consecutivo."""
        # Obtener siguiente consecutivo de forma atómica
        consecutivo = DocumentoCRUDService._obtener_siguiente_consecutivo(resolucion)

        documento = DocumentoSoporte.objects.create(
            empresa=empresa,
            resolucion_dian=resolucion,
            consecutivo=consecutivo,
            **data
        )
        logger.info(
            f"[DocumentoCRUD] Creado documento ID={documento.id}, "
            f"consecutivo={consecutivo}"
        )
        return documento

    @staticmethod
    def _obtener_siguiente_consecutivo(resolucion: ResolucionDIAN) -> int:
        """Calcula el siguiente consecutivo atómicamente."""
        # Lock para evitar race conditions
        res_locked = ResolucionDIAN.objects.select_for_update().get(pk=resolucion.pk)

        ultimo = DocumentoSoporte.objects.filter(
            resolucion_dian=res_locked
        ).aggregate(max_val=models.Max('consecutivo'))['max_val']

        nuevo = (ultimo + 1) if ultimo else res_locked.rango_desde

        if nuevo > res_locked.rango_hasta:
            raise ValidationError(
                f"Rango de resolución {res_locked.numero_resolucion} agotado"
            )

        # Verificar que no exista (doble verificación)
        existe = DocumentoSoporte.objects.filter(
            resolucion_dian=res_locked,
            consecutivo=nuevo
        ).exists()

        if existe:
            raise ValidationError(
                f"El consecutivo {nuevo} ya existe para esta resolución"
            )

        return nuevo

    @staticmethod
    @transaction.atomic
    def anular_documento(documento: DocumentoSoporte) -> DocumentoSoporte:
        """Marca un documento como anulado (inmutabilidad contable)."""
        if documento.anulado:
            raise ValidationError("El documento ya está anulado")

        documento.anulado = True
        documento.save(update_fields=['anulado'])
        logger.info(f"[DocumentoCRUD] Anulado documento ID={documento.id}")
        return documento





# Import necesario para _obtener_siguiente_consecutivo
from django.db import models
