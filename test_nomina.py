import os
import django
from decimal import Decimal
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from apps.tenant.empleados.services.business_service import NominaCalculationService

class DummyContrato:
    salario_mensual = 1300000
    auxilio_transporte = 162000
    tipo = 'FIJO'
    horas_semanales = 42
    estado = 'ACTIVO'
    activo = True

calculo = NominaCalculationService.calcular_liquidacion(
    contrato=DummyContrato(),
    dias_laborados=15,
    horas_trabajadas=None
)
print(calculo)
