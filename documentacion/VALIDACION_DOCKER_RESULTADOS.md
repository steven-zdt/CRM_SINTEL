# VALIDACIÓN DOCKER — RESULTADOS

**Fecha:** 2026-02-10  
**Objetivo:** Validar stack Docker (app + celery + beat) y pipeline universal

---

## 📋 CONFIGURACIÓN DEL STACK

### Servicios Definidos

| Servicio | Imagen/Context | Puerto | Estado |
|----------|----------------|--------|--------|
| `app` | Build desde `infra/docker/app/Dockerfile` | 8000 | ⏳ Pendiente |
| `db` | `postgres:16` | 5432 | ⏳ Pendiente |
| `redis` | `redis:7-alpine` | 6379 | ⏳ Pendiente |
| `celery` | Build desde `infra/docker/app/Dockerfile` | - | ⏳ Pendiente |
| `beat` | Build desde `infra/docker/app/Dockerfile` | - | ⏳ Pendiente |
| `opensearch` | `opensearchproject/opensearch:latest` | 9200, 9600 | ⏳ Pendiente |
| `traefik` | `traefik:v3.3` | 80, 8080 | ⏳ Pendiente |

### Comandos Celery

- **Celery Worker:** `celery -A config worker -l INFO --concurrency=2 -Q high_priority,default`
- **Celery Beat:** `celery -A config beat -l INFO`

---

## 🔍 PASOS DE VALIDACIÓN

### 1. Verificación de Configuración

```bash
docker compose -f infra/compose/docker-compose.yml config --services
```

**Resultado esperado:**
```
db
opensearch
redis
app
traefik
beat
celery
```

**Estado:** ✅ Configuración válida

---

### 2. Construcción de Imágenes

```bash
docker compose -f infra/compose/docker-compose.yml --env-file infra/compose/.env build --no-cache
```

**Estado:** ⏳ Pendiente de ejecución

**Nota:** Requiere archivo `.env` en `infra/compose/.env`

---

### 3. Levantamiento de Servicios

```bash
docker compose -f infra/compose/docker-compose.yml --env-file infra/compose/.env up -d
```

**Estado:** ⏳ Pendiente de ejecución

---

### 4. Verificación de Estado

```bash
docker compose -f infra/compose/docker-compose.yml ps
```

**Estado:** ⏳ Pendiente de ejecución

**Resultado esperado:**
- Todos los servicios con estado `running` o `healthy`
- Healthchecks pasando para `app`, `db`, `opensearch`

---

### 5. Verificación de Logs Celery

```bash
docker compose -f infra/compose/docker-compose.yml logs celery --tail=30
```

**Estado:** ⏳ Pendiente de ejecución

**Resultado esperado:**
- ✅ Sin tracebacks
- ✅ Mensaje de inicio: `celery@... ready`
- ✅ Colas registradas: `high_priority`, `default`
- ✅ Tarea `document_ingest_task` registrada

---

### 6. Verificación de Logs Beat

```bash
docker compose -f infra/compose/docker-compose.yml logs beat --tail=30
```

**Estado:** ⏳ Pendiente de ejecución

**Resultado esperado:**
- ✅ Sin tracebacks
- ✅ Mensaje: `beat: Starting...`
- ✅ Sin errores de conexión a Redis/DB

---

### 7. Verificación de Logs App

```bash
docker compose -f infra/compose/docker-compose.yml logs app --tail=50 | grep -i "keyerror\|filename\|documento_upload\|error\|exception"
```

**Estado:** ⏳ Pendiente de ejecución

**Resultado esperado:**
- ✅ **NO** debe aparecer `KeyError: "Attempt to overwrite 'filename'"`
- ✅ Debe aparecer `upload_filename` en logs estructurados
- ✅ Sin tracebacks relacionados con logging

---

### 8. Verificación de Tarea Celery

```bash
docker compose -f infra/compose/docker-compose.yml exec -T celery celery -A config inspect registered | grep document_ingest
```

**Estado:** ⏳ Pendiente de ejecución

**Resultado esperado:**
- ✅ Debe aparecer `apps.services.document_ingest.tasks.document_ingest_task`

---

## 🧪 PRUEBAS E2E (End-to-End)

### Prueba 1: Preview de Factura (200 OK)

**Comando:**
```bash
curl -i -X POST "http://localhost:8000/api/v1/core/documentos/upload/?preview=true" \
  -H "Cookie: sessionid=<session_id>; csrftoken=<csrf_token>" \
  -H "X-CSRFToken: <csrf_token>" \
  -F "file=@/tmp/invoice.xml"
```

**Resultado esperado:**
- Status: `200 OK`
- Body: `{"persisted": false, "dto": {...}, "sha256": "...", ...}`
- **Sin KeyError en logs**

**Estado:** ⏳ Pendiente de ejecución

---

### Prueba 2: Persistencia de Factura (201 Created)

**Comando:**
```bash
curl -i -X POST "http://localhost:8000/api/v1/core/documentos/upload/?preview=false" \
  -H "Cookie: sessionid=<session_id>; csrftoken=<csrf_token>" \
  -H "X-CSRFToken: <csrf_token>" \
  -F "file=@/tmp/invoice.xml"
```

**Resultado esperado:**
- Status: `201 Created` o `200 OK` (si idempotente)
- Body: `{"persisted": true, "dto": {...}, "id": 123, "numero": "...", ...}`
- **Sin KeyError en logs**

**Estado:** ⏳ Pendiente de ejecución

---

### Prueba 3: Idempotencia (409 Conflict)

**Comando:**
```bash
# Repetir el mismo comando del paso 2
curl -i -X POST "http://localhost:8000/api/v1/core/documentos/upload/?preview=false" \
  -H "Cookie: sessionid=<session_id>; csrftoken=<csrf_token>" \
  -H "X-CSRFToken: <csrf_token>" \
  -F "file=@/tmp/invoice.xml"
```

**Resultado esperado:**
- Status: `409 Conflict`
- Body: `{"persisted": false, "error": "duplicate", "message": "..."}`
- **Sin KeyError en logs**

**Estado:** ⏳ Pendiente de ejecución

---

### Prueba 4: Nota Crédito (201 Created)

**Comando:**
```bash
curl -i -X POST "http://localhost:8000/api/v1/core/documentos/upload/?preview=false" \
  -H "Cookie: sessionid=<session_id>; csrftoken=<csrf_token>" \
  -H "X-CSRFToken: <csrf_token>" \
  -F "file=@/tmp/credit_note.xml"
```

**Resultado esperado:**
- Status: `201 Created` o `200 OK`
- Body: `{"persisted": true, "dto": {...}, "id": 456, "tipo": "creditnote", ...}`
- **Sin KeyError en logs**

**Estado:** ⏳ Pendiente de ejecución

---

## 📊 RESULTADOS

### Estado de Servicios

| Servicio | Estado | Healthcheck | Notas |
|----------|--------|-------------|-------|
| `app` | ⏳ | ⏳ | - |
| `db` | ⏳ | ⏳ | - |
| `redis` | ⏳ | ⏳ | - |
| `celery` | ⏳ | - | - |
| `beat` | ⏳ | - | - |
| `opensearch` | ⏳ | ⏳ | - |
| `traefik` | ⏳ | - | - |

### Logs Críticos

**KeyError en Logs:**
- Estado: ⏳ Pendiente de verificación
- Resultado esperado: ✅ **NO** debe aparecer `KeyError: "Attempt to overwrite 'filename'"`

**Tarea Celery:**
- Estado: ⏳ Pendiente de verificación
- Resultado esperado: ✅ `document_ingest_task` registrada

### Pruebas E2E

| Prueba | Estado | Resultado | Notas |
|--------|--------|-----------|-------|
| Preview Factura | ⏳ | - | - |
| Persistencia Factura | ⏳ | - | - |
| Idempotencia (409) | ⏳ | - | - |
| Nota Crédito | ⏳ | - | - |

---

## ⚠️ PREREQUISITOS

### Archivos Requeridos

1. **`.env` en `infra/compose/.env`**
   - Variables de entorno para servicios
   - Configuración de DB, Redis, etc.

2. **Dockerfile en `infra/docker/app/Dockerfile`**
   - Imagen base para `app`, `celery`, `beat`

3. **Archivo XML de prueba**
   - Factura UBL 2.1 válida
   - Nota Crédito UBL 2.1 válida

### Credenciales

- **Session ID:** Obtener desde login
- **CSRF Token:** Obtener desde cookies o headers

---

## 📝 NOTAS

1. **PowerShell:** Los comandos están adaptados para PowerShell (no Bash)
2. **Rutas:** Todos los comandos se ejecutan desde el directorio raíz del proyecto
3. **Healthchecks:** Esperar al menos 30-60 segundos después de `up -d` para que los healthchecks pasen
4. **Logs:** Usar `docker compose logs -f` para seguir logs en tiempo real

---

## 🚀 PRÓXIMOS PASOS

1. ✅ Verificar que existe `infra/compose/.env`
2. ✅ Ejecutar build: `docker compose -f infra/compose/docker-compose.yml --env-file infra/compose/.env build --no-cache`
3. ✅ Ejecutar up: `docker compose -f infra/compose/docker-compose.yml --env-file infra/compose/.env up -d`
4. ✅ Esperar healthchecks (30-60 segundos)
5. ✅ Verificar logs de celery, beat, app
6. ✅ Ejecutar pruebas E2E con curl
7. ✅ Generar reporte final con resultados

---

**Última actualización:** 2026-02-10  
**Estado:** ⏳ Pendiente de ejecución completa
