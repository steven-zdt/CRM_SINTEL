"""
Extractor de Clientes para Dashboard — Pull Model.
Usa ClienteSelector, no importa models.py directamente.
"""
from django.utils import timezone

from apps.tenant.dashboard.services.dtos import WidgetClientesDTO


class ClientesExtractor:

    @staticmethod
    def extraer_metricas(empresa_id: int) -> WidgetClientesDTO:
        try:
            from apps.tenant.clientes.services.selectors import ClienteSelector

            qs = ClienteSelector.get_cliente_list(empresa_id)
            total_clientes = qs.count()
            clientes_activos = qs.filter(activo=True).count()
            personas_juridicas = qs.filter(tipo_persona='JURIDICA').count()
            retenedores = qs.filter(es_retenedor=True).count()

            inicio_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            nuevos_mes = qs.filter(created_at__gte=inicio_mes).count()

            return WidgetClientesDTO(
                total_clientes=total_clientes,
                clientes_activos=clientes_activos,
                nuevos_mes=nuevos_mes,
                personas_juridicas=personas_juridicas,
                retenedores=retenedores,
            )

        except Exception:
            return WidgetClientesDTO(0, 0, 0, 0, 0)
