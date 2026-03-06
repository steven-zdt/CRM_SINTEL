"""
Schema de índices versionados con alias para OpenSearch.

Define el alias y los mappings con analyzers personalizados para búsqueda
en español con sinónimos tributarios.
"""
INDEX_ALIAS = "impuestos-docs"


def index_name(version: int) -> str:
    """
    Genera el nombre de un índice versionado.
    
    Args:
        version: Número de versión (ej: 1, 2, 3)
    
    Returns:
        str: Nombre del índice (ej: "impuestos-docs-v1")
    """
    return f"impuestos-docs-v{version}"


MAPPINGS = {
    "settings": {
        "analysis": {
            "filter": {
                "spanish_stop": {
                    "type": "stop",
                    "stopwords": "_spanish_",
                },
                "spanish_stemmer": {
                    "type": "stemmer",
                    "language": "light_spanish",
                },
                "syns_tributarios": {
                    "type": "synonym",
                    "synonyms": [
                        "iva, impuesto al valor agregado",
                        "retefuente, retención en la fuente",
                        "dian, autoridad tributaria",
                        "ica, impuesto de industria y comercio",
                    ],
                },
                "ngram_3_20": {
                    "type": "ngram",
                    "min_gram": 3,
                    "max_gram": 20,
                },
            },
            "analyzer": {
                "txt_tributario": {
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "asciifolding",
                        "spanish_stop",
                        "spanish_stemmer",
                        "syns_tributarios",
                    ],
                },
                "titulo_autocomplete": {
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding", "ngram_3_20"],
                },
            },
        },
    },
    "mappings": {
        "properties": {
            "titulo": {
                "type": "text",
                "analyzer": "titulo_autocomplete",
                "search_analyzer": "txt_tributario",
            },
            "tipo_fuente": {"type": "keyword"},
            "articulo": {
                "type": "text",
                "analyzer": "txt_tributario",
            },
            "impuesto": {
                "type": "text",
                "analyzer": "txt_tributario",
            },
            "tema": {
                "type": "text",
                "analyzer": "txt_tributario",
            },
            "vigencia_desde": {"type": "date"},
            "vigencia_hasta": {"type": "date"},
            "texto": {
                "type": "text",
                "analyzer": "txt_tributario",
            },
            "norma_id": {"type": "keyword"},
            "referencias": {"type": "keyword"},
        },
    },
}