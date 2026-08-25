"""
Document Intake Service -- contratos transversales para recepcion de
documentos desde multiples canales (MAIL, UPLOAD, API, IMPORT).

WARNING: PRINCIPIO CENTRAL: este paquete NO conoce Factura/Venta/Compra/
Cliente/Proveedor/Inventario/Banco/Contabilidad/Nomina. Solo conoce
mensaje/adjunto/archivo/tipo documental/origen/contexto tenant. Las apps de
dominio (facturas, compras, ...) registran sus propios DocumentHandler en el
`dispatcher` compartido -- ver apps/tenant/facturas/document_intake/.

No duplica el parser UBL ni el pipeline de mail existentes: reutiliza
apps.services.document_ingest (deteccion/normalizacion) y
apps.services.maildigester (canal MAIL) tal como estan.
"""
from apps.services.document_intake.contracts import (
    DocumentHandler,
    DocumentSource,
    ProcessingResult,
    ProcessingStatus,
    ReceivedDocument,
)
from apps.services.document_intake.dispatcher import DocumentDispatcher, dispatcher

__all__ = [
    "DocumentDispatcher",
    "DocumentHandler",
    "DocumentSource",
    "ProcessingResult",
    "ProcessingStatus",
    "ReceivedDocument",
    "dispatcher",
]
