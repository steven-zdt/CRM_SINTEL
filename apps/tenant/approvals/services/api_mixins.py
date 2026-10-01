from apps.tenant.api.mixins import BaseServiceMixin
from apps.tenant.approvals.services.business_service import ApprovalBusinessService
from apps.tenant.approvals.services.selectors import SolicitudAprobacionSelector
from apps.tenant.approvals.services.trace_service import ApprovalTraceService


class SolicitudAprobacionServiceMixin(BaseServiceMixin):
    """Mixin para inyectar logica de negocio y acceso a datos de
    SolicitudAprobacion en el ViewSet (mismo patron que
    RequisicionCompraServiceMixin)."""

    selector_class = SolicitudAprobacionSelector
    business_service_class = ApprovalBusinessService

    def get_qs_list(self):
        empresa_id = self._get_empresa_id_seguro()
        estado = self.request.query_params.get("estado") if hasattr(self, "request") else None
        tipo_documento = (
            self.request.query_params.get("tipo_documento") if hasattr(self, "request") else None
        )
        return self.selector_class.get_list(
            empresa_id, estado=estado, tipo_documento=tipo_documento
        )

    def get_qs_detail(self, solicitud_uuid: str):
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_detail(empresa_id, solicitud_uuid)

    def service_aprobar(self, solicitud_uuid: str, observacion: str = ""):
        empresa_id = self._get_empresa_id_seguro()
        usuario = getattr(self.request.user, "tenant_profile", None)
        return self.business_service_class.aprobar(solicitud_uuid, empresa_id, usuario, observacion)

    def service_rechazar(self, solicitud_uuid: str, motivo: str):
        empresa_id = self._get_empresa_id_seguro()
        usuario = getattr(self.request.user, "tenant_profile", None)
        return self.business_service_class.rechazar(solicitud_uuid, empresa_id, usuario, motivo)

    def service_trazabilidad(self, solicitud):
        empresa_id = self._get_empresa_id_seguro()
        return ApprovalTraceService.construir_trazabilidad(solicitud, empresa_id)
