"""
CONSOLE_TENANTS_CRUD / TENANT_LIFECYCLE (docs/console/TENANT_LIFECYCLE.md,
docs/console/TRIAL_PERIOD.md) -- tests dirigidos de la logica de trial/
lifecycle, puros (sin necesidad de crear un schema de tenant real, salvo
donde se indica explicitamente).

Complementan (no duplican) la evidencia end-to-end real ya documentada en
docs/console/CONSOLE_TENANTS_FINAL_REPORT.md: creacion de 2 tenants QA
reales, trial forzado a "ayer" sin ejecutar Celery -> bloqueo real
confirmado por curl + verificacion directa de BD.
"""
from datetime import timedelta
from types import SimpleNamespace

from django.utils import timezone

from apps.public.tenants.services.lifecycle import (
    LifecycleStatus,
    compute_lifecycle_status,
    is_trial_expired,
    reconcile_tenant_lifecycle,
    trial_days_remaining,
)


def _fake_client(*, on_trial=True, paid_until=None, is_active=True):
    """Objeto minimo que expone los mismos atributos que Client, sin BD."""
    return SimpleNamespace(
        on_trial=on_trial, paid_until=paid_until, is_active=is_active,
        schema_name="fake_schema_test",
    )


class TestIsTrialExpired:
    def test_no_on_trial_nunca_expira(self):
        c = _fake_client(on_trial=False, paid_until=timezone.localdate() - timedelta(days=10))
        assert is_trial_expired(c) is False

    def test_sin_paid_until_nunca_expira(self):
        c = _fake_client(on_trial=True, paid_until=None)
        assert is_trial_expired(c) is False

    def test_paid_until_ayer_expirado(self):
        c = _fake_client(on_trial=True, paid_until=timezone.localdate() - timedelta(days=1))
        assert is_trial_expired(c) is True

    def test_paid_until_hoy_vigente(self):
        """FASE 22 del plan (caso exacto): politica elegida y documentada
        explicitamente (CONSOLE_TENANTS_BASELINE.md) -- paid_until es
        INCLUSIVE (el tenant sigue activo todo el dia calendario
        indicado, consistente con el nombre del campo 'pagado HASTA').
        Expira al iniciar el dia SIGUIENTE, no a la medianoche exacta de
        paid_until. Sin ambiguedad de > vs >= -- se usa estrictamente >."""
        c = _fake_client(on_trial=True, paid_until=timezone.localdate())
        assert is_trial_expired(c) is False

    def test_paid_until_manana_vigente(self):
        c = _fake_client(on_trial=True, paid_until=timezone.localdate() + timedelta(days=1))
        assert is_trial_expired(c) is False


class TestComputeLifecycleStatus:
    def test_expired_tiene_prioridad_sobre_is_active_true(self):
        """La fecha es determinante (Fase 16) -- si el trial vencio, el
        estado es EXPIRED sin importar que is_active todavia no se haya
        reconciliado a False."""
        c = _fake_client(on_trial=True, paid_until=timezone.localdate() - timedelta(days=1), is_active=True)
        assert compute_lifecycle_status(c) == LifecycleStatus.EXPIRED

    def test_suspendido_manualmente_distinto_de_expirado(self):
        """FASE 27: MANUALLY_SUSPENDED (aqui SUSPENDED_BY_ADMIN) no debe
        confundirse con TRIAL_EXPIRED -- is_active=False sin trial
        vencido implica suspension administrativa."""
        c = _fake_client(on_trial=False, paid_until=None, is_active=False)
        assert compute_lifecycle_status(c) == LifecycleStatus.SUSPENDED_BY_ADMIN

    def test_active_trial(self):
        c = _fake_client(on_trial=True, paid_until=timezone.localdate() + timedelta(days=5), is_active=True)
        assert compute_lifecycle_status(c) == LifecycleStatus.ACTIVE_TRIAL

    def test_active_subscription_sin_trial_con_fecha(self):
        c = _fake_client(on_trial=False, paid_until=timezone.localdate() + timedelta(days=30), is_active=True)
        assert compute_lifecycle_status(c) == LifecycleStatus.ACTIVE_SUBSCRIPTION

    def test_no_expiration_sin_trial_sin_fecha(self):
        c = _fake_client(on_trial=False, paid_until=None, is_active=True)
        assert compute_lifecycle_status(c) == LifecycleStatus.NO_EXPIRATION


class TestTrialDaysRemaining:
    def test_dias_restantes_positivos(self):
        c = _fake_client(on_trial=True, paid_until=timezone.localdate() + timedelta(days=7))
        assert trial_days_remaining(c) == 7

    def test_dias_restantes_negativos_si_vencido(self):
        c = _fake_client(on_trial=True, paid_until=timezone.localdate() - timedelta(days=3))
        assert trial_days_remaining(c) == -3

    def test_none_si_no_aplica(self):
        assert trial_days_remaining(_fake_client(on_trial=False)) is None


class TestReconcileTenantLifecycle:
    def test_no_reconcilia_si_no_expirado(self):
        c = _fake_client(on_trial=True, paid_until=timezone.localdate() + timedelta(days=1), is_active=True)
        changed = reconcile_tenant_lifecycle(c, save=False)
        assert changed is False
        assert c.is_active is True

    def test_reconcilia_desactiva_si_expirado(self):
        """FASE 18/20: la reconciliacion debe desactivar un tenant con
        trial vencido, sin depender de Celery -- esta es la MISMA
        funcion que llama tanto el middleware (runtime) como la tarea
        periodica de Celery, nunca hay 2 implementaciones de la regla."""
        c = _fake_client(on_trial=True, paid_until=timezone.localdate() - timedelta(days=1), is_active=True)
        changed = reconcile_tenant_lifecycle(c, save=False)
        assert changed is True
        assert c.is_active is False

    def test_no_reactiva_suspendido_manualmente(self):
        """FASE 26: reconcile_tenant_lifecycle NUNCA reactiva -- solo
        desactiva. Un tenant ya inactivo (por cualquier causa) se queda
        inactivo; la reactivacion es siempre una accion administrativa
        explicita (extend-trial / toggle-active)."""
        c = _fake_client(on_trial=False, paid_until=None, is_active=False)
        changed = reconcile_tenant_lifecycle(c, save=False)
        assert changed is False
        assert c.is_active is False

    def test_idempotente_ya_reconciliado(self):
        """Un tenant ya reconciliado (is_active=False, trial vencido) no
        vuelve a marcarse como cambiado en llamadas subsecuentes."""
        c = _fake_client(on_trial=True, paid_until=timezone.localdate() - timedelta(days=5), is_active=False)
        assert reconcile_tenant_lifecycle(c, save=False) is False
