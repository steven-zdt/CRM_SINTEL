import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from decimal import Decimal
from apps.tenant.empleados.services.business_service import NominaCalculationService
from apps.tenant.empleados.models import Contrato

def run_smoke_test():
    print("--- INICIANDO PRUEBA DE HUMO (CÁLCULO NÓMINA) ---")
    contrato = Contrato.objects.filter(estado='ACTIVO', activo=True).first()
    if not contrato:
        print("No hay contratos activos para probar.")
        return
        
    print(f"Probando cálculo para contrato ID: {contrato.id} - Salario Mensual: {contrato.salario_mensual}")
    empresa_id = contrato.empresa_id
    
    # Prueba 1: 30 días
    print("\n[Prueba 1] 30 días laborados:")
    calc_30 = NominaCalculationService.calcular_liquidacion(
        contrato=contrato,
        dias_laborados=Decimal('30'),
        empresa_id=empresa_id
    )
    for k, v in calc_30.items():
        print(f"  {k}: {v}")
        
    # Prueba 2: 15 días (Debe ser la mitad proporcional)
    print("\n[Prueba 2] 15 días laborados:")
    calc_15 = NominaCalculationService.calcular_liquidacion(
        contrato=contrato,
        dias_laborados=Decimal('15'),
        empresa_id=empresa_id
    )
    for k, v in calc_15.items():
        print(f"  {k}: {v}")

    # Verificar que el salario base de 15 días es la mitad de 30 días
    base_30 = Decimal(calc_30['salario_base'])
    base_15 = Decimal(calc_15['salario_base'])
    
    if base_15 == base_30 / Decimal('2'):
        print("\nSUCCESS: El cálculo proporcional es exacto según normativa colombiana.")
    else:
        print("\nFAILURE: La proporción no coincide.")

if __name__ == '__main__':
    run_smoke_test()
