# 🔧 Solución: Error "You're accessing the development server over HTTPS"

## ❌ Error
```
You're accessing the development server over HTTPS, but it only supports HTTP.
code 400, message Bad request version
```

## 🔍 Causa
El servidor de desarrollo de Django solo soporta **HTTP**, pero estás intentando acceder con **HTTPS**.

## ✅ Soluciones

### Solución 1: Usar HTTP explícitamente (Recomendado)

**Accede usando HTTP, NO HTTPS:**

```
✅ CORRECTO:  http://localhost:8000/admin/
✅ CORRECTO:  http://127.0.0.1:8000/admin/
❌ INCORRECTO: https://localhost:8000/admin/
```

### Solución 2: Limpiar caché del navegador

Si tu navegador está redirigiendo automáticamente a HTTPS:

1. **Chrome/Edge:**
   - Presiona `Ctrl + Shift + Delete`
   - Selecciona "Caché" y "Cookies"
   - Marca "Todo el tiempo"
   - Click en "Borrar datos"

2. **Firefox:**
   - Presiona `Ctrl + Shift + Delete`
   - Selecciona "Caché" y "Cookies"
   - Marca "Todo"
   - Click en "Limpiar ahora"

3. **Usar modo incógnito:**
   - `Ctrl + Shift + N` (Chrome/Edge)
   - `Ctrl + Shift + P` (Firefox)
   - Accede a `http://localhost:8000/admin/`

### Solución 3: Deshabilitar HSTS para localhost

**Chrome/Edge:**
1. Abre: `chrome://net-internals/#hsts`
2. En "Delete domain security policies"
3. Escribe: `localhost`
4. Click en "Delete"
5. Repite para `127.0.0.1`

**Firefox:**
1. Abre: `about:config`
2. Busca: `network.stricttransportsecurity.preloadlist`
3. Cambia a `false`
4. Reinicia el navegador

### Solución 4: Usar IP directa

En lugar de `localhost`, usa la IP directa:

```
http://127.0.0.1:8000/admin/
```

### Solución 5: Verificar que el servidor esté corriendo

```powershell
# Ver logs del contenedor
docker compose logs -f web

# Verificar que el puerto esté expuesto
docker compose ps
```

Deberías ver algo como:
```
web-1  | Starting development server at http://0.0.0.0:8000/
```

## 🚀 Verificación Rápida

1. **Verifica que Docker esté corriendo:**
   ```powershell
   docker compose ps
   ```

2. **Verifica los logs:**
   ```powershell
   docker compose logs web | Select-String "Starting development server"
   ```

3. **Accede correctamente:**
   - Abre el navegador
   - Escribe: `http://localhost:8000/admin/` (con http://, NO https://)
   - Presiona Enter

## 📝 Nota Importante

El servidor de desarrollo de Django (`runserver`) **NO soporta HTTPS** por defecto. Para producción necesitarás:
- Un servidor web como Nginx o Apache
- Un proxy reverso con certificado SSL
- O usar Django con SSL/TLS configurado

Para desarrollo local, **siempre usa HTTP**.

## 🔗 URLs Correctas

- Admin: `http://localhost:8000/admin/`
- API (cuando la configures): `http://localhost:8000/api/`
- Root: `http://localhost:8000/`
