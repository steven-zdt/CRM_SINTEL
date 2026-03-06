"""
Indexador bulk para OpenSearch.

Proporciona funciones para indexación eficiente de normas tributarias.
"""
from opensearchpy.helpers import bulk
from apps.public.impuestos.search.client import get_search_client
from apps.public.impuestos.search.schema import INDEX_ALIAS
from apps.public.impuestos.models import NormaTributaria


def gen_docs_from_normas(qs):
    """
    Genera documentos para indexación desde un QuerySet de NormaTributaria.
    
    Args:
        qs: QuerySet de NormaTributaria
    
    Yields:
        dict: Documento formateado para bulk index
    """
    for n in qs.iterator():
        # Generar título desde artículo o tema
        titulo = f"Artículo {n.articulo}" if n.articulo else (n.tema or "Sin título")
        
        yield {
            "_op_type": "index",
            "_index": INDEX_ALIAS,  # Escribir siempre contra el alias actual
            "_id": f"norma-{n.id}",
            "_source": {
                "titulo": titulo,
                "tipo_fuente": "norma",
                "articulo": n.articulo or "",
                "impuesto": n.impuesto or "",
                "tema": n.tema or "",
                "vigencia_desde": n.vigencia_desde.isoformat() if n.vigencia_desde else None,
                "vigencia_hasta": n.vigencia_hasta.isoformat() if n.vigencia_hasta else None,
                "texto": n.texto_plano or "",
                "norma_id": str(n.id),
                "referencias": n.referencias or [],
            },
        }


def bulk_index_normas(qs=None):
    """
    Indexa todas las normas tributarias en OpenSearch usando bulk.
    
    Args:
        qs: QuerySet opcional (default: todas las normas)
    
    Returns:
        dict: Estadísticas de indexación {"ok": int, "fail": int}
    """
    client = get_search_client()
    
    if qs is None:
        qs = NormaTributaria.objects.all()
    
    success_count, failed_items = bulk(client, gen_docs_from_normas(qs))
    
    return {
        "ok": success_count,
        "fail": len(failed_items) if failed_items else 0,
        "failed_items": failed_items,
    }