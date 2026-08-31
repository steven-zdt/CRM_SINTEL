"""
Tests de humo del Production Check Registry (Fase 55 -- ProductionReadinessRun).

No revalidan cada regla de negocio individual de cada check (eso ya
esta cubierto por evidencia real documentada en docs/production/ y por
las suites de las misiones que cada check referencia) -- validan que el
FRAMEWORK en si funcione: que el registro se pueble, que corra sin
crashear, que el veredicto final respete la regla de negocio (Fase 56:
un solo BLOCKER hace NOT_READY sin importar el score).
"""
import pytest

from apps.public.core.production_readiness.registry import (
    CheckResult,
    CheckStatus,
    _REGISTRY,
    compute_blockers,
    overall_status,
    run_all_checks,
)


def test_registry_se_puebla_con_checks_reales():
    from apps.public.core.production_readiness import checks  # noqa: F401

    assert len(_REGISTRY) >= 15, "Se esperaban al menos 15 checks registrados"


@pytest.mark.django_db
def test_run_all_checks_no_crashea_y_produce_resultados():
    results = run_all_checks()
    assert len(results) == len(_REGISTRY)
    for r in results:
        assert isinstance(r, CheckResult)
        assert r.status in CheckStatus.ALL
        assert r.id and r.category and r.severity and r.owner


def test_overall_status_un_solo_blocker_hace_not_ready():
    """Fase 56: NO usar un porcentaje como sustituto de blockers -- 95%
    de PASS con 1 BLOCKER sigue siendo NOT_READY."""
    results = [
        CheckResult(id=f"X-{i}", category="APPLICATION", severity="P2", owner="core", status=CheckStatus.PASS, evidence="ok")
        for i in range(19)
    ] + [
        CheckResult(id="SEC-critico", category="SECURITY", severity="P0", owner="core", status=CheckStatus.BLOCKER, evidence="hallazgo real"),
    ]
    assert overall_status(results) == "NOT_READY"
    assert len(compute_blockers(results)) == 1


def test_overall_status_sin_blockers_pero_con_external_dependency():
    results = [
        CheckResult(id="X", category="APPLICATION", severity="P2", owner="core", status=CheckStatus.PASS, evidence="ok"),
        CheckResult(id="DIAN", category="FISCAL", severity="P0", owner="facturas", status=CheckStatus.EXTERNAL_DEPENDENCY, evidence="sin credenciales"),
    ]
    assert overall_status(results) == "READY_WITH_EXTERNAL_DEPENDENCIES"


def test_overall_status_todo_pass_es_ready():
    results = [
        CheckResult(id="X", category="APPLICATION", severity="P2", owner="core", status=CheckStatus.PASS, evidence="ok"),
    ]
    assert overall_status(results) == "READY"


def test_check_no_crashea_el_run_completo_si_uno_falla(monkeypatch):
    """Un check individual roto se convierte en BLOCKER, nunca aborta
    el resto de la corrida (Fase 3)."""
    from apps.public.core.production_readiness import registry

    def _broken():
        raise RuntimeError("check roto deliberadamente")

    monkeypatch.setattr(
        registry, "_REGISTRY",
        [("BROKEN-01", "APPLICATION", "P0", "core", _broken)],
    )
    results = registry.run_all_checks()
    assert len(results) == 1
    assert results[0].status == CheckStatus.BLOCKER
    assert "check roto deliberadamente" in results[0].evidence
