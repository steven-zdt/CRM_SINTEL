import os
import django
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.public.tenants.models import Client
from apps.tenant.empresa.models import Empresa
from apps.tenant.contabilidad.services.selectors import balance_prueba_selector, estado_resultados_selector
from django_tenants.utils import tenant_context

def run_test():
    try:
        tenant = Client.objects.get(schema_name='home')
        with tenant_context(tenant):
            print(f"--- Probando Reportes para Tenant: {tenant.schema_name} ---")
            
            # Obtener empresa (Singleton)
            empresa = Empresa.objects.first()
            if not empresa:
                print("Error: No se encontró la empresa en el tenant.")
                return

            print(f"Empresa: {empresa.razon_social} (ID: {empresa.id})")
            
            # Fechas de prueba
            fecha_ini = '2024-01-01'
            fecha_fin = '2024-12-31'

            # 1. Balance de Prueba
            print("\n[BALANCE DE PRUEBA]")
            balance = balance_prueba_selector(empresa_id=empresa.id, fecha_inicio=fecha_ini, fecha_fin=fecha_fin)
            print(f"Items en balance: {len(balance)}")
            for item in balance:
                codigo = item.get('cuenta__codigo') or item.get('codigo')
                nombre = item.get('cuenta__nombre') or item.get('nombre')
                debito = item.get('debito', 0)
                credito = item.get('credito', 0)
                saldo = item.get('nuevo_saldo', 0)
                print(f"  {codigo} - {nombre}: Debito={debito}, Credito={credito}, Saldo={saldo}")
            
            # 2. Estado de Resultados
            print("\n[ESTADO DE RESULTADOS]")
            resultados = estado_resultados_selector(empresa_id=empresa.id, fecha_inicio=fecha_ini, fecha_fin=fecha_fin)
            totales = resultados.get('totales', {})
            print(f"Total Ingresos: {totales.get('ingresos', 0)}")
            print(f"Total Gastos: {totales.get('gastos', 0)}")
            print(f"Total Costos: {totales.get('costos', 0)}")
            print(f"Utilidad Neta: {totales.get('utilidad_neta', 0)}")
            
            # Detalle de ingresos
            print("\nDetalle Ingresos:")
            for ing in resultados.get('ingresos', []):
                print(f"  {ing['codigo']} - {ing['nombre']}: {ing['valor']}")
            
            print("\n--- Prueba Finalizada con Éxito ---")
            
    except Exception as e:
        print(f"Error en la prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
