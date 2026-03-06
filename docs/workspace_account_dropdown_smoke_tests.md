# Pruebas de Humo - Dropdown de Cuenta en Navbar

## ✅ Verificaciones Manuales

### 1. Dropdown de Cuenta en Navbar
**Ubicación:** `apps/tenant/core/templates/tenant/partials/_header.html`

**Verificaciones:**
- [ ] Abrir `http://cliente.sintel.com:8000/workspace/` (autenticado)
- [ ] Verificar que en el navbar superior derecho hay un botón con el nombre del usuario (o email) + icono de caret (▼)
- [ ] Hacer click en el botón → se abre un dropdown con:
  - [ ] "👤 Perfil" (enlace)
  - [ ] "Cerrar Sesión" (botón)

### 2. Perfil Eliminado del Sidebar
**Ubicación:** `apps/tenant/core/templates/tenant/core/workspace.html`

**Verificaciones:**
- [ ] Abrir `http://cliente.sintel.com:8000/workspace/`
- [ ] Verificar que en el sidebar izquierdo NO aparece "👤 Perfil"
- [ ] Verificar que el sidebar solo contiene:
  - [ ] 🏢 Empresa
  - [ ] 🧾 Facturas
  - [ ] 📚 Contabilidad
  - [ ] ⋯ Más

### 3. Navegación a Perfil desde Dropdown
**Verificaciones:**
- [ ] Hacer click en el dropdown de cuenta
- [ ] Hacer click en "👤 Perfil"
- [ ] Verificar que:
  - [ ] La URL cambia a `http://cliente.sintel.com:8000/workspace/#perfil`
  - [ ] Se muestra la sección de Perfil (formulario con campos: nombre, email, cargo, etc.)
  - [ ] El dropdown se cierra automáticamente

### 4. Hash-Routing Funcional
**Verificaciones:**
- [ ] Navegar directamente a `http://cliente.sintel.com:8000/workspace/#perfil`
- [ ] Verificar que se carga la sección de Perfil
- [ ] Navegar a `http://cliente.sintel.com:8000/workspace/#empresa`
- [ ] Verificar que se carga la sección de Empresa
- [ ] Usar los botones del navegador (atrás/adelante) → el hash cambia y la vista se actualiza

### 5. Logout API-First
**Verificaciones:**
- [ ] Abrir DevTools → Network tab
- [ ] Hacer click en "Cerrar Sesión" del dropdown
- [ ] Verificar en Network:
  - [ ] Se hace un `POST /api/v1/core/auth/logout/`
  - [ ] Headers incluyen:
    - [ ] `Content-Type: application/json`
    - [ ] `X-CSRFToken: <token>`
  - [ ] Response es `200 OK` con JSON:
    ```json
    {
      "detail": "Sesión finalizada.",
      "redirect_url": "/login/"
    }
    ```
- [ ] Verificar que el navegador redirige a `/login/`

### 6. JavaScript del Dropdown
**Verificaciones:**
- [ ] Abrir DevTools → Console
- [ ] Hacer click en el dropdown → no debe haber errores en consola
- [ ] Hacer click fuera del dropdown → el dropdown se cierra
- [ ] Verificar que el código JavaScript incluye:
  - [ ] `account-dropdown-toggle`
  - [ ] `account-dropdown-menu`
  - [ ] `account-menu-perfil`
  - [ ] `account-menu-logout`

### 7. Estilos CSS
**Verificaciones:**
- [ ] El dropdown tiene sombra y bordes redondeados
- [ ] Los items del dropdown tienen hover (fondo gris claro)
- [ ] El botón toggle tiene hover (fondo gris oscuro)
- [ ] El dropdown está posicionado correctamente (debajo del botón, alineado a la derecha)

## 🔍 Verificaciones Técnicas (Inspección de Código)

### Elementos HTML Requeridos

**En `_header.html`:**
```html
<div id="account-dropdown-container">
  <button id="account-dropdown-toggle">...</button>
  <div id="account-dropdown-menu" class="hidden">...</div>
</div>
```

**En `workspace.html`:**
- Sidebar NO debe contener: `<a href="#perfil" data-view="perfil">`
- JavaScript debe contener: `account-dropdown-toggle`, `account-dropdown-menu`, `account-menu-perfil`, `account-menu-logout`

### JavaScript Requerido

**Funcionalidades:**
1. Toggle del dropdown (abrir/cerrar)
2. Cerrar al hacer click fuera
3. Navegación a `#perfil` desde el dropdown
4. Logout con `POST /api/v1/core/auth/logout/` (CSRF + JSON)

## 📝 Checklist de Implementación

- [x] Dropdown agregado en `_header.html`
- [x] Perfil eliminado del sidebar en `workspace.html`
- [x] JavaScript del dropdown implementado en `workspace.html`
- [x] Estilos CSS para el dropdown en `workspace.html`
- [x] Logout API-First con CSRF
- [x] Hash-routing mantenido para todas las vistas

## 🐛 Problemas Conocidos

Ninguno reportado.

## 📚 Referencias

- **Archivos modificados:**
  - `apps/tenant/core/templates/tenant/partials/_header.html`
  - `apps/tenant/core/templates/tenant/core/workspace.html`
- **Endpoints consumidos:**
  - `POST /api/v1/core/auth/logout/` (logout API-First)
