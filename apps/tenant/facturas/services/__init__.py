from .business_service import FacturaBusinessService
from .crud_service import FacturaCRUDService
from .selectors import FacturaSelectors

# SSoT Constants for Serializers/API
from .selectors import LIST_FIELDS, DETAIL_FIELDS

# Compatibility exports (Proxying to new modular services)
from .business_service import FacturaService
from .api_mixins import FacturaServiceMixin

# Exporting new SSoT Constants from Selectors for Serializers/API
from .selectors import LIST_FIELDS, DETAIL_FIELDS
