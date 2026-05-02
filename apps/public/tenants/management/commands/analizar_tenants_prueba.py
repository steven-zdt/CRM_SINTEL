"""
Comando de management para analizar el comportamiento de tenants de prueba.

WARNING: v3.3: Análisis de comportamiento activo de tenants privados
WARNING: Uso: python manage.py analizar_tenants_prueba

Este comando:
1. Analiza todos los tenants activos
2. Genera estadísticas de uso (clientes, cotizaciones, proyectos)
3. Identifica tenants activos vs inactivos
4. Genera reporte en JSON y CSV
"""

import csv
import json
import logging
from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from apps.public.tenants.models import Client, Domain, TenantMembership

logger = logging.getLogger(__name__)
User = get_user_model()


def analizar_tenant(schema_name: str) -> dict:
    """
    Analiza un tenant y retorna estadísticas.

    Returns:
        dict con estadísticas del tenant
    """
    stats = {
        "schema_name": schema_name,
        "activo": False,
        "empresa": None,
        "clientes": 0,
        "productos": 0,
        "servicios": 0,
        "cotizaciones": 0,
        "proyectos": 0,
        "ultima_actividad": None,
        "fecha_creacion": None,
        "miembros": 0,
    }

    try:
        with schema_context(schema_name):
            from apps.tenant.clientes.models import Cliente
            from apps.tenant.cotizaciones.models import Cotizacion, Producto, Servicio
            from apps.tenant.empresa.models import Empresa
            from apps.tenant.proyectos.models import Proyecto

            # Empresa
            empresa = Empresa.objects.first()
            if empresa:
                stats["empresa"] = empresa.razon_social
                stats["fecha_creacion"] = (
                    empresa.created_at.isoformat() if hasattr(empresa, "created_at") else None
                )
                stats["activo"] = True

            # Clientes
            stats["clientes"] = Cliente.objects.filter(activo=True).count()

            # Productos y Servicios
            stats["productos"] = Producto.objects.filter(activo=True).count()
            stats["servicios"] = Servicio.objects.count()

            # Cotizaciones
            stats["cotizaciones"] = Cotizacion.objects.count()
            ultima_cotizacion = Cotizacion.objects.order_by("-created_at").first()
            if ultima_cotizacion and hasattr(ultima_cotizacion, "created_at"):
                stats["ultima_actividad"] = ultima_cotizacion.created_at.isoformat()

            # Proyectos
            stats["proyectos"] = Proyecto.objects.filter(activo=True).count()
            ultimo_proyecto = Proyecto.objects.order_by("-updated_at").first()
            if ultimo_proyecto and hasattr(ultimo_proyecto, "updated_at"):
                if not stats[
                    "ultima_actividad"
                ] or ultimo_proyecto.updated_at > datetime.fromisoformat(
                    stats["ultima_actividad"].replace("Z", "+00:00")
                ):
                    stats["ultima_actividad"] = ultimo_proyecto.updated_at.isoformat()

    except Exception as e:
        logger.error(f"[analizar_tenants_prueba] Error analizando tenant {schema_name}: {e}")
        stats["error"] = str(e)

    # Obtener información del Client (en schema public)
    try:
        client = Client.objects.get(schema_name=schema_name)
        stats["nombre"] = client.nombre
        stats["is_active"] = client.is_active
        stats["on_trial"] = client.on_trial
        stats["paid_until"] = client.paid_until.isoformat() if client.paid_until else None
        stats["created_on"] = (
            client.created_on.isoformat() if hasattr(client, "created_on") else None
        )

        # Miembros
        stats["miembros"] = TenantMembership.objects.filter(client=client, is_active=True).count()

        # Dominio
        domain = Domain.objects.filter(tenant=client, is_primary=True).first()
        if domain:
            stats["dominio"] = domain.domain
    except Client.DoesNotExist:
        stats["error"] = "Client no encontrado en schema public"
    except Exception as e:
        logger.error(f"[analizar_tenants_prueba] Error obteniendo info de Client: {e}")

    return stats


class Command(BaseCommand):
    help = "Analiza el comportamiento de tenants de prueba creados"

    def add_arguments(self, parser):
        parser.add_argument(
            "--formato",
            type=str,
            choices=["json", "csv", "ambos"],
            default="ambos",
            help="Formato de salida (default: ambos)",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default=None,
            help="Directorio para guardar reportes (default: BASE_DIR)",
        )
        parser.add_argument(
            "--solo-activos",
            action="store_true",
            help="Analizar solo tenants activos (is_active=True)",
        )
        parser.add_argument(
            "--filtro-schema",
            type=str,
            default=None,
            help="Filtrar por schema_name (contiene)",
        )

    def handle(self, *args, **options):
        formato = options["formato"]
        output_dir = options.get("output_dir")
        solo_activos = options.get("solo_activos", False)
        filtro_schema = options.get("filtro_schema")

        self.stdout.write(self.style.SUCCESS("🔍 Iniciando análisis de tenants..."))
        self.stdout.write("=" * 80)

        # Obtener todos los tenants (excluyendo public)
        public_schema = get_public_schema_name()
        queryset = Client.objects.exclude(schema_name=public_schema)

        if solo_activos:
            queryset = queryset.filter(is_active=True)

        if filtro_schema:
            queryset = queryset.filter(schema_name__icontains=filtro_schema)

        tenants = queryset.order_by("schema_name")
        total_tenants = tenants.count()

        self.stdout.write(f"📊 Analizando {total_tenants} tenants...")

        resultados = []
        errores = []

        for i, client in enumerate(tenants, 1):
            self.stdout.write(f"[{i}/{total_tenants}] Analizando: {client.schema_name}")

            try:
                stats = analizar_tenant(client.schema_name)
                resultados.append(stats)

                # Mostrar resumen
                if stats.get("activo"):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  OK: Activo: {stats['clientes']} clientes, "
                            f"{stats['cotizaciones']} cotizaciones, {stats['proyectos']} proyectos"
                        )
                    )
                else:
                    self.stdout.write(self.style.WARNING("  WARNING:  Sin datos"))

            except Exception as e:
                error_msg = f"Error analizando {client.schema_name}: {e}"
                errores.append(error_msg)
                logger.error(f"[analizar_tenants_prueba] {error_msg}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"  ERROR: {error_msg}"))

        # Calcular estadísticas agregadas
        stats_agregadas = {
            "total_tenants": total_tenants,
            "tenants_activos": sum(1 for r in resultados if r.get("activo")),
            "tenants_inactivos": sum(1 for r in resultados if not r.get("activo")),
            "total_clientes": sum(r.get("clientes", 0) for r in resultados),
            "total_productos": sum(r.get("productos", 0) for r in resultados),
            "total_servicios": sum(r.get("servicios", 0) for r in resultados),
            "total_cotizaciones": sum(r.get("cotizaciones", 0) for r in resultados),
            "total_proyectos": sum(r.get("proyectos", 0) for r in resultados),
            "total_miembros": sum(r.get("miembros", 0) for r in resultados),
            "fecha_analisis": timezone.now().isoformat(),
        }

        # Reporte en consola
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 ESTADÍSTICAS AGREGADAS"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total tenants: {stats_agregadas['total_tenants']}")
        self.stdout.write(f"Tenants activos: {stats_agregadas['tenants_activos']}")
        self.stdout.write(f"Tenants inactivos: {stats_agregadas['tenants_inactivos']}")
        self.stdout.write(f"Total clientes: {stats_agregadas['total_clientes']}")
        self.stdout.write(f"Total productos: {stats_agregadas['total_productos']}")
        self.stdout.write(f"Total servicios: {stats_agregadas['total_servicios']}")
        self.stdout.write(f"Total cotizaciones: {stats_agregadas['total_cotizaciones']}")
        self.stdout.write(f"Total proyectos: {stats_agregadas['total_proyectos']}")
        self.stdout.write(f"Total miembros: {stats_agregadas['total_miembros']}")

        if errores:
            self.stdout.write(f"\nERROR: Errores: {len(errores)}")

        # Guardar reportes
        import os

        from django.conf import settings

        if not output_dir:
            output_dir = settings.BASE_DIR

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if formato in ["json", "ambos"]:
            json_file = os.path.join(output_dir, f"analisis_tenants_{timestamp}.json")
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "estadisticas_agregadas": stats_agregadas,
                        "resultados": resultados,
                        "errores": errores,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            self.stdout.write(f"\n📄 Reporte JSON guardado en: {json_file}")

        if formato in ["csv", "ambos"]:
            csv_file = os.path.join(output_dir, f"analisis_tenants_{timestamp}.csv")
            if resultados:
                fieldnames = [
                    "schema_name",
                    "nombre",
                    "dominio",
                    "activo",
                    "is_active",
                    "on_trial",
                    "empresa",
                    "clientes",
                    "productos",
                    "servicios",
                    "cotizaciones",
                    "proyectos",
                    "miembros",
                    "fecha_creacion",
                    "ultima_actividad",
                    "paid_until",
                ]

                with open(csv_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for r in resultados:
                        row = {k: r.get(k, "") for k in fieldnames}
                        writer.writerow(row)

                self.stdout.write(f"📄 Reporte CSV guardado en: {csv_file}")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("OK: Análisis completado!"))
