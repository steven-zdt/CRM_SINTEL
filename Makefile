.PHONY: up down down-full shell logs makemigrations makemigrations-accounts migrate-shared migrate-tenants migrate-shared-init migrate-tenants-init check-migrations fix-migrations superuser setup poblar-dian crear-empresa backup-tenant backup-all restore-tenant api-check api-schema test test-ingesta test-etl test-api test-search test-ops audit ruff bandit dj-check static-check pip-audit

up:
	docker compose up --build -d

down:
	docker compose down

# DEVOPS-A5: "make down" ya no borra el volumen de Postgres (antes ejecutaba
# "docker compose down -v" sin advertencia — un desarrollador que solo queria
# detener servicios borraba su base de datos local). Usar down-full para el
# reset completo, con confirmacion explicita.
down-full:
	@echo "⚠️  Esto borrara el volumen de Postgres (todos los datos locales)."
	@read -p "Escriba 'si' para confirmar: " confirm; \
	if [ "$$confirm" = "si" ]; then \
		docker compose down -v; \
	else \
		echo "Cancelado."; \
	fi

shell:
	docker compose exec web bash

logs:
	docker compose logs -f web

makemigrations:
	docker compose exec web python manage.py makemigrations

makemigrations-accounts:
	docker compose exec web python manage.py makemigrations accounts

# [PERF-M5] --fake-initial ya no es el default: enmascaraba drift real de esquema
# marcando la migracion inicial como aplicada si las tablas ya coincidian, en vez
# de dejar que una migracion realmente pendiente falle de forma visible. Se
# preserva como los targets -init explicitos de abajo, para el caso legitimo de
# adoptar un esquema cuyas tablas ya existen fuera del historial de Django.
migrate-shared:
	docker compose exec web python manage.py migrate_schemas --shared

migrate-tenants:
	docker compose exec web python manage.py migrate_schemas --tenant

# Uso excepcional: bootstrap/adopcion de un esquema cuyas tablas ya existen
# (coinciden con la migracion inicial) sin historial de migraciones de Django.
migrate-shared-init:
	docker compose exec web python manage.py migrate_schemas --shared --fake-initial

migrate-tenants-init:
	docker compose exec web python manage.py migrate_schemas --tenant --fake-initial

check-migrations:
	docker compose exec web python manage.py check_migrations

fix-migrations:
	docker compose exec web python manage.py fix_migration_history --fake-accounts

reset-migrations:
	@echo "⚠️  RESETEANDO HISTORIAL DE MIGRACIONES..."
	docker compose exec web python manage.py fix_migration_history --reset
	docker compose exec web python manage.py migrate_schemas --shared --fake-initial
	@echo "✅ Historial de migraciones reseteado y reconstruido"

setup:
	docker compose exec web python manage.py setup_public_tenant

poblar-dian:
	docker compose exec web python manage.py poblar_catalogo_dian

superuser:
	docker compose exec web python manage.py createsuperuser

crear-empresa:
	@echo "Uso: make crear-empresa NOMBRE=\"Nombre Empresa\" DOMINIO=\"dominio.localhost\" EMAIL=\"admin@email.com\""
	@echo "Ejemplo: make crear-empresa NOMBRE=\"Mi Empresa S.A.\" DOMINIO=\"mi-empresa.localhost\" EMAIL=\"admin@mi-empresa.com\""
	docker compose exec web python manage.py crear_empresa "$(NOMBRE)" "$(DOMINIO)" "$(EMAIL)"

backup-tenant:
	@echo "Uso: make backup-tenant SCHEMA=\"schema_name\""
	@echo "Ejemplo: make backup-tenant SCHEMA=\"mi_empresa\""
	docker compose exec web python manage.py backup_tenant "$(SCHEMA)"

backup-all:
	docker compose exec web python manage.py backup_all_tenants

restore-tenant:
	@echo "Uso: make restore-tenant FILE=\"ruta/al/backup.dump\""
	@echo "Ejemplo: make restore-tenant FILE=\"backups/mi_empresa_20240101_120000.dump\""
	docker compose exec web python manage.py restore_tenant "$(FILE)"

api-check:
	@echo "🔍 Validando esquema OpenAPI..."
	docker compose exec web python manage.py spectacular --file openapi.yaml --validate

api-schema:
	@echo "📝 Generando esquema OpenAPI..."
	docker compose exec web python manage.py spectacular --file openapi.yaml

api-validate:
	@echo "✅ Validando esquema OpenAPI..."
	docker compose exec web python manage.py spectacular --file /tmp/openapi.yaml --validate

docker-lint:
	@echo "🔍 Linting Dockerfile con Hadolint..."
	@if command -v hadolint > /dev/null; then \
		hadolint Dockerfile; \
	else \
		echo "⚠️  Hadolint no está instalado. Instalar con: brew install hadolint"; \
		echo "   O usar contenedor: docker run --rm -i hadolint/hadolint < Dockerfile"; \
	fi

docker-test:
	@echo "🧪 Ejecutando tests de Docker..."
	python -m pytest tests/docker/test_docker.py -v

docker-cst:
	@echo "🏗️  Ejecutando Container Structure Tests..."
	@if command -v container-structure-test > /dev/null; then \
		docker compose build web; \
		container-structure-test test --image sintel_web:local --config tests/docker/container-structure-test.yaml; \
	else \
		echo "⚠️  container-structure-test no está instalado."; \
		echo "   Instalar desde: https://github.com/GoogleContainerTools/container-structure-test"; \
	fi

# Tests con pytest
test:
	@echo "🧪 Ejecutando todos los tests (pytest)..."
	docker compose exec web pytest

test-file:
	@echo "🧪 Ejecutando tests en archivo: $(FILE)"
	docker compose exec web pytest --maxfail=1 -q $(FILE)

test-ingesta:
	@echo "🧪 Ejecutando tests de ingesta (Fase A)..."
	docker compose exec web pytest tests/public/impuestos/test_ingesta_api.py -v

test-etl:
	@echo "🧪 Ejecutando tests de ETL (Fase B)..."
	docker compose exec web pytest tests/public/impuestos/test_etl_pipeline.py -v

test-api:
	@echo "🧪 Ejecutando tests de API ReadOnly (Fase C)..."
	docker compose exec web pytest tests/public/impuestos/test_api_readonly.py -v

test-search:
	@echo "🧪 Ejecutando tests de búsqueda (Fase C)..."
	docker compose exec web pytest tests/public/impuestos/test_search_api.py -v

test-ops:
	@echo "🧪 Ejecutando tests de operación (Fase D)..."
	docker compose exec web pytest tests/public/impuestos/test_ops_health.py -v

# Auditoría y refactor seguro
audit: ruff bandit pip-audit dj-check static-check audit-scripts
	@echo "✅ Auditoría completa finalizada"

audit-scripts:
	@echo "🔍 Ejecutando scripts de auditoría..."
	@docker compose exec web python scripts/audit_empresa_duplication.py || true
	@docker compose exec web python scripts/audit_no_duplication.py || true
	@docker compose exec web python scripts/audit_templates_and_branding.py || true
	@docker compose exec web python scripts/audit_tenant_ui_compliance.py || true
	@docker compose exec web python scripts/audit_xml_pipeline_duplication.py || true

ruff:
	@echo "🔍 Ejecutando Ruff (linter/formatter)..."
	docker compose exec web python -m ruff check apps config --fix || true
	docker compose exec web python -m ruff format apps config || true

bandit:
	@echo "🔒 Ejecutando Bandit (seguridad)..."
	docker compose exec web python -m bandit -q -r apps -x "*/migrations/*" || true

# DEVOPS-A4: escaneo de dependencias vulnerables (CVEs conocidos en requirements.txt).
# Mismo patron `|| true` que ruff/bandit hasta triar el backlog inicial de
# hallazgos preexistentes (ver PLAN_UNICO_CORRECCIONES.md Fase 8).
pip-audit:
	@echo "🔍 Ejecutando pip-audit (dependencias vulnerables)..."
	docker compose exec web python -m pip_audit -r requirements.txt || true

dj-check:
	@echo "🔧 Ejecutando Django System Check..."
	docker compose exec web python manage.py check --deploy

static-check:
	@echo "📦 Verificando archivos estáticos..."
	docker compose exec web python manage.py collectstatic --dry-run --noinput || true

# ⚠️ FASE 5: Observabilidad y Smoke Tests
.PHONY: smoke-facturas
smoke-facturas:
	@BASE_URL="$(BASE_URL)" XML_FILE="$(XML_FILE)" bash tools/smoke_facturas.sh

.PHONY: smoke-xml-pipeline
smoke-xml-pipeline:
	@echo "🧪 Ejecutando smoke tests del pipeline XML canónico..."
	@docker compose exec web python manage.py test apps/tenant/facturas/tests/test_xml_pipeline_canonical.py --keepdb

.PHONY: smoke
smoke:
	@echo "🧪 Ejecutando suite completa de smoke tests..."
	@$(MAKE) audit-scripts
	@$(MAKE) smoke-xml-pipeline
	@$(MAKE) test-api

.PHONY: health
health:
	@curl -sS --fail-with-body "$(BASE_URL)/api/v1/core/health/" | jq .

# ── Enterprise Knowledge Graph (EKG) — tools/ekg/ ───────────────────────────
# Rollout completo: 17/17 apps tenant. Ver tools/ekg/PILOT_REPORT.md para alcance y limitaciones conocidas.
.PHONY: ekg-build
ekg-build:
	@echo "🕸️  Construyendo y cargando el Knowledge Graph para APP=$(APP)..."
	@docker compose exec web python -m tools.ekg.build_graph --app $(APP)

.PHONY: ekg-dry-run
ekg-dry-run:
	@echo "🕸️  Extrayendo el grafo para APP=$(APP) sin cargar a Neo4j (dry-run)..."
	@docker compose exec web python -m tools.ekg.build_graph --app $(APP) --dry-run --output tools/ekg/out/$(APP).json

.PHONY: ekg-validate
ekg-validate:
	@echo "🔎 Validando integridad del grafo (nodos huerfanos, referencias rotas)..."
	@docker compose exec web python -m tools.ekg.validate --app $(APP)

.PHONY: ekg-ask
ekg-ask:
	@docker compose exec web python -m tools.ekg.queries --live "$(Q)"

.PHONY: ekg-impact
ekg-impact:
	@echo "💥 Motor de impacto: que depende de NAME=$(NAME)? (offline, todas las apps fusionadas)"
	@docker compose exec web python -m tools.ekg.impact --offline --name "$(NAME)"

.PHONY: ekg-governance
ekg-governance:
	@echo "🏛️  Barrido de gobernanza (Fase 7): reglas de arquitectura verificables sobre el grafo completo"
	@docker compose exec web python -m tools.ekg.governance --offline

.PHONY: ekg-explorer
ekg-explorer:
	@echo "🗺️  Exportando explorador HTML navegable (Fase 9): grafo completo, offline, sin servidor"
	@docker compose exec web python -m tools.ekg.export_html
	@echo "Abrir tools/ekg/out/graph_explorer.html en un navegador."

.PHONY: ekg-summary
ekg-summary:
	@echo "📊 Resumen de plataforma (Fase 10): cumplimiento de arquitectura + modulos desacoplados"
	@docker compose exec web python -m tools.ekg.platform --summary

.PHONY: ekg-dossier
ekg-dossier:
	@echo "📁 Expediente completo (Fase 10): impacto + cumplimiento para NAME=$(NAME)"
	@docker compose exec web python -m tools.ekg.platform --dossier "$(NAME)"