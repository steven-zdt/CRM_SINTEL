# 📦 Documentación Módulo Clientes (v3.5.0)

**Última Actualización:** 2026-05-11  
**Versión:** 3.5.0 (Backend/API) + v2.61+ (Frontend/UX)  
**Status:** ✅ PRODUCTION READY (Blocker issues CORREGIDOS)

---

## 🚀 Inicio Rápido

| Necesitas... | Ve a... |
|---|---|
| 📋 **Estado actual de la app** | [ESTADO_ACTUAL_v350.md](ESTADO_ACTUAL_v350.md) ⭐ |
| 🔒 **Cómo funciona la seguridad (DSV)** | [GARANTIA_SEGURIDAD_DSV.md](GARANTIA_SEGURIDAD_DSV.md) |
| 🏗️ **Arquitectura completa del módulo** | [AUDITORIA_FLUJO_CLIENTES.md](AUDITORIA_FLUJO_CLIENTES.md) |
| 🗺️ **Diagramas de flujo (Mermaid)** | [docs/clientes_flow_map.md](docs/clientes_flow_map.md) |
| 🧠 **Reglas de negocio y validaciones** | [docs/clientes_business_logic.md](docs/clientes_business_logic.md) |
| 📂 **Microtareas y responsabilidades** | [docs/clientes_microtasks_architecture.md](docs/clientes_microtasks_architecture.md) |

---

## ✅ Últimos Cambios (Sprint Actual - v3.5.0)

### 🎯 Blocker Issues CORREGIDOS

#### 1. ✨ UUID Lookup Field (AGENTS.md §14)
- ✅ Modelo `Cliente.uuid` UUIDField(unique=True)
- ✅ Modelo `ContactoCliente.uuid` UUIDField(unique=True)
- ✅ Migración: `0002_add_uuid_fields.py` (población segura)
- ✅ ViewSets: Hereda `lookup_field="uuid"` de BaseTenantViewSet

#### 2. 🔒 Service Layer Verificado
- ✅ ClienteServiceMixin + ContactoClienteServiceMixin
- ✅ Selectors + CRUD + Business service modulares
- ✅ `services/__init__.py` reexportaciones correctas
- ✅ DSV (Double Semantic Verification) integrado

#### 3. 👁️ Namespace JavaScript Documentado
- ✅ `window.Sintel.Clientes` (correcto y consistente)
- ✅ Sin colisión de namespaces

**Documentación detallada:** [ESTADO_ACTUAL_v350.md](ESTADO_ACTUAL_v350.md)

---

## 🛠️ Stack Tecnológico

```
Backend
├─ Django DRF (REST API)
├─ django-tenants (Multi-tenant PostgreSQL)
└─ Service Layer (selectors + crud + business)

Frontend
├─ Vanilla JS ES6+ (Namespace: window.Sintel.Clientes)
├─ Tabulator.js (Grid/tabla)
├─ Bootstrap 5.3.2 (UI)
├─ HTMX (Server-driven fragments)
└─ HTMX-OOB (Out-of-Band updates)

Storage
├─ PostgreSQL (Datos por empresa)
└─ SintelTenantBaseModel (empresa_id obligatorio)
```

---

## 📊 Estructura de Datos

### Modelo Principal: Cliente

**Campos Lookup & Identificación:**
- `uuid`: UUIDField, unique=True (NUEVO - AGENTS.md §14) ⭐
- `tipo_documento`, `numero_documento`: SSoT de identificación
- Único por empresa: (empresa, tipo_documento, numero_documento)

**Campos de Contexto:**
- `razon_social`: Nombre legal
- `nombre_comercial`: (opcional)
- `regimen_tributario`: SIMPLE | ORDINARIO | NO_RESP

**Campos Comerciales:**
- `email`, `telefono`: Contacto directo
- `direccion`, `ciudad`: Ubicación

**Auditoría:**
- `empresa`: FK (SSoT, immutable)
- `created_at`, `updated_at`: Timestamps
- `activo`: Flag de estado

### Modelo ContactoCliente

**Campos Lookup:**
- `uuid`: UUIDField, unique=True (NUEVO) ⭐

**Campos de Relación:**
- `cliente`: FK a Cliente (CASCADE)

**Campos de Contacto:**
- `nombre_completo`, `cargo`, `email`, `telefono`
- `is_principal`: Marca contacto principal
- `activo`: Estado

---

## 🔒 Garantía de Seguridad (AGENTS.md §13)

### Validación en 7 Capas

```
1. Frontend (UI)
   └─ Formulario HTMX sin editores inline

2. Network (HTTP)
   └─ POST/PATCH con campos permitidos

3. ViewSet (Enrutamiento)
   └─ IsTenantMember + resolve_tenant_empresa()

4. BusinessService (Lógica)
   └─ DSV (Double Semantic Verification)

5. Serializer (Validación de tipos)
   └─ ClienteDetailSerializer

6. ORM (Modelo)
   └─ SintelTenantBaseModel + constraints

7. Database (Integridad)
   └─ UNIQUE + FK PROTECT
```

---

## 📁 Rutas Principales (AGENTS.md §6)

**API Endpoints:**
- `GET /api/v1/clientes/` - Listar
- `POST /api/v1/clientes/` - Crear
- `PATCH /api/v1/clientes/{uuid}/` - Editar
- `DELETE /api/v1/clientes/{uuid}/` - Eliminar

**API Contactos:**
- `GET /api/v1/contactos/` - Listar contactos
- `POST /api/v1/clientes/{cliente_uuid}/contactos/` - Crear contacto

---

## 🧪 Testing

### Test Básico (UI)
1. Abre Gestión de Clientes
2. Click "Nuevo Cliente"
3. Completa: tipo_documento, numero_documento, razon_social
4. Click "Guardar" → Cliente creado ✅
5. Grid se actualiza automáticamente ✅

### Test Seguridad (API)
```bash
# Válido (usuario pertenece a empresa_id)
curl -X POST /api/v1/clientes/ \
  -H "Authorization: Bearer {token}" \
  -d '{"tipo_documento": "NIT", "numero_documento": "123", ...}'
→ 201 Created ✅

# Inválido (empresa_id mismatch - DSV falla)
curl -X POST /api/v1/clientes/ \
  -H "Authorization: Bearer {token}" \
  -d '{"empresa_id": 999, ...}'
→ 403 Forbidden ❌
```

---

## ❓ Preguntas Frecuentes

**P: ¿Cómo se previenen ataques IDOR?**  
R: Triple validación: IsTenantMember, DSV en BusinessService, SintelTenantBaseModel.

**P: ¿Por qué UUID en lugar de PK secuencial?**  
R: AGENTS.md §14 - evita enumeration attacks.

**P: ¿Se puede mover un cliente a otra empresa?**  
R: No, `empresa` es FK con PROTECT - es el contexto SSoT del cliente.

**P: ¿Cómo se eliminan clientes?**  
R: DELETE valida con DSV. Los contactos se eliminan en cascada (CASCADE).

---

## 🤝 Contribución

Para cambios en este módulo:
1. Lee [ESTADO_ACTUAL_v350.md](ESTADO_ACTUAL_v350.md)
2. Revisa [GARANTIA_SEGURIDAD_DSV.md](GARANTIA_SEGURIDAD_DSV.md)
3. Consulta [docs/clientes_business_logic.md](docs/clientes_business_logic.md)

---

**Last Updated:** 2026-05-11  
**Status:** ✅ **V3.5.0 READY**
