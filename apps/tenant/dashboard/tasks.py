"""
Celery tasks para Dashboard v3.9.4
Snapshots históricos + invalidación de caché
"""
from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime

import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def crear_snapshot_metricas_diarias(self):
    """
    Celery Beat task: Crear snapshot de métricas diarias (2 AM nightly).
    Corre cada noche a las 2 AM para guardar historial de métricas.

    Cron: 0 2 * * * (cada día a las 2:00 AM)
    """
    try:
        from apps.tenant.empresa.models import Empresa
        from apps.tenant.dashboard.models import SnapshotMetricaDiaria
        from apps.tenant.dashboard.services.business_service import DashboardBusinessService

        logger.info("📊 [Dashboard] Iniciando creación de snapshots diarios...")

        hoy = timezone.now().date()
        empresas_procesadas = 0
        empresas_error = 0

        # Iterar sobre todas las empresas
        for empresa in Empresa.objects.all():
            try:
                # Obtener métricas consolidadas
                metricas = DashboardBusinessService.obtener_metricas_consolidadas(empresa.id)

                # Crear snapshot en DB
                snapshot = SnapshotMetricaDiaria.objects.create(
                    empresa=empresa,
                    fecha=hoy,
                    total_facturas=metricas.facturas.total_facturas,
                    facturas_pendientes=metricas.facturas.facturas_pendientes,
                    facturas_vencidas=metricas.facturas.facturas_vencidas,
                    ingresos_mes=metricas.facturas.ingresos_mes,
                    total_productos=metricas.inventario.total_productos,
                    productos_bajo_stock=metricas.inventario.productos_bajo_stock,
                    valor_inventario=metricas.inventario.valor_inventario,
                    total_empleados=metricas.empleados.total_empleados,
                    empleados_activos=metricas.empleados.empleados_activos,
                    nominas_pendientes=metricas.empleados.nominas_pendientes,
                    generado_por='celery-beat'
                )

                empresas_procesadas += 1
                logger.debug(f"✅ Snapshot creado para empresa {empresa.id} ({empresa.nombre})")

            except Exception as e:
                empresas_error += 1
                logger.warning(
                    f"⚠️ Error creando snapshot para empresa {empresa.id}: {str(e)}",
                    exc_info=True
                )
                # Continuar con siguiente empresa en lugar de fallar todo

        logger.info(
            f"📊 [Dashboard] Snapshots completados: {empresas_procesadas} OK, {empresas_error} errores"
        )

        return {
            'status': 'success',
            'empresas_procesadas': empresas_procesadas,
            'empresas_error': empresas_error,
            'fecha': hoy.isoformat()
        }

    except Exception as e:
        logger.error(
            f"❌ [Dashboard] Error crítico en crear_snapshot_metricas_diarias: {str(e)}",
            exc_info=True
        )
        # Reintentar hasta 3 veces
        raise self.retry(exc=e, countdown=300)  # Reintentar en 5 minutos


@shared_task(bind=True)
def limpiar_snapshots_antiguos(self, dias=90):
    """
    Celery Beat task: Limpiar snapshots más antiguos que N días.
    Por defecto: mantener 90 días de historia (≈3 meses).

    Cron: 0 3 1 * * (1er día del mes a las 3:00 AM)
    """
    try:
        from apps.tenant.dashboard.models import SnapshotMetricaDiaria
        from datetime import timedelta

        logger.info(f"🗑️ [Dashboard] Limpiando snapshots más antiguos que {dias} días...")

        fecha_corte = timezone.now().date() - timedelta(days=dias)

        # Eliminar snapshots antiguos
        resultado = SnapshotMetricaDiaria.objects.filter(
            fecha__lt=fecha_corte
        ).delete()

        registros_eliminados = resultado[0]  # Count de registros eliminados

        logger.info(f"🗑️ [Dashboard] Snapshots eliminados: {registros_eliminados}")

        return {
            'status': 'success',
            'registros_eliminados': registros_eliminados,
            'fecha_corte': fecha_corte.isoformat()
        }

    except Exception as e:
        logger.error(
            f"❌ [Dashboard] Error limpiando snapshots: {str(e)}",
            exc_info=True
        )
        raise


@shared_task(bind=True)
def invalidar_cache_todas_empresas(self):
    """
    Celery task: Invalida caché para todas las empresas.
    Útil después de operaciones masivas (import, sincronización, etc).

    Puede ejecutarse manualmente o vía API con permisos admin.
    """
    try:
        from apps.tenant.empresa.models import Empresa

        logger.info("🔄 [Dashboard] Invalidando caché para todas las empresas...")

        empresas = Empresa.objects.all().values_list('id', flat=True)
        invalidadas = 0

        for empresa_id in empresas:
            from apps.tenant.dashboard.services.business_service import DashboardBusinessService
            DashboardBusinessService.invalidar_cache(empresa_id)
            invalidadas += 1

        logger.info(f"🔄 [Dashboard] Caché invalidado para {invalidadas} empresas")

        return {
            'status': 'success',
            'empresas_invalidadas': invalidadas
        }

    except Exception as e:
        logger.error(
            f"❌ [Dashboard] Error invalidando caché: {str(e)}",
            exc_info=True
        )
        raise
