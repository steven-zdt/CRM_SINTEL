"""
Checks reales del Production Check Registry (Fase 4-52 del plan
PRODUCTION_EXPOSURE, subset automatizable).

Cada check consulta el estado REAL del sistema (settings, filesystem,
BD, comandos ya existentes) -- ninguno simula un resultado. Donde la
verificacion requiere infraestructura que no existe en este entorno
(TLS real, DNS publico, staging, carga), el check retorna
NOT_APPLICABLE con la razon explicita, nunca un PASS fingido.
"""
from __future__ import annotations

import os
import re
import subprocess

from django.conf import settings

from .registry import CheckStatus, Severity, register_check

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


# ---------------------------------------------------------------------------
# APPLICATION
# ---------------------------------------------------------------------------

@register_check("APP-01-debug", "APPLICATION", Severity.P0, "core")
def check_debug():
    if settings.DEBUG:
        return CheckStatus.BLOCKER, (
            "settings.DEBUG=True actualmente. Debe ser False antes de exponer a produccion "
            "(revela tracebacks, SQL, y variables de entorno en errores 500)."
        )
    return CheckStatus.PASS, "settings.DEBUG=False"


@register_check("APP-02-secret-key", "APPLICATION", Severity.P0, "core")
def check_secret_key():
    key = getattr(settings, "SECRET_KEY", "")
    if not key or len(key) < 32:
        return CheckStatus.BLOCKER, "SECRET_KEY ausente o demasiado corta (<32 chars)."
    insecure_markers = ("django-insecure", "changeme", "CHANGE_ME", "secret-key")
    if any(m in key for m in insecure_markers):
        return CheckStatus.BLOCKER, "SECRET_KEY contiene un marcador de valor por defecto/inseguro."
    return CheckStatus.PASS, f"SECRET_KEY definida, {len(key)} caracteres, sin marcadores inseguros."


@register_check("APP-03-allowed-hosts", "APPLICATION", Severity.P0, "core")
def check_allowed_hosts():
    hosts = getattr(settings, "ALLOWED_HOSTS", [])
    if not hosts:
        return CheckStatus.BLOCKER, "ALLOWED_HOSTS vacio -- Django rechazaria todas las requests."
    if "*" in hosts:
        return CheckStatus.BLOCKER, "ALLOWED_HOSTS contiene '*' -- acepta cualquier Host header (riesgo de cache poisoning / host header injection)."
    return CheckStatus.PASS, f"ALLOWED_HOSTS definido explicitamente: {hosts}"


@register_check("APP-04-check-deploy", "APPLICATION", Severity.P1, "core")
def check_django_deploy_check():
    """Fase 7: manage.py check --deploy."""
    try:
        result = subprocess.run(
            ["python", "manage.py", "check", "--deploy"],
            cwd=_REPO_ROOT, capture_output=True, text=True, timeout=60,
        )
    except Exception as exc:
        return CheckStatus.WARN, f"No se pudo ejecutar 'manage.py check --deploy': {exc}"
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0 and "System check identified" not in output:
        return CheckStatus.BLOCKER, f"'manage.py check --deploy' fallo (exit {result.returncode}):\n{output[-2000:]}"
    warning_count = output.count("(security.")
    if warning_count:
        return CheckStatus.WARN, f"'manage.py check --deploy' reporta {warning_count} security warning(s) (esperado en DEBUG=True dev):\n{output[-2000:]}"
    return CheckStatus.PASS, output[-500:] or "Sin warnings."


# ---------------------------------------------------------------------------
# SECURITY
# ---------------------------------------------------------------------------

@register_check("SEC-01-secret-scanning", "SECURITY", Severity.P0, "core")
def check_hardcoded_secrets():
    """Fase 6: grep de patrones de secretos hardcodeados en codigo
    fuente real (.py/.js), excluyendo tests/migrations/settings (donde
    referenciar el NOMBRE de una env var es normal) y el propio .env."""
    patterns = re.compile(
        r"(AWS_SECRET|BEGIN (RSA |EC )?PRIVATE KEY|-----BEGIN CERTIFICATE-----)"
    )
    hits = []
    search_dirs = ["apps", "config"]
    for base in search_dirs:
        base_path = os.path.join(_REPO_ROOT, base)
        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "migrations", "tests", "node_modules", "static", "staticfiles", "production_readiness")]
            for fname in files:
                if not fname.endswith((".py", ".js")):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                except OSError:
                    continue
                if patterns.search(content):
                    hits.append(os.path.relpath(fpath, _REPO_ROOT))
    if hits:
        return CheckStatus.BLOCKER, f"Posibles secretos/claves privadas hardcodeadas en: {hits[:10]}"
    return CheckStatus.PASS, "Sin patrones de secretos hardcodeados (AWS_SECRET/PRIVATE KEY/CERTIFICATE) en apps/config."


@register_check("SEC-02-cors-csrf", "SECURITY", Severity.P1, "core")
def check_cors_csrf():
    cors = getattr(settings, "CORS_ALLOWED_ORIGINS", None)
    cors_all = getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False)
    csrf_trusted = getattr(settings, "CSRF_TRUSTED_ORIGINS", [])
    problems = []
    if cors_all:
        problems.append("CORS_ALLOW_ALL_ORIGINS=True (abierto a cualquier origen)")
    if "*" in (csrf_trusted or []):
        problems.append("CSRF_TRUSTED_ORIGINS contiene '*'")
    if problems:
        return CheckStatus.WARN, "; ".join(problems) + " -- revisar antes de producción (puede ser deliberado para dev multi-dominio)."
    return CheckStatus.PASS, f"CORS_ALLOWED_ORIGINS={cors!r}, CSRF_TRUSTED_ORIGINS acotado (sin '*')."


@register_check("SEC-03-mock-transport-guard", "SECURITY", Severity.P0, "facturas")
def check_fiscal_mock_guard():
    """Fase 45: el mock de transporte DIAN debe estar deshabilitado por
    defecto y NUNCA activable por el cliente (querystring/cookie/body)."""
    allow_mock = getattr(settings, "FISCAL_ALLOW_MOCK_TRANSPORT", False)
    if allow_mock and not settings.DEBUG:
        return CheckStatus.BLOCKER, "FISCAL_ALLOW_MOCK_TRANSPORT=True fuera de DEBUG -- el mock de DIAN podria activarse en producción."
    if allow_mock:
        return CheckStatus.WARN, "FISCAL_ALLOW_MOCK_TRANSPORT=True (esperado en DEBUG=True dev) -- DEBE ser False antes de exponer a producción."
    return CheckStatus.PASS, "FISCAL_ALLOW_MOCK_TRANSPORT=False (default seguro)."


# Fase 44: 65 ocurrencias clasificadas manualmente 2026-08-31, todas
# legitimas (fallbacks getattr(settings,...), comentarios/docstrings,
# codigo gateado por settings.DEBUG, whitelist de seguridad deliberada
# en capas, herramientas de dev standalone, health-check propio). Ver
# docs/production/SEC04_LOCALHOST_CLASSIFICATION.md para el detalle
# completo por categoria -- no se reclasifican en cada corrida, solo se
# senalan ocurrencias NUEVAS por encima de este baseline.
_SEC04_BASELINE_CLASSIFIED = 65


@register_check("SEC-04-localhost-leaks", "SECURITY", Severity.P2, "core")
def check_localhost_leaks():
    """Fase 44: localhost/127.0.0.1 hardcodeado fuera de settings/tests
    -- candidato a URL de desarrollo filtrada a produccion. Compara
    contra un baseline ya clasificado (ver
    docs/production/SEC04_LOCALHOST_CLASSIFICATION.md) en vez de WARN
    perpetuo sin salida -- solo senala ocurrencias NUEVAS para revision
    dirigida."""
    pattern = re.compile(r"localhost|127\.0\.0\.1")
    hits = []
    for base in ("apps",):
        base_path = os.path.join(_REPO_ROOT, base)
        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "tests", "test", "node_modules", "static", "staticfiles", "migrations")]
            if "/tests/" in root.replace("\\", "/") or root.replace("\\", "/").endswith("/tests"):
                continue
            for fname in files:
                if not fname.endswith((".py", ".js")):
                    continue
                if fname.startswith("test_"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, encoding="utf-8", errors="ignore") as fh:
                        for lineno, line in enumerate(fh, 1):
                            if pattern.search(line) and "getenv" not in line and "os.environ" not in line:
                                hits.append(f"{os.path.relpath(fpath, _REPO_ROOT)}:{lineno}")
                except OSError:
                    continue
    if not hits:
        return CheckStatus.PASS, "Sin localhost/127.0.0.1 hardcodeado fuera de tests/settings."
    if len(hits) <= _SEC04_BASELINE_CLASSIFIED:
        return CheckStatus.PASS, (
            f"{len(hits)} ocurrencias, todas dentro del baseline ya clasificado "
            f"({_SEC04_BASELINE_CLASSIFIED}, 2026-08-31) -- ver "
            f"docs/production/SEC04_LOCALHOST_CLASSIFICATION.md."
        )
    nuevas = len(hits) - _SEC04_BASELINE_CLASSIFIED
    return CheckStatus.WARN, (
        f"{len(hits)} ocurrencias -- {nuevas} por encima del baseline clasificado "
        f"({_SEC04_BASELINE_CLASSIFIED}). Revisar las nuevas antes de asumir que son "
        f"tan legitimas como las ya documentadas en "
        f"docs/production/SEC04_LOCALHOST_CLASSIFICATION.md. Ultimas del listado: {hits[-10:]}"
    )


# ---------------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------------

@register_check("DB-01-pending-migrations", "DATABASE", Severity.P0, "core")
def check_pending_migrations():
    try:
        result = subprocess.run(
            ["python", "manage.py", "makemigrations", "--check", "--dry-run"],
            cwd=_REPO_ROOT, capture_output=True, text=True, timeout=90,
        )
    except Exception as exc:
        return CheckStatus.WARN, f"No se pudo ejecutar makemigrations --check: {exc}"
    if result.returncode != 0:
        return CheckStatus.BLOCKER, f"Hay cambios de modelo sin migracion generada:\n{(result.stdout + result.stderr)[-1500:]}"
    return CheckStatus.PASS, "Sin migraciones pendientes de generar."


# ---------------------------------------------------------------------------
# TENANT (evidencia ya recolectada en misiones previas de esta sesion --
# no se re-ejecuta un E2E completo en cada corrida de este check, se
# referencia la evidencia real y su fecha).
# ---------------------------------------------------------------------------

@register_check("TEN-01-isolation-evidence", "TENANT", Severity.P0, "tenants")
def check_tenant_isolation_evidence():
    ref = os.path.join(_REPO_ROOT, "docs", "e2e", "ONBOARDING_E2E_REPORT.md")
    if not os.path.exists(ref):
        return CheckStatus.WARN, "Sin evidencia documentada de aislamiento cross-tenant en docs/e2e/."
    return CheckStatus.PASS, (
        "Aislamiento cross-tenant verificado en vivo (2026-08-31, docs/e2e/ONBOARDING_E2E_REPORT.md, "
        "Fase 19): sesion de un tenant contra otro -> 401 + invalidacion forzada de cookie. "
        "Nota: es evidencia de una corrida real puntual, no una suite automatizada corriendo en CI."
    )


@register_check("TEN-02-privilege-escalation-fix", "TENANT", Severity.P0, "tenants")
def check_privilege_escalation_fixed():
    """Regresion especifica del hallazgo critico E2E-03 (owner_is_staff
    default=True) -- confirma que el codigo actual tiene el default
    seguro, no solo que en algun momento se corrigio."""
    try:
        from apps.public.tenants.api.serializers import OnboardTenantWithOwnerSerializer

        field = OnboardTenantWithOwnerSerializer().fields["owner_is_staff"]
    except Exception as exc:
        return CheckStatus.BLOCKER, f"No se pudo inspeccionar OnboardTenantWithOwnerSerializer: {exc}"
    if field.default is not False:
        return CheckStatus.BLOCKER, (
            f"REGRESION CRITICA: owner_is_staff.default={field.default!r} (debe ser False). "
            "Ver docs/e2e/ONBOARDING_E2E_REPORT.md hallazgo E2E-03 -- escalacion de privilegios real."
        )
    return CheckStatus.PASS, "owner_is_staff.default=False -- fix de escalacion de privilegios (E2E-03) vigente."


@register_check("TEN-03-trial-enforcement", "TENANT", Severity.P0, "tenants")
def check_trial_enforcement_wired():
    """Confirma que el middleware realmente invoca la reconciliacion de
    lifecycle -- no solo que el modulo lifecycle.py exista."""
    try:
        import inspect

        from apps.public.tenants.middleware import TenantSecurityMiddleware

        src = inspect.getsource(TenantSecurityMiddleware.__call__)
    except Exception as exc:
        return CheckStatus.BLOCKER, f"No se pudo inspeccionar TenantSecurityMiddleware: {exc}"
    if "reconcile_tenant_lifecycle" not in src:
        return CheckStatus.BLOCKER, "TenantSecurityMiddleware ya no invoca reconcile_tenant_lifecycle() -- el bloqueo por trial vencido podria haberse desconectado."
    return CheckStatus.PASS, "TenantSecurityMiddleware invoca reconcile_tenant_lifecycle() en cada request (verificado en vivo, docs/console/TENANT_E2E_TEST.md)."


# ---------------------------------------------------------------------------
# INFRA
# ---------------------------------------------------------------------------

@register_check("INFRA-01-services-up", "INFRA", Severity.P1, "devops")
def check_docker_services():
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            cwd=_REPO_ROOT, capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        return CheckStatus.WARN, (
            "Binario 'docker' no disponible en este contexto de ejecucion -- este check "
            "requiere correrse desde el HOST (no dentro del contenedor 'web', que no tiene "
            "acceso al socket de Docker). Ejecutar 'docker compose ps' manualmente desde el "
            "host para verificar este item."
        )
    except Exception as exc:
        return CheckStatus.WARN, f"No se pudo consultar docker compose ps: {exc}"
    if result.returncode != 0:
        return CheckStatus.WARN, f"docker compose ps fallo: {result.stderr[-500:]}"
    import json as _json
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    unhealthy = []
    for line in lines:
        try:
            svc = _json.loads(line)
        except Exception:
            continue
        health = svc.get("Health", "")
        state = svc.get("State", "")
        if state != "running" or (health and health != "healthy"):
            unhealthy.append(f"{svc.get('Service')}={state}/{health}")
    if unhealthy:
        return CheckStatus.WARN, f"Servicios no saludables: {unhealthy}"
    return CheckStatus.PASS, f"{len(lines)} servicios docker compose corriendo y saludables."


@register_check("INFRA-02-celery-beat", "INFRA", Severity.P2, "devops")
def check_celery_beat():
    if getattr(settings, "CELERY_BEAT_SCHEDULE", None):
        return CheckStatus.PASS, "CELERY_BEAT_SCHEDULE configurado."
    return CheckStatus.WARN, (
        "Sin CELERY_BEAT_SCHEDULE configurado y sin servicio 'beat' en docker-compose.yaml. "
        "La reconciliacion de trial (reconcile_tenants_lifecycle_task) existe pero no corre automaticamente "
        "-- no es bloqueante porque el enforcement real vive en el middleware (runtime), no en esta tarea."
    )


@register_check("INFRA-03-tls-dns", "INFRA", Severity.P0, "devops")
def check_tls_dns():
    return CheckStatus.NOT_APPLICABLE, (
        "No existe ambiente de staging/produccion real expuesto en este momento -- "
        "TLS/DNS solo pueden verificarse contra infraestructura real desplegada. "
        "docker-compose.yaml ya contempla nginx + volumen nginx_certs + cloudflared "
        "(tunnel), pero no se puede confirmar un certificado real cargado ni resolucion "
        "DNS publica desde este entorno de auditoria. Ver docs/production/DEPLOYMENT_RUNBOOK.md."
    )


# ---------------------------------------------------------------------------
# BACKUP
# ---------------------------------------------------------------------------

@register_check("BAK-01-commands-exist", "BACKUP", Severity.P1, "devops")
def check_backup_commands_exist():
    cmd_dir = os.path.join(_REPO_ROOT, "apps", "public", "tenants", "management", "commands")
    required = ["backup_tenant.py", "backup_all_tenants.py", "restore_tenant.py"]
    missing = [f for f in required if not os.path.exists(os.path.join(cmd_dir, f))]
    if missing:
        return CheckStatus.BLOCKER, f"Comandos de backup/restore faltantes: {missing}"
    return CheckStatus.PASS, f"Comandos existentes: {required} (via pg_dump, backup por schema)."


@register_check("BAK-02-restore-tested", "BACKUP", Severity.P0, "devops")
def check_restore_tested():
    """Evidencia real de un drill end-to-end (backup -> corromper dato ->
    restore --clean -> verificar), no una re-ejecucion del drill completo
    en cada corrida de este check (demasiado costoso para un check
    rutinario) -- igual que TEN-01/E2E, se referencia evidencia real
    fechada, con la fecha y el resultado explicitos en vez de un PASS
    fijo sin sustento."""
    ref = os.path.join(_REPO_ROOT, "docs", "production", "BACKUP_RESTORE_RUNBOOK.md")
    if not os.path.exists(ref):
        return CheckStatus.BLOCKER, "docs/production/BACKUP_RESTORE_RUNBOOK.md no existe."
    try:
        with open(ref, encoding="utf-8") as fh:
            content = fh.read()
    except OSError as exc:
        return CheckStatus.WARN, f"No se pudo leer BACKUP_RESTORE_RUNBOOK.md: {exc}"
    if "BAK-02-restore-tested` = **PASS**" not in content:
        return CheckStatus.BLOCKER, (
            "No existe evidencia documentada de una prueba de restauracion end-to-end "
            "ejecutada (backup -> restore -> verificacion de datos/schemas/integridad, "
            "con RPO/RTO medidos). Ver docs/production/BACKUP_RESTORE_RUNBOOK.md "
            "para el procedimiento a ejecutar antes de cerrar este blocker."
        )
    return CheckStatus.PASS, (
        "Drill end-to-end ejecutado y verificado 2026-08-31 (tenant QA desechable "
        "bak_drill_20260831120616): backup -> dato corrompido -> restore --clean (RTO "
        "16.86s, exit 0) -> dato revertido + Client/Domain/Membership/Empresa/"
        "TenantProfile coherentes. Ver docs/production/BACKUP_RESTORE_RUNBOOK.md "
        "para evidencia completa. Nota: es una corrida real puntual, no una suite "
        "automatizada corriendo en CI -- re-verificar tras cambios al mecanismo."
    )


@register_check("BAK-03-schedule", "BACKUP", Severity.P2, "devops")
def check_backup_schedule():
    return CheckStatus.WARN, (
        "Sin programacion automatica de backups (no hay celery beat ni cron configurado "
        "en docker-compose.yaml). Los comandos existen pero requieren ejecucion manual hoy."
    )


@register_check("BAK-04-pg-client-server-version-match", "BACKUP", Severity.P0, "devops")
def check_pg_client_server_version_match():
    """Regresion especifica del hallazgo real de BAK-02: pg_restore mas
    nuevo que el servidor Postgres antepone GUCs que el servidor rechaza
    (ej. 'transaction_timeout', introducido en PG17), rompiendo CUALQUIER
    restauracion real sin que ningun otro check lo detecte. Compara la
    version major del cliente pg_dump/pg_restore instalado contra la
    version major real del servidor (via Django connection), en vez de
    asumir que coinciden."""
    try:
        result = subprocess.run(
            ["pg_dump", "--version"], capture_output=True, text=True, timeout=10,
        )
    except FileNotFoundError:
        return CheckStatus.WARN, (
            "'pg_dump' no esta en PATH en este contexto de ejecucion -- este check debe "
            "correrse desde donde vive el cliente real (contenedor 'web'), no desde el host "
            "si el host no tiene postgresql-client instalado."
        )
    except Exception as exc:
        return CheckStatus.WARN, f"No se pudo ejecutar 'pg_dump --version': {exc}"
    match_client = re.search(r"(\d+)(?:\.\d+)*", result.stdout)
    if not match_client:
        return CheckStatus.WARN, f"No se pudo parsear la version de pg_dump: {result.stdout!r}"
    client_major = int(match_client.group(1))
    try:
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute("SHOW server_version")
            server_version = cur.fetchone()[0]
    except Exception as exc:
        return CheckStatus.WARN, f"No se pudo consultar server_version real: {exc}"
    match_server = re.search(r"(\d+)", server_version)
    if not match_server:
        return CheckStatus.WARN, f"No se pudo parsear server_version: {server_version!r}"
    server_major = int(match_server.group(1))
    if client_major != server_major:
        return CheckStatus.BLOCKER, (
            f"pg_dump/pg_restore cliente v{client_major} != servidor Postgres v{server_major}. "
            "CUALQUIER restauracion real fallaria (GUCs de sesion incompatibles entre versiones "
            "major). Fijar postgresql-client-{server_major} en el Dockerfile de la imagen que "
            "ejecuta backup_tenant/restore_tenant. Ver docs/production/BACKUP_RESTORE_RUNBOOK.md."
        )
    return CheckStatus.PASS, f"pg_dump/pg_restore cliente v{client_major} coincide con servidor Postgres v{server_major}."


# ---------------------------------------------------------------------------
# OBSERVABILITY
# ---------------------------------------------------------------------------

@register_check("OBS-01-health-endpoint", "OBSERVABILITY", Severity.P1, "core")
def check_health_endpoint():
    try:
        import requests

        resp = requests.get("http://localhost:8000/health", timeout=5)
    except Exception as exc:
        return CheckStatus.WARN, f"No se pudo alcanzar /health: {exc}"
    if resp.status_code != 200:
        return CheckStatus.BLOCKER, f"/health respondio {resp.status_code}, se esperaba 200."
    return CheckStatus.PASS, f"/health respondio 200 ({resp.text[:100]!r})."


@register_check("OBS-02-liveness-readiness-split", "OBSERVABILITY", Severity.P2, "core")
def check_liveness_readiness_split():
    return CheckStatus.WARN, (
        "Existe un unico endpoint /health (verifica estado de DB, per el .agent doc de core) "
        "sin distincion explicita liveness ('el proceso vive') vs readiness ('puede servir "
        "trafico') -- ver Fase 21. No bloqueante para un despliegue simple de Docker Compose "
        "(sin orquestador que consuma esa distincion), pero relevante si se migra a un "
        "orquestador que sí la requiera (k8s, ECS, etc.)."
    )


# ---------------------------------------------------------------------------
# DOCUMENTATION
# ---------------------------------------------------------------------------

@register_check("DOC-01-core-docs-exist", "DOCUMENTATION", Severity.P2, "core")
def check_core_docs_exist():
    required = ["AGENTS.md", "MEMORY.md", "CLAUDE.md"]
    missing = [f for f in required if not os.path.exists(os.path.join(_REPO_ROOT, f))]
    if missing:
        return CheckStatus.WARN, f"Documentos core faltantes: {missing}"
    return CheckStatus.PASS, f"Documentos core presentes: {required}."


# ---------------------------------------------------------------------------
# FISCAL / EXTERNAL
# ---------------------------------------------------------------------------

@register_check("FISCAL-01-dian-transmission", "FISCAL", Severity.P0, "facturas")
def check_dian_transmission():
    return CheckStatus.EXTERNAL_DEPENDENCY, (
        "Transmision real DIAN de facturas electronicas: sin credenciales/certificado/WSDL "
        "de un tenant real en produccion. Adaptador SOAP real existe "
        "(apps/tenant/core/dian/adapters.py) pero no verificado contra el ambiente real de "
        "la DIAN. Ver docs/remediation/REM-EXT-01.md. No se puede declarar 'DIAN production "
        "ready' sin esos insumos externos (regla explicita del plan)."
    )


@register_check("FISCAL-02-dspne-transmission", "FISCAL", Severity.P0, "empleados")
def check_dspne_transmission():
    return CheckStatus.EXTERNAL_DEPENDENCY, (
        "Transmision real DSPNE de nomina electronica: mismo motivo que DIAN -- sin "
        "credenciales/certificado/URL de produccion. Ver docs/remediation/REM-EXT-02.md."
    )
