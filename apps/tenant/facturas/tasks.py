from celery import shared_task
from django.db import transaction

from .services import FacturaService


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def procesar_factura_xml_task(self, xml_content, empresa_id, usuario_id):
    """
    Procesa una factura XML UBL 2.1 de forma asíncrona, asegurando aislamiento multi-tenant y protección anti-IDOR.
    """
    try:
        with transaction.atomic():
            FacturaService.crear_desde_xml(xml_content, empresa_id, usuario_id)
    except Exception as exc:
        self.retry(exc=exc)
