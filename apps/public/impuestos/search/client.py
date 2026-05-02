"""
Cliente OpenSearch para la biblioteca tributaria.

Configuración del cliente Python oficial (opensearch-py).
Referencia: https://opensearch.org/docs/latest/clients/python/
"""

import os

from opensearchpy import OpenSearch


def get_search_client():
    """
    Obtiene un cliente OpenSearch configurado.

    Variables de entorno:
    - OPENSEARCH_HOST: Host de OpenSearch (default: localhost)
    - OPENSEARCH_PORT: Puerto de OpenSearch (default: 9200)
    - OPENSEARCH_USER: Usuario (default: admin)
    - OPENSEARCH_PASS: Contraseña (default: admin)

    Returns:
        OpenSearch: Cliente OpenSearch configurado
    """
    host = os.getenv("OPENSEARCH_HOST", "localhost")
    port = int(os.getenv("OPENSEARCH_PORT", "9200"))
    user = os.getenv("OPENSEARCH_USER", "admin")
    pwd = os.getenv("OPENSEARCH_PASS", "admin")

    # Para clusters seguros usa SSL y certs según tu despliegue
    # En desarrollo, use_ssl=False y verify_certs=False
    # En producción, configura SSL correctamente
    client = OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=(user, pwd),
        use_ssl=os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true",
        verify_certs=os.getenv("OPENSEARCH_VERIFY_CERTS", "false").lower() == "true",
        ssl_show_warn=False,
    )

    return client
