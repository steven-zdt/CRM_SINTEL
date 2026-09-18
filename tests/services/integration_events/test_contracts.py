"""
N8N-SINTEL-02 (FASE 7): apps/services/integration_events/contracts.py no tenia
ningun test propio -- DomainEvent es el contrato real que n8n consume del lado
del webhook, verificar sus invariantes (event_id unico, serializacion completa)
directamente, sin pasar por publisher.py/tasks.py.
"""
from django.test import SimpleTestCase

from apps.services.integration_events.contracts import DomainEvent


class DomainEventTests(SimpleTestCase):
    def _build(self, **overrides):
        kwargs = dict(
            event_type="invoice.processed",
            tenant="home",
            aggregate_type="Factura",
            aggregate_uuid="11111111-1111-1111-1111-111111111111",
        )
        kwargs.update(overrides)
        return DomainEvent(**kwargs)

    def test_defaults_version_1_y_payload_vacio(self):
        event = self._build()

        assert event.version == 1
        assert event.payload == {}

    def test_event_id_es_uuid_real_y_unico_por_instancia(self):
        import uuid

        event_a = self._build()
        event_b = self._build()

        # No debe lanzar -- confirma formato UUID valido, no un string arbitrario.
        uuid.UUID(event_a.event_id)
        uuid.UUID(event_b.event_id)
        assert event_a.event_id != event_b.event_id

    def test_occurred_at_es_iso_8601_parseable(self):
        from datetime import datetime

        event = self._build()

        # No debe lanzar -- confirma que occurred_at es ISO-8601 real, no un
        # string libre (n8n lo parsea del lado del workflow).
        datetime.fromisoformat(event.occurred_at)

    def test_to_dict_serializa_todos_los_campos(self):
        event = self._build(payload={"numero": "FE-1"}, tenant="aipoc")

        data = event.to_dict()

        assert data == {
            "event_type": "invoice.processed",
            "tenant": "aipoc",
            "aggregate_type": "Factura",
            "aggregate_uuid": "11111111-1111-1111-1111-111111111111",
            "payload": {"numero": "FE-1"},
            "version": 1,
            "event_id": event.event_id,
            "occurred_at": event.occurred_at,
        }

    def test_es_inmutable(self):
        event = self._build()

        with self.assertRaises(Exception):
            event.tenant = "otro_tenant"
