"""
N8N-SINTEL-02 (FASE 7): apps/services/integration_events/tasks.py (entrega real
del webhook hacia n8n) no tenia ningun test propio. Cubre: firma HMAC real
(no solo que "algo" se envie), y el contrato de error handling documentado en
el propio archivo -- 5xx/errores transitorios reintentan, 4xx no.

Los casos que deben RAISEAR (transitorio/5xx, para que autoretry_for de Celery
los reintente) se ejercitan llamando `.run(event=...)` -- Celery liga `self`
automaticamente a la instancia real del Task (`.request` degrada a un Context
vacio con `.retries=0` fuera de una ejecucion real) -- para no disparar el
backoff real (retry_backoff=True financia reintentos con sleep real incluso
en modo eager, lo que haria estos tests lentos/fragiles sin aportar cobertura
nueva; lo que se quiere probar es que la funcion decide raisear, no el
mecanismo de reintento de Celery). Los casos que NO deben raisear (skip sin
webhook, exito, 4xx) si usan `.apply()` real (mismo patron que
tests/services/maildigester/test_tasks.py) porque ahi no hay riesgo de
reintento.
"""
import hashlib
import hmac
import json
from types import SimpleNamespace
from unittest.mock import patch

import requests
from django.test import SimpleTestCase, override_settings

from apps.services.integration_events.tasks import send_webhook_event

EVENT = {
    "event_type": "invoice.processed",
    "tenant": "home",
    "aggregate_type": "Factura",
    "aggregate_uuid": "uuid-1",
    "payload": {"numero": "FE-1"},
    "version": 1,
    "event_id": "11111111-1111-1111-1111-111111111111",
    "occurred_at": "2026-09-10T00:00:00+00:00",
}


class SendWebhookEventSkipTests(SimpleTestCase):
    @override_settings(N8N_WEBHOOK_URL="")
    def test_sin_webhook_url_no_llama_a_requests(self):
        with patch("requests.post") as mock_post:
            result = send_webhook_event.apply(
                kwargs={"event": EVENT}, task_id="test-skip-1"
            ).get()

        mock_post.assert_not_called()
        assert result is None


class SendWebhookEventSuccessTests(SimpleTestCase):
    @override_settings(
        N8N_WEBHOOK_URL="http://n8n.local/webhook/sintel",
        N8N_WEBHOOK_SECRET="s3cret",
    )
    def test_firma_hmac_real_y_headers_correctos(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = SimpleNamespace(status_code=200, text="ok")

            result = send_webhook_event.apply(
                kwargs={"event": EVENT}, task_id="test-success-1"
            ).get()

        assert result is None
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["data"] == json.dumps(EVENT, sort_keys=True).encode("utf-8")

        expected_signature = hmac.new(
            b"s3cret", kwargs["data"], hashlib.sha256
        ).hexdigest()
        assert kwargs["headers"]["X-Sintel-Signature"] == expected_signature
        assert kwargs["headers"]["X-Sintel-Event-Id"] == EVENT["event_id"]
        assert kwargs["headers"]["X-Sintel-Event-Type"] == EVENT["event_type"]


class SendWebhookEvent4xxTests(SimpleTestCase):
    @override_settings(N8N_WEBHOOK_URL="http://n8n.local/webhook/sintel")
    def test_4xx_se_registra_y_no_reintenta(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = SimpleNamespace(status_code=404, text="not found")

            # No debe lanzar -- un 4xx es un error del propio evento, reintentar
            # no lo arregla (contrato documentado en tasks.py).
            result = send_webhook_event.apply(
                kwargs={"event": EVENT}, task_id="test-4xx-1"
            ).get()

        assert result is None
        mock_post.assert_called_once()


class SendWebhookEventRetryableTests(SimpleTestCase):
    @override_settings(N8N_WEBHOOK_URL="http://n8n.local/webhook/sintel")
    def test_5xx_lanza_requestexception_para_que_celery_reintente(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = SimpleNamespace(status_code=500, text="boom")

            with self.assertRaises(requests.exceptions.RequestException):
                send_webhook_event.run(event=EVENT)

    @override_settings(N8N_WEBHOOK_URL="http://n8n.local/webhook/sintel")
    def test_error_de_red_se_repropaga_para_que_celery_reintente(self):
        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("network down")

            with self.assertRaises(requests.exceptions.ConnectionError):
                send_webhook_event.run(event=EVENT)
