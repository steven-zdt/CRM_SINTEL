"""
CRUD Service for Proveedores v3.5 - Atomic Persistence.
"""
from django.db import transaction, IntegrityError
from rest_framework.exceptions import ValidationError
from ..models import Proveedor, Representante

class ProveedorCRUDService:
    """
    Pure persistence layer for Proveedor.
    No business logic, only DB operations.
    """

    @transaction.atomic
    def create(self, empresa_id, data):
        """Crea un proveedor en la base de datos."""
        try:
            return Proveedor.objects.create(empresa_id=empresa_id, **data)
        except IntegrityError as e:
            self._handle_integrity_error(e)

    @transaction.atomic
    def update(self, proveedor, data):
        """Actualiza una instancia de proveedor."""
        try:
            for attr, value in data.items():
                setattr(proveedor, attr, value)
            proveedor.save()
            return proveedor
        except IntegrityError as e:
            self._handle_integrity_error(e)

    @transaction.atomic
    def delete(self, proveedor):
        """Eliminación física del proveedor."""
        proveedor.delete()

    @transaction.atomic
    def update_or_create(self, empresa_id, filter_data, defaults):
        """Busca o crea un proveedor el la base de datos (Idempotencia)."""
        try:
            return Proveedor.objects.update_or_create(
                empresa_id=empresa_id,
                **filter_data,
                defaults=defaults
            )
        except IntegrityError as e:
            self._handle_integrity_error(e)

    def _handle_integrity_error(self, e):
        error_msg = str(e)
        if 'uniq_proveedor_empresa' in error_msg or 'UNIQUE constraint' in error_msg:
            raise ValidationError({
                'numero_documento': [
                    'Ya existe un proveedor registrado con este tipo y número de documento en esta empresa.'
                ]
            })
        raise e


class RepresentanteCRUDService:
    """
    Pure persistence layer for Representante.
    No business logic, only DB operations with @transaction.atomic.
    """

    @transaction.atomic
    def create(self, empresa_id, proveedor_id, data):
        """Crea un representante en la base de datos (DSV: empresa_id + proveedor_id)."""
        try:
            return Representante.objects.create(
                empresa_id=empresa_id,
                proveedor_id=proveedor_id,
                **data
            )
        except IntegrityError as e:
            self._handle_integrity_error(e)

    @transaction.atomic
    def update(self, representante, data):
        """Actualiza una instancia de representante."""
        try:
            for attr, value in data.items():
                setattr(representante, attr, value)
            representante.save()
            return representante
        except IntegrityError as e:
            self._handle_integrity_error(e)

    @transaction.atomic
    def delete(self, representante):
        """Eliminación física del representante."""
        representante.delete()

    def _handle_integrity_error(self, e):
        error_msg = str(e)
        if 'uniq_representante_empresa_proveedor_doc' in error_msg or 'UNIQUE constraint' in error_msg:
            raise ValidationError({
                'numero_documento': [
                    'Ya existe un representante con este documento para este proveedor en esta empresa.'
                ]
            })
        raise e
