"""AI-VECTOR-07 -- RetrievalTool integrada al AI Engine.

Verifica, con evidencia real (DB + AIEngine.run_tool end-to-end):
- la tool esta registrada y NO rompe el punto de entrada (`run_tool` sin tocar)
- doble gate: AI_READ_ENABLED (engine) + AI_RETRIEVAL_ENABLED (tool)
- el alcance organizacional se aplica DESDE el AIContext (no un parametro)
- AI WRITE sigue deshabilitado
"""

from unittest.mock import patch

from django.test import override_settings

from apps.services.ai.engine import run_tool
from apps.services.ai.providers.embedding_base import EmbeddingResult
from apps.services.ai.tools import get_tool, tool_metadata
from apps.tenant.ai_knowledge.services import EmbeddingService
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

DIM = 768


class _Stub:
    name = "stub"
    model = "stub-model"
    dimension = DIM

    def _vec(self, text):
        import hashlib

        h = hashlib.sha256(text.encode()).digest()
        return ([b / 255.0 for b in h] * 24)[:DIM]

    def embed_documents(self, texts):
        return EmbeddingResult(
            vectors=[self._vec(t) for t in texts], model=self.model,
            provider=self.name, dimension=self.dimension,
        )

    def embed_query(self, text):
        return self._vec(text)


class _FakeRequest:
    def __init__(self, user, tenant=None):
        self.user = user
        self.tenant = tenant


ALL_ON = {"AI_ENABLED": True, "AI_READ_ENABLED": True, "AI_RETRIEVAL_ENABLED": True}


def _patched_provider():
    stub = _Stub()
    return (
        patch(
            "apps.tenant.ai_knowledge.services.embedding_service.get_embedding_provider",
            return_value=stub,
        ),
        patch(
            "apps.tenant.ai_knowledge.services.retrieval_service.get_embedding_provider",
            return_value=stub,
        ),
    )


class RetrievalToolTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA POC S.A.S.", nit="900222222", direccion="Cra 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B")
        self.profile = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="EMPRESA",
        )
        self._p1, self._p2 = _patched_provider()
        self._p1.start(); self._p2.start()
        self.addCleanup(self._p1.stop); self.addCleanup(self._p2.stop)

        emb = EmbeddingService()
        emb.index_text(empresa=self.empresa, source_type="cliente_observaciones",
                       source_id="C1", text="condiciones comerciales especiales de pago a 45 dias")
        emb.index_text(empresa=self.empresa, source_type="producto_descripcion",
                       source_id="P1", text="tornillo de acero inoxidable para exteriores")
        emb.index_text(empresa=self.empresa, source_type="cliente_observaciones",
                       source_id="C_SEDE_B", text="nota restringida de la sede B",
                       metadata={"sede_id": self.sede_b.id})

    def _req(self):
        return _FakeRequest(self.user, self.tenant)

    # ---------------------------------------------------------------- #
    def test_tool_registrada_y_metadata(self):
        tool = get_tool("buscar_conocimiento")
        assert tool is not None
        assert tool.kind.value == "READ"
        assert tool.domain == "ai_knowledge"
        names = {m["name"] for m in tool_metadata()}
        assert "buscar_conocimiento" in names

    @override_settings(AI_ENABLED=True, AI_READ_ENABLED=True)  # AI_RETRIEVAL_ENABLED por defecto: False
    def test_deshabilitada_por_defecto_aunque_read_este_on(self):
        res = run_tool("buscar_conocimiento", self._req(), query="condiciones de pago")
        assert res.status == "PERMISSION_DENIED"
        assert "recuperacion semantica" in res.message.lower()

    @override_settings(AI_ENABLED=True, AI_READ_ENABLED=False, AI_RETRIEVAL_ENABLED=True)
    def test_bloqueada_por_el_flag_de_kind_del_engine(self):
        res = run_tool("buscar_conocimiento", self._req(), query="condiciones de pago")
        assert res.status == "PERMISSION_DENIED"

    @override_settings(**ALL_ON)
    def test_retrieval_ok_devuelve_hits(self):
        res = run_tool("buscar_conocimiento", self._req(), query="condiciones comerciales de pago", k=3)
        assert res.status == "OK"
        assert res.data and res.data[0]["source_id"] == "C1"
        assert set(res.data[0]) == {"content", "source_type", "source_id", "document_uuid", "score"}

    @override_settings(**ALL_ON)
    def test_query_vacia_es_validation_error(self):
        res = run_tool("buscar_conocimiento", self._req(), query="   ")
        assert res.status == "VALIDATION_ERROR"

    @override_settings(**ALL_ON)
    def test_k_fuera_de_rango(self):
        assert run_tool("buscar_conocimiento", self._req(), query="x", k=0).status == "VALIDATION_ERROR"
        assert run_tool("buscar_conocimiento", self._req(), query="x", k=99).status == "VALIDATION_ERROR"

    @override_settings(**ALL_ON)
    def test_alcance_empresa_ve_el_doc_de_sede_b(self):
        res = run_tool("buscar_conocimiento", self._req(), query="nota restringida sede", k=10)
        assert any(h["source_id"] == "C_SEDE_B" for h in res.data)

    @override_settings(**ALL_ON)
    def test_alcance_sede_a_no_ve_el_doc_de_sede_b(self):
        self.profile.alcance = "SEDE"
        self.profile.save()
        self.profile.sedes_asignadas.set([self.sede_a])
        res = run_tool("buscar_conocimiento", self._req(), query="nota restringida sede", k=10)
        got = {h["source_id"] for h in res.data}
        assert "C_SEDE_B" not in got  # unauthorized_retrieval = 0
        # los docs sin sede siguen visibles
        res2 = run_tool("buscar_conocimiento", self._req(), query="condiciones comerciales de pago", k=10)
        assert any(h["source_id"] == "C1" for h in res2.data)

    @override_settings(**ALL_ON)
    def test_write_sigue_deshabilitado(self):
        from django.conf import settings

        assert getattr(settings, "AI_WRITE_ENABLED", False) is False
