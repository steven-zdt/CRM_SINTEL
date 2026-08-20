"""
API Mixins para Proyectos v3.5 - Inyeccion de servicios en ViewSets (v3.10.1).

SINTEL v3.10.1: Arquitectura Service Layer Modular.
- Hereda de BaseServiceMixin (canonical, consolidado)
- Mantiene solo metodos service_* especificos de Proyectos

Nota: la clase `ProyectoServiceMixin` que existia antes en este archivo
fue eliminada -- `ProyectoViewSet` usa el mixin propio de
`api/mixins.py` (patron mas simple, basado en properties sobre el
modulo `services`), no este. La version de aqui (heredaba de
BaseServiceMixin, con docstring "Service mixin para Gasto ViewSet" --
copy-paste de otra app) nunca tuvo consumidores reales, confirmado con
grep repo-wide.
"""
from apps.tenant.api.mixins import BaseServiceMixin
from apps.tenant.proyectos.services.selectors import TareaCortaSelector
from apps.tenant.proyectos.services.business_service import (
    TareasCortasBusinessService,
)


class TareaCortaServiceMixin(BaseServiceMixin):
    """
    Service mixin para TareaCorta ViewSet.
    """

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        empleado_uuid = self.request.query_params.get('empleado_uuid')
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_fin = self.request.query_params.get('fecha_fin')
        return TareaCortaSelector.qs_por_empleado(
            empresa_id=empresa_id,
            empleado_uuid=empleado_uuid,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )

    def get_qs_detail(self):
        """Retorna instancia de detalle usando selector."""
        empresa_id = self.get_empresa_id()
        uuid = self.kwargs.get('uuid')
        return TareaCortaSelector.get_tarea_corta(empresa_id, uuid)

    def service_crear_tarea_corta(self, data):
        """Crea tarea corta usando business service."""
        empresa = self._get_empresa()
        empleado = data.pop('empleado', None)
        return TareasCortasBusinessService.crear_tarea_corta(
            empresa=empresa,
            empleado=empleado,
            **data
        )

    def service_actualizar_tarea_corta(self, tarea_corta, data):
        """Actualiza tarea corta usando business service."""
        return TareasCortasBusinessService.actualizar_tarea_corta(tarea_corta, data)

    def service_eliminar_tarea_corta(self, tarea_corta):
        """Elimina tarea corta usando business service."""
        return TareasCortasBusinessService.eliminar_tarea_corta(tarea_corta)
