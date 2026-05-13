from django_tenants.utils import schema_context
from apps.tenant.contabilidad.integracion.extractores.gastos import ExtractorGastos
from apps.tenant.empresa.models import Empresa
import json

with schema_context('home'):
    empresa = Empresa.objects.first()
    if not empresa:
        print("No se encontro empresa en el tenant home")
        exit()
        
    extractor = ExtractorGastos(empresa_id=empresa.id)
    pendientes = extractor.extraer_pendientes()
    
    print(f"--- VALIDACION EXTRACTOR GASTOS (home) ---")
    print(f"Pendientes encontrados: {len(pendientes)}")
    
    for idx, p in enumerate(pendientes):
        print(f"\nDocumento {idx + 1}:")
        print(f"  Numero: {p.documento_origen.numero}")
        print(f"  Fecha: {p.fecha}")
        print(f"  Tercero: {p.tercero.nit} - {p.tercero.razon_social}")
        
        print(f"  Lineas:")
        for l in p.lineas:
            print(f"    - {l.lado}: Concepto={l.concepto}, Monto={l.monto}")
            if l.impuestos:
                print(f"      Impuestos/Retenciones:")
                for i in l.impuestos:
                    print(f"        * {i.tipo}: Base={i.base}, Valor={i.valor} ({i.lado})")
