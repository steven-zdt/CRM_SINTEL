# 🔧 Solución: Error HTTPS en Tenants (ERR_SSL_PROTOCOL_ERROR)

## ❌ Error

```
Este sitio no puede proporcionar una conexión segura
home.com envió una respuesta no válida.
ERR_SSL_PROTOCOL_ERROR
```

O en los logs del servidor:
```
code 400, message Bad request version
You're accessing the development server over HTTPS, but it only supports HTTP.
```

## 🔍 Causa

El servidor de desarrollo de Django (`runserver`) **solo soporta HTTP**, NO HTTPS. Cuando intentas acceder con `https://home.com:8000`, el navegador intenta establecer una conexión SSL/TLS, pero el servidor HTTP no puede procesarla.

## ✅ Soluciones

### Solución 1: Usar HTTP Explícitamente (Recomendado)

**Accede usando HTTP, NO HTTPS:**

```
✅ CORRECTO:  http://home.com:8000/admin/login/
✅ CORRECTO:  http://home.com:8000/
❌ INCORRECTO: https://home.com:8000/admin/login/
```

### Solución 2: Limpiar HSTS del Navegador

Si tu navegador está forzando HTTPS automáticamente (HSTS):

**Chrome/Edge:**
1. Abre: `chrome://net-internals/#hsts`
2. En "Delete domain security policies"
3. Escribe: `home.com`
4. Click en "Delete"
5. Repite para `localhost` y `127.0.0.1` si es necesario

**Firefox:**
1. Abre: `about:config`
2. Busca: `network.stricttransportsecurity.preloadlist`
3. Cambia a `false`
4. Reinicia el navegador

### Solución 3: Usar Modo Incógnito

El modo incógnito no tiene HSTS guardado:

- `Ctrl + Shift + N` (Chrome/Edge)
- `Ctrl + Shift + P` (Firefox)
- Accede a `http://home.com:8000/admin/login/`

### Solución 4: Verificar Configuración de Dominio

Asegúrate de que el dominio `home.com` esté correctamente configurado:

```bash
# Verificar que el dominio existe en la BD
docker-compose exec web python manage.py shell
```

```python
from django.db import connection
from apps.public.tenants.models import Client, Domain

connection.set_schema_to_public()
domain = Domain.objects.filter(domain='home.com').first()
if domain:
    print(f"✅ Dominio encontrado: {domain.domain} -> Tenant: {domain.tenant.nombre}")
else:
    print("❌ Dominio no encontrado")
```

### Solución 5: Agregar Dominio a /etc/hosts (Windows)

Si estás usando `home.com` en desarrollo local, agrégalo a tu archivo hosts:

**Windows:** `C:\Windows\System32\drivers\etc\hosts`
```
127.0.0.1   home.com
127.0.0.1   localhost
```

**Linux/Mac:** `/etc/hosts`
```
127.0.0.1   home.com
127.0.0.1   localhost
```

Luego accede con: `http://home.com:8000/admin/login/`

## 🚀 Verificación Rápida

1. **Verifica que Docker esté corriendo:**
   ```bash
   docker compose ps
   ```

2. **Verifica los logs:**
   ```bash
   docker compose logs web | grep "Starting development server"
   ```
   
   Deberías ver:
   ```
   Starting development server at http://0.0.0.0:8000/
   ```

3. **Accede correctamente:**
   - Abre el navegador
   - Escribe: `http://home.com:8000/admin/login/` (con `http://`, NO `https://`)
   - Presiona Enter

## 📝 Nota Importante

El servidor de desarrollo de Django (`runserver`) **NO soporta HTTPS** por defecto. 

**Para desarrollo local:**
- ✅ Siempre usar HTTP: `http://home.com:8000`
- ✅ El middleware `HTTPSRedirectMiddleware` intenta redirigir HTTPS -> HTTP (solo si Django puede procesar la petición)

**Para producción:**
- Necesitarás un servidor web como Nginx o Apache
- Un proxy reverso con certificado SSL
- O configurar Django con SSL/TLS

## 🔗 URLs Correctas para Tenants

- Landing: `http://home.com:8000/`
- Dashboard: `http://home.com:8000/dashboard/`
- Admin Login: `http://home.com:8000/admin/login/`
- API: `http://home.com:8000/api/v1/facturas/facturas/`

## ⚠️ Si el Problema Persiste

1. **Limpiar caché del navegador completamente**
2. **Usar modo incógnito**
3. **Verificar que el dominio esté en /etc/hosts**
4. **Usar IP directa:** `http://127.0.0.1:8000/admin/login/`
5. **Verificar logs del servidor:** `docker compose logs -f web`
