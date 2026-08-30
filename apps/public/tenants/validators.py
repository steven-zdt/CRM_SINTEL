"""
Validadores para modelos de tenants.

Referencia: https://docs.djangoproject.com/en/stable/ref/validators/
"""

from apps.public.tenants.utils import validate_schema_name as _validate_schema_name

# REM ONBOARDING-05 (documentacion/AUDITORIA_ONBOARDING_TENANTS_2026-08-30.md
# Hallazgo #5): este modulo tenia su propia implementacion de
# validate_schema_name(), divergente de apps/public/tenants/utils.py (permitia
# empezar con digito, solo bloqueaba 'public' como reservado). Ninguna de las
# dos permitia caracteres peligrosos para SQL -- sin riesgo de inyeccion real
# en ninguna variante -- pero dos reglas distintas para el mismo dato es deuda
# de mantenimiento real. Se consolida en la version de utils.py (ya en la ruta
# critica via empresa_service.py) reexportandola aqui, para no romper los
# import existentes en models.py y api/serializers.py.
validate_schema_name = _validate_schema_name
