"""Siembra el dataset del POC de recuperacion semantica (AI-VECTOR-08).

SOLO para el tenant de POC. Texto libre sintetico, NO sensible
(observaciones de clientes / descripciones de productos) -- nunca nomina,
bancos, saldos, informacion fiscal sensible (mandato AI-VECTOR §3).

Uso:
    python manage.py seed_ai_poc --schema aipoc
    python manage.py seed_ai_poc --schema otro --force   # anular el candado
"""

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context

# Candado: schemas donde este comando puede sembrar sin --force.
POC_SCHEMAS = {"aipoc"}

CLIENTES = [
    ("JURIDICA", "NIT", "900100001", "Ferreteria Andina SAS", "ORDINARIO",
     "Cliente institucional del sector construccion. Compra por volumen, "
     "pago a 45 dias contra entrega. Preferencia por herramienta electrica "
     "de marca reconocida. Contacto de compras responde rapido por correo."),
    ("JURIDICA", "NIT", "900100002", "Distribuidora El Roble Ltda", "SIMPLE",
     "Mayorista de material electrico y de plomeria. Solicita siempre ficha "
     "tecnica y garantia por escrito. Descuento negociado del 8 por ciento "
     "en pedidos superiores a diez millones."),
    ("NATURAL", "CC", "10203040", "Carlos Mendoza", "NO_RESP",
     "Contratista independiente de remodelaciones. Compras pequenas y "
     "frecuentes, paga de contado. Suele pedir asesoria sobre anclajes y "
     "fijaciones para muro seco."),
    ("JURIDICA", "NIT", "900100003", "Constructora Marina del Caribe SAS", "ORDINARIO",
     "Proyectos de vivienda en zona costera. Exige productos con proteccion "
     "contra corrosion y acero inoxidable. Entregas coordinadas con el "
     "residente de obra, nunca los viernes."),
    ("JURIDICA", "NIT", "900100004", "Suministros Hospitalarios del Valle SAS", "ORDINARIO",
     "Compra insumos de proteccion y aseo para clinicas: guantes, batas, "
     "gafas de seguridad. Requiere lote y fecha de vencimiento en cada "
     "remision. Condiciones comerciales: credito a 60 dias aprobado."),
    ("NATURAL", "CC", "52607080", "Ana Lucia Restrepo", "NO_RESP",
     "Disenadora de interiores. Pide catalogos de acabados y herrajes "
     "decorativos. Sensible al tiempo de entrega, prefiere retiro en tienda."),
    ("JURIDICA", "NIT", "900100005", "Agroinsumos La Sabana SAS", "SIMPLE",
     "Cliente rural, pedidos estacionales grandes antes de cada cosecha. "
     "Transporte por su cuenta. Historial de pago puntual, sin retenciones "
     "especiales aplicables."),
    ("JURIDICA", "NIT", "900100006", "Taller Industrial MecanoPro Ltda", "ORDINARIO",
     "Metalmecanica: consume pernos de alta resistencia, discos de corte y "
     "soldadura. Compra recurrente mensual. Solicita factura con detalle de "
     "grado y norma de cada sujetador."),
    ("NATURAL", "CC", "1090304050", "Julian Ospina", "NO_RESP",
     "Administrador de propiedad horizontal. Compra material de mantenimiento "
     "para zonas comunes. Requiere cotizacion formal antes de cada compra por "
     "politica del consejo."),
    ("JURIDICA", "NIT", "900100007", "Hoteles Serrania SAS", "ORDINARIO",
     "Cadena hotelera pequena. Reposicion de menaje, iluminacion y pequenos "
     "electrodomesticos. Facturacion consolidada mensual por sede. Pago a 30 dias."),
    ("JURIDICA", "NIT", "900100008", "Cooperativa de Transportadores Union", "SIMPLE",
     "Compra repuestos menores y lubricantes para flota. Negocia precio por "
     "contrato anual. Entrega en bodega central, horario de la manana."),
    ("NATURAL", "CC", "79508070", "Ricardo Pena", "NO_RESP",
     "Electricista certificado. Cliente frecuente de cable, canaletas y "
     "tableros. Aprecia disponibilidad inmediata; se va a la competencia si "
     "hay agotados."),
]

PRODUCTOS = [
    ("FE-TOR-001", "Tornillo autorroscante 4.2x25",
     "Tornillo autorroscante de acero galvanizado, cabeza plana Phillips, "
     "4.2 x 25 mm. Ideal para fijar lamina metalica delgada y perfileria de "
     "muro seco. Caja de 500 unidades."),
    ("FE-PER-002", "Perno hexagonal grado 8.8 M10x60",
     "Perno hexagonal estructural grado 8.8, M10 x 60 mm, galvanizado en "
     "caliente. Alta resistencia a la traccion para uniones de acero en "
     "estructura metalica y bases de maquinaria."),
    ("FE-ANC-003", "Anclaje quimico para concreto 12 mm",
     "Sistema de anclaje quimico con cartucho de resina epoxica y varilla "
     "roscada de 12 mm. Fijacion de alta carga en concreto fisurado, "
     "barandas, estanterias industriales y equipos."),
    ("FE-DIS-004", "Disco de corte para metal 4-1/2",
     "Disco abrasivo de corte para metal, 4-1/2 pulgadas, espesor 1.0 mm, "
     "para amoladora angular. Corte rapido y limpio en varilla, tuberia y "
     "perfil. Maxima 13300 rpm."),
    ("EL-CAB-005", "Cable THHN 12 AWG rollo 100 m",
     "Cable de cobre THHN calibre 12 AWG, aislamiento termoplastico 90 C, "
     "600 V. Uso en circuitos ramales de iluminacion y tomacorrientes en "
     "instalaciones residenciales y comerciales. Rollo de 100 metros."),
    ("EL-BRK-006", "Breaker enchufable 2x30 A",
     "Interruptor termomagnetico enchufable bipolar 2 x 30 amperios, curva C, "
     "10 kA. Proteccion de circuitos de aire acondicionado y cargas de mayor "
     "consumo en tablero residencial."),
    ("PL-TUB-007", "Tuberia PVC presion 1/2 x 6 m",
     "Tuberia de PVC para presion, diametro 1/2 pulgada, longitud 6 metros, "
     "RDE 21. Conduccion de agua potable fria a presion en redes internas. "
     "Union con soldadura liquida PVC."),
    ("PR-GUA-008", "Guante de nitrilo azul talla M caja x100",
     "Guante de examen de nitrilo, sin polvo, color azul, talla M. "
     "Resistente a quimicos y punciones leves, uso medico y de laboratorio. "
     "Caja dispensadora de 100 unidades."),
    ("HE-TAL-009", "Taladro percutor 800 W",
     "Taladro percutor electrico de 800 W, portabrocas de 13 mm, velocidad "
     "variable y reversa. Perfora concreto, metal y madera. Incluye "
     "empunadura lateral y tope de profundidad."),
    ("PI-EPX-010", "Pintura epoxica gris para piso galon",
     "Recubrimiento epoxico bicomponente color gris para pisos de concreto "
     "en bodegas y talleres. Alta resistencia a la abrasion, aceites y "
     "trafico de montacargas. Rendimiento 8 m2 por galon."),
    ("SE-SOL-011", "Electrodo de soldadura 6013 x 1 kg",
     "Electrodo revestido E6013 de 1/8 pulgada para soldadura de arco "
     "manual. Arco suave y facil encendido, ideal para lamina y estructura "
     "liviana en todas las posiciones. Presentacion 1 kg."),
    ("AS-ESC-012", "Escoba industrial cerda dura",
     "Escoba de uso industrial con cerda de polipropileno rigida y cabo "
     "metalico reforzado. Para barrido de superficies rugosas, exteriores y "
     "residuos de obra."),
]


class Command(BaseCommand):
    help = "Siembra clientes/productos sinteticos (texto libre no sensible) para el POC de retrieval."

    def add_arguments(self, parser):
        parser.add_argument("--schema", default="aipoc", help="Schema del tenant (default: aipoc)")
        parser.add_argument("--force", action="store_true", help="Sembrar aunque el schema no sea de POC")
        parser.add_argument("--wipe", action="store_true", help="Borrar los clientes/productos sembrados antes")

    def handle(self, *args, **opts):
        schema = opts["schema"]
        if schema not in POC_SCHEMAS and not opts["force"]:
            raise CommandError(
                f"'{schema}' no esta en POC_SCHEMAS ({sorted(POC_SCHEMAS)}). "
                f"Usa --force si de verdad quieres sembrar ahi."
            )

        with schema_context(schema):
            from apps.tenant.clientes.models import Cliente
            from apps.tenant.empresa.models import Empresa
            from apps.tenant.inventario.models import Producto

            empresa = Empresa.objects.first()
            if empresa is None:
                raise CommandError(f"El schema '{schema}' no tiene Empresa -- crea el tenant primero.")

            if opts["wipe"]:
                nd = Cliente.objects.filter(empresa=empresa, numero_documento__in=[c[2] for c in CLIENTES]).delete()
                np = Producto.objects.filter(empresa=empresa, codigo__in=[p[0] for p in PRODUCTOS]).delete()
                self.stdout.write(f"wipe: clientes={nd[0]} productos={np[0]}")

            c_created = 0
            for tp, td, num, rs, reg, obs in CLIENTES:
                _, created = Cliente.objects.update_or_create(
                    empresa=empresa, tipo_documento=td, numero_documento=num,
                    defaults={
                        "tipo_persona": tp, "razon_social": rs,
                        "regimen_tributario": reg, "observaciones": obs, "activo": True,
                    },
                )
                c_created += int(created)

            p_created = 0
            for cod, nom, desc in PRODUCTOS:
                _, created = Producto.objects.update_or_create(
                    empresa=empresa, codigo=cod,
                    defaults={"nombre": nom, "descripcion": desc, "activo": True},
                )
                p_created += int(created)

            self.stdout.write(self.style.SUCCESS(
                f"OK schema={schema}: clientes {c_created} nuevos / {len(CLIENTES)} totales; "
                f"productos {p_created} nuevos / {len(PRODUCTOS)} totales."
            ))
            self.stdout.write("Siguiente: python manage.py shell -> reindex_tenant_knowledge o el task Celery.")
