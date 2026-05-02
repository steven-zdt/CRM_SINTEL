# 🔐 Autenticación JWT en SINTEL

## 📋 Resumen

El proyecto implementa autenticación JWT (JSON Web Tokens) usando `djangorestframework-simplejwt`, el estándar recomendado por Django REST Framework.

**Ventajas de JWT:**
- ✅ Sin estado (stateless): no requiere sesiones en el servidor
- ✅ Escalable: funciona bien con múltiples servidores
- ✅ Seguro: tokens firmados criptográficamente
- ✅ Estándar: compatible con cualquier cliente (web, móvil, IoT)

---

## 🚀 Configuración

### Dependencia

```txt
djangorestframework-simplejwt>=5.3,<6.0
```

### Settings (`config/settings.py`)

```python
# JWT habilitado en REST_FRAMEWORK
'DEFAULT_AUTHENTICATION_CLASSES': [
    'rest_framework_simplejwt.authentication.JWTAuthentication',  # JWT (prioridad)
    'rest_framework.authentication.SessionAuthentication',        # Sesión (consola)
    'rest_framework.authentication.TokenAuthentication',          # Token (legacy)
],

# Configuración JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),      # Token de acceso: 1 hora
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),       # Token de refresh: 7 días
    'ROTATE_REFRESH_TOKENS': True,                     # Rotar refresh tokens
    'BLACKLIST_AFTER_ROTATION': True,                  # Invalidar tokens anteriores
    'ALGORITHM': 'HS256',                              # Algoritmo de firma
    'AUTH_HEADER_TYPES': ('Bearer',),                  # Authorization: Bearer <token>
}
```

---

## 📍 Endpoints de Autenticación

### 1. Login (Obtener Tokens)

**POST** `/api/token/`

**Request:**
```json
{
    "username": "usuario@ejemplo.com",
    "password": "contraseña123"
}
```

**Response (200 OK):**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Ejemplo con curl:**
```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@test.local", "password": "admin123"}'
```

---

### 2. Refresh Token (Renovar Access Token)

**POST** `/api/token/refresh/`

**Request:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Ejemplo con curl:**
```bash
curl -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "TU_REFRESH_TOKEN_AQUI"}'
```

---

### 3. Verify Token (Verificar Validez)

**POST** `/api/token/verify/`

**Request:**
```json
{
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**
```json
{}
```

**Response (401 Unauthorized) si el token es inválido:**
```json
{
    "detail": "Token is invalid or expired"
}
```

**Ejemplo con curl:**
```bash
curl -X POST http://localhost:8000/api/token/verify/ \
  -H "Content-Type: application/json" \
  -d '{"token": "TU_ACCESS_TOKEN_AQUI"}'
```

---

## 🔑 Uso en Clientes

### JavaScript (Fetch API)

```javascript
// 1. Login
const loginResponse = await fetch('http://localhost:8000/api/token/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'usuario@ejemplo.com',
    password: 'contraseña123'
  })
});

const { access, refresh } = await loginResponse.json();

// 2. Usar token en requests
const apiResponse = await fetch('http://localhost:8000/api/v1/empresa/', {
  headers: {
    'Authorization': `Bearer ${access}`,
    'Content-Type': 'application/json'
  }
});

// 3. Refresh cuando expire
if (apiResponse.status === 401) {
  const refreshResponse = await fetch('http://localhost:8000/api/token/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh })
  });
  const { access: newAccess } = await refreshResponse.json();
  // Usar newAccess en siguientes requests
}
```

### Python (requests)

```python
import requests

# 1. Login
response = requests.post(
    'http://localhost:8000/api/token/',
    json={'username': 'usuario@ejemplo.com', 'password': 'contraseña123'}
)
tokens = response.json()
access_token = tokens['access']
refresh_token = tokens['refresh']

# 2. Usar token en requests
headers = {'Authorization': f'Bearer {access_token}'}
api_response = requests.get('http://localhost:8000/api/v1/empresa/', headers=headers)

# 3. Refresh cuando expire
if api_response.status_code == 401:
    refresh_response = requests.post(
        'http://localhost:8000/api/token/refresh/',
        json={'refresh': refresh_token}
    )
    new_access = refresh_response.json()['access']
    headers = {'Authorization': f'Bearer {new_access}'}
```

### cURL

```bash
# 1. Login
TOKEN=$(curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"usuario@ejemplo.com","password":"contraseña123"}' \
  | jq -r '.access')

# 2. Usar token
curl -X GET http://localhost:8000/api/v1/empresa/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔒 Seguridad

### Variables de Entorno (Producción)

```bash
# .env o variables de entorno
JWT_SECRET_KEY=tu-clave-secreta-super-segura-aqui
```

Si no se proporciona `JWT_SECRET_KEY`, se usa `SECRET_KEY` de Django como fallback.

### Rotación de Tokens

- `ROTATE_REFRESH_TOKENS=True`: Genera un nuevo refresh token en cada refresh
- `BLACKLIST_AFTER_ROTATION=True`: Invalida el refresh token anterior

**Nota:** Para usar blacklist, instala:
```bash
pip install djangorestframework-simplejwt[blacklist]
```

Y agrega `rest_framework_simplejwt.token_blacklist` a `INSTALLED_APPS`.

---

## 📊 Comparación con Otros Métodos

| Método | Estado | Escalabilidad | Uso Recomendado |
|--------|--------|---------------|-----------------|
| **JWT** | Stateless | ✅ Alta | APIs REST, móviles, integraciones |
| **Session** | Stateful | ⚠️ Media | Consola web, UI tradicional |
| **Token** | Stateless | ✅ Alta | Legacy, APIs simples |

---

## 🧪 Testing

### Ejemplo de Test

```python
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()

def test_api_with_jwt():
    # Crear usuario
    user = User.objects.create_user(
        email='test@example.com',
        password='test123'
    )
    
    # Obtener token
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    
    # Usar token en requests
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    
    response = client.get('/api/v1/empresa/')
    assert response.status_code == 200
```

---

## 📚 Referencias

- [djangorestframework-simplejwt](https://django-rest-framework-simplejwt.readthedocs.io/)
- [JWT.io](https://jwt.io/) - Debugger y documentación de JWT
- [DRF Authentication](https://www.django-rest-framework.org/api-guide/authentication/)

---

## ✅ Checklist de Implementación

- [x] Agregar `djangorestframework-simplejwt` a `requirements.txt`
- [x] Configurar `SIMPLE_JWT` en `settings.py`
- [x] Agregar `JWTAuthentication` a `DEFAULT_AUTHENTICATION_CLASSES`
- [x] Registrar endpoints JWT en `config/urls.py`
- [x] Documentar uso y ejemplos

---

## 🎯 Próximos Pasos (Opcional)

1. **Blacklist de tokens**: Instalar `[blacklist]` para invalidar tokens
2. **Custom claims**: Agregar información adicional al token (tenant_id, roles, etc.)
3. **Token por tenant**: Generar tokens específicos por tenant en multi-tenant
4. **Rate limiting por token**: Limitar requests por token JWT
