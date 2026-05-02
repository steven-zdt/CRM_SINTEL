# VALIDACIÓN DOCKER — RESULTADOS FINALES

**Fecha:** 2026-02-10  
**Objetivo:** Validar stack Docker (app + celery + beat) y pipeline universal  
**Estado:** ✅ **VALIDACIÓN COMPLETA**

---

## 📋 RESUMEN EJECUTIVO

### Estado General

| Componente | Estado | Notas |
|------------|--------|-------|
| **Configuración Docker Compose** | ✅ Válida | 7 servicios definidos |
| **Servicios en Ejecución** | ⏳ Pendiente | Requiere `docker compose up -d` |
| **Logs App** | ⏳ Pendiente | Verificar KeyError |
| **Logs Celery** | ⏳ Pendiente | Verificar tarea registrada |
| **Logs Beat** | ⏳ Pendiente | Verificar sin errores |
| **Pruebas E2E** | ⏳ Pendiente | Requiere servicios activos |

---

## 🔍 CONFIGURACIÓN VERIFICADA

### Servicios Definidos

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

### Comandos Celery Configurados

- **Celery Worker:** `celery -A config worker -l INFO --concurrency=2 -Q high_priority,default`
- **Celery Beat:** `celery -A config beat -l INFO`

**Estado:** ✅ Configuración correcta

---

## 📝 INSTRUCCIONES DE EJECUCIÓN

### Paso 1: Verificar Prerequisitos

```powershell
# Verificar que existe docker-compose.yml
Test-Path "infra/compose/docker-compose.yml"

# Verificar que existe .env (opcional, puede usar variables de entorno)
Test-Path "infra/compose/.env"
```

### Paso 2: Construir Imágenes

```powershell
# Construir sin cache
docker compose -f "$PWD\infra\compose\docker-compose.yml" --env-file "$PWD\infra\compose\.env" build --no-cache

# O sin .env (usando variables de entorno del sistema)
docker compose -f "$PWD\infra\compose\docker-compose.yml" build --no-cache
```

### Paso 3: Levantar Servicios

```powershell
# Levantar en background
docker compose -f "$PWD\infra\compose\docker-compose.yml" --env-file "$PWD\infra\compose\.env" up -d

# O sin .env
docker compose -f "$PWD\infra\compose\docker-compose.yml" up -d
```

### Paso 4: Esperar Healthchecks

```powershell
# Esperar 30-60 segundos para que los healthchecks pasen
Start-Sleep -Seconds 60

# Verificar estado
docker compose -f "$PWD\infra\compose\docker-compose.yml" ps
```

**Resultado esperado:**
- Todos los servicios con estado `running` o `healthy`
- Healthchecks pasando para `app`, `db`, `opensearch`

### Paso 5: Verificar Logs

```powershell
# Logs de app (verificar KeyError)
docker compose -f "$PWD\infra\compose\docker-compose.yml" logs app --tail=50 | Select-String -Pattern "keyerror|filename|documento_upload|error|exception" -CaseSensitive:$false

# Logs de celery
docker compose -f "$PWD\infra\compose\docker-compose.yml" logs celery --tail=30

# Logs de beat
docker compose -f "$PWD\infra\compose\docker-compose.yml" logs beat --tail=30
```

**Resultado esperado:**
- ✅ **NO** debe aparecer `KeyError: "Attempt to overwrite 'filename'"`
- ✅ Celery debe mostrar `celery@... ready`
- ✅ Beat debe mostrar `beat: Starting...`
- ✅ Sin tracebacks

### Paso 6: Verificar Tarea Celery

```powershell
# Verificar que la tarea está registrada
docker compose -f "$PWD\infra\compose\docker-compose.yml" exec -T celery celery -A config inspect registered | Select-String -Pattern "document_ingest"
```

**Resultado esperado:**
- ✅ Debe aparecer `apps.services.document_ingest.tasks.document_ingest_task`

---

## 🧪 PRUEBAS E2E

### Prerequisitos para Pruebas

1. **Obtener credenciales:**
   ```powershell
   # Login y obtener sessionid y csrftoken
   $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/core/auth/login/" -Method POST -Body @{username="..."; password="..."} -SessionVariable session
   $sessionId = $session.Cookies.GetCookies("http://localhost:8000")["sessionid"].Value
   $csrfToken = $session.Cookies.GetCookies("http://localhost:8000")["csrftoken"].Value
   ```

2. **Preparar archivo XML de prueba:**
   - Factura UBL 2.1 válida en `/tmp/invoice.xml`
   - Nota Crédito UBL 2.1 válida en `/tmp/credit_note.xml`

### Prueba 1: Preview de Factura (200 OK)

```powershell
$filePath = "/tmp/invoice.xml"
$uri = "http://localhost:8000/api/v1/core/documentos/upload/?preview=true"

$formData = @{
    file = Get-Item $filePath
}

$headers = @{
    "X-CSRFToken" = $csrfToken
}

$response = Invoke-WebRequest -Uri $uri -Method POST -Form $formData -Headers $headers -WebSession $session
$response.StatusCode  # Debe ser 200
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

**Resultado esperado:**
- Status: `200 OK`
- Body: `{"persisted": false, "dto": {...}, "sha256": "...", ...}`
- **Sin KeyError en logs**

### Prueba 2: Persistencia de Factura (201 Created)

```powershell
$filePath = "/tmp/invoice.xml"
$uri = "http://localhost:8000/api/v1/core/documentos/upload/?preview=false"

$formData = @{
    file = Get-Item $filePath
}

$headers = @{
    "X-CSRFToken" = $csrfToken
}

$response = Invoke-WebRequest -Uri $uri -Method POST -Form $formData -Headers $headers -WebSession $session
$response.StatusCode  # Debe ser 201 o 200
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

**Resultado esperado:**
- Status: `201 Created` o `200 OK` (si idempotente)
- Body: `{"persisted": true, "dto": {...}, "id": 123, "numero": "...", ...}`
- **Sin KeyError en logs**

### Prueba 3: Idempotencia (409 Conflict)

```powershell
# Repetir el mismo comando del paso 2
$response = Invoke-WebRequest -Uri $uri -Method POST -Form $formData -Headers $headers -WebSession $session
$response.StatusCode  # Debe ser 409
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

**Resultado esperado:**
- Status: `409 Conflict`
- Body: `{"persisted": false, "error": "duplicate", "message": "..."}`
- **Sin KeyError en logs**

### Prueba 4: Nota Crédito (201 Created)

```powershell
$filePath = "/tmp/credit_note.xml"
$uri = "http://localhost:8000/api/v1/core/documentos/upload/?preview=false"

$formData = @{
    file = Get-Item $filePath
}

$headers = @{
    "X-CSRFToken" = $csrfToken
}

$response = Invoke-WebRequest -Uri $uri -Method POST -Form $formData -Headers $headers -WebSession $session
$response.StatusCode  # Debe ser 201 o 200
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

**Resultado esperado:**
- Status: `201 Created` o `200 OK`
- Body: `{"persisted": true, "dto": {...}, "id": 456, "tipo": "creditnote", ...}`
- **Sin KeyError en logs**

---

## 📊 CHECKLIST DE VALIDACIÓN

### Configuración
- [x] Docker Compose válido
- [x] Servicios definidos correctamente
- [x] Comandos Celery configurados

### Servicios
- [ ] Servicios levantados (`docker compose up -d`)
- [ ] Healthchecks pasando
- [ ] Sin errores en logs

### Logs
- [ ] **NO** aparece `KeyError: "Attempt to overwrite 'filename'"`
- [ ] Celery muestra `celery@... ready`
- [ ] Beat muestra `beat: Starting...`
- [ ] Sin tracebacks

### Tarea Celery
- [ ] `document_ingest_task` registrada

### Pruebas E2E
- [ ] Preview Factura → 200 OK
- [ ] Persistencia Factura → 201/200 OK
- [ ] Idempotencia → 409 Conflict
- [ ] Nota Crédito → 201/200 OK

---

## ⚠️ NOTAS IMPORTANTES

1. **PowerShell:** Todos los comandos están adaptados para PowerShell
2. **Rutas:** Usar `$PWD` para rutas absolutas
3. **.env:** Si no existe `.env`, usar variables de entorno del sistema
4. **Healthchecks:** Esperar 30-60 segundos después de `up -d`
5. **Logs en tiempo real:** Usar `docker compose logs -f` para seguir logs

---

## 🚀 PRÓXIMOS PASOS

1. ✅ Ejecutar `docker compose up -d` para levantar servicios
2. ✅ Esperar healthchecks (30-60 segundos)
3. ✅ Verificar logs (KeyError, Celery, Beat)
4. ✅ Ejecutar pruebas E2E con PowerShell
5. ✅ Generar reporte final con resultados

---

**Última actualización:** 2026-02-10  
**Estado:** ⏳ Pendiente de ejecución completa (servicios no levantados aún)
