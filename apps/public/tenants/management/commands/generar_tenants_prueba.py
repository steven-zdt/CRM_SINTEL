"""
Comando de management para generar 100 tenants privados con datos de prueba.

WARNING: v3.3: Genera tenants con datos realistas para análisis de comportamiento
WARNING: Uso: python manage.py generar_tenants_prueba --cantidad 100 --con-datos

Este comando:
1. Crea usuarios admin únicos para cada tenant
2. Crea tenants usando crear_tenant_con_owner()
3. Pobla cada tenant con datos de prueba (empresa, clientes, cotizaciones, proyectos)
4. Genera reporte de creación
"""

import importlib.util
import logging
import os
import random
from datetime import timedelta
from decimal import Decimal

# Importar desde el archivo services.py (evitar conflicto con directorio services/)
# Solución: Usar importlib para cargar el archivo services.py directamente
# ya que Python importa el directorio services/ en lugar del archivo services.py
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django_tenants.utils import schema_context

# Obtener el path base del proyecto
base_path = (
    settings.BASE_DIR
    if hasattr(settings, "BASE_DIR")
    else os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
services_py_path = os.path.join(base_path, "apps", "public", "tenants", "services.py")

if os.path.exists(services_py_path):
    spec = importlib.util.spec_from_file_location("tenants_services_py", services_py_path)
    tenants_services_py = importlib.util.module_from_spec(spec)
    # Necesitamos configurar el __package__ para que los imports relativos funcionen
    tenants_services_py.__package__ = "apps.public.tenants"
    spec.loader.exec_module(tenants_services_py)
    crear_tenant_con_owner = tenants_services_py.crear_tenant_con_owner
else:
    raise ImportError(
        f"No se encontró el archivo services.py en: {services_py_path}. "
        "Verifica que el archivo existe."
    )

from apps.public.accounts.api.services.user_service import create_user_service

logger = logging.getLogger(__name__)
User = get_user_model()

# Datos de prueba para generar nombres y datos realistas
NOMBRES_EMPRESAS = [
    "Tecnología",
    "Soluciones",
    "Servicios",
    "Consultoría",
    "Ingeniería",
    "Construcción",
    "Comercializadora",
    "Distribuidora",
    "Manufactura",
    "Logística",
]

SECTORES = [
    "Tecnología",
    "Construcción",
    "Retail",
    "Manufactura",
    "Servicios",
    "Consultoría",
    "Logística",
    "Alimentación",
    "Salud",
    "Educación",
]

NOMBRES_CLIENTES = [
    "Juan",
    "María",
    "Carlos",
    "Ana",
    "Luis",
    "Laura",
    "Pedro",
    "Carmen",
    "Roberto",
    "Patricia",
    "Fernando",
    "Sandra",
    "Miguel",
    "Diana",
    "Andrés",
]

APELLIDOS = [
    "García",
    "Rodríguez",
    "López",
    "Martínez",
    "González",
    "Pérez",
    "Sánchez",
    "Ramírez",
    "Torres",
    "Flores",
    "Rivera",
    "Gómez",
    "Díaz",
    "Cruz",
    "Morales",
]

CIUDADES = [
    "Bogotá",
    "Medellín",
    "Cali",
    "Barranquilla",
    "Cartagena",
    "Bucaramanga",
    "Pereira",
    "Santa Marta",
    "Manizales",
    "Armenia",
    "Villavicencio",
    "Pasto",
]


def generar_nombre_empresa(index: int) -> str:
    """Genera un nombre de empresa único."""
    sector = random.choice(SECTORES)
    tipo = random.choice(NOMBRES_EMPRESAS)
    return f"{sector} {tipo} {index:03d} S.A.S."


def generar_email_admin(index: int) -> str:
    """Genera un email único para admin."""
    return f"admin.tenant{index:03d}@test.local"


def poblar_datos_tenant(schema_name: str, tenant_index: int):
    """
    Pobla un tenant con datos de prueba.

    Crea:
    - Empresa (singleton)
    - Clientes (5-10)
    - Productos (10-20)
    - Cotizaciones (3-8)
    - Proyectos (2-5)
    """
    with schema_context(schema_name):
        from apps.tenant.clientes.models import Cliente
        from apps.tenant.cotizaciones.models import Cotizacion, Producto, Servicio
        from apps.tenant.empresa.models import Empresa
        from apps.tenant.proyectos.models import Proyecto

        logger.info(f"[generar_tenants_prueba] Poblando datos para tenant {schema_name}...")

        # 1. Crear Empresa (singleton)
        try:
            empresa = Empresa.objects.first()
            if not empresa:
                nit_base = f"{80000000 + tenant_index}"
                empresa = Empresa.objects.create(
                    razon_social=generar_nombre_empresa(tenant_index),
                    nit=nit_base,
                    dv=str(random.randint(0, 9)),
                    direccion=f"Calle {random.randint(1, 200)} #{random.randint(1, 100)}-{random.randint(1, 99)}",
                    telefono=f"3{random.randint(1000000, 9999999)}",
                    email_contacto=f"contacto.tenant{tenant_index:03d}@test.local",
                    ciudad=random.choice(CIUDADES),
                    regimen_tributario=random.choice(["SIMPLE", "ORDINARIO", "NO_RESP"]),
                    moneda="COP",
                )
                logger.info(f"[generar_tenants_prueba] Empresa creada: {empresa.razon_social}")
        except Exception as e:
            logger.error(f"[generar_tenants_prueba] Error creando empresa: {e}")
            return

        # 2. Crear Clientes (5-10)
        num_clientes = random.randint(5, 10)
        clientes_creados = []
        for i in range(num_clientes):
            try:
                nombre = random.choice(NOMBRES_CLIENTES)
                apellido = random.choice(APELLIDOS)
                tipo_persona = random.choice(["NATURAL", "JURIDICA"])

                if tipo_persona == "NATURAL":
                    razon_social = f"{nombre} {apellido}"
                    numero_doc = f"{random.randint(10000000, 99999999)}"
                    tipo_doc = random.choice(["CC", "CE"])
                else:
                    razon_social = f"{nombre} {apellido} S.A.S."
                    numero_doc = f"{random.randint(80000000, 99999999)}"
                    tipo_doc = "NIT"

                cliente = Cliente.objects.create(
                    empresa=empresa,
                    tipo_persona=tipo_persona,
                    tipo_documento=tipo_doc,
                    numero_documento=numero_doc,
                    razon_social=razon_social,
                    nombre_comercial=razon_social if tipo_persona == "JURIDICA" else "",
                    regimen_tributario=random.choice(["SIMPLE", "ORDINARIO", "NO_RESP"]),
                    email=f"{nombre.lower()}.{apellido.lower()}@test.local",
                    telefono=f"3{random.randint(1000000, 9999999)}",
                    direccion=f"Calle {random.randint(1, 200)} #{random.randint(1, 100)}",
                    ciudad=random.choice(CIUDADES),
                    activo=True,
                )
                clientes_creados.append(cliente)
            except Exception as e:
                logger.warning(f"[generar_tenants_prueba] Error creando cliente {i}: {e}")

        logger.info(f"[generar_tenants_prueba] Clientes creados: {len(clientes_creados)}")

        # 3. Crear Productos (10-20)
        num_productos = random.randint(10, 20)
        productos_creados = []
        for i in range(num_productos):
            try:
                producto = Producto.objects.create(
                    empresa=empresa,
                    codigo=f"PROD-{tenant_index:03d}-{i + 1:03d}",
                    nombre=f"Producto {i + 1} - Tenant {tenant_index}",
                    descripcion=f"Descripción del producto {i + 1} para análisis de comportamiento",
                    marca=random.choice(["Marca A", "Marca B", "Marca C", None]),
                    referencia=f"REF-{random.randint(1000, 9999)}"
                    if random.random() > 0.3
                    else None,
                    unidad=random.choice(["UND", "MT", "KG", "LT"]),
                    precio_venta=Decimal(random.randint(10000, 5000000)),
                    activo=True,
                )
                productos_creados.append(producto)
            except Exception as e:
                logger.warning(f"[generar_tenants_prueba] Error creando producto {i}: {e}")

        logger.info(f"[generar_tenants_prueba] Productos creados: {len(productos_creados)}")

        # 4. Crear Servicios (5-10)
        num_servicios = random.randint(5, 10)
        servicios_creados = []
        for i in range(num_servicios):
            try:
                servicio = Servicio.objects.create(
                    empresa=empresa,
                    codigo=f"SERV-{tenant_index:03d}-{i + 1:03d}",
                    nombre=f"Servicio {i + 1} - Tenant {tenant_index}",
                    descripcion=f"Descripción del servicio {i + 1}",
                    precio_venta=Decimal(random.randint(50000, 2000000)),
                )
                servicios_creados.append(servicio)
            except Exception as e:
                logger.warning(f"[generar_tenants_prueba] Error creando servicio {i}: {e}")

        logger.info(f"[generar_tenants_prueba] Servicios creados: {len(servicios_creados)}")

        # 5. Crear Cotizaciones (3-8)
        num_cotizaciones = random.randint(3, 8)
        cotizaciones_creadas = []
        for i in range(num_cotizaciones):
            try:
                if not clientes_creados:
                    continue

                cliente = random.choice(clientes_creados)
                fecha_emision = timezone.now().date() - timedelta(days=random.randint(0, 90))
                fecha_vencimiento = fecha_emision + timedelta(days=random.randint(15, 60))

                cotizacion = Cotizacion.objects.create(
                    empresa=empresa,
                    cliente=cliente,
                    numero=f"COT-{tenant_index:03d}-{i + 1:03d}",
                    modelo_tipo=random.choice(["SERVICIO", "EQUIPO", "MATERIAL", "MIXTO"]),
                    atencion_a=cliente.razon_social,
                    asunto=f"Propuesta comercial {i + 1}",
                    fecha_emision=fecha_emision,
                    fecha_vencimiento=fecha_vencimiento,
                    estado=random.choice(["BORRADOR", "ENVIADA", "ACEPTADA", "RECHAZADA"]),
                    es_aiu=random.choice([True, False]),
                    aiu_admin_porcentaje=Decimal("10.00")
                    if random.random() > 0.5
                    else Decimal("0.00"),
                    aiu_imprevistos_porcentaje=Decimal("5.00")
                    if random.random() > 0.5
                    else Decimal("0.00"),
                    aiu_utilidad_porcentaje=Decimal("15.00")
                    if random.random() > 0.5
                    else Decimal("0.00"),
                    subtotal=Decimal(random.randint(1000000, 50000000)),
                    iva_porcentaje=Decimal("19.00"),
                    iva_valor=Decimal("0.00"),  # Se calcula automáticamente
                    total_neto=Decimal("0.00"),  # Se calcula automáticamente
                )
                cotizaciones_creadas.append(cotizacion)
            except Exception as e:
                logger.warning(f"[generar_tenants_prueba] Error creando cotizacion {i}: {e}")

        logger.info(f"[generar_tenants_prueba] Cotizaciones creadas: {len(cotizaciones_creadas)}")

        # 6. Crear Proyectos (2-5)
        num_proyectos = random.randint(2, 5)
        proyectos_creados = []
        for i in range(num_proyectos):
            try:
                if not clientes_creados:
                    continue

                cliente = random.choice(clientes_creados)
                fecha_inicio = timezone.now().date() - timedelta(days=random.randint(0, 180))
                fecha_fin_prevista = fecha_inicio + timedelta(days=random.randint(30, 365))

                proyecto = Proyecto.objects.create(
                    empresa=empresa,
                    codigo=f"PROY-{tenant_index:03d}-{i + 1:03d}",
                    nombre=f"Proyecto {i + 1} - {cliente.razon_social}",
                    descripcion=f"Descripción del proyecto {i + 1} para análisis de comportamiento",
                    tipo_servicio=random.choice(
                        ["INSTALACION", "MANTENIMIENTO", "CONSULTORIA", "DESARROLLO"]
                    ),
                    fase_actual=random.choice(
                        ["BORRADOR", "INICIO", "PLANEACION", "EJECUCION", "CIERRE"]
                    ),
                    estado_tarea=random.choice(
                        ["PENDIENTE", "EN_PROCESO", "COMPLETADA", "CANCELADA"]
                    ),
                    cliente_id=cliente.id,
                    cliente_nombre=cliente.razon_social,
                    fecha_inicio=fecha_inicio,
                    fecha_fin_estimada=fecha_fin_prevista,
                    valor_contrato_proyectado=Decimal(random.randint(5000000, 100000000)),
                    porcentaje_avance=random.randint(0, 100),  # PositiveIntegerField, no Decimal
                )
                proyectos_creados.append(proyecto)
            except Exception as e:
                logger.warning(f"[generar_tenants_prueba] Error creando proyecto {i}: {e}")

        logger.info(f"[generar_tenants_prueba] Proyectos creados: {len(proyectos_creados)}")

        return {
            "empresa": empresa,
            "clientes": len(clientes_creados),
            "productos": len(productos_creados),
            "servicios": len(servicios_creados),
            "cotizaciones": len(cotizaciones_creadas),
            "proyectos": len(proyectos_creados),
        }


class Command(BaseCommand):
    help = "Genera múltiples tenants privados con datos de prueba para análisis de comportamiento"

    def add_arguments(self, parser):
        parser.add_argument(
            "--cantidad",
            type=int,
            default=100,
            help="Cantidad de tenants a crear (default: 100)",
        )
        parser.add_argument(
            "--con-datos",
            action="store_true",
            help="Poblar cada tenant con datos de prueba (empresa, clientes, cotizaciones, proyectos)",
        )
        parser.add_argument(
            "--inicio",
            type=int,
            default=1,
            help="Número inicial para indexación (default: 1)",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Omitir tenants que ya existen (por schema_name)",
        )

    def handle(self, *args, **options):
        cantidad = options["cantidad"]
        con_datos = options.get("con_datos", False)
        inicio = options.get("inicio", 1)
        skip_existing = options.get("skip_existing", False)

        self.stdout.write(self.style.SUCCESS(f"🚀 Iniciando generación de {cantidad} tenants..."))
        self.stdout.write("=" * 80)

        if con_datos:
            self.stdout.write(
                self.style.WARNING(
                    "WARNING:  Modo CON DATOS activado - Esto puede tardar varios minutos"
                )
            )

        # Estadísticas
        stats = {"creados": 0, "omitidos": 0, "errores": 0, "con_datos": 0, "sin_datos": 0}

        errores_detallados = []

        # Crear un usuario admin base si no existe
        try:
            admin_base = User.objects.filter(email="admin.base@test.local").first()
            if not admin_base:
                admin_base = create_user_service(
                    email="admin.base@test.local",
                    password="Admin123!",
                    first_name="Admin",
                    last_name="Base",
                    is_staff=True,
                    is_active=True,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"OK: Usuario admin base creado: {admin_base.email}")
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"ERROR: Error creando usuario admin base: {e}"))
            raise CommandError(f"No se pudo crear usuario admin base: {e}")

        # Generar tenants
        for i in range(inicio, inicio + cantidad):
            tenant_index = i
            nombre_empresa = generar_nombre_empresa(tenant_index)
            email_admin = generar_email_admin(tenant_index)

            self.stdout.write(
                f"\n[{tenant_index}/{inicio + cantidad - 1}] Procesando: {nombre_empresa}"
            )

            try:
                # Verificar si ya existe
                from apps.public.tenants.models import Client

                schema_name_esperado = (
                    nombre_empresa.lower()
                    .replace(" ", "-")
                    .replace(".", "")
                    .replace("sas", "")[:63]
                )

                if (
                    skip_existing
                    and Client.objects.filter(schema_name__icontains=str(tenant_index)).exists()
                ):
                    self.stdout.write(
                        self.style.WARNING(f"  ⏭️  Tenant {tenant_index} ya existe, omitiendo...")
                    )
                    stats["omitidos"] += 1
                    continue

                # Crear usuario admin para este tenant
                try:
                    admin_user = User.objects.filter(email=email_admin).first()
                    if not admin_user:
                        admin_user = create_user_service(
                            email=email_admin,
                            password="Admin123!",
                            first_name="Admin",
                            last_name=f"Tenant{tenant_index:03d}",
                            is_staff=True,
                            is_active=True,
                        )
                except Exception:
                    # Si el usuario ya existe, usarlo
                    admin_user = User.objects.get(email=email_admin)

                # Crear tenant
                client, domain, membership, login_url = crear_tenant_con_owner(
                    nombre=nombre_empresa,
                    admin_user_id=admin_user.id,
                    schema_name=None,  # Se genera automáticamente
                    on_trial=random.choice([True, False]),
                    paid_until=None,
                )

                stats["creados"] += 1
                self.stdout.write(self.style.SUCCESS(f"  OK: Tenant creado: {client.schema_name}"))

                # Poblar datos si se solicita
                if con_datos:
                    try:
                        datos = poblar_datos_tenant(client.schema_name, tenant_index)
                        stats["con_datos"] += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  📊 Datos: {datos['clientes']} clientes, "
                                f"{datos['productos']} productos, {datos['cotizaciones']} cotizaciones, "
                                f"{datos['proyectos']} proyectos"
                            )
                        )
                    except Exception as e:
                        logger.error(
                            f"[generar_tenants_prueba] Error poblando datos: {e}", exc_info=True
                        )
                        self.stdout.write(
                            self.style.WARNING(f"  WARNING:  Error poblando datos: {e}")
                        )
                        stats["sin_datos"] += 1
                else:
                    stats["sin_datos"] += 1

            except Exception as e:
                stats["errores"] += 1
                error_msg = f"Error creando tenant {tenant_index}: {e}"
                errores_detallados.append(error_msg)
                logger.error(f"[generar_tenants_prueba] {error_msg}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"  ERROR: {error_msg}"))

        # Reporte final
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 REPORTE FINAL"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"OK: Tenants creados: {stats['creados']}")
        self.stdout.write(f"⏭️  Tenants omitidos: {stats['omitidos']}")
        self.stdout.write(f"ERROR: Errores: {stats['errores']}")

        if con_datos:
            self.stdout.write(f"📊 Con datos: {stats['con_datos']}")
            self.stdout.write(f"📊 Sin datos: {stats['sin_datos']}")

        if errores_detallados:
            self.stdout.write("\nERROR: Errores detallados:")
            for error in errores_detallados[:10]:  # Mostrar solo los primeros 10
                self.stdout.write(f"  - {error}")
            if len(errores_detallados) > 10:
                self.stdout.write(f"  ... y {len(errores_detallados) - 10} errores más")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("OK: Proceso completado!"))

        # Guardar estadísticas en archivo
        import json
        import os

        from django.conf import settings

        stats_file = os.path.join(settings.BASE_DIR, "tenants_prueba_stats.json")
        with open(stats_file, "w") as f:
            json.dump(
                {
                    "fecha": timezone.now().isoformat(),
                    "cantidad_solicitada": cantidad,
                    "stats": stats,
                    "errores": errores_detallados,
                },
                f,
                indent=2,
            )

        self.stdout.write(f"\n📄 Estadísticas guardadas en: {stats_file}")
