import logging
from django.db import transaction
from rest_framework.exceptions import ValidationError
from ..models import Cliente, ContactoCliente
from .crud_service import ClienteCRUDService, ContactoCRUDService
from .selectors import ClienteSelector

logger = logging.getLogger(__name__)

class ClienteBusinessService:
    """Orchestration and Business logic for Clientes."""

    def __init__(self):
        self.crud = ClienteCRUDService()
        self.contacto_crud = ContactoCRUDService()
        self.selector = ClienteSelector()

    @transaction.atomic
    def registrar_cliente_completo(self, empresa_id: int, data: dict, contactos_raw: list = None, cliente_instance: Cliente = None) -> Cliente:
        """
        Orchestrates creation or update of a client and their contacts.
        If cliente_instance is provided, updates directly without upsert logic.
        """
        data = self._sanitize_retenciones(data)
        
        if cliente_instance:
            cliente = self.crud.update_cliente(cliente_instance, data)
        else:
            # 1. Normalize and check uniqueness
            tipo_doc = data.get("tipo_documento")
            num_doc = data.get("numero_documento")
            
            # Upsert logic (Idempotency)
            existing = Cliente.objects.filter(
                empresa_id=empresa_id,
                tipo_documento=tipo_doc,
                numero_documento=num_doc
            ).first()

            if existing:
                cliente = self.crud.update_cliente(existing, data)
            else:
                cliente = self.crud.create_cliente(empresa_id, data)

        # 2. Sync contacts if provided
        if contactos_raw is not None:
            self.sincronizar_contactos(empresa_id, cliente.id, contactos_raw)
            
        return cliente

    def sincronizar_contactos(self, empresa_id: int, cliente_id: int, contactos_raw: list):
        """
        Sync contacts for a client (Create/Update/Delete).
        MOVED FROM VIEWSET - Fase 0 Phantom Logic Purge.
        """
        if not isinstance(contactos_raw, list):
            return

        existing_ids = set(
            ContactoCliente.objects.filter(
                cliente_id=cliente_id, empresa_id=empresa_id
            ).values_list('id', flat=True)
        )
        submitted_ids = set()

        for c_data in contactos_raw:
            if not isinstance(c_data, dict):
                continue
            
            # Basic validation
            nombre = str(c_data.get('nombre_completo', '')).strip()
            email = str(c_data.get('email', '')).strip()
            if not nombre or not email:
                continue

            c_id = c_data.get('id')
            if c_id and int(c_id) in existing_ids:
                # Update
                contacto = ContactoCliente.objects.get(id=c_id, empresa_id=empresa_id)
                payload = self._clean_payload(c_data)
                self.contacto_crud.update_contacto(contacto, payload)
                submitted_ids.add(int(c_id))
            else:
                # Create
                payload = self._clean_payload(c_data)
                payload['cliente_id'] = cliente_id
                new_c = self.contacto_crud.create_contacto(empresa_id, payload)
                submitted_ids.add(new_c.id)

        # Delete removed contacts
        to_delete = existing_ids - submitted_ids
        if to_delete:
            ContactoCliente.objects.filter(id__in=to_delete, empresa_id=empresa_id).delete()

    def _sanitize_retenciones(self, payload: dict) -> dict:
        """
        Zero Trust: Limpia flags y porcentajes de retención si el cliente no es retenedor.
        """
        es_retenedor = payload.get("es_retenedor", False)
        
        if not es_retenedor:
            payload["aplica_retefuente"] = False
            payload["retefuente_porcentaje"] = 0
            payload["aplica_reteica"] = False
            payload["reteica_porcentaje"] = 0
            payload["aplica_reteiva"] = False
            payload["reteiva_porcentaje"] = 0
        else:
            # Sanitización fina: si la flag individual es False, el porcentaje debe ser 0
            if not payload.get("aplica_retefuente", False):
                payload["retefuente_porcentaje"] = 0
            if not payload.get("aplica_reteica", False):
                payload["reteica_porcentaje"] = 0
            if not payload.get("aplica_reteiva", False):
                payload["reteiva_porcentaje"] = 0
                
        return payload

    def _clean_payload(self, data: dict) -> dict:
        """Removes metadata fields before DB save."""
        p = dict(data)
        p.pop('id', None)
        p.pop('empresa', None)
        p.pop('empresa_id', None)
        p.pop('cliente', None)
        return p
