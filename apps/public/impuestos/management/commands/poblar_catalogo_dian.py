"""
Comando para poblar el catálogo básico de la DIAN con datos iniciales.
Incluye tarifas de IVA, conceptos de retención y códigos tributarios comunes.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from apps.public.impuestos.models import (
    TipoImpuesto,
    TarifaIVA,
    ConceptoRetencion,
    CodigoTributario,
    ActividadEconomica,
    RegimenRenta,
    ContribuyenteTipo,
    ResponsabilidadRUT,
)


class Command(BaseCommand):
    help = 'Pobla el catálogo de la DIAN con datos iniciales (IVA, Retenciones, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar la creación incluso si ya existen datos',
        )

    def handle(self, *args, **options):
        force = options['force']
        fecha_vigencia = date.today()

        self.stdout.write(self.style.SUCCESS('🚀 Iniciando poblamiento del catálogo DIAN...'))

        # 1. Tipos de Impuesto
        self.stdout.write('\n📋 Creando tipos de impuesto...')
        tipos_impuesto = [
            {'codigo': '01', 'nombre': 'IVA', 'descripcion': 'Impuesto al Valor Agregado'},
            {'codigo': '02', 'nombre': 'Retención en la Fuente', 'descripcion': 'Retenciones en la fuente'},
            {'codigo': '03', 'nombre': 'ICA', 'descripcion': 'Impuesto de Industria y Comercio'},
            {'codigo': '04', 'nombre': 'Renta', 'descripcion': 'Impuesto sobre la Renta'},
        ]

        for tipo_data in tipos_impuesto:
            tipo, created = TipoImpuesto.objects.get_or_create(
                codigo=tipo_data['codigo'],
                defaults={
                    'nombre': tipo_data['nombre'],
                    'descripcion': tipo_data['descripcion'],
                    'fecha_vigencia': fecha_vigencia,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✅ {tipo.codigo} - {tipo.nombre}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ℹ️  {tipo.codigo} - {tipo.nombre} (ya existe)'))

        # 2. Tarifas de IVA
        self.stdout.write('\n💰 Creando tarifas de IVA...')
        tarifas_iva = [
            {'codigo': '01', 'nombre': 'IVA General', 'porcentaje': 19.00, 'tipo_tarifa': 'general'},
            {'codigo': '02', 'nombre': 'IVA Excluido', 'porcentaje': 0.00, 'tipo_tarifa': 'excluido'},
            {'codigo': '03', 'nombre': 'IVA Exento', 'porcentaje': 0.00, 'tipo_tarifa': 'exento'},
            {'codigo': '04', 'nombre': 'IVA Reducido 5%', 'porcentaje': 5.00, 'tipo_tarifa': 'reducida'},
        ]

        for tarifa_data in tarifas_iva:
            tarifa, created = TarifaIVA.objects.get_or_create(
                codigo=tarifa_data['codigo'],
                defaults={
                    'nombre': tarifa_data['nombre'],
                    'porcentaje': tarifa_data['porcentaje'],
                    'tipo_tarifa': tarifa_data['tipo_tarifa'],
                    'fecha_vigencia': fecha_vigencia,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✅ {tarifa.codigo} - {tarifa.nombre} ({tarifa.porcentaje}%)'))
            else:
                self.stdout.write(self.style.WARNING(f'  ℹ️  {tarifa.codigo} - {tarifa.nombre} (ya existe)'))

        # 3. Conceptos de Retención
        self.stdout.write('\n📊 Creando conceptos de retención...')
        conceptos_retencion = [
            # Retención ICA
            {'codigo': 'ICA01', 'nombre': 'Retención ICA - Servicios', 'tipo_retencion': 'ica', 'porcentaje': 4.00, 'base_minima': 0},
            {'codigo': 'ICA02', 'nombre': 'Retención ICA - Comercio', 'tipo_retencion': 'ica', 'porcentaje': 2.00, 'base_minima': 0},
            
            # Retención IVA
            {'codigo': 'IVA01', 'nombre': 'Retención IVA - Compras', 'tipo_retencion': 'iva', 'porcentaje': 15.00, 'base_minima': 0},
            {'codigo': 'IVA02', 'nombre': 'Retención IVA - Servicios', 'tipo_retencion': 'iva', 'porcentaje': 11.00, 'base_minima': 0},
            
            # Retención Renta
            {'codigo': 'RENTA01', 'nombre': 'Retención Renta - Servicios', 'tipo_retencion': 'renta', 'porcentaje': 11.00, 'base_minima': 0},
            {'codigo': 'RENTA02', 'nombre': 'Retención Renta - Honorarios', 'tipo_retencion': 'renta', 'porcentaje': 10.00, 'base_minima': 0},
        ]

        for concepto_data in conceptos_retencion:
            concepto, created = ConceptoRetencion.objects.get_or_create(
                codigo=concepto_data['codigo'],
                defaults={
                    'nombre': concepto_data['nombre'],
                    'tipo_retencion': concepto_data['tipo_retencion'],
                    'porcentaje': concepto_data.get('porcentaje'),
                    'base_minima': concepto_data.get('base_minima', 0),
                    'fecha_vigencia': fecha_vigencia,
                }
            )
            if created:
                pct = f"{concepto.porcentaje}%" if concepto.porcentaje else "Variable"
                self.stdout.write(self.style.SUCCESS(f'  ✅ {concepto.codigo} - {concepto.nombre} ({pct})'))
            else:
                self.stdout.write(self.style.WARNING(f'  ℹ️  {concepto.codigo} - {concepto.nombre} (ya existe)'))

        # 4. Códigos Tributarios (Responsabilidades)
        self.stdout.write('\n🏛️  Creando códigos tributarios...')
        codigos_tributarios = [
            {'codigo': 'R-99-PN', 'nombre': 'No aplica', 'tipo': 'Responsabilidad'},
            {'codigo': 'O-13', 'nombre': 'Obligado a Facturar Electrónicamente', 'tipo': 'Responsabilidad'},
            {'codigo': 'O-15', 'nombre': 'Obligado a Facturar Electrónicamente - Régimen Simple', 'tipo': 'Responsabilidad'},
            {'codigo': 'O-47', 'nombre': 'Régimen Simple de Tributación', 'tipo': 'Régimen'},
            {'codigo': 'O-48', 'nombre': 'Régimen Ordinario', 'tipo': 'Régimen'},
        ]

        for codigo_data in codigos_tributarios:
            codigo, created = CodigoTributario.objects.get_or_create(
                codigo=codigo_data['codigo'],
                defaults={
                    'nombre': codigo_data['nombre'],
                    'tipo': codigo_data['tipo'],
                    'fecha_vigencia': fecha_vigencia,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✅ {codigo.codigo} - {codigo.nombre}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ℹ️  {codigo.codigo} - {codigo.nombre} (ya existe)'))

        # 5. Actividades Económicas (algunas comunes)
        self.stdout.write('\n🏢 Creando actividades económicas comunes...')
        actividades = [
            {'codigo': '6201', 'nombre': 'Programación de computadoras'},
            {'codigo': '6202', 'nombre': 'Consultoría en informática'},
            {'codigo': '7010', 'nombre': 'Actividades de administración empresarial'},
            {'codigo': '4641', 'nombre': 'Comercio al por mayor de computadores'},
            {'codigo': '4791', 'nombre': 'Comercio al por menor por internet'},
        ]

        for actividad_data in actividades:
            actividad, created = ActividadEconomica.objects.get_or_create(
                codigo=actividad_data['codigo'],
                defaults={
                    'nombre': actividad_data['nombre'],
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✅ {actividad.codigo} - {actividad.nombre}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ℹ️  {actividad.codigo} - {actividad.nombre} (ya existe)'))

        # 6. Regímenes de Renta
        self.stdout.write('\n📋 Creando regímenes de renta...')
        regimenes_renta = [
            {
                'codigo': RegimenRenta.ORD,
                'nombre': 'Régimen Ordinario',
                'descripcion': 'Régimen tributario ordinario según la DIAN',
                'tarifa_base_pj': 33.00,
                'requiere_facturacion_electronica': True,
                'aplica_retenciones': True,
            },
            {
                'codigo': RegimenRenta.RTE,
                'nombre': 'Régimen Tributario Especial (RTE)',
                'descripcion': 'Régimen Tributario Especial según Ley 1943 de 2018',
                'tarifa_base_pj': None,
                'requiere_facturacion_electronica': True,
                'aplica_retenciones': True,
            },
            {
                'codigo': RegimenRenta.SIMPLE,
                'nombre': 'Régimen Simple de Tributación (SIMPLE)',
                'descripcion': 'Régimen Simple de Tributación según Ley 1819 de 2016',
                'tarifa_base_pj': None,
                'requiere_facturacion_electronica': True,
                'aplica_retenciones': True,
            },
        ]

        for regimen_data in regimenes_renta:
            regimen, created = RegimenRenta.objects.get_or_create(
                codigo=regimen_data['codigo'],
                defaults={
                    'nombre': regimen_data['nombre'],
                    'descripcion': regimen_data['descripcion'],
                    'tarifa_base_pj': regimen_data['tarifa_base_pj'],
                    'requiere_facturacion_electronica': regimen_data['requiere_facturacion_electronica'],
                    'aplica_retenciones': regimen_data['aplica_retenciones'],
                    'activo': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✅ {regimen.codigo} - {regimen.nombre}'))
            else:
                # Actualizar si ya existe pero está inactivo
                if not regimen.activo:
                    regimen.activo = True
                    regimen.save()
                    self.stdout.write(self.style.SUCCESS(f'  ✅ {regimen.codigo} - {regimen.nombre} (reactivado)'))
                else:
                    self.stdout.write(self.style.WARNING(f'  ℹ️  {regimen.codigo} - {regimen.nombre} (ya existe)'))

        # 7. Tipos de Contribuyente
        self.stdout.write('\n👤 Creando tipos de contribuyente...')
        tipos_contribuyente = [
            {
                'clase': 'PN',
                'nombre': 'Persona Natural',
                'descripcion': 'Persona natural según clasificación DIAN',
            },
            {
                'clase': 'PJ',
                'nombre': 'Persona Jurídica',
                'descripcion': 'Persona jurídica según clasificación DIAN',
            },
        ]

        for tipo_data in tipos_contribuyente:
            tipo, created = ContribuyenteTipo.objects.get_or_create(
                clase=tipo_data['clase'],
                defaults={
                    'nombre': tipo_data['nombre'],
                    'descripcion': tipo_data['descripcion'],
                    'activo': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✅ {tipo.clase} - {tipo.nombre}'))
            else:
                if not tipo.activo:
                    tipo.activo = True
                    tipo.save()
                    self.stdout.write(self.style.SUCCESS(f'  ✅ {tipo.clase} - {tipo.nombre} (reactivado)'))
                else:
                    self.stdout.write(self.style.WARNING(f'  ℹ️  {tipo.clase} - {tipo.nombre} (ya existe)'))

        # 8. Responsabilidades RUT (algunas comunes)
        self.stdout.write('\n🏛️  Creando responsabilidades RUT...')
        responsabilidades = [
            {'codigo': '48', 'nombre': 'Responsable de IVA', 'descripcion': 'Responsable del Impuesto al Valor Agregado'},
            {'codigo': '49', 'nombre': 'No responsable de IVA', 'descripcion': 'No responsable del Impuesto al Valor Agregado'},
            {'codigo': '47', 'nombre': 'Responsable de IVA como agente de retención', 'descripcion': 'Responsable de IVA como agente de retención (Régimen SIMPLE)'},
            {'codigo': '52', 'nombre': 'Gran contribuyente', 'descripcion': 'Gran contribuyente según DIAN'},
            {'codigo': '13', 'nombre': 'Obligado a facturar electrónicamente', 'descripcion': 'Obligado a facturar electrónicamente'},
        ]

        for resp_data in responsabilidades:
            resp, created = ResponsabilidadRUT.objects.get_or_create(
                codigo=resp_data['codigo'],
                defaults={
                    'nombre': resp_data['nombre'],
                    'descripcion': resp_data['descripcion'],
                    'activo': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✅ {resp.codigo} - {resp.nombre}'))
            else:
                if not resp.activo:
                    resp.activo = True
                    resp.save()
                    self.stdout.write(self.style.SUCCESS(f'  ✅ {resp.codigo} - {resp.nombre} (reactivado)'))
                else:
                    self.stdout.write(self.style.WARNING(f'  ℹ️  {resp.codigo} - {resp.nombre} (ya existe)'))

        # Resumen
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('🎉 Catálogo DIAN poblado exitosamente!'))
        self.stdout.write(f'\n📊 Resumen:')
        self.stdout.write(f'   - Tipos de Impuesto: {TipoImpuesto.objects.count()}')
        self.stdout.write(f'   - Tarifas de IVA: {TarifaIVA.objects.count()}')
        self.stdout.write(f'   - Conceptos de Retención: {ConceptoRetencion.objects.count()}')
        self.stdout.write(f'   - Códigos Tributarios: {CodigoTributario.objects.count()}')
        self.stdout.write(f'   - Actividades Económicas: {ActividadEconomica.objects.count()}')
        self.stdout.write(f'   - Regímenes de Renta: {RegimenRenta.objects.filter(activo=True).count()}')
        self.stdout.write(f'   - Tipos de Contribuyente: {ContribuyenteTipo.objects.filter(activo=True).count()}')
        self.stdout.write(f'   - Responsabilidades RUT: {ResponsabilidadRUT.objects.filter(activo=True).count()}')
        self.stdout.write('\n✅ El catálogo está disponible para todos los tenants en el esquema public.')
