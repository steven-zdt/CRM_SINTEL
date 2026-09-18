"""
N8N-SINTEL-02 (FASE 7): apps/services/integration_events/publisher.py no tenia
ningun test propio pese a ser el unico punto de entrada real que los dominios
(hoy solo facturas/api/mixins/factura_ubl_mixin.py) usan para publicar
eventos hacia n8n. Cubre los 2 invariantes de diseno documentados en el propio
modulo: (1) publicar nunca debe tocar Celery si no hay N8N_WEBHOOK_URL
configurada (entorno sin n8n -- este mismo checkout hoy), (2) cuando si hay
webhook configurado, encola via apply_async sin bloquear al caller.
"""
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.services.integration_events.publisher import publish_event


class PublishEventTests(SimpleTestCase):
    @override_settings(N8N_WEBHOOK_URL="")
    def test_sin_webhook_url_no_encola_nada(self):
        with patch(
            "apps.services.integration_events.tasks.send_webhook_event.apply_async"
        ) as mock_apply_async:
            event = publish_event(
                event_type="invoice.processed",
                tenant="home",
                aggregate_type="Factura",
                aggregate_uuid="uuid-1",
            )

        mock_apply_async.assert_not_called()
        assert event.event_type == "invoice.processed"
        assert event.tenant == "home"

    @override_settings(N8N_WEBHOOK_URL="http://n8n.local/webhook/sintel")
    def test_con_webhook_url_encola_el_evento_completo(self):
        with patch(
            "apps.services.integration_events.tasks.send_webhook_event.apply_async"
        ) as mock_apply_async:
            event = publish_event(
                event_type="invoice.duplicate",
                tenant="aipoc",
                aggregate_type="Factura",
                aggregate_uuid="uuid-2",
                payload={"numero": "FE-42"},
            )

        mock_apply_async.assert_called_once_with(
            kwargs={"event": event.to_dict()}, queue="default"
        )

    @override_settings(N8N_WEBHOOK_URL="http://n8n.local/webhook/sintel")
    def test_aggregate_uuid_siempre_se_normaliza_a_str(self):
        with patch("apps.services.integration_events.tasks.send_webhook_event.apply_async"):
            event = publish_event(
                event_type="invoice.processed",
                tenant="home",
                aggregate_type="Factura",
                aggregate_uuid=123,
            )

        assert event.aggregate_uuid == "123"
