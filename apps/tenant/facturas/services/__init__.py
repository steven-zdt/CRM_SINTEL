from .business_service import FacturaBusinessService, FacturaInterAppAPI
from .crud_service import FacturaCRUDService
from .selectors import FacturaSelectors

# SSoT Constants for Serializers/API
from .selectors import LIST_FIELDS, DETAIL_FIELDS

# Compatibility exports (Proxying to new modular services)
from .business_service import FacturaService
from .api_mixins import FacturaServiceMixin

# [v3.10.0] Inter-App API — acceso sin restriccion empresa_id para apps de negocio
# Uso: from apps.tenant.facturas.services import FacturaInterAppAPI
# API abierto para lectura — ver clase en business_service.py §FacturaInterAppAPI
