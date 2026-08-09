"""
Tests con fixtures sinteticas (monkeypatch de TENANT_APPS_DIR a un tmp_path)
- no dependen del estado real del repositorio, para poder probar casos
BUENOS y MALOS a proposito (F14.23/F14.24 del prompt maestro).
"""
import pytest

from tools.organizational_governance import extract


@pytest.fixture
def fake_app(tmp_path, monkeypatch):
    def _make(app_label: str, models_py: str) -> None:
        app_dir = tmp_path / app_label
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "models.py").write_text(models_py, encoding="utf-8")
        monkeypatch.setattr(extract, "TENANT_APPS_DIR", tmp_path)

    return _make


def test_extract_models_recognizes_sintel_tenant_base_model(fake_app):
    fake_app(
        "demo",
        """
from apps.tenant.core.models import SintelTenantBaseModel
from django.db import models

class Legitimo(SintelTenantBaseModel):
    nombre = models.CharField(max_length=50)
""",
    )
    models = extract.extract_models_for_app("demo")
    assert len(models) == 1
    assert models[0].qualified_id == "demo.Legitimo"
    assert models[0].has_empresa is True
    assert models[0].has_sede is False


def test_extract_models_detects_sede_aware_model_and_area_field(fake_app):
    fake_app(
        "demo",
        """
from apps.tenant.core.models import SedeAwareModel
from django.db import models

class OrdenDemo(SedeAwareModel):
    area = models.ForeignKey('empresa.Area', on_delete=models.SET_NULL, null=True)
""",
    )
    models = extract.extract_models_for_app("demo")
    assert len(models) == 1
    m = models[0]
    assert m.inherits_sede_aware_model is True
    assert m.has_sede is True
    assert m.has_area is True


def test_extract_models_excludes_text_choices_enum(fake_app):
    """[F14.23-style: caso malo que NO debe colarse] Un TextChoices no es
    un modelo - regresion directa del bug real que la auditoria EKG
    2026-08-07 encontro y corrigio para su propio extractor (documentacion/
    INFORME_FINAL_EKG_GOBERNANZA_2026-08-07.md, bug #4)."""
    fake_app(
        "demo",
        """
from django.db import models

class RolDemo(models.TextChoices):
    ADMIN = 'ADMIN', 'Administrador'
""",
    )
    models = extract.extract_models_for_app("demo")
    assert models == []


def test_extract_models_flags_direct_models_model_inheritance(fake_app):
    """[F14.23] Caso MALO real: hereda models.Model directo, no una base
    tenant - debe seguir apareciendo en el grafo (con scope SCOPE_NONE) para
    que ARCH-002 lo pueda detectar; extract.py no filtra este caso, solo lo
    clasifica correctamente."""
    fake_app(
        "demo",
        """
from django.db import models

class Huerfano(models.Model):
    nombre = models.CharField(max_length=50)
""",
    )
    models = extract.extract_models_for_app("demo")
    assert len(models) == 1
    assert models[0].has_empresa is False
    assert "Model" in models[0].bases


def test_extract_adrs_accepts_status_in_english_regression_guard(tmp_path, monkeypatch):
    """Regresion directa: docs/ADR-001-*.md usa '**Status:**' (ingles) en
    vez de '**Estado:**' (espanol, usado por ADR-002..005) - hallazgo real
    encontrado durante el desarrollo de este extractor (antes reportaba
    ADR-001 como estado UNKNOWN por error, no porque el ADR real lo este)."""
    monkeypatch.setattr(extract, "DOCS_DIR", tmp_path)
    monkeypatch.setattr(extract, "PROJECT_ROOT", tmp_path)
    (tmp_path / "ADR-001-demo.md").write_text(
        "# ADR-001: Demo\n\n**Status:** ACCEPTED\n**Date:** 2026-01-01\n",
        encoding="utf-8",
    )
    adrs = extract.extract_adrs()
    assert len(adrs) == 1
    assert adrs[0].estado == "ACCEPTED"


def test_app_uses_organizational_scope_ignores_negated_docstring_mention(tmp_path, monkeypatch):
    """Regresion directa: apps/tenant/ventas/services/api_mixins.py:27 dice
    literalmente 'no OrganizationalScope' en un docstring explicando que
    usa OrganizationalContext en su lugar - un check de texto crudo lo
    contaba como 'la app SI usa OrganizationalScope', exactamente al reves
    de la realidad."""
    monkeypatch.setattr(extract, "TENANT_APPS_DIR", tmp_path)
    services_dir = tmp_path / "demo" / "services"
    services_dir.mkdir(parents=True)
    (services_dir / "api_mixins.py").write_text(
        '"""Resuelve la sede activa (OrganizationalContext, no OrganizationalScope)."""\n'
        "def foo():\n"
        "    pass\n",
        encoding="utf-8",
    )
    assert extract.app_uses_organizational_scope("demo") is False


def test_app_uses_organizational_context_detects_real_ast_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(extract, "TENANT_APPS_DIR", tmp_path)
    services_dir = tmp_path / "demo" / "services"
    services_dir.mkdir(parents=True)
    (services_dir / "api_mixins.py").write_text(
        "from apps.tenant.core.services.organizational_context import OrganizationalContext\n\n"
        "def foo(request):\n"
        "    return OrganizationalContext.resolve(request).sede_id\n",
        encoding="utf-8",
    )
    assert extract.app_uses_organizational_context("demo") is True
    assert extract.app_uses_organizational_scope("demo") is False


def test_extract_models_excludes_sede_aware_model_definition_itself(fake_app):
    fake_app(
        "core",
        """
from django.db import models

class SintelTenantBaseModel(models.Model):
    empresa = models.ForeignKey('empresa.Empresa', on_delete=models.PROTECT)

class SedeAwareModel(SintelTenantBaseModel):
    sede = models.ForeignKey('empresa.Sede', on_delete=models.PROTECT)
""",
    )
    models = extract.extract_models_for_app("core")
    names = {m.class_name for m in models}
    assert "SedeAwareModel" not in names, "la definicion del mixin no debe contarse como consumidor"
    assert "SintelTenantBaseModel" in names
