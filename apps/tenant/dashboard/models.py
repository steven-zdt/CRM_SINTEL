"""
Modelos para Dashboard v3.9.4 — Snapshots de métricas.
Opcional: para histórico de métricas calculadas por Celery Beat.
"""
from decimal import Decimal

from django.db import models

from apps.tenant.core.models import SintelTenantBaseModel


class SnapshotMetricaDiaria(SintelTenantBaseModel):
    """
    Snapshot diario de métricas consolidadas.
    Generado por Celery Beat cada noche para histórico/analytics.
    """

    fecha = models.DateField(auto_now=False, db_index=True)

    # Facturas
    total_facturas = models.IntegerField(default=0)
    facturas_pendientes = models.IntegerField(default=0)
    facturas_vencidas = models.IntegerField(default=0)
    ingresos_mes = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00')
    )

    # Inventario
    total_productos = models.IntegerField(default=0)
    productos_bajo_stock = models.IntegerField(default=0)
    valor_inventario = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00')
    )

    # Empleados
    total_empleados = models.IntegerField(default=0)
    empleados_activos = models.IntegerField(default=0)
    nominas_pendientes = models.IntegerField(default=0)

    # Metadata
    generado_por = models.CharField(
        max_length=50, default='celery-beat', help_text='Origen del snapshot'
    )

    class Meta:
        db_table = 'dashboard_snapshot_metrica_diaria'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['empresa_id', 'fecha']),
        ]
        verbose_name = 'Snapshot de Métrica Diaria'
        verbose_name_plural = 'Snapshots de Métricas Diarias'

    def __str__(self):
        return f"{self.empresa_id} - {self.fecha}"
