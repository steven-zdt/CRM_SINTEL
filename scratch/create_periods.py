from django_tenants.utils import schema_context
from apps.tenant.contabilidad.models import PeriodoContable
from apps.tenant.empresa.models import Empresa
from datetime import date
import calendar

with schema_context('home'):
    empresa = Empresa.objects.first()
    if not empresa:
        print("Error: Empresa no encontrada en schema 'home'")
    else:
        created_count = 0
        for year in [2024, 2025, 2026]:
            for month in range(1, 13):
                periodo_str = f"{year}-{month:02d}"
                last_day = calendar.monthrange(year, month)[1]
                obj, created = PeriodoContable.objects.get_or_create(
                    empresa=empresa, 
                    periodo=periodo_str, 
                    defaults={
                        'fecha_inicio': date(year, month, 1),
                        'fecha_fin': date(year, month, last_day),
                        'estado': 'ABIERTO'
                    }
                )
                if created:
                    created_count += 1
        print(f"Periodos creados: {created_count}")
