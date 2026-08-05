# 🔧 Solución: Error 404 en /console/tenants/

## Problema

Al acceder a `http://sintel.net.co/console/tenants/` se obtiene un error 404.

## Causas Comunes

### 1. Acceso desde localhost en lugar de sintel.net.co

**Síntoma**: Accedes desde `http://localhost:8000/console/tenants/` o similar.

**Solución**: Accede desde `http://sintel.net.co/console/tenants/`

**En Windows (PowerShell como Administrador)**:
```powershell
# Añadir sintel.net.co a hosts
Add-Content -Path C:\Windows\System32\drivers\etc\hosts -Value "127.0.0.1 sintel.net.co"
```

**En Linux/Mac**:
```bash
# Añadir sintel.net.co a hosts
echo "127.0.0.1 sintel.net.co" | sudo tee -a /etc/hosts
```

### 2. Uso de HTTPS en lugar de HTTP

**Síntoma**: El navegador fuerza HTTPS automáticamente.

**Solución**: 
- Usar HTTP explícitamente: `http://sintel.net.co/console/tenants/` (NO `https://`)
- Si el navegador fuerza HTTPS, limpiar HSTS:
  - Chrome: `chrome://net-internals/#hsts`
  - Buscar "sintel.net.co" y eliminarlo

### 3. No estás autenticado o no eres staff

**Síntoma**: Redirección a login o 403 Forbidden.

**Solución**:
1. Inicia sesión en `http://sintel.net.co/admin/` con un usuario `is_staff=True`
2. Luego accede a `http://sintel.net.co/console/tenants/`

### 4. Dominio no registrado en la base de datos

**Síntoma**: El middleware no resuelve el tenant público.

**Solución**:
```bash
docker compose exec web python scripts/add_sintel_domain.py
```

## Verificación Rápida

Ejecuta el script de diagnóstico:

```bash
docker compose exec web python scripts/debug_console_access.py
```

Este script verifica:
- ✅ Dominio público registrado
- ✅ URLs configuradas correctamente
- ✅ Usuarios staff disponibles
- ✅ ALLOWED_HOSTS incluye sintel.net.co

## Flujo Correcto

1. **Asegurar dominio en hosts** (si es local):
   ```
   127.0.0.1 sintel.net.co
   ```

2. **Acceder al admin** (para autenticarte):
   ```
   http://sintel.net.co/admin/
   ```

3. **Iniciar sesión** con usuario staff

4. **Acceder a la consola**:
   ```
   http://sintel.net.co/console/tenants/
   ```

## Comandos Útiles

```bash
# Verificar dominio público
docker compose exec web python scripts/verify_public_domain_access.py

# Añadir dominio si falta
docker compose exec web python scripts/add_sintel_domain.py

# Diagnóstico completo
docker compose exec web python scripts/debug_console_access.py

# Ver logs del servidor
docker compose logs -f web
```

## Estado Actual

Según el diagnóstico:
- ✅ Dominio `sintel.net.co` registrado
- ✅ Rutas configuradas correctamente
- ✅ 3 usuarios staff disponibles
- ✅ ALLOWED_HOSTS incluye sintel.net.co
- ✅ Redirección a login funcionando (302)

**El sistema está correctamente configurado. El problema es probablemente de acceso (localhost vs sintel.net.co).**
