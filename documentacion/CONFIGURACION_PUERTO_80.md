# 🔧 Configuración de Puerto 80 para Tenants Privados

## ✅ Estado Actual

El dominio `home.com` está **correctamente registrado** en la base de datos:
- ✅ ID: 105
- ✅ Tenant: `home` (schema_name: home)
- ✅ Primary: True
- ✅ Is Active: True

## ❌ Problema

Cuando accedes a `http://home.com/`, no se registra actividad porque:

1. **El servidor Django no está escuchando en el puerto 80**
2. **El archivo hosts no está configurado** para apuntar `home.com` a `localhost`
3. **El navegador está resolviendo `home.com` a una IP externa** (no localhost)

## ✅ Soluciones

### Opción 1: Configurar Archivo Hosts (Recomendado para Desarrollo)

**Windows:**
1. Abre el Bloc de notas como **Administrador**
2. Abre el archivo: `C:\Windows\System32\drivers\etc\hosts`
3. Agrega esta línea al final:
   ```
   127.0.0.1    home.com
   127.0.0.1    tupapi.com
   ```
4. Guarda el archivo
5. Reinicia el navegador

**Linux/macOS:**
```bash
sudo nano /etc/hosts
```

Agrega:
```
127.0.0.1    home.com
127.0.0.1    tupapi.com
```

### Opción 2: Configurar Docker para Escuchar en Puerto 80

**Modificar `docker-compose.yaml`:**

```yaml
services:
  web:
    ports:
      - "80:8000"  # Mapear puerto 80 del host al 8000 del contenedor
```

**Luego reiniciar:**
```bash
docker-compose down
docker-compose up -d
```

### Opción 3: Usar Nginx como Proxy Reverso (Producción)

Configurar Nginx para escuchar en puerto 80 y hacer proxy a Django en puerto 8000:

```nginx
server {
    listen 80;
    server_name home.com tupapi.com *.sintel.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🔍 Verificación

### 1. Verificar que el dominio está registrado:
```bash
docker-compose exec web python manage.py check_domains --domain home.com
```

### 2. Verificar que el archivo hosts está configurado:
```bash
# Windows PowerShell
Get-Content C:\Windows\System32\drivers\etc\hosts | Select-String "home.com"

# Linux/macOS
cat /etc/hosts | grep home.com
```

### 3. Verificar resolución DNS:
```bash
# Windows
nslookup home.com

# Linux/macOS
dig home.com
```

Debería mostrar `127.0.0.1` si el archivo hosts está configurado correctamente.

### 4. Probar acceso:
```bash
# Debería mostrar la landing page del tenant
curl -H "Host: home.com" http://localhost/
```

## 📝 Notas Importantes

1. **Puerto 80 requiere permisos de administrador** en la mayoría de sistemas operativos
2. **En desarrollo**, es más fácil usar el archivo hosts + puerto 8000
3. **En producción**, usa Nginx/Apache como proxy reverso en puerto 80
4. **django-tenants** identifica el tenant por el header `Host` de la petición HTTP

## 🚀 Solución Rápida (Desarrollo)

1. **Configurar archivo hosts:**
   ```
   127.0.0.1    home.com
   ```

2. **Acceder con puerto 8000:**
   ```
   http://home.com:8000/
   ```

3. **O configurar Docker para puerto 80:**
   ```yaml
   ports:
     - "80:8000"
   ```
