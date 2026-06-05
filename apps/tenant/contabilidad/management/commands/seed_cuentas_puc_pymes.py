"""
Comando para poblar cuentas contables PUC Colombia — Clases 1 a 6.

Decreto 2650 de 1993 adaptado para NIIF PYMES (IFRS for SMEs).
Alineado con APP_ORIGEN_PREFIJOS en contabilidad/services/selectors.py.
Idempotente: usa get_or_create, seguro de ejecutar varias veces.

Uso:
    python manage.py seed_cuentas_puc_pymes
    python manage.py seed_cuentas_puc_pymes --tenants=1,2
    python manage.py seed_cuentas_puc_pymes --dry-run
    python manage.py seed_cuentas_puc_pymes --solo-activo
    python manage.py seed_cuentas_puc_pymes --solo-pasivo
    python manage.py seed_cuentas_puc_pymes --solo-patrimonio
    python manage.py seed_cuentas_puc_pymes --solo-ingreso
    python manage.py seed_cuentas_puc_pymes --solo-gasto
    python manage.py seed_cuentas_puc_pymes --solo-costo
"""
from django.core.management.base import BaseCommand
from django_tenants.utils import get_tenant_model

Tenant = get_tenant_model()

# ---------------------------------------------------------------------------
# nivel: len(codigo) indica el nivel jerarquico
#   1 digito  -> nivel 1 (clase)
#   2 digitos -> nivel 2 (grupo)
#   4 digitos -> nivel 4 (cuenta)
#   6 digitos -> nivel 6 (subcuenta / auxiliar transaccional)
# tipo: ACTIVO | PASIVO | PATRIMONIO | INGRESO | GASTO
# ---------------------------------------------------------------------------

# ============================================================================
# CLASE 1 — ACTIVO
# ============================================================================
CUENTAS_ACTIVO = [
    {'codigo': '1',       'nombre': 'Activo',                                        'nivel': 1},

    # Grupo 11 — Efectivo y Equivalentes
    {'codigo': '11',      'nombre': 'Efectivo y Equivalentes de Efectivo',            'nivel': 2},
    {'codigo': '1105',    'nombre': 'Caja',                                           'nivel': 4},
    {'codigo': '110505',  'nombre': 'Caja General',                                   'nivel': 6},
    {'codigo': '110510',  'nombre': 'Caja Menor',                                     'nivel': 6},
    {'codigo': '1110',    'nombre': 'Bancos',                                          'nivel': 4},
    {'codigo': '111005',  'nombre': 'Moneda Nacional',                                'nivel': 6},
    {'codigo': '111010',  'nombre': 'Moneda Extranjera',                              'nivel': 6},
    {'codigo': '1115',    'nombre': 'Remesas en Transito',                             'nivel': 4},
    {'codigo': '1120',    'nombre': 'Cuentas de Ahorro',                              'nivel': 4},
    {'codigo': '112005',  'nombre': 'Cuentas de Ahorro Moneda Nacional',              'nivel': 6},

    # Grupo 12 — Inversiones
    {'codigo': '12',      'nombre': 'Inversiones e Instrumentos Derivados',           'nivel': 2},
    {'codigo': '1205',    'nombre': 'Inversiones en Acciones',                        'nivel': 4},
    {'codigo': '1210',    'nombre': 'Inversiones en Cuotas',                          'nivel': 4},

    # Grupo 13 — Cuentas por Cobrar Comerciales
    {'codigo': '13',      'nombre': 'Cuentas por Cobrar Comerciales y Otras',         'nivel': 2},
    {'codigo': '1305',    'nombre': 'Clientes',                                        'nivel': 4},
    {'codigo': '130505',  'nombre': 'Clientes Nacionales',                            'nivel': 6},
    {'codigo': '130510',  'nombre': 'Clientes del Exterior',                          'nivel': 6},
    {'codigo': '1310',    'nombre': 'Cuentas Corrientes Comerciales',                 'nivel': 4},
    {'codigo': '1330',    'nombre': 'Anticipos y Avances',                            'nivel': 4},
    {'codigo': '133005',  'nombre': 'A Proveedores',                                  'nivel': 6},
    {'codigo': '133010',  'nombre': 'A Empleados',                                    'nivel': 6},
    {'codigo': '1355',    'nombre': 'Anticipo de Impuestos y Contribuciones',         'nivel': 4},
    {'codigo': '135515',  'nombre': 'Retencion en la Fuente (a Favor)',               'nivel': 6},
    {'codigo': '135517',  'nombre': 'Impuesto a las Ventas IVA Pagado',               'nivel': 6},
    {'codigo': '135518',  'nombre': 'Impuesto de Industria y Comercio ICA Pagado',    'nivel': 6},
    {'codigo': '1360',    'nombre': 'Reclamaciones',                                  'nivel': 4},
    {'codigo': '1365',    'nombre': 'Cuentas por Cobrar a Socios',                    'nivel': 4},
    {'codigo': '1375',    'nombre': 'Deudores Varios',                                'nivel': 4},
    {'codigo': '137505',  'nombre': 'Empleados',                                      'nivel': 6},
    {'codigo': '137510',  'nombre': 'Otros Deudores',                                 'nivel': 6},
    {'codigo': '1380',    'nombre': 'Deudores de Dificil Cobro',                      'nivel': 4},
    {'codigo': '1399',    'nombre': 'Deterioro de Valor Cartera',                     'nivel': 4},
    {'codigo': '139905',  'nombre': 'Clientes',                                       'nivel': 6},

    # Grupo 14 — Inventarios
    {'codigo': '14',      'nombre': 'Inventarios',                                    'nivel': 2},
    {'codigo': '1405',    'nombre': 'Materias Primas',                                'nivel': 4},
    {'codigo': '1410',    'nombre': 'Productos en Proceso',                           'nivel': 4},
    {'codigo': '1415',    'nombre': 'Obras de Construccion en Curso',                 'nivel': 4},
    {'codigo': '1420',    'nombre': 'Contratos en Ejecucion',                         'nivel': 4},
    {'codigo': '1430',    'nombre': 'Productos Terminados',                           'nivel': 4},
    {'codigo': '1435',    'nombre': 'Mercancias No Fabricadas por la Empresa',        'nivel': 4},
    {'codigo': '143505',  'nombre': 'Productos Terminados',                           'nivel': 6},
    {'codigo': '143510',  'nombre': 'Materiales y Suministros',                       'nivel': 6},
    {'codigo': '143515',  'nombre': 'Repuestos y Accesorios',                         'nivel': 6},

    # Grupo 15 — Propiedades, Planta y Equipo
    {'codigo': '15',      'nombre': 'Propiedades, Planta y Equipo',                   'nivel': 2},
    {'codigo': '1504',    'nombre': 'Terrenos',                                        'nivel': 4},
    {'codigo': '1508',    'nombre': 'Construcciones y Edificaciones',                 'nivel': 4},
    {'codigo': '1516',    'nombre': 'Maquinaria y Equipo',                            'nivel': 4},
    {'codigo': '1520',    'nombre': 'Equipo de Oficina',                              'nivel': 4},
    {'codigo': '1524',    'nombre': 'Equipo de Oficina',                              'nivel': 4},
    {'codigo': '152405',  'nombre': 'Muebles y Enseres',                              'nivel': 6},
    {'codigo': '152410',  'nombre': 'Equipos de Oficina',                             'nivel': 6},
    {'codigo': '1528',    'nombre': 'Equipo de Computacion y Comunicacion',           'nivel': 4},
    {'codigo': '152805',  'nombre': 'Equipos de Computo',                             'nivel': 6},
    {'codigo': '152810',  'nombre': 'Equipos de Comunicacion',                        'nivel': 6},
    {'codigo': '1532',    'nombre': 'Armamento de Vigilancia',                        'nivel': 4},
    {'codigo': '1536',    'nombre': 'Vehiculos',                                      'nivel': 4},
    {'codigo': '153605',  'nombre': 'Automoviles y Camionetas',                       'nivel': 6},
    {'codigo': '1540',    'nombre': 'Flota y Equipo de Transporte',                   'nivel': 4},
    {'codigo': '1548',    'nombre': 'Plantas, Ductos y Tuneles',                      'nivel': 4},
    {'codigo': '1552',    'nombre': 'Redes Lineas y Cables',                          'nivel': 4},
    {'codigo': '1560',    'nombre': 'Activos Fijos en Transito',                      'nivel': 4},
    {'codigo': '1592',    'nombre': 'Depreciacion Acumulada',                         'nivel': 4},
    {'codigo': '159205',  'nombre': 'Construcciones y Edificaciones',                 'nivel': 6},
    {'codigo': '159210',  'nombre': 'Maquinaria y Equipo',                            'nivel': 6},
    {'codigo': '159215',  'nombre': 'Equipo de Oficina',                              'nivel': 6},
    {'codigo': '159220',  'nombre': 'Equipo de Computo',                              'nivel': 6},
    {'codigo': '159225',  'nombre': 'Vehiculos',                                      'nivel': 6},
    {'codigo': '159230',  'nombre': 'Flota y Equipo de Transporte',                   'nivel': 6},

    # Grupo 17 — Intangibles
    {'codigo': '17',      'nombre': 'Intangibles',                                    'nivel': 2},
    {'codigo': '1705',    'nombre': 'Concesiones y Franquicias',                      'nivel': 4},
    {'codigo': '1710',    'nombre': 'Patentes',                                       'nivel': 4},
    {'codigo': '1715',    'nombre': 'Marcas',                                         'nivel': 4},
    {'codigo': '1720',    'nombre': 'Know How',                                       'nivel': 4},
    {'codigo': '1725',    'nombre': 'Licencias',                                      'nivel': 4},
    {'codigo': '1728',    'nombre': 'Software',                                       'nivel': 4},

    # Grupo 18 — Diferidos
    {'codigo': '18',      'nombre': 'Activos Diferidos',                              'nivel': 2},
    {'codigo': '1805',    'nombre': 'Gastos Pagados por Anticipado',                  'nivel': 4},
    {'codigo': '180505',  'nombre': 'Seguros Pagados por Anticipado',                 'nivel': 6},
    {'codigo': '180510',  'nombre': 'Arrendamientos Pagados por Anticipado',          'nivel': 6},
    {'codigo': '180595',  'nombre': 'Otros Gastos Pagados por Anticipado',            'nivel': 6},
    {'codigo': '1820',    'nombre': 'Cargos Diferidos',                               'nivel': 4},
]

# ============================================================================
# CLASE 2 — PASIVO
# ============================================================================
CUENTAS_PASIVO = [
    {'codigo': '2',       'nombre': 'Pasivo',                                         'nivel': 1},

    # Grupo 21 — Obligaciones Financieras
    {'codigo': '21',      'nombre': 'Obligaciones Financieras',                       'nivel': 2},
    {'codigo': '2105',    'nombre': 'Bancos Nacionales',                              'nivel': 4},
    {'codigo': '210505',  'nombre': 'Prestamos de Bancos',                            'nivel': 6},
    {'codigo': '2110',    'nombre': 'Bancos del Exterior',                            'nivel': 4},
    {'codigo': '2145',    'nombre': 'Obligaciones con Entidades Financieras',         'nivel': 4},
    {'codigo': '2195',    'nombre': 'Otras Obligaciones Financieras',                 'nivel': 4},

    # Grupo 22 — Proveedores
    {'codigo': '22',      'nombre': 'Proveedores',                                    'nivel': 2},
    {'codigo': '2205',    'nombre': 'Proveedores Nacionales',                         'nivel': 4},
    {'codigo': '220501',  'nombre': 'Proveedores Nacionales - Bienes',                'nivel': 6},
    {'codigo': '220505',  'nombre': 'Proveedores Nacionales - Servicios',             'nivel': 6},
    {'codigo': '220510',  'nombre': 'Proveedores Nacionales - Mixto',                 'nivel': 6},
    {'codigo': '2210',    'nombre': 'Proveedores del Exterior',                       'nivel': 4},
    {'codigo': '221005',  'nombre': 'Proveedores del Exterior - Bienes',              'nivel': 6},
    {'codigo': '221010',  'nombre': 'Proveedores del Exterior - Servicios',           'nivel': 6},

    # Grupo 23 — Cuentas por Pagar
    {'codigo': '23',      'nombre': 'Cuentas por Pagar Comerciales y Otras',         'nivel': 2},
    {'codigo': '2315',    'nombre': 'Cuentas Corrientes Comerciales',                 'nivel': 4},
    {'codigo': '2335',    'nombre': 'Costos y Gastos por Pagar',                      'nivel': 4},
    {'codigo': '233505',  'nombre': 'Gastos Bancarios',                               'nivel': 6},
    {'codigo': '233510',  'nombre': 'Honorarios por Pagar',                           'nivel': 6},
    {'codigo': '233515',  'nombre': 'Comisiones por Pagar',                           'nivel': 6},
    {'codigo': '233520',  'nombre': 'Arrendamientos por Pagar',                       'nivel': 6},
    {'codigo': '233525',  'nombre': 'Servicios Publicos por Pagar',                   'nivel': 6},
    {'codigo': '233530',  'nombre': 'Transporte por Pagar',                           'nivel': 6},
    {'codigo': '233535',  'nombre': 'Publicidad por Pagar',                           'nivel': 6},
    {'codigo': '233540',  'nombre': 'Seguro por Pagar',                               'nivel': 6},
    {'codigo': '233545',  'nombre': 'Mantenimiento por Pagar',                        'nivel': 6},
    {'codigo': '233550',  'nombre': 'Servicios Publicos',                             'nivel': 6},
    {'codigo': '233595',  'nombre': 'Otros Costos y Gastos',                          'nivel': 6},
    {'codigo': '2340',    'nombre': 'Instalamentos por Pagar',                        'nivel': 4},
    {'codigo': '2355',    'nombre': 'Deudas con Accionistas o Socios',                'nivel': 4},
    {'codigo': '2360',    'nombre': 'Dividendos o Participaciones por Pagar',         'nivel': 4},

    # Retenciones en la Fuente
    {'codigo': '2365',    'nombre': 'Retencion en la Fuente',                         'nivel': 4},
    {'codigo': '236505',  'nombre': 'Retencion en la Fuente - Salarios',              'nivel': 6},
    {'codigo': '236510',  'nombre': 'Retencion en la Fuente - Honorarios',            'nivel': 6},
    {'codigo': '236515',  'nombre': 'Retencion en la Fuente - Servicios',             'nivel': 6},
    {'codigo': '236520',  'nombre': 'Retencion en la Fuente - Rendimientos Fin.',     'nivel': 6},
    {'codigo': '236525',  'nombre': 'Retencion en la Fuente - Arrendamientos',        'nivel': 6},
    {'codigo': '236530',  'nombre': 'Retencion en la Fuente - Dividendos',            'nivel': 6},
    {'codigo': '236540',  'nombre': 'Retencion en la Fuente - Compras',               'nivel': 6},
    {'codigo': '236550',  'nombre': 'Retencion en la Fuente - Loteria y Rifas',       'nivel': 6},
    {'codigo': '236595',  'nombre': 'Retencion en la Fuente - Otros',                 'nivel': 6},

    # ReteICA
    {'codigo': '2368',    'nombre': 'Impuesto de Industria y Comercio Retenido',      'nivel': 4},
    {'codigo': '236805',  'nombre': 'ICA Retenido - Actividades Comerciales',         'nivel': 6},
    {'codigo': '236810',  'nombre': 'ICA Retenido - Actividades de Servicio',         'nivel': 6},
    {'codigo': '236815',  'nombre': 'ICA Retenido - Actividades Industriales',        'nivel': 6},

    # Nomina y SS
    {'codigo': '2370',    'nombre': 'Retenciones y Aportes de Nomina',                'nivel': 4},
    {'codigo': '237005',  'nombre': 'Aportes a Seguridad Social EPS',                 'nivel': 6},
    {'codigo': '237006',  'nombre': 'Aportes a Riesgos Laborales ARL',                'nivel': 6},
    {'codigo': '237010',  'nombre': 'Aportes a Fondos de Pensiones AFP',              'nivel': 6},
    {'codigo': '237015',  'nombre': 'Aportes al SENA',                                'nivel': 6},
    {'codigo': '237020',  'nombre': 'Aportes al ICBF',                                'nivel': 6},
    {'codigo': '237025',  'nombre': 'Aportes Caja de Compensacion',                   'nivel': 6},
    {'codigo': '2375',    'nombre': 'Acreedores Oficiales',                           'nivel': 4},
    {'codigo': '2380',    'nombre': 'Acreedores Varios',                              'nivel': 4},
    {'codigo': '238005',  'nombre': 'Cuotas por Pagar',                               'nivel': 6},
    {'codigo': '238030',  'nombre': 'Fondos de Cesantias',                            'nivel': 6},
    {'codigo': '238095',  'nombre': 'Anticipos Recibidos de Clientes',                'nivel': 6},
    {'codigo': '2395',    'nombre': 'Otras Cuentas por Pagar',                        'nivel': 4},
    {'codigo': '239505',  'nombre': 'Otras Obligaciones',                             'nivel': 6},

    # Grupo 24 — Impuestos
    {'codigo': '24',      'nombre': 'Impuestos, Gravamenes y Tasas',                  'nivel': 2},
    {'codigo': '2404',    'nombre': 'Impuesto de Renta y Complementarios',            'nivel': 4},
    {'codigo': '2408',    'nombre': 'Impuesto sobre las Ventas por Pagar',            'nivel': 4},
    {'codigo': '240805',  'nombre': 'IVA Generado',                                   'nivel': 6},
    {'codigo': '240810',  'nombre': 'IVA Descontable',                                'nivel': 6},
    {'codigo': '2412',    'nombre': 'Impuesto de Industria y Comercio',               'nivel': 4},
    {'codigo': '2416',    'nombre': 'Impuesto a la Propiedad Raiz',                   'nivel': 4},
    {'codigo': '2424',    'nombre': 'Impuesto de Vehiculos',                          'nivel': 4},
    {'codigo': '2480',    'nombre': 'Impuesto de Timbre Nacional',                    'nivel': 4},

    # Grupo 25 — Obligaciones Laborales
    {'codigo': '25',      'nombre': 'Obligaciones Laborales',                         'nivel': 2},
    {'codigo': '2505',    'nombre': 'Salarios por Pagar',                             'nivel': 4},
    {'codigo': '250505',  'nombre': 'Nomina por Pagar',                               'nivel': 6},
    {'codigo': '2510',    'nombre': 'Cesantias Consolidadas',                         'nivel': 4},
    {'codigo': '251005',  'nombre': 'Cesantias del Ejercicio',                        'nivel': 6},
    {'codigo': '2515',    'nombre': 'Intereses sobre Cesantias',                      'nivel': 4},
    {'codigo': '2520',    'nombre': 'Prima de Servicios',                             'nivel': 4},
    {'codigo': '252005',  'nombre': 'Prima Legal de Servicios',                       'nivel': 6},
    {'codigo': '2525',    'nombre': 'Vacaciones Consolidadas',                        'nivel': 4},
    {'codigo': '252505',  'nombre': 'Vacaciones del Ejercicio',                       'nivel': 6},
    {'codigo': '2530',    'nombre': 'Prestaciones Extralegales',                      'nivel': 4},
    {'codigo': '2595',    'nombre': 'Otras Obligaciones Laborales',                   'nivel': 4},

    # Grupo 26 — Pasivos Diferidos
    {'codigo': '26',      'nombre': 'Pasivos Diferidos',                              'nivel': 2},
    {'codigo': '2605',    'nombre': 'Arrendamientos Recibidos por Anticipado',        'nivel': 4},
    {'codigo': '2615',    'nombre': 'Ingresos Recibidos por Anticipado',              'nivel': 4},
    {'codigo': '261505',  'nombre': 'Anticipos de Clientes',                          'nivel': 6},

    # Grupo 27 — Bonos y Papeles Comerciales
    {'codigo': '27',      'nombre': 'Bonos y Papeles Comerciales',                    'nivel': 2},

    # Grupo 28 — Pasivos Estimados y Provisiones
    {'codigo': '28',      'nombre': 'Pasivos Estimados y Provisiones',                'nivel': 2},
    {'codigo': '2805',    'nombre': 'Para Costos y Gastos',                           'nivel': 4},
    {'codigo': '280505',  'nombre': 'Para Prestaciones Sociales',                     'nivel': 6},
    {'codigo': '2815',    'nombre': 'Para Obligaciones Fiscales',                     'nivel': 4},
    {'codigo': '2895',    'nombre': 'Otros Pasivos Estimados',                        'nivel': 4},
]

# ============================================================================
# CLASE 3 — PATRIMONIO
# ============================================================================
CUENTAS_PATRIMONIO = [
    {'codigo': '3',       'nombre': 'Patrimonio',                                     'nivel': 1},

    {'codigo': '31',      'nombre': 'Capital Social',                                 'nivel': 2},
    {'codigo': '3105',    'nombre': 'Capital suscrito y pagado',                      'nivel': 4},
    {'codigo': '310505',  'nombre': 'Capital autorizado',                             'nivel': 6},
    {'codigo': '310510',  'nombre': 'Capital por suscribir',                          'nivel': 6},
    {'codigo': '3115',    'nombre': 'Aportes sociales',                               'nivel': 4},
    {'codigo': '311505',  'nombre': 'Cuotas o partes de interes social',              'nivel': 6},
    {'codigo': '3120',    'nombre': 'Fondo social',                                   'nivel': 4},
    {'codigo': '3125',    'nombre': 'Capital garantia',                               'nivel': 4},
    {'codigo': '3130',    'nombre': 'Capital de personas naturales',                  'nivel': 4},

    {'codigo': '32',      'nombre': 'Superavit de Capital',                           'nivel': 2},
    {'codigo': '3205',    'nombre': 'Prima en colocacion de acciones',                'nivel': 4},
    {'codigo': '3210',    'nombre': 'Know how',                                       'nivel': 4},
    {'codigo': '3215',    'nombre': 'Donaciones',                                     'nivel': 4},
    {'codigo': '3220',    'nombre': 'Credito mercantil',                              'nivel': 4},
    {'codigo': '3225',    'nombre': 'Superavit metodo de participacion',              'nivel': 4},
    {'codigo': '3230',    'nombre': 'Superavit por donacion',                         'nivel': 4},
    {'codigo': '3295',    'nombre': 'Otros superavit de capital',                     'nivel': 4},

    {'codigo': '33',      'nombre': 'Reservas',                                       'nivel': 2},
    {'codigo': '3305',    'nombre': 'Reserva legal',                                  'nivel': 4},
    {'codigo': '330505',  'nombre': 'Apropiacion del 10% utilidad neta',              'nivel': 6},
    {'codigo': '3310',    'nombre': 'Reservas para capital',                          'nivel': 4},
    {'codigo': '3315',    'nombre': 'Reservas para readquisicion de acciones',        'nivel': 4},
    {'codigo': '3320',    'nombre': 'Reservas estatutarias',                          'nivel': 4},
    {'codigo': '3325',    'nombre': 'Reservas ocasionales',                           'nivel': 4},
    {'codigo': '332505',  'nombre': 'Para futuros ensanches',                         'nivel': 6},
    {'codigo': '332510',  'nombre': 'Para proteccion de inversiones',                 'nivel': 6},
    {'codigo': '332515',  'nombre': 'Para fines especificos',                         'nivel': 6},
    {'codigo': '3330',    'nombre': 'Reservas por disposiciones fiscales',            'nivel': 4},
    {'codigo': '3395',    'nombre': 'Otras reservas',                                 'nivel': 4},

    {'codigo': '34',      'nombre': 'Revalorizacion del Patrimonio',                  'nivel': 2},
    {'codigo': '3405',    'nombre': 'Ajuste por inflacion al patrimonio',             'nivel': 4},

    {'codigo': '36',      'nombre': 'Resultados del Ejercicio',                       'nivel': 2},
    {'codigo': '3605',    'nombre': 'Utilidad del ejercicio',                         'nivel': 4},
    {'codigo': '3610',    'nombre': 'Perdida del ejercicio',                          'nivel': 4},

    {'codigo': '37',      'nombre': 'Resultados de Ejercicios Anteriores',            'nivel': 2},
    {'codigo': '3705',    'nombre': 'Utilidades acumuladas',                          'nivel': 4},
    {'codigo': '3710',    'nombre': 'Perdidas acumuladas',                            'nivel': 4},
    {'codigo': '3715',    'nombre': 'Ganancias o excedentes acumulados',              'nivel': 4},

    {'codigo': '38',      'nombre': 'Superavit por Valorizaciones',                   'nivel': 2},
    {'codigo': '3805',    'nombre': 'Valorizaciones de inmuebles',                    'nivel': 4},
    {'codigo': '3810',    'nombre': 'Valorizaciones de inversiones',                  'nivel': 4},
    {'codigo': '3815',    'nombre': 'Valorizaciones de maquinaria y equipo',          'nivel': 4},
    {'codigo': '3820',    'nombre': 'Valorizaciones de muebles y enseres',            'nivel': 4},
    {'codigo': '3895',    'nombre': 'Otras valorizaciones',                           'nivel': 4},
]

# ============================================================================
# CLASE 4 — INGRESOS
# ============================================================================
CUENTAS_INGRESO = [
    {'codigo': '4',       'nombre': 'Ingresos',                                       'nivel': 1},

    # Grupo 41 — Ingresos Operacionales
    {'codigo': '41',      'nombre': 'Ingresos Operacionales',                         'nivel': 2},
    {'codigo': '4105',    'nombre': 'Industria Manufacturera',                        'nivel': 4},
    {'codigo': '4110',    'nombre': 'Industria Extractiva',                           'nivel': 4},
    {'codigo': '4115',    'nombre': 'Servicios',                                      'nivel': 4},
    {'codigo': '411505',  'nombre': 'Servicios Prestados',                            'nivel': 6},
    {'codigo': '4120',    'nombre': 'Honorarios',                                     'nivel': 4},
    {'codigo': '412005',  'nombre': 'Honorarios por Servicios Profesionales',         'nivel': 6},
    {'codigo': '4125',    'nombre': 'Comisiones',                                     'nivel': 4},
    {'codigo': '4130',    'nombre': 'Intereses y Correcciones Monetarias',            'nivel': 4},
    {'codigo': '4135',    'nombre': 'Comercio al por Mayor y al por Menor',           'nivel': 4},
    {'codigo': '413505',  'nombre': 'Venta de Mercancias',                            'nivel': 6},
    {'codigo': '413510',  'nombre': 'Venta de Servicios',                             'nivel': 6},
    {'codigo': '413515',  'nombre': 'Venta de Productos Terminados',                  'nivel': 6},
    {'codigo': '4140',    'nombre': 'Construccion',                                   'nivel': 4},
    {'codigo': '4155',    'nombre': 'Contratos con el Estado',                        'nivel': 4},
    {'codigo': '4165',    'nombre': 'Agricultura Ganaderia y Similares',              'nivel': 4},
    {'codigo': '4175',    'nombre': 'Devoluciones en Ventas DB',                      'nivel': 4},
    {'codigo': '417505',  'nombre': 'Devoluciones y Descuentos en Ventas',            'nivel': 6},
    {'codigo': '4180',    'nombre': 'Descuentos Comerciales en Ventas',               'nivel': 4},
    {'codigo': '418005',  'nombre': 'Descuentos Comerciales Concedidos',              'nivel': 6},

    # Grupo 42 — Ingresos No Operacionales
    {'codigo': '42',      'nombre': 'Ingresos No Operacionales',                      'nivel': 2},
    {'codigo': '4205',    'nombre': 'Utilidad en Venta de Inversiones',               'nivel': 4},
    {'codigo': '4210',    'nombre': 'Financieros',                                    'nivel': 4},
    {'codigo': '421005',  'nombre': 'Intereses Bancarios',                            'nivel': 6},
    {'codigo': '421010',  'nombre': 'Descuentos Comerciales Obtenidos',               'nivel': 6},
    {'codigo': '421015',  'nombre': 'Rendimientos Financieros',                       'nivel': 6},
    {'codigo': '4215',    'nombre': 'Dividendos y Participaciones',                   'nivel': 4},
    {'codigo': '4220',    'nombre': 'Arrendamientos',                                 'nivel': 4},
    {'codigo': '4225',    'nombre': 'Comisiones',                                     'nivel': 4},
    {'codigo': '4230',    'nombre': 'Honorarios',                                     'nivel': 4},
    {'codigo': '4235',    'nombre': 'Servicios',                                      'nivel': 4},
    {'codigo': '4240',    'nombre': 'Utilidad en Venta de Propiedades Planta y Equipo','nivel': 4},
    {'codigo': '4245',    'nombre': 'Devoluciones en Compras',                        'nivel': 4},
    {'codigo': '4250',    'nombre': 'Recuperaciones',                                 'nivel': 4},
    {'codigo': '4255',    'nombre': 'Indemnizaciones',                                'nivel': 4},
    {'codigo': '4295',    'nombre': 'Diversos',                                       'nivel': 4},
    {'codigo': '429505',  'nombre': 'Otros Ingresos No Operacionales',                'nivel': 6},
]

# ============================================================================
# CLASE 5 — GASTOS
# ============================================================================
CUENTAS_GASTO = [
    {'codigo': '5',       'nombre': 'Gastos',                                         'nivel': 1},

    # Grupo 51 — Gastos de Personal
    {'codigo': '51',      'nombre': 'Gastos de Personal',                             'nivel': 2},

    {'codigo': '5105',    'nombre': 'Sueldos y salarios',                             'nivel': 4},
    {'codigo': '510505',  'nombre': 'Jornales',                                       'nivel': 6},
    {'codigo': '510506',  'nombre': 'Sueldos',                                        'nivel': 6},
    {'codigo': '510527',  'nombre': 'Auxilio de Transporte',                          'nivel': 6},
    {'codigo': '510530',  'nombre': 'Cesantias',                                      'nivel': 6},
    {'codigo': '510533',  'nombre': 'Intereses sobre Cesantias',                      'nivel': 6},
    {'codigo': '510536',  'nombre': 'Prima de Servicios',                             'nivel': 6},
    {'codigo': '510539',  'nombre': 'Vacaciones',                                     'nivel': 6},
    {'codigo': '510568',  'nombre': 'Aportes a Seguridad Social Integral',            'nivel': 6},
    {'codigo': '510570',  'nombre': 'Aportes a Cajas de Compensacion Familiar',       'nivel': 6},

    {'codigo': '5110',    'nombre': 'Horas extras y recargos',                        'nivel': 4},
    {'codigo': '511005',  'nombre': 'Horas extras diurnas',                           'nivel': 6},
    {'codigo': '511010',  'nombre': 'Horas extras nocturnas',                         'nivel': 6},
    {'codigo': '511015',  'nombre': 'Recargo nocturno',                               'nivel': 6},
    {'codigo': '511020',  'nombre': 'Recargo dominical y festivo',                    'nivel': 6},

    {'codigo': '5115',    'nombre': 'Auxilios',                                       'nivel': 4},
    {'codigo': '511505',  'nombre': 'Auxilio de transporte',                          'nivel': 6},
    {'codigo': '511510',  'nombre': 'Auxilio de alimentacion',                        'nivel': 6},
    {'codigo': '511515',  'nombre': 'Auxilio educativo',                              'nivel': 6},
    {'codigo': '511520',  'nombre': 'Auxilio de vivienda',                            'nivel': 6},

    {'codigo': '5120',    'nombre': 'Cesantias consolidadas',                         'nivel': 4},
    {'codigo': '512005',  'nombre': 'Cesantias del ejercicio',                        'nivel': 6},
    {'codigo': '512010',  'nombre': 'Construcciones y Edificaciones',                 'nivel': 6},

    {'codigo': '5125',    'nombre': 'Intereses sobre cesantias',                      'nivel': 4},
    {'codigo': '512505',  'nombre': 'Intereses sobre cesantias del ejercicio',        'nivel': 6},

    {'codigo': '5130',    'nombre': 'Prima de servicios',                             'nivel': 4},
    {'codigo': '513005',  'nombre': 'Prima legal de servicios',                       'nivel': 6},
    {'codigo': '513010',  'nombre': 'Prima extralegal de servicios',                  'nivel': 6},
    {'codigo': '513025',  'nombre': 'Seguro contra incendio',                         'nivel': 6},

    {'codigo': '5135',    'nombre': 'Vacaciones consolidadas',                        'nivel': 4},
    {'codigo': '513505',  'nombre': 'Aseo y Vigilancia',                              'nivel': 6},
    {'codigo': '513520',  'nombre': 'Energia Electrica',                              'nivel': 6},
    {'codigo': '513525',  'nombre': 'Acueducto y Alcantarillado',                     'nivel': 6},
    {'codigo': '513530',  'nombre': 'Gas Natural',                                    'nivel': 6},
    {'codigo': '513535',  'nombre': 'Telefono / Internet',                            'nivel': 6},

    {'codigo': '5140',    'nombre': 'Dotacion y suministros',                         'nivel': 4},
    {'codigo': '514005',  'nombre': 'Calzado y vestido de labor',                     'nivel': 6},
    {'codigo': '514510',  'nombre': 'Construcciones y Edificaciones',                 'nivel': 6},
    {'codigo': '514525',  'nombre': 'Equipo de Computacion',                          'nivel': 6},

    {'codigo': '5145',    'nombre': 'Pensiones de jubilacion',                        'nivel': 4},
    {'codigo': '5150',    'nombre': 'Indemnizaciones laborales',                      'nivel': 4},

    {'codigo': '5155',    'nombre': 'Gastos medicos y drogas',                        'nivel': 4},
    {'codigo': '515505',  'nombre': 'Medicamentos y droguerias',                      'nivel': 6},
    {'codigo': '515510',  'nombre': 'Servicios medicos',                              'nivel': 6},

    {'codigo': '5160',    'nombre': 'Capacitacion al personal',                       'nivel': 4},
    {'codigo': '516005',  'nombre': 'Cursos y seminarios',                            'nivel': 6},

    {'codigo': '5165',    'nombre': 'Aportes EPS',                                    'nivel': 4},
    {'codigo': '516505',  'nombre': 'Aporte empleador salud',                         'nivel': 6},

    {'codigo': '5170',    'nombre': 'Aportes AFP',                                    'nivel': 4},
    {'codigo': '517005',  'nombre': 'Aporte empleador pension',                       'nivel': 6},

    {'codigo': '5175',    'nombre': 'Aportes ARL',                                    'nivel': 4},
    {'codigo': '517505',  'nombre': 'Aporte empleador ARL',                           'nivel': 6},

    {'codigo': '5180',    'nombre': 'Aportes SENA, ICBF y Caja',                      'nivel': 4},
    {'codigo': '518005',  'nombre': 'Aporte al SENA',                                 'nivel': 6},
    {'codigo': '518010',  'nombre': 'Aporte al ICBF',                                 'nivel': 6},
    {'codigo': '518015',  'nombre': 'Aporte caja de compensacion familiar',           'nivel': 6},

    {'codigo': '5195',    'nombre': 'Otros gastos de personal',                       'nivel': 4},
    {'codigo': '519505',  'nombre': 'Otros gastos de personal',                       'nivel': 6},
    {'codigo': '519525',  'nombre': 'Elementos de Aseo y Cafeteria',                  'nivel': 6},
    {'codigo': '519530',  'nombre': 'Utiles, Papeleria y Fotocopias',                 'nivel': 6},

    # Grupo 52 — Honorarios
    {'codigo': '52',      'nombre': 'Honorarios',                                     'nivel': 2},
    {'codigo': '5205',    'nombre': 'Junta directiva y/o consejo',                    'nivel': 4},
    {'codigo': '5210',    'nombre': 'Revisor fiscal',                                 'nivel': 4},
    {'codigo': '5215',    'nombre': 'Auditoria externa',                              'nivel': 4},
    {'codigo': '5220',    'nombre': 'Avaluos',                                        'nivel': 4},
    {'codigo': '5225',    'nombre': 'Asesoria juridica',                              'nivel': 4},
    {'codigo': '5230',    'nombre': 'Asesoria financiera',                            'nivel': 4},
    {'codigo': '5235',    'nombre': 'Asesoria tecnica',                               'nivel': 4},
    {'codigo': '5240',    'nombre': 'Asesoria en sistemas e informatica',             'nivel': 4},
    {'codigo': '5245',    'nombre': 'Asesoria contable',                              'nivel': 4},
    {'codigo': '5295',    'nombre': 'Otros honorarios',                               'nivel': 4},

    # Grupo 53 — Impuestos
    {'codigo': '53',      'nombre': 'Impuestos',                                      'nivel': 2},
    {'codigo': '5305',    'nombre': 'Impuesto de renta y complementarios',            'nivel': 4},
    {'codigo': '5310',    'nombre': 'Impuesto de ventas no descontable',              'nivel': 4},
    {'codigo': '5315',    'nombre': 'Impuesto de industria y comercio',               'nivel': 4},
    {'codigo': '5320',    'nombre': 'Impuesto de vehiculos',                          'nivel': 4},
    {'codigo': '5325',    'nombre': 'Impuesto predial unificado',                     'nivel': 4},
    {'codigo': '5330',    'nombre': 'Impuesto de timbre',                             'nivel': 4},
    {'codigo': '5340',    'nombre': 'Gravamen a movimientos financieros 4x1000',      'nivel': 4},
    {'codigo': '5395',    'nombre': 'Otros impuestos',                                'nivel': 4},

    # Grupo 54 — Arrendamientos
    {'codigo': '54',      'nombre': 'Arrendamientos',                                 'nivel': 2},
    {'codigo': '5405',    'nombre': 'Arrendamiento de terrenos',                      'nivel': 4},
    {'codigo': '5410',    'nombre': 'Arrendamiento de construcciones y edificios',    'nivel': 4},
    {'codigo': '5415',    'nombre': 'Arrendamiento de maquinaria y equipo',           'nivel': 4},
    {'codigo': '5420',    'nombre': 'Arrendamiento de equipo de oficina',             'nivel': 4},
    {'codigo': '5425',    'nombre': 'Arrendamiento de equipo de computo',             'nivel': 4},
    {'codigo': '5430',    'nombre': 'Arrendamiento de equipo de transporte',          'nivel': 4},
    {'codigo': '5435',    'nombre': 'Arrendamiento parqueadero',                      'nivel': 4},
    {'codigo': '5495',    'nombre': 'Otros arrendamientos',                           'nivel': 4},

    # Grupo 55 — Contribuciones y Afiliaciones
    {'codigo': '55',      'nombre': 'Contribuciones y Afiliaciones',                  'nivel': 2},
    {'codigo': '5505',    'nombre': 'Asociaciones gremiales',                         'nivel': 4},
    {'codigo': '5510',    'nombre': 'Asociaciones cientificas y tecnologicas',        'nivel': 4},
    {'codigo': '5515',    'nombre': 'Contribuciones y afiliaciones civicas',          'nivel': 4},
    {'codigo': '5595',    'nombre': 'Otras contribuciones',                           'nivel': 4},

    # Grupo 56 — Seguros
    {'codigo': '56',      'nombre': 'Seguros',                                        'nivel': 2},
    {'codigo': '5605',    'nombre': 'Seguro de vida colectivo',                       'nivel': 4},
    {'codigo': '5610',    'nombre': 'Seguro de incendio y terremoto',                 'nivel': 4},
    {'codigo': '5615',    'nombre': 'Seguro de maquinaria y equipo',                  'nivel': 4},
    {'codigo': '5620',    'nombre': 'Seguro de vehiculos',                            'nivel': 4},
    {'codigo': '5625',    'nombre': 'Seguro de transporte',                           'nivel': 4},
    {'codigo': '5630',    'nombre': 'Seguro de manejo',                               'nivel': 4},
    {'codigo': '5635',    'nombre': 'Seguro de sustraccion',                          'nivel': 4},
    {'codigo': '5640',    'nombre': 'Seguro todo riesgo',                             'nivel': 4},
    {'codigo': '5695',    'nombre': 'Otros seguros',                                  'nivel': 4},

    # Grupo 57 — Servicios
    {'codigo': '57',      'nombre': 'Servicios',                                      'nivel': 2},
    {'codigo': '5705',    'nombre': 'Aseo y vigilancia',                              'nivel': 4},
    {'codigo': '570505',  'nombre': 'Aseo y limpieza',                                'nivel': 6},
    {'codigo': '570510',  'nombre': 'Vigilancia y seguridad',                         'nivel': 6},
    {'codigo': '5710',    'nombre': 'Acueducto energia y gas',                        'nivel': 4},
    {'codigo': '571005',  'nombre': 'Acueducto y alcantarillado',                     'nivel': 6},
    {'codigo': '571010',  'nombre': 'Energia electrica',                              'nivel': 6},
    {'codigo': '571015',  'nombre': 'Gas domiciliario',                               'nivel': 6},
    {'codigo': '5715',    'nombre': 'Telefonia y comunicaciones',                     'nivel': 4},
    {'codigo': '571505',  'nombre': 'Telefono fijo',                                  'nivel': 6},
    {'codigo': '571510',  'nombre': 'Celular y movil',                                'nivel': 6},
    {'codigo': '571515',  'nombre': 'Internet y datos',                               'nivel': 6},
    {'codigo': '571520',  'nombre': 'Correo y correspondencia',                       'nivel': 6},
    {'codigo': '5720',    'nombre': 'Transporte fletes y acarreos',                   'nivel': 4},
    {'codigo': '572005',  'nombre': 'Fletes de mercancias',                           'nivel': 6},
    {'codigo': '572010',  'nombre': 'Transporte de personal',                         'nivel': 6},
    {'codigo': '5725',    'nombre': 'Publicidad propaganda y promocion',              'nivel': 4},
    {'codigo': '572505',  'nombre': 'Publicidad',                                     'nivel': 6},
    {'codigo': '572510',  'nombre': 'Propaganda y marketing',                         'nivel': 6},
    {'codigo': '5730',    'nombre': 'Relaciones publicas',                            'nivel': 4},
    {'codigo': '5735',    'nombre': 'Servicios de computacion y tecnologia',          'nivel': 4},
    {'codigo': '573505',  'nombre': 'Licencias de software',                          'nivel': 6},
    {'codigo': '573510',  'nombre': 'Hosting y servicios en la nube',                 'nivel': 6},
    {'codigo': '573515',  'nombre': 'Soporte tecnico',                                'nivel': 6},
    {'codigo': '5740',    'nombre': 'Correo portes y telegramas',                     'nivel': 4},
    {'codigo': '5745',    'nombre': 'Traducc. transcripc. y fotocopias',              'nivel': 4},
    {'codigo': '5750',    'nombre': 'Casino y restaurante',                           'nivel': 4},
    {'codigo': '5755',    'nombre': 'Mantenimiento y reparaciones',                   'nivel': 4},
    {'codigo': '575505',  'nombre': 'Mantenimiento de edificios',                     'nivel': 6},
    {'codigo': '575510',  'nombre': 'Mantenimiento de maquinaria y equipo',           'nivel': 6},
    {'codigo': '575515',  'nombre': 'Mantenimiento de equipo de computo',             'nivel': 6},
    {'codigo': '575520',  'nombre': 'Mantenimiento de vehiculos',                     'nivel': 6},
    {'codigo': '5760',    'nombre': 'Adecuacion e instalacion',                       'nivel': 4},
    {'codigo': '5765',    'nombre': 'Asistencia tecnica',                             'nivel': 4},
    {'codigo': '5770',    'nombre': 'Servicios temporales',                           'nivel': 4},
    {'codigo': '5795',    'nombre': 'Otros servicios',                                'nivel': 4},

    # Grupo 58 — Gastos Legales
    {'codigo': '58',      'nombre': 'Gastos Legales',                                 'nivel': 2},
    {'codigo': '5805',    'nombre': 'Gastos notariales',                              'nivel': 4},
    {'codigo': '5810',    'nombre': 'Registro mercantil',                             'nivel': 4},
    {'codigo': '5815',    'nombre': 'Tramites y licencias',                           'nivel': 4},
    {'codigo': '5820',    'nombre': 'Investigacion de mercados',                      'nivel': 4},
    {'codigo': '5895',    'nombre': 'Otros gastos legales',                           'nivel': 4},

    # Grupo 59 — Gastos Diversos
    {'codigo': '59',      'nombre': 'Gastos Diversos',                                'nivel': 2},
    {'codigo': '5905',    'nombre': 'Depreciaciones',                                 'nivel': 4},
    {'codigo': '590505',  'nombre': 'Depreciacion de edificaciones',                  'nivel': 6},
    {'codigo': '590510',  'nombre': 'Depreciacion de maquinaria y equipo',            'nivel': 6},
    {'codigo': '590515',  'nombre': 'Depreciacion de muebles y enseres',              'nivel': 6},
    {'codigo': '590520',  'nombre': 'Depreciacion de equipo de oficina',              'nivel': 6},
    {'codigo': '590525',  'nombre': 'Depreciacion de equipo de computo',              'nivel': 6},
    {'codigo': '590530',  'nombre': 'Depreciacion de equipo de comunicacion',         'nivel': 6},
    {'codigo': '590535',  'nombre': 'Depreciacion de vehiculos',                      'nivel': 6},
    {'codigo': '590540',  'nombre': 'Depreciacion de activos fijos en general',       'nivel': 6},
    {'codigo': '5910',    'nombre': 'Amortizaciones',                                 'nivel': 4},
    {'codigo': '591005',  'nombre': 'Amortizacion de gastos pagados por anticipado',  'nivel': 6},
    {'codigo': '591010',  'nombre': 'Amortizacion de intangibles',                    'nivel': 6},
    {'codigo': '591015',  'nombre': 'Amortizacion de cargos diferidos',               'nivel': 6},
    {'codigo': '5920',    'nombre': 'Provisiones',                                    'nivel': 4},
    {'codigo': '592005',  'nombre': 'Provision para deudas de dificil cobro',         'nivel': 6},
    {'codigo': '592010',  'nombre': 'Provision para obligaciones laborales',          'nivel': 6},
    {'codigo': '5925',    'nombre': 'Perdidas en venta y retiro de bienes',           'nivel': 4},
    {'codigo': '592505',  'nombre': 'Perdidas en venta de construcciones',            'nivel': 6},
    {'codigo': '592510',  'nombre': 'Perdidas en venta de maquinaria',                'nivel': 6},
    {'codigo': '592595',  'nombre': 'Perdidas en venta de otros activos',             'nivel': 6},
    {'codigo': '5940',    'nombre': 'Gastos extraordinarios',                         'nivel': 4},
    {'codigo': '594005',  'nombre': 'Costas y gastos procesales',                     'nivel': 6},
    {'codigo': '594010',  'nombre': 'Sanciones y multas',                             'nivel': 6},
    {'codigo': '594015',  'nombre': 'Relaciones publicas extraordinarias',            'nivel': 6},
    {'codigo': '5945',    'nombre': 'Gastos de ejercicios anteriores',                'nivel': 4},
    {'codigo': '5995',    'nombre': 'Otros gastos diversos',                          'nivel': 4},
    {'codigo': '599505',  'nombre': 'Elementos de aseo y cafeteria',                  'nivel': 6},
    {'codigo': '599510',  'nombre': 'Utiles y papeleria',                             'nivel': 6},
    {'codigo': '599515',  'nombre': 'Combustibles y lubricantes',                     'nivel': 6},
    {'codigo': '599520',  'nombre': 'Casino y restaurante',                           'nivel': 6},
    {'codigo': '599525',  'nombre': 'Libros revistas y suscripciones',                'nivel': 6},
    {'codigo': '599530',  'nombre': 'Gastos de viaje y representacion',               'nivel': 6},
    {'codigo': '599535',  'nombre': 'Fotocopias e impresiones',                       'nivel': 6},
    {'codigo': '599540',  'nombre': 'Equipos y bienes de menor cuantia',              'nivel': 6},
    {'codigo': '599545',  'nombre': 'Gastos bancarios y comisiones',                  'nivel': 6},
    {'codigo': '599550',  'nombre': 'Estampillas y timbre nacional',                  'nivel': 6},
    {'codigo': '599595',  'nombre': 'Otros gastos no clasificados',                   'nivel': 6},

    # Grupo 5199 — Deterioro
    {'codigo': '5199',    'nombre': 'Deterioro de Valor Gasto',                       'nivel': 4},
]

# ============================================================================
# CLASE 6 — COSTOS DE VENTAS (tipo=GASTO — no existe tipo COSTO en el modelo)
# ============================================================================
CUENTAS_COSTO = [
    {'codigo': '6',       'nombre': 'Costos de Ventas',                               'nivel': 1},

    # Grupo 61 — Costo de Ventas y Prestacion de Servicios
    {'codigo': '61',      'nombre': 'Costo de Ventas y Prestacion de Servicios',      'nivel': 2},
    {'codigo': '6105',    'nombre': 'Industria Manufacturera',                        'nivel': 4},
    {'codigo': '6110',    'nombre': 'Industria Extractiva',                           'nivel': 4},
    {'codigo': '6115',    'nombre': 'Compras',                                        'nivel': 4},
    {'codigo': '611505',  'nombre': 'Compras Mercancias',                             'nivel': 6},
    {'codigo': '6120',    'nombre': 'Servicios',                                      'nivel': 4},
    {'codigo': '612005',  'nombre': 'Costo de Servicios Prestados',                   'nivel': 6},
    {'codigo': '6125',    'nombre': 'Honorarios',                                     'nivel': 4},
    {'codigo': '6130',    'nombre': 'Mano de Obra',                                   'nivel': 4},
    {'codigo': '6135',    'nombre': 'Comercio al por Mayor y al por Menor',           'nivel': 4},
    {'codigo': '613505',  'nombre': 'Costo de Mercancias Vendidas',                   'nivel': 6},
    {'codigo': '613510',  'nombre': 'Costo de Servicios Prestados',                   'nivel': 6},
    {'codigo': '613515',  'nombre': 'Fletes y Acarreos en Ventas',                    'nivel': 6},
    {'codigo': '6140',    'nombre': 'Construccion',                                   'nivel': 4},
    {'codigo': '6145',    'nombre': 'Contratistas',                                   'nivel': 4},
    {'codigo': '6160',    'nombre': 'Agricultura Ganaderia y Similares',              'nivel': 4},
    {'codigo': '6175',    'nombre': 'Devoluciones en Compras DB',                     'nivel': 4},
    {'codigo': '617505',  'nombre': 'Devoluciones y Descuentos en Compras',           'nivel': 6},
    {'codigo': '6195',    'nombre': 'Otros Costos',                                   'nivel': 4},

    # Grupo 62 — Costos de Produccion
    {'codigo': '62',      'nombre': 'Costos de Produccion',                           'nivel': 2},
    {'codigo': '6205',    'nombre': 'Materias Primas',                                'nivel': 4},
    {'codigo': '6210',    'nombre': 'Mano de Obra Directa',                           'nivel': 4},
    {'codigo': '6215',    'nombre': 'Costos Indirectos',                              'nivel': 4},
]


# Mapa: tipo contable por clase de PUC
TIPO_POR_CLASE = {
    'ACTIVO':      'ACTIVO',
    'PASIVO':      'PASIVO',
    'PATRIMONIO':  'PATRIMONIO',
    'INGRESO':     'INGRESO',
    'GASTO':       'GASTO',
    'COSTO':       'GASTO',   # Sin tipo COSTO en el modelo — se guarda como GASTO
}

GRUPOS_DISPONIBLES = [
    ('ACTIVO',     CUENTAS_ACTIVO),
    ('PASIVO',     CUENTAS_PASIVO),
    ('PATRIMONIO', CUENTAS_PATRIMONIO),
    ('INGRESO',    CUENTAS_INGRESO),
    ('GASTO',      CUENTAS_GASTO),
    ('COSTO',      CUENTAS_COSTO),
]


class Command(BaseCommand):
    help = 'Poblar cuentas PUC Colombia PYMES — Clases 1 a 6 para todos los tenants activos'

    def add_arguments(self, parser):
        parser.add_argument('--tenants', type=str,
            help='IDs de tenants separados por coma (default: todos los activos)')
        parser.add_argument('--dry-run', action='store_true',
            help='Mostrar que se crearia sin persistir')
        parser.add_argument('--solo-activo',     action='store_true', help='Solo Clase 1 — Activo')
        parser.add_argument('--solo-pasivo',     action='store_true', help='Solo Clase 2 — Pasivo')
        parser.add_argument('--solo-patrimonio', action='store_true', help='Solo Clase 3 — Patrimonio')
        parser.add_argument('--solo-ingreso',    action='store_true', help='Solo Clase 4 — Ingreso')
        parser.add_argument('--solo-gasto',      action='store_true', help='Solo Clase 5 — Gasto')
        parser.add_argument('--solo-costo',      action='store_true', help='Solo Clase 6 — Costo de Ventas')

    def handle(self, *args, **options):
        from django.db import connection

        dry_run = options.get('dry_run', False)

        # Filtro de grupos por flags
        filtros = {
            'solo_activo':     'ACTIVO',
            'solo_pasivo':     'PASIVO',
            'solo_patrimonio': 'PATRIMONIO',
            'solo_ingreso':    'INGRESO',
            'solo_gasto':      'GASTO',
            'solo_costo':      'COSTO',
        }
        activos = [v for k, v in filtros.items() if options.get(k)]
        grupos = [(n, c) for n, c in GRUPOS_DISPONIBLES if not activos or n in activos]

        # Seleccionar tenants
        tenant_ids = None
        if options.get('tenants'):
            tenant_ids = [int(x.strip()) for x in options['tenants'].split(',')]
        tenants = (
            Tenant.objects.filter(id__in=tenant_ids)
            if tenant_ids
            else Tenant.objects.exclude(schema_name='public').filter(is_active=True)
        )

        if not tenants.exists():
            self.stdout.write(self.style.WARNING('No se encontraron tenants activos.'))
            return

        total = sum(len(c) for _, c in grupos)
        self.stdout.write(self.style.SUCCESS(
            f'PUC PYMES — {tenants.count()} tenant(s) | '
            f'{len(grupos)} clase(s) | {total} cuentas a verificar por tenant'
        ))

        for tenant in tenants:
            self.stdout.write(f'\n  Tenant: {tenant.nombre} (schema={tenant.schema_name})')

            with tenant:
                from django.apps import apps as django_apps
                try:
                    Empresa = django_apps.get_model('empresa', 'Empresa')
                    empresa = Empresa.objects.first()
                    if not empresa:
                        self.stdout.write(self.style.ERROR('    Sin Empresa configurada — omitir'))
                        continue
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f'    [WARN] {exc}'))
                    continue

                try:
                    with connection.cursor() as cur:
                        cur.execute(
                            "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                            "WHERE table_name='contabilidad_cuentacontable')"
                        )
                        if not cur.fetchone()[0]:
                            self.stdout.write(self.style.WARNING(
                                '    Tabla no existe — ejecutar migrate_schemas primero'))
                            continue
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f'    No se pudo verificar tabla: {exc}'))

                from apps.tenant.contabilidad.models import CuentaContable

                creadas = existentes = errores = 0

                for tipo_label, cuentas in grupos:
                    tipo_db = TIPO_POR_CLASE[tipo_label]
                    for c in cuentas:
                        try:
                            if dry_run:
                                if not CuentaContable.objects.filter(
                                    empresa=empresa, codigo=c['codigo']
                                ).exists():
                                    creadas += 1
                                    self.stdout.write(
                                        f'    [DRY] {c["codigo"]:12s}  {c["nombre"][:55]}'
                                    )
                                else:
                                    existentes += 1
                            else:
                                _, created = CuentaContable.objects.get_or_create(
                                    empresa=empresa,
                                    codigo=c['codigo'],
                                    defaults={
                                        'nombre': c['nombre'],
                                        'tipo': tipo_db,
                                        'nivel': c['nivel'],
                                        'activa': True,
                                    },
                                )
                                if created:
                                    creadas += 1
                                else:
                                    existentes += 1
                        except Exception as exc:
                            errores += 1
                            self.stdout.write(
                                self.style.ERROR(f'    [ERROR] {c["codigo"]}: {exc}')
                            )

                msg = (
                    f'    [DRY-RUN] Crearia {creadas} | Ya existen {existentes} | Errores {errores}'
                    if dry_run else
                    f'    [OK] Creadas: {creadas} | Ya existian: {existentes} | Errores: {errores}'
                )
                fn = self.style.WARNING if dry_run else self.style.SUCCESS
                self.stdout.write(fn(msg))

        self.stdout.write(self.style.SUCCESS('\n[DONE] Seed PUC PYMES (Clases 1-6) completado.'))
