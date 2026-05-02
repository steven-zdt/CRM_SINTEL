# Suite de Pruebas: Impuestos (Fases A-D)

Suite de pruebas end-to-end para el módulo de impuestos, cubriendo todas las fases de la arquitectura:

- **Fase A**: Ingesta (scraping/upload)
- **Fase B**: ETL (normalización)
- **Fase C**: Exposición (API ReadOnly + Búsqueda OpenSearch)
- **Fase D**: Operación (salud, blue/green, comandos)

## Estructura

```
tests/public/impuestos/
├── conftest.py              # Fixtures base (Django, Celery eager, OpenSearch fake)
├── factories.py             # Factories para modelos (factory_boy)
├── test_ingesta_api.py      # Fase A: Ingesta
├── test_etl_pipeline.py     # Fase B: ETL
├── test_api_readonly.py     # Fase C: Catálogos ReadOnly
├── test_search_api.py       # Fase C: Búsqueda OpenSearch
└── test_ops_health.py       # Fase D: Operación y salud
```

## Configuración

### Dependencias

```bash
pip install pytest pytest-django factory-boy responses
```

O usar `requirements.txt` (incluye las dependencias de testing).

### Configuración pytest

Crear `pytest.ini` en la raíz del proyecto:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --tb=short --strict-markers
```

### Migraciones

Asegurar migraciones en esquema `public`:

```bash
python manage.py migrate_schemas --shared
```

## Ejecución

### Todos los tests

```bash
pytest tests/public/impuestos/ -v
```

### Por fase

```bash
# Fase A: Ingesta
pytest tests/public/impuestos/test_ingesta_api.py -v

# Fase B: ETL
pytest tests/public/impuestos/test_etl_pipeline.py -v

# Fase C: API + Búsqueda
pytest tests/public/impuestos/test_api_readonly.py -v
pytest tests/public/impuestos/test_search_api.py -v

# Fase D: Operación
pytest tests/public/impuestos/test_ops_health.py -v
```

### Con Makefile

```bash
make test              # Todos los tests
make test-ingesta      # Solo ingesta
make test-etl          # Solo ETL
make test-api          # Solo API ReadOnly
make test-search       # Solo búsqueda
make test-ops          # Solo operación
```

## Fixtures

### Celery Eager

Las tareas Celery se ejecutan síncronamente (sin worker) para pruebas deterministas.

```python
@pytest.fixture(autouse=True)
def celery_eager():
    with override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield
```

### OpenSearch Fake

Cliente fake de OpenSearch para tests sin cluster real.

```python
def test_search(patch_opensearch, api_client):
    # Agregar documentos al fake
    patch_opensearch._docs.append({"_source": {...}})
    # Test...
```

## Cobertura

### Fase A: Ingesta

- ✅ POST multipart con archivo (CSV/HTML/PDF)
- ✅ POST JSON con `url_origen`
- ✅ Transición de estados: RECIBIDO → EN_PROCESO → PROCESADO/ERROR
- ✅ Throttling scope `impuestos_ingesta` → 429
- ✅ Idempotencia por `hash_sha256`

### Fase B: ETL

- ✅ Pipeline completo: parse → tokenize → normalize → validate → upsert
- ✅ Atomicidad: `transaction.atomic()` previene catálogos a medio poblar
- ✅ Manejo de errores: rollback ante validaciones fallidas

### Fase C: Exposición

**API ReadOnly:**
- ✅ Listado de catálogos (AllowAny, sin autenticación)
- ✅ Filtrado, búsqueda, ordenación
- ✅ Paginación estándar
- ✅ Métodos POST/PUT/DELETE retornan 405

**Búsqueda:**
- ✅ GET `/search/` con query → resultados con highlight
- ✅ Uso del alias `impuestos-docs` (blue/green)
- ✅ Throttling scope `impuestos_search` → 429

### Fase D: Operación

- ✅ GET `/search/health/` solo accesible por admin
- ✅ Comando `impuestos_reindex` (blue/green)
- ✅ Comando `impuestos_seed` (re-indexación)
- ✅ Comando `impuestos_smoke` (smoke test)
- ✅ Comando `impuestos_export_json` (backup)

## Notas

- **Celery eager**: Las tareas se ejecutan síncronamente; útil para tests deterministas.
- **OpenSearch fake**: Permite probar `/search` sin cluster real; cuando haya cluster, no usar `patch_opensearch`.
- **Tenancy**: Tests corren sobre esquema `public` con `migrate_schemas --shared` previo.

## Referencias

- [DRF Throttling](https://www.django-rest-framework.org/api-guide/throttling/)
- [OpenSearch Python Client](https://opensearch.org/docs/latest/clients/python/index/)
- [Celery Testing](https://docs.celeryproject.org/en/stable/userguide/testing.html)
- [Django Atomic Transactions](https://docs.djangoproject.com/en/stable/topics/db/transactions/)
