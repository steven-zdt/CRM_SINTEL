# Makefile para gestión del stack Docker Compose
# Uso: make -C infra/compose <target>

.PHONY: help up down build logs test health clean

help:
	@echo "Comandos disponibles:"
	@echo "  make up       - Levantar stack completo"
	@echo "  make down     - Detener stack"
	@echo "  make build    - Construir imágenes"
	@echo "  make logs     - Ver logs del servicio app"
	@echo "  make test     - Ejecutar tests en contenedor"
	@echo "  make health   - Verificar health endpoint"
	@echo "  make clean    - Limpiar volúmenes y contenedores"

up:
	docker compose -f docker-compose.yml --env-file .env up -d

down:
	docker compose -f docker-compose.yml down

build:
	docker compose -f docker-compose.yml --env-file .env build

logs:
	docker compose -f docker-compose.yml logs -f app

test:
	docker compose -f docker-compose.yml -f docker-compose.test.yml --env-file .env up --abort-on-container-exit --build

health:
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Health check falló"

clean:
	docker compose -f docker-compose.yml down -v
	docker system prune -f
