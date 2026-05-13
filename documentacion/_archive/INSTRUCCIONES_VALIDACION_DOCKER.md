# INSTRUCCIONES DE VALIDACIÓN DOCKER

**Fecha:** 2026-02-10  
**Objetivo:** Validar stack Docker y pipeline universal

---

## 📋 PASOS DE VALIDACIÓN

### 1. Verificar Configuración

```powershell
# Desde el directorio raíz del proyecto
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

---

### 2. Construir Imágenes

```powershell
# Con archivo .env (si existe)
docker compose -f infra/compose/docker-compose.yml --env-file infra/compose/.env build --no-cache

# Sin archivo .env (usar variables de entorno del sistema)
docker compose -f infra/compose/docker-compose.yml build --no-cache
```

---

### 3. Levantar Servicios

```powershell
# Con archivo .env
docker compose -f infra/compose/docker-compose.yml --env-file infra/compose/.env up -d

# Sin archivo .env
docker compose -f infra/compose/docker-compose.yml up -d
```

---

### 4. Esperar Healthchecks

```powershell
# Esperar 30-60 segundos
Start-Sleep -Seconds 60

# Verificar estado
docker compose -f infra/compose/docker-compose.yml ps
```

**Resultado esperado:**
- Todos los servicios con estado `running` o `healthy`

---

### 5. Verificar Logs

#### Logs de App (verificar KeyError)

```powershell
docker compose -f infra/compose/docker-compose.yml logs app --tail=50 | Select-String -Pattern "keyerror|filename|documento_upload|error|exception" -CaseSensitive:$false
```

**Resultado esperado:**
- ✅ **NO** debe aparecer `KeyError: "Attempt to overwrite 'filename'"`
- ✅ Debe aparecer `upload_filename` en logs estructurados

#### Logs de Celery

```powershell
docker compose -f infra/compose/docker-compose.yml logs celery --tail=30
```

**Resultado esperado:**
- ✅ `celery@... ready`
- ✅ Colas registradas: `high_priority`, `default`
- ✅ Sin tracebacks

#### Logs de Beat

```powershell
docker compose -f infra/compose/docker-compose.yml logs beat --tail=30
```

**Resultado esperado:**
- ✅ `beat: Starting...`
- ✅ Sin errores de conexión

---

### 6. Verificar Tarea Celery

```powershell
docker compose -f infra/compose/docker-compose.yml exec -T celery celery -A config inspect registered | Select-String -Pattern "document_ingest"
```

**Resultado esperado:**
- ✅ Debe aparecer `apps.services.document_ingest.tasks.document_ingest_task`

---

## 🧪 PRUEBAS E2E

### Prerequisitos

1. **Obtener credenciales (sessionid y csrftoken):**
   - Login en la aplicación
   - Extraer cookies de la sesión

2. **Preparar archivos XML de prueba:**
   - Factura UBL 2.1 válida
   - Nota Crédito UBL 2.1 válida

### Prueba 1: Preview de Factura (200 OK)

```powershell
$uri = "http://localhost:8000/api/v1/core/documentos/upload/?preview=true"
$filePath = "C:\ruta\a\invoice.xml"

$formData = @{
    file = Get-Item $filePath
}

$headers = @{
    "X-CSRFToken" = "<csrf_token>"
}

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$session.Cookies.Add((New-Object System.Net.Cookie("sessionid", "<session_id>", "/", "localhost")))
$session.Cookies.Add((New-Object System.Net.Cookie("csrftoken", "<csrf_token>", "/", "localhost")))

$response = Invoke-WebRequest -Uri $uri -Method POST -Form $formData -Headers $headers -WebSession $session
$response.StatusCode  # Debe ser 200
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

**Resultado esperado:**
- Status: `200 OK`
- Body: `{"persisted": false, "dto": {...}, "sha256": "...", ...}`

### Prueba 2: Persistencia de Factura (201 Created)

```powershell
$uri = "http://localhost:8000/api/v1/core/documentos/upload/?preview=false"
# ... (mismo código que Prueba 1, cambiar preview=false)
```

**Resultado esperado:**
- Status: `201 Created` o `200 OK`
- Body: `{"persisted": true, "dto": {...}, "id": 123, ...}`

### Prueba 3: Idempotencia (409 Conflict)

```powershell
# Repetir el mismo comando del paso 2
```

**Resultado esperado:**
- Status: `409 Conflict`
- Body: `{"persisted": false, "error": "duplicate", ...}`

### Prueba 4: Nota Crédito (201 Created)

```powershell
$filePath = "C:\ruta\a\credit_note.xml"
# ... (mismo código que Prueba 2, cambiar archivo)
```

**Resultado esperado:**
- Status: `201 Created` o `200 OK`
- Body: `{"persisted": true, "dto": {...}, "tipo": "creditnote", ...}`

---

## 📊 CHECKLIST

- [ ] Configuración Docker Compose válida
- [ ] Imágenes construidas
- [ ] Servicios levantados
- [ ] Healthchecks pasando
- [ ] Logs sin KeyError
- [ ] Celery funcionando
- [ ] Beat funcionando
- [ ] Tarea `document_ingest_task` registrada
- [ ] Preview Factura → 200 OK
- [ ] Persistencia Factura → 201/200 OK
- [ ] Idempotencia → 409 Conflict
- [ ] Nota Crédito → 201/200 OK

---

## ⚠️ NOTAS

1. **Rutas:** Todos los comandos se ejecutan desde el directorio raíz del proyecto
2. **PowerShell:** Comandos adaptados para PowerShell (no Bash)
3. **.env:** Si no existe, usar variables de entorno del sistema
4. **Healthchecks:** Esperar 30-60 segundos después de `up -d`

---

**Última actualización:** 2026-02-10
