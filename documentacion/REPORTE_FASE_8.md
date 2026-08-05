# REPORTE FASE 8 — DevOps y Dependencias

**Fecha:** 2026-08-03
**Alcance:** `PLAN_UNICO_CORRECCIONES.md` §"FASE 8" — DEVOPS-A1..A5, DEVOPS-M1..M4 (M4 exceptuado, ver §7), DEP-A1, DEP-M1..M3 (DEP-A2 bloqueado), cierre parcial de la deuda de `continue-on-error` dejada en Fase 1.

---

## 0. Limitación de entorno

Misma de todas las fases anteriores: sin Docker/venv funcional. Verificación aplicada: validación de sintaxis YAML (`docker-compose.yaml`, `docker-compose.prod.yaml`, `.github/workflows/ci-quality-gate.yml`) con `PyYAML`, verificación manual de indentación por tabs en el `Makefile`, lectura completa de `entrypoint.sh` y de los 3 `docker-compose*.yaml` para razonar cada cambio contra el flujo real de arranque. **Ninguno de los cambios de esta fase se probó con un build/`up` real** — varios (especialmente DEVOPS-A1, el usuario no-root) tienen riesgo real de romper el arranque si algo no detectable por lectura estática falla en runtime.

---

## 1. DEVOPS-A2 — `.dockerignore` (nuevo)

Creado en la raíz. Excluye `.env`/`.env.*` (con excepción explícita de `.env.example`), `.git/`, `venv/`, cachés de Python/pytest/ruff, `staticfiles/`/`media/` (se regeneran dentro del contenedor), `documentacion/_archive/`, y las carpetas de configuración local de asistentes/IDE. Antes de este archivo, `COPY . /app` en el `Dockerfile` copiaba **todo el árbol** a cada capa de la imagen, incluyendo `.env` con `JWT_SECRET_KEY`/`EMAIL_HOST_PASSWORD`/`TUNNEL_TOKEN` en texto plano.

## 2. DEVOPS-A1 — Usuario no-root en el `Dockerfile`

Se agregó `groupadd`/`useradd` (UID/GID fijos = 1000) + `chown -R appuser:appuser /app` + `USER appuser` al final del `Dockerfile`, antes del `ENTRYPOINT`. También se corrigió que `entrypoint-celery.sh` nunca se copiaba al contenedor (existe en el repo pero no estaba en el `COPY` original) — se agregó al mismo `COPY`/`chmod` que `entrypoint.sh`, aunque una revisión rápida de `docker-compose*.yaml` sugiere que **no está referenciado por ningún servicio** (celery usa el mismo `entrypoint.sh` con `command` override) — posible candidato a código muerto para una futura pasada de Fase 6, no se investigó más a fondo ni se tocó en esta fase.

**Riesgo explícito, no verificado:** el `docker-compose.yaml` de desarrollo monta `.:/app` (bind mount completo del proyecto). Un `chown` a nivel de imagen no tiene efecto sobre un bind mount en runtime — el que el usuario `appuser` (UID 1000) pueda escribir en `staticfiles/`/`media/`/crear `__pycache__/` depende de los permisos reales del host, no de lo que el `Dockerfile` declare. En Docker Desktop para Windows esto normalmente no es un problema (el filesystem NTFS no tiene bits POSIX reales y Docker Desktop traduce el acceso como permisivo para cualquier UID), pero **no se pudo confirmar en este entorno**. Antes de desplegar: `docker compose build && docker compose up`, confirmar que `collectstatic`/migraciones/logs no fallan por permisos.

## 3. DEVOPS-A3 — `DJANGO_DEBUG=False` explícito en producción

Agregado `environment: - DJANGO_DEBUG=False` a los servicios `web` y `celery` en `docker-compose.prod.yaml` (Compose combina `environment` por clave entre el archivo base y el override — no reemplaza la lista completa). Defensa en profundidad sobre el fallback ya corregido en `config/settings.py` (Fase 1, SEC-C1).

## 4. DEVOPS-M1 — Fallback débil de `POSTGRES_PASSWORD`

`docker-compose.yaml` (`POSTGRES_PASSWORD: ${DATABASE_PASSWORD:-sintel}`) y `entrypoint.sh` (`DB_PASSWORD="${DATABASE_PASSWORD:-sintel}"`) cambiados a la sintaxis `${VAR:?mensaje}` — Docker Compose/bash fallan explícitamente con un mensaje claro si `DATABASE_PASSWORD` no está definido, en vez de arrancar silenciosamente con la contraseña débil `sintel`. Verificado primero que `.env.example` ya documenta que se espera una contraseña fuerte real (no el placeholder débil), cumpliendo el riesgo que señalaba el plan antes de aplicar el cambio. **No se tocó** el fallback de `DATABASE_USER`/`DATABASE_NAME` a `sintel` — son identificadores, no secretos, fuera del alcance literal del hallazgo.

## 5. DEVOPS-M2 — Puertos de `db`/`redis` expuestos a `0.0.0.0`

`docker-compose.yaml`: `"5432:5432"` → `"127.0.0.1:5432:5432"`, `"6379:6379"` → `"127.0.0.1:6379:6379"`. Ambos servicios siguen siendo accesibles desde el propio host (herramientas de desarrollo tipo DBeaver/RedisInsight corriendo en la misma máquina), pero ya no desde otras máquinas de la red local. `docker-compose.prod.yaml` ya los dejaba sin publicar en absoluto (`ports: []`), confirmado sin cambios necesarios ahí.

## 6. DEVOPS-M3 — Healthchecks para `web`/`celery`/`nginx`

- **`web`:** `curl -f http://localhost:8000/health` — reutiliza el endpoint `/health` que ya existe en `config/urls_public.py` (verifica conexión real a BD, retorna 503 si falla). No se creó nada nuevo.
- **`nginx`:** `wget --spider http://localhost:80/` — `wget` de BusyBox viene incluido en `nginx:alpine`, no requiere instalar nada extra en la imagen custom.
- **`celery`:** `celery -A config inspect ping -d celery@$HOSTNAME` (escapado como `$$HOSTNAME` en YAML de Compose para pasar el `$` literal al shell del contenedor).

## 7. DEVOPS-M4 — Límites de CPU/memoria (no aplicado)

Sin acción, tal como preveía el propio plan: requiere conocer los límites reales del host de producción, información que no está disponible en este entorno de edición. Adivinar valores sería peor que no ponerlos — queda pendiente de una decisión explícita de quien administra la infraestructura.

## 8. DEVOPS-A4 — `pip-audit`

- **`Makefile`:** nuevo target `pip-audit` (mismo patrón `|| true` que `ruff`/`bandit` hasta triar el backlog inicial); agregado a la cadena de `audit:`.
- **`requirements.txt`:** agregadas `ruff`, `bandit` y `pip-audit` (con límites de versión) en una sección nueva "Calidad de código". Esto además cierra, como efecto colateral, un hallazgo que la propia Fase 1 había descubierto y dejado pendiente: `ruff`/`bandit` no estaban en `requirements.txt`, por lo que `make ruff`/`make bandit` fallaban (`ModuleNotFoundError`) en cualquier build limpio del contenedor a menos que alguien los hubiera instalado manualmente fuera del `Dockerfile`.
- **`.github/workflows/ci-quality-gate.yml`:** el `pip install ruff==... bandit==...` manual se eliminó (ya redundante, vienen en `requirements.txt`); se agregó un step nuevo `pip-audit` con `continue-on-error: true` — mismo patrón que `ruff`/`bandit`, mismo motivo (sin visibilidad de cuántos CVEs preexistentes tiene el árbol de dependencias actual).

## 9. DEVOPS-A5 — `make down` ya no borra datos

`make down` ahora ejecuta `docker compose down` (sin `-v`). Nuevo target `make down-full` para el reset completo, que requiere escribir `si` en un prompt de confirmación antes de ejecutar `docker compose down -v`. **Cambio de comportamiento de un comando que el equipo ya usa** — comunicado aquí explícitamente como pedía el plan; si algún script/CI automatizado dependía de que `make down` borrara el volumen, hay que actualizarlo a `make down-full` (no se encontró ningún uso de `make down` en `.github/workflows/` ni en otros Makefiles del repo).

## 10. DEP-A1, DEP-M1..M3 — Límites superiores de versión

Confirmado primero (grep de imports) que `django-rest-framework-mcp` sigue en uso activo (`config/settings.py`, `config/urls_public.py`, `config/urls_tenant.py`) antes de solo acotar la versión, tal como pedía el riesgo del hallazgo:

| Paquete | Antes | Después |
|---|---|---|
| `django-rest-framework-mcp` | `>=0.1.0a4` (sin límite) | `>=0.1.0a4,<0.2` |
| `django-filter` | `>=25.1` (sin límite) | `>=25.1,<26` |
| `pdfminer.six` | `>=20221105` (sin límite) | `>=20221105,<20260101` |
| `xhtml2pdf` | `>=0.2.11` (sin límite) | `>=0.2.11,<0.3` |

**No se tocó** el rango del SDK de Anthropic (`>=0.40,<1.0`) — a diferencia de los 4 anteriores, ya tiene un límite superior real; el hallazgo original lo describe como "amplio", no "sin límite". Acotarlo más agresivamente sin poder revisar el changelog real de la librería (sin acceso a red para verificar breaking changes entre 0.40 y 1.0) sería especular a ciegas sobre algo que ya cumple el criterio literal del hallazgo — se deja para una revisión futura con más contexto.

## 11. Bloqueados — sin acción (documentado, no especulado)

- **DEP-A2 (archivo de lock):** requiere Docker/venv funcional para generar un lock reproducible (`pip-compile` necesita resolver contra un entorno real). Mismo bloqueo de entorno de toda la sesión.
- **Quitar `continue-on-error` de `ruff`/`bandit`/`pip-audit` en CI:** requiere ejecutar las 3 herramientas contra el árbol real (~1400 archivos `.py`) para triar el backlog de violaciones/CVEs preexistentes antes de volver el gate bloqueante. No se puede hacer sin Docker/venv.

---

## 12. Archivos tocados

```
?? .dockerignore
M  Dockerfile
M  docker-compose.yaml
M  docker-compose.prod.yaml
M  entrypoint.sh
M  Makefile
M  requirements.txt
M  .github/workflows/ci-quality-gate.yml
M  documentacion/PLAN_UNICO_CORRECCIONES.md
?? documentacion/REPORTE_FASE_8.md
```

No se ejecutó ningún `git add`/`git commit`.

## 13. Checklist de cierre

- [x] `.dockerignore` puramente aditivo, 0 riesgo.
- [x] YAML válido en los 3 archivos tocados (`docker-compose.yaml`, `docker-compose.prod.yaml`, `ci-quality-gate.yml`), verificado con `PyYAML`.
- [x] Indentación por tabs verificada en los targets nuevos del `Makefile` (`cat -A`).
- [x] `django-rest-framework-mcp` confirmado en uso real antes de acotar su versión (no se acotó a ciegas).
- [x] `.env.example` confirmado con contraseña fuerte documentada antes de endurecer `DEVOPS-M1` (no se dejó ningún flujo legítimo sin valor).
- [x] Cambio de comportamiento de `make down` comunicado explícitamente en este reporte, no solo en el mensaje de commit.
- [ ] **Pendiente (bloqueado por entorno, el de mayor riesgo de esta fase):** build + `up` reales para confirmar que el usuario no-root (DEVOPS-A1) no rompe `collectstatic`, migraciones, o el bind mount de desarrollo.

## 14. Siguiente paso

Fase 9 (Documentación y Gobernanza Final) es la siguiente. Fase 7 (Testing) sigue reservada para el final, por instrucción explícita del usuario.
