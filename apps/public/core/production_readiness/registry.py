"""
Production Check Registry (Fase 1-3, PRODUCTION_EXPOSURE mission).

Modelo conceptual REAL (no simulado) de ProductionReadiness: un
`ProductionReadinessRun` es la ejecucion de TODOS los checks registrados
en un momento dado, contra el codigo/config real -- nunca contra datos
inventados. Reutilizable como proceso recurrente (Fase 70): correr
`manage.py production_readiness` en cualquier release futuro produce una
evaluacion fresca, no una foto congelada de esta sesion.

Regla de no duplicacion (Fase 2 del plan): antes de crear esto se
confirmo por grep que no existe ningun ProductionReadiness/
ProductionCheckRegistry/EnvironmentConfig/FeatureFlag/SecretManager/
HealthService/ReleaseService previo en el repositorio.
"""
from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from django.utils import timezone


class CheckStatus:
    """Resultado de un check individual (Fase 3)."""

    PASS = "PASS"
    WARN = "WARN"
    BLOCKER = "BLOCKER"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"

    ALL = (PASS, WARN, BLOCKER, NOT_APPLICABLE, EXTERNAL_DEPENDENCY)


class Severity:
    """Severidad de un check (Fase 57 -- blocker matrix)."""

    P0 = "P0"  # bloquea
    P1 = "P1"  # bloquea normalmente
    P2 = "P2"  # warning
    P3 = "P3"  # mejora


class ReadinessStatus:
    """Estados del ciclo de vida de una release (Fase 1). Solo los que
    tienen sentido real para este proyecto -- no se agregan estados
    especulativos sin uso (BLUE/GREEN, CANARY, etc. no aplican porque la
    infraestructura real es Docker Compose, ver DEPLOYMENT_RUNBOOK.md)."""

    DRAFT = "DRAFT"
    AUDITING = "AUDITING"
    BLOCKED = "BLOCKED"
    READY_FOR_STAGING = "READY_FOR_STAGING"
    STAGING = "STAGING"
    PRODUCTION_CANDIDATE = "PRODUCTION_CANDIDATE"
    DEPLOYED = "DEPLOYED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass
class CheckResult:
    id: str
    category: str
    severity: str
    owner: str
    status: str
    evidence: str
    timestamp: datetime = field(default_factory=timezone.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "severity": self.severity,
            "owner": self.owner,
            "status": self.status,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat(),
        }


_REGISTRY: list[tuple[str, str, str, str, Callable[[], tuple[str, str]]]] = []


def register_check(check_id: str, category: str, severity: str, owner: str):
    """
    Decorador para registrar un check. La funcion decorada debe retornar
    una tupla (status, evidence) usando CheckStatus.* -- nunca debe
    imprimir directamente ni lanzar excepciones no controladas (el
    runner ya captura cualquier excepcion como BLOCKER, per Fase 3: un
    check que crashea es, en si mismo, una senal de que algo esta mal).

    Categorias (Fase 2): APPLICATION, DATABASE, SECURITY, TENANT, INFRA,
    BACKUP, OBSERVABILITY, PERFORMANCE, DOCUMENTATION, FISCAL, EXTERNAL.
    """

    def decorator(fn: Callable[[], tuple[str, str]]):
        _REGISTRY.append((check_id, category, severity, owner, fn))
        return fn

    return decorator


def run_all_checks() -> list[CheckResult]:
    """Ejecuta TODOS los checks registrados contra el estado real del
    sistema. Nunca falla globalmente por un check individual roto -- un
    check que lanza excepcion se registra como BLOCKER con el traceback
    como evidencia (un check roto es, el mismo, un hallazgo real)."""
    # Import tardio: fuerza que checks.py (que puebla el registro via
    # decoradores) ya se haya importado antes de correr.
    from . import checks  # noqa: F401

    results = []
    for check_id, category, severity, owner, fn in _REGISTRY:
        try:
            status, evidence = fn()
        except Exception:  # noqa: BLE001 -- un check roto es un hallazgo real
            status = CheckStatus.BLOCKER
            evidence = f"El check crasheo al ejecutarse:\n{traceback.format_exc()}"
        results.append(
            CheckResult(
                id=check_id, category=category, severity=severity,
                owner=owner, status=status, evidence=evidence,
            )
        )
    return results


def compute_blockers(results: list[CheckResult]) -> list[CheckResult]:
    """Fase 3: BLOCKER -> no release. WARN no bloquea automaticamente."""
    return [r for r in results if r.status == CheckStatus.BLOCKER]


def compute_scorecard(results: list[CheckResult]) -> dict:
    """
    Fase 56: score por categoria. NUNCA se usa como sustituto de
    blockers -- ver overall_status() para la regla real (un solo BLOCKER
    en cualquier categoria hace NOT_READY sin importar el score global).
    """
    by_category: dict[str, dict[str, int]] = {}
    for r in results:
        cat = by_category.setdefault(r.category, {s: 0 for s in CheckStatus.ALL})
        cat[r.status] += 1
    return by_category


def overall_status(results: list[CheckResult]) -> str:
    """
    Fase 65-66: veredicto final, NUNCA 'certificado'. Solo 4 valores
    posibles, exactamente los que el plan autoriza.
    """
    blockers = compute_blockers(results)
    if blockers:
        return "NOT_READY"
    external = [r for r in results if r.status == CheckStatus.EXTERNAL_DEPENDENCY]
    if external:
        return "READY_WITH_EXTERNAL_DEPENDENCIES"
    return "READY"
