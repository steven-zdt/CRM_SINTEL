import logging
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError
from ..models import Cliente, ContactoCliente
from .selectors import DETAIL_FIELDS

logger = logging.getLogger(__name__)

class ClienteCRUDService:
    """Atomic database mutations for Cliente."""

    @staticmethod
    @transaction.atomic
    def create_cliente(empresa_id: int, data: dict) -> Cliente:
        """Creates a new client record safely."""
        try:
            return Cliente.objects.create(empresa_id=empresa_id, **data)
        except IntegrityError as e:
            if "uniq_doc_cliente_empresa" in str(e):
                raise ValidationError({"numero_documento": ["Ya existe un cliente con este documento en esta empresa."]})
            raise e

    @staticmethod
    @transaction.atomic
    def update_cliente(cliente: Cliente, data: dict) -> Cliente:
        """Updates an existing client record."""
        for field, value in data.items():
            setattr(cliente, field, value)
        try:
            cliente.save()
            return cliente
        except IntegrityError as e:
            if "uniq_doc_cliente_empresa" in str(e):
                raise ValidationError({"numero_documento": ["Ya existe otro cliente con este documento en esta empresa."]})
            raise e

    @staticmethod
    @transaction.atomic
    def delete_cliente(cliente: Cliente):
        """Deletes a client only if inactive."""
        if cliente.activo:
            raise ValidationError({"detail": "No se puede eliminar un cliente activo. Inactívelo primero."})
        cliente.delete()


class ContactoCRUDService:
    """Atomic database mutations for ContactoCliente."""

    @staticmethod
    @transaction.atomic
    def create_contacto(empresa_id: int, data: dict) -> ContactoCliente:
        try:
            return ContactoCliente.objects.create(empresa_id=empresa_id, **data)
        except IntegrityError as e:
            if "uniq_contacto_cliente_email" in str(e):
                raise ValidationError({"email": ["Ya existe un contacto con este email para este cliente."]})
            raise e

    @staticmethod
    @transaction.atomic
    def update_contacto(contacto: ContactoCliente, data: dict) -> ContactoCliente:
        for field, value in data.items():
            setattr(contacto, field, value)
        try:
            contacto.save()
            return contacto
        except IntegrityError as e:
            if "uniq_contacto_cliente_email" in str(e):
                raise ValidationError({"email": ["Ya existe otro contacto con este email para este cliente."]})
            raise e

    @staticmethod
    @transaction.atomic
    def delete_contacto(contacto: ContactoCliente):
        contacto.delete()
