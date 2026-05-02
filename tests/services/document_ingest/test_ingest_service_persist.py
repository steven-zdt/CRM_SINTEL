"""
Tests para servicio de ingestión con persistencia (FASE 9).

[WARNING] PRINCIPIOS:
- Persistencia en dominio
- Idempotencia
- Materialización por router de dominio
"""
import pytest
from django.conf import settings
from apps.services.document_ingest.ingest_service import ingest_document


@pytest.mark.django_db
class TestIngestServicePersist:
    """Tests para ingest_service con persistencia."""
    
    @pytest.mark.skipif(
        not getattr(settings, 'FEATURE_XML_PIPELINE', False),
        reason="FEATURE_XML_PIPELINE no está activo"
    )
    def test_persist_invoice(self):
        """Test: Persistir Invoice."""
        # Este test requiere FEATURE_XML_PIPELINE=True
        # y un tenant activo
        pass
    
    @pytest.mark.skipif(
        not getattr(settings, 'FEATURE_XML_PIPELINE', False),
        reason="FEATURE_XML_PIPELINE no está activo"
    )
    def test_persist_idempotency(self):
        """Test: Idempotencia en persistencia."""
        # Este test requiere FEATURE_XML_PIPELINE=True
        # y verificar que no se dupliquen documentos
        pass
