# 🔍 Auditoría de Flujo - Módulo Clientes (Backend) v2.60

## 📋 Resumen Ejecutivo

**Fecha de Auditoría:** 2026-01-XX  
**Última Actualización:** 2026-01-XX  
**Versión:** 2.60  
**Objetivo:** Documentar flujo completo, arquitectura, servicios y funcionalidad del módulo Clientes en el backend  
**Estado:** ✅ **DOCUMENTADO Y VALIDADO**

---


## 📁 Estructura del Módulo

```
apps/tenant/clientes/
├── __init__.py
├── admin.py                    # Configuración de Django Admin
├── apps.py                     # Configuración de la app Django
├── models.py                   # Modelo Cliente
├── services.py                 # Servicios de dominio (CRUD, queries)
├── services/
│   └── cliente_service.py     # Servicios adicionales (upsert, ventas)
├── api/
│   ├── __init__.py
│   ├── serializers.py         # ClienteListSerializer, ClienteDetailSerializer
│   ├── urls.py                # Router DRF
│   └── viewsets.py            # ClienteViewSet (CRUD completo)
├── migrations/
│   └── 0001_initial.py        # Migración inicial
└── tests/
    ├── test_clientes_api_and_service.py
    ├── test_clientes_crud_workspace.py
    └── test_auth_session_smoke.py
```

---

## 🏗️ Arquitectura

### Principios de Diseño

1. **API-First**: Endpoints RESTful para consumo desde Tabulator (Vanilla JS)
2. **SSoT (Single Source of Truth)**: Empresa se inyecta automáticamente desde el tenant
3. **Service Layer**: Lógica de negocio separada en `services.py`
4. **Optimización de Queries**: Uso de `.only()` y filtrado por empresa
5. **Transaccionalidad**: Uso de `@transaction.atomic` para integridad
6. **Validación de Duplicados**: Restricción única a nivel de base de datos

### Capas de la Aplicación

```
┌─────────────────────────────────────────────────────────┐
│  CAPA DE PRESENTACIÓN (ViewSet)                         │
│  - ClienteViewSet (CRUD completo)                        │
│  - Manejo de paginación                                  │
│  - Validación de permisos                                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  CAPA DE SERIALIZACIÓN (Serializers)                    │
│  - ClienteListSerializer (optimizado para listas)       │
│  - ClienteDetailSerializer (completo para CRUD)         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  CAPA DE SERVICIOS (Services)                           │
│  - qs_list() (queryset optimizado)                      │
│  - qs_detail() (obtener por ID)                         │
│  - crear_cliente() (con validación de duplicados)       │
│  - actualizar_cliente() (con validación de duplicados)  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  CAPA DE DATOS (Models)                                 │
│  - Cliente (modelo principal)                           │
│  - Restricciones únicas                                 │
│  - Índices para optimización                            │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Modelo Cliente

### Definición del Modelo

**Archivo:** `apps/tenant/clientes/models.py`

```python
class Cliente(models.Model):
    """
    Información legal y comercial de clientes (Microempresa Colombia).
    SSoT: apps.tenant.empresa
    """
    TIPO_PERSONA = [("NATURAL", "Persona natural"), ("JURIDICA", "Persona jurídica")]
    TIPO_DOCUMENTO = [("CC", "Cédula de ciudadanía"), ("CE", "Cédula de extranjería"), ("NIT", "NIT"), ("PA", "Pasaporte")]
    REGIMEN = [("SIMPLE", "Régimen Simple"), ("ORDINARIO", "Régimen Ordinario"), ("NO_RESP", "No responsable de IVA")]
    SEGMENTO = [("B2B", "B2B"), ("B2C", "B2C"), ("MIXTO", "Mixto")]

    # Identificación
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='clientes', help_text='SSoT')
    tipo_persona = models.CharField(max_length=10, choices=TIPO_PERSONA)
    tipo_documento = models.CharField(max_length=5, choices=TIPO_DOCUMENTO)
    numero_documento = models.CharField(max_length=32)
    razon_social = models.CharField(max_length=180)
    nombre_comercial = models.CharField(max_length=180, blank=True)

    # Tributario & Contacto
    regimen_tributario = models.CharField(max_length=15, choices=REGIMEN)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=32, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    ciudad = models.CharField(max_length=80, blank=True)
    
    # Comercial
    activo = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Campos del Modelo

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `empresa` | `ForeignKey(Empresa)` | ✅ | SSoT - Se inyecta automáticamente |
| `tipo_persona` | `CharField` | ✅ | NATURAL o JURIDICA |
| `tipo_documento` | `CharField` | ✅ | CC, CE, NIT, PA |
| `numero_documento` | `CharField(32)` | ✅ | Número del documento |
| `razon_social` | `CharField(180)` | ✅ | Razón social o nombre completo |
| `nombre_comercial` | `CharField(180)` | ❌ | Nombre comercial (opcional) |
| `regimen_tributario` | `CharField(15)` | ✅ | SIMPLE, ORDINARIO, NO_RESP |
| `email` | `EmailField` | ❌ | Email de contacto |
| `telefono` | `CharField(32)` | ❌ | Teléfono de contacto |
| `direccion` | `CharField(255)` | ❌ | Dirección |
| `ciudad` | `CharField(80)` | ❌ | Ciudad |
| `activo` | `BooleanField` | ❌ | Estado activo (default: True) |
| `observaciones` | `TextField` | ❌ | Observaciones adicionales |
| `created_at` | `DateTimeField` | Auto | Fecha de creación |
| `updated_at` | `DateTimeField` | Auto | Fecha de actualización |

### Restricciones y Validaciones

#### Restricción Única

```python
constraints = [
    models.UniqueConstraint(
        fields=["empresa", "tipo_documento", "numero_documento"], 
        name="uniq_doc_cliente_empresa"
    )
]
```

**Propósito:** Garantizar que no existan dos clientes con el mismo tipo y número de documento en la misma empresa.

**Validación:** Se valida a nivel de base de datos y se captura en `crear_cliente()` y `actualizar_cliente()`.

#### Índices

```python
indexes = [
    models.Index(fields=["empresa", "activo"]),  # Para filtrado por empresa y estado
    models.Index(fields=["numero_documento"]),   # Para búsqueda rápida por documento
]
```

**Propósito:** Optimizar consultas frecuentes.

### Ordenamiento por Defecto

```python
ordering = ["razon_social"]
```

**Propósito:** Ordenar clientes alfabéticamente por razón social.

---

## 🔄 Serializers

### ClienteListSerializer

**Archivo:** `apps/tenant/clientes/api/serializers.py` (líneas 4-28)

**Propósito:** Serializer optimizado para listas (Tabulator). Solo incluye campos necesarios para la tabla del frontend.

**Campos Expuestos:**

```python
fields = [
    'id', 
    'tipo_persona', 'tipo_persona_display',      # Display para UI
    'tipo_documento', 'tipo_documento_display',  # Display para UI
    'numero_documento', 
    'razon_social', 
    'nombre_comercial',
    'regimen_tributario', 'regimen_tributario_display',  # Display para UI
    'email', 
    'telefono',
    'ciudad',
    'activo'
]
```

**Campos de Solo Lectura:**

```python
read_only_fields = ['id', 'tipo_documento_display', 'tipo_persona_display', 'regimen_tributario_display']
```

**Campos Display (SerializerMethodField):**

- `tipo_documento_display`: Muestra el label del choice (ej: "Cédula de ciudadanía")
- `tipo_persona_display`: Muestra el label del choice (ej: "Persona natural")
- `regimen_tributario_display`: Muestra el label del choice (ej: "Régimen Ordinario")

### ClienteDetailSerializer

**Archivo:** `apps/tenant/clientes/api/serializers.py` (líneas 30-52)

**Propósito:** Serializer completo para detalle/edición de Clientes. Incluye todos los campos del modelo excepto empresa (SSoT) y timestamps.

**Campos Expuestos:**

```python
fields = [
    'id',
    'tipo_persona',
    'tipo_documento',
    'numero_documento',
    'razon_social',
    'nombre_comercial',
    'regimen_tributario',
    'email',
    'telefono',
    'direccion',
    'ciudad',
    'activo',
    'observaciones'
]
```

**Campos de Solo Lectura:**

```python
read_only_fields = ['id']
```

**Nota:** `empresa` no se expone porque se inyecta automáticamente desde el tenant (SSoT).

---

## 🔌 ViewSet y Endpoints

### ClienteViewSet

**Archivo:** `apps/tenant/clientes/api/viewsets.py`

**Herencia:**

```python
class ClienteViewSet(
    mixins.ListModelMixin,      # GET /api/v1/clientes/
    mixins.RetrieveModelMixin,  # GET /api/v1/clientes/{id}/
    mixins.CreateModelMixin,    # POST /api/v1/clientes/
    mixins.UpdateModelMixin,    # PUT/PATCH /api/v1/clientes/{id}/
    mixins.DestroyModelMixin,   # DELETE /api/v1/clientes/{id}/
    viewsets.GenericViewSet
):
```

### Endpoints Disponibles

| Método | Endpoint | Acción | Serializer | Descripción |
|--------|----------|--------|------------|-------------|
| `GET` | `/api/v1/clientes/` | `list()` | `ClienteListSerializer` | Lista paginada con búsqueda |
| `GET` | `/api/v1/clientes/{id}/` | `retrieve()` | `ClienteDetailSerializer` | Detalle de un cliente |
| `POST` | `/api/v1/clientes/` | `create()` | `ClienteDetailSerializer` | Crear nuevo cliente |
| `PUT` | `/api/v1/clientes/{id}/` | `update()` | `ClienteDetailSerializer` | Actualizar cliente completo |
| `PATCH` | `/api/v1/clientes/{id}/` | `partial_update()` | `ClienteDetailSerializer` | Actualizar cliente parcial |
| `DELETE` | `/api/v1/clientes/{id}/` | `destroy()` | N/A | Eliminar cliente (solo si inactivo) |

### Paginación

**Clase:** `StandardResultsSetPagination`

```python
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10  # Default: 10 (estándar SaaS)
    page_size_query_param = 'page_size'
    max_page_size = 100
```

**Formato de Respuesta:**

```json
{
  "count": 150,
  "next": "http://example.com/api/v1/clientes/?page=2",
  "previous": null,
  "results": [...]
}
```

### Métodos del ViewSet

#### `get_empresa()`

**Líneas:** 51-63

**Propósito:** Obtiene la empresa del tenant actual (SSoT).

```python
def get_empresa(self):
    empresa = Empresa.objects.only('id').first()
    if not empresa:
        from rest_framework.exceptions import APIException
        raise APIException(detail='No se encontró empresa para este tenant')
    return empresa
```

**Optimización:** Usa `.only('id')` para reducir carga.

#### `list()`

**Líneas:** 65-100

**Propósito:** Endpoint para Tabulator (GET /api/v1/clientes/).

**Parámetros de Consulta:**
- `search`: Búsqueda en `razon_social`, `numero_documento`, `email`, `nombre_comercial`
- `page`: Número de página
- `page_size`: Tamaño de página (máx 100)

**Flujo:**

```python
def list(self, request):
    empresa = self.get_empresa()
    search = request.query_params.get('search', '').strip()
    
    queryset = qs_list(empresa.id, search if search else None)
    
    # Paginación DRF estándar
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = ClienteListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    # Fallback: sin paginación
    serializer = ClienteListSerializer(queryset, many=True)
    return Response(serializer.data)
```

#### `get_object()`

**Líneas:** 102-110

**Propósito:** Obtiene el objeto Cliente para retrieve/update/partial_update.

```python
def get_object(self):
    empresa = self.get_empresa()
    pk = self.kwargs.get('pk')
    cliente = qs_detail(empresa.id, pk)
    if not cliente:
        from rest_framework.exceptions import NotFound
        raise NotFound('Cliente no encontrado')
    return cliente
```

**Validación:** Filtra por empresa (SSoT) para garantizar aislamiento de datos.

#### `retrieve()`

**Líneas:** 112-116

**Propósito:** Obtiene detalle de un cliente.

```python
def retrieve(self, request, *args, **kwargs):
    cliente = self.get_object()
    serializer = ClienteDetailSerializer(cliente)
    return Response(serializer.data)
```

#### `create()`

**Líneas:** 118-136

**Propósito:** Crea un nuevo cliente.

**Flujo:**

```python
def create(self, request, *args, **kwargs):
    empresa = self.get_empresa()
    serializer = ClienteDetailSerializer(data=request.data)
    if serializer.is_valid():
        # crear_cliente puede lanzar ValidationError si hay duplicados
        cliente = crear_cliente(empresa, serializer.validated_data)
        return Response(
            ClienteDetailSerializer(cliente).data, 
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

**Manejo de Errores:**
- `ValidationError` del servicio (duplicados) se convierte automáticamente en HTTP 400
- DRF maneja automáticamente `ValidationError` a través de `exception_handler`

#### `update()`

**Líneas:** 138-151

**Propósito:** Actualiza un cliente (PUT completo).

```python
def update(self, request, *args, **kwargs):
    cliente = self.get_object()
    serializer = ClienteDetailSerializer(cliente, data=request.data, partial=False)
    if serializer.is_valid():
        cliente = actualizar_cliente(cliente, serializer.validated_data)
        return Response(ClienteDetailSerializer(cliente).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

#### `partial_update()`

**Líneas:** 153-166

**Propósito:** Actualiza un cliente parcialmente (PATCH).

```python
def partial_update(self, request, *args, **kwargs):
    cliente = self.get_object()
    serializer = ClienteDetailSerializer(cliente, data=request.data, partial=True)
    if serializer.is_valid():
        cliente = actualizar_cliente(cliente, serializer.validated_data)
        return Response(ClienteDetailSerializer(cliente).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

#### `destroy()`

**Líneas:** 168-193

**Propósito:** Elimina un cliente (solo si está inactivo).

**⚠️ REGLA DE SEGURIDAD DE ELIMINACIÓN:**

- No se puede eliminar un cliente activo.
- El cliente debe estar inactivo (`activo=False`) antes de poder eliminarlo.
- Eliminación física (hard delete) solo si está inactivo.

**Flujo:**

```python
def destroy(self, request, *args, **kwargs):
    cliente = self.get_object()
    
    # Validar que el cliente no esté activo
    if cliente.activo:
        return Response(
            {
                "error": "active_record",
                "message": "No se puede eliminar un ítem activo. Cámbielo a 'Inactivo' en el formulario de edición antes de intentar borrarlo."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # ⚠️ HARD DELETE: Eliminación física solo si está inactivo
    cliente.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
```

---

## 🔧 Servicios de Dominio

### qs_list()

**Archivo:** `apps/tenant/clientes/services.py` (líneas 16-56)

**Propósito:** Retorna listado optimizado para Tabulator (Zero Waste).

**⚠️ PERFORMANCE BIBLE:**
- PROHIBIDO `objects.all()`: Siempre filtrar por `empresa_id` (SSoT)
- PROHIBIDO `SELECT *`: Solo campos que usa `ClienteListSerializer`
- Campos display (`get_*_display`) son métodos Python, no necesitan estar en `.only()`

**Código:**

```python
def qs_list(empresa_id, search=None):
    # ⚠️ CRÍTICO: Siempre filtrar por empresa (SSoT) - PROHIBIDO .all()
    qs = Cliente.objects.filter(empresa_id=empresa_id).only(
        'id', 
        'tipo_persona',  # Para get_tipo_persona_display()
        'tipo_documento',  # Para get_tipo_documento_display()
        'numero_documento', 
        'razon_social', 
        'nombre_comercial',
        'regimen_tributario',  # Para get_regimen_tributario_display()
        'email', 
        'telefono',
        'ciudad',
        'activo'
    ).order_by('razon_social')
    
    if search:
        qs = qs.filter(
            Q(razon_social__icontains=search) | 
            Q(numero_documento__icontains=search) |
            Q(email__icontains=search) |
            Q(nombre_comercial__icontains=search)
        )
    
    return qs
```

**Búsqueda:** Busca en `razon_social`, `numero_documento`, `email`, `nombre_comercial` (case-insensitive).

### qs_detail()

**Archivo:** `apps/tenant/clientes/services.py` (líneas 59-75)

**Propósito:** Retorna detalle completo para edición (Zero Waste).

**⚠️ PERFORMANCE BIBLE:**
- Siempre filtrar por `empresa_id` (SSoT)
- No usa `select_related()` porque `ClienteDetailSerializer` no accede a relaciones

**Código:**

```python
def qs_detail(empresa_id, pk):
    # ⚠️ CRÍTICO: Siempre filtrar por empresa (SSoT) - PROHIBIDO .all()
    return Cliente.objects.filter(empresa_id=empresa_id, pk=pk).first()
```

### crear_cliente()

**Archivo:** `apps/tenant/clientes/services.py` (líneas 78-106)

**Propósito:** Crea un cliente asignando la empresa SSoT automáticamente.

**Decorador:** `@transaction.atomic`

**Validación de Duplicados:**

```python
@transaction.atomic
def crear_cliente(empresa, data):
    try:
        return Cliente.objects.create(empresa=empresa, **data)
    except IntegrityError as e:
        # ⚠️ CRÍTICO: Capturar IntegrityError de restricción única
        # La restricción uniq_doc_cliente_empresa valida: empresa + tipo_documento + numero_documento
        error_msg = str(e)
        if 'uniq_doc_cliente_empresa' in error_msg or 'UNIQUE constraint' in error_msg:
            raise ValidationError({
                'numero_documento': [
                    'Ya existe un cliente registrado con este tipo y número de documento en esta empresa.'
                ]
            })
        # Re-lanzar otros IntegrityError sin modificar
        raise
```

**Manejo de Errores:**
- Captura `IntegrityError` de restricción única
- Convierte a `ValidationError` con mensaje amigable
- Re-lanza otros `IntegrityError` sin modificar

### actualizar_cliente()

**Archivo:** `apps/tenant/clientes/services.py` (líneas 109-140)

**Propósito:** Actualiza datos del cliente.

**Decorador:** `@transaction.atomic`

**Validación de Duplicados:**

```python
@transaction.atomic
def actualizar_cliente(cliente, data):
    try:
        for key, value in data.items():
            setattr(cliente, key, value)
        cliente.save()
        return cliente
    except IntegrityError as e:
        # ⚠️ CRÍTICO: Capturar IntegrityError de restricción única
        error_msg = str(e)
        if 'uniq_doc_cliente_empresa' in error_msg or 'UNIQUE constraint' in error_msg:
            raise ValidationError({
                'numero_documento': [
                    'Ya existe un cliente registrado con este tipo y número de documento en esta empresa.'
                ]
            })
        # Re-lanzar otros IntegrityError sin modificar
        raise
```

**Manejo de Errores:**
- Similar a `crear_cliente()`
- Captura `IntegrityError` y convierte a `ValidationError`

---

## 🔗 URLs y Routing

### Router DRF

**Archivo:** `apps/tenant/clientes/api/urls.py`

```python
router = DefaultRouter()
# ⚠️ CRÍTICO: Registrar con prefijo vacío porque el path 'clientes/' ya está en config/api_urls.py
# Esto genera rutas: /api/v1/clientes/ (list, create), /api/v1/clientes/{id}/ (retrieve, update, partial_update)
# El basename debe ser 'cliente' (singular) para que DRF genere los nombres correctos
router.register(r"", ClienteViewSet, basename="cliente")

urlpatterns = router.urls
```

### Rutas Generadas

| Nombre | URL | Método | Acción |
|--------|-----|--------|--------|
| `cliente-list` | `/api/v1/clientes/` | GET | `list()` |
| `cliente-list` | `/api/v1/clientes/` | POST | `create()` |
| `cliente-detail` | `/api/v1/clientes/{id}/` | GET | `retrieve()` |
| `cliente-detail` | `/api/v1/clientes/{id}/` | PUT | `update()` |
| `cliente-detail` | `/api/v1/clientes/{id}/` | PATCH | `partial_update()` |
| `cliente-detail` | `/api/v1/clientes/{id}/` | DELETE | `destroy()` |

---

## 🔄 Flujo Completo de Operaciones

### CREATE (Crear Cliente)

```
1. Frontend: POST /api/v1/clientes/ con payload JSON
   ↓
2. ClienteViewSet.create() recibe request
   ↓
3. get_empresa() obtiene empresa del tenant (SSoT)
   ↓
4. ClienteDetailSerializer valida datos
   ├── Si inválido → HTTP 400 con errores
   └── Si válido → Continúa
   ↓
5. crear_cliente(empresa, validated_data) se ejecuta
   ├── @transaction.atomic inicia transacción
   ├── Cliente.objects.create(empresa=empresa, **data)
   ├── Si IntegrityError (duplicado):
   │   └── Captura y convierte a ValidationError
   └── Si éxito → Cliente creado
   ↓
6. ClienteDetailSerializer serializa cliente creado
   ↓
7. HTTP 201 Created con datos del cliente
```

### READ (Listar Clientes)

```
1. Frontend: GET /api/v1/clientes/?page=1&page_size=10&search=...
   ↓
2. ClienteViewSet.list() recibe request
   ↓
3. get_empresa() obtiene empresa del tenant (SSoT)
   ↓
4. Extrae parámetros de consulta:
   ├── search (opcional)
   ├── page (opcional, default: 1)
   └── page_size (opcional, default: 10, máx: 100)
   ↓
5. qs_list(empresa.id, search) se ejecuta
   ├── Filtra por empresa_id (SSoT)
   ├── Usa .only() para optimizar
   ├── Aplica búsqueda si existe
   └── Ordena por razon_social
   ↓
6. StandardResultsSetPagination pagina queryset
   ↓
7. ClienteListSerializer serializa página
   ↓
8. HTTP 200 OK con {count, next, previous, results: [...]}
```

### READ (Detalle de Cliente)

```
1. Frontend: GET /api/v1/clientes/{id}/
   ↓
2. ClienteViewSet.retrieve() recibe request
   ↓
3. get_object() se ejecuta
   ├── get_empresa() obtiene empresa (SSoT)
   ├── qs_detail(empresa.id, pk) busca cliente
   └── Si no existe → HTTP 404 Not Found
   ↓
4. ClienteDetailSerializer serializa cliente
   ↓
5. HTTP 200 OK con datos completos del cliente
```

### UPDATE (Actualizar Cliente)

```
1. Frontend: PATCH /api/v1/clientes/{id}/ con payload JSON
   ↓
2. ClienteViewSet.partial_update() recibe request
   ↓
3. get_object() obtiene cliente (filtrado por empresa)
   ↓
4. ClienteDetailSerializer valida datos (partial=True)
   ├── Si inválido → HTTP 400 con errores
   └── Si válido → Continúa
   ↓
5. actualizar_cliente(cliente, validated_data) se ejecuta
   ├── @transaction.atomic inicia transacción
   ├── setattr() actualiza campos
   ├── cliente.save()
   ├── Si IntegrityError (duplicado):
   │   └── Captura y convierte a ValidationError
   └── Si éxito → Cliente actualizado
   ↓
6. ClienteDetailSerializer serializa cliente actualizado
   ↓
7. HTTP 200 OK con datos actualizados
```

### DELETE (Eliminar Cliente)

```
1. Frontend: DELETE /api/v1/clientes/{id}/
   ↓
2. ClienteViewSet.destroy() recibe request
   ↓
3. get_object() obtiene cliente (filtrado por empresa)
   ↓
4. Validación de seguridad:
   ├── Si cliente.activo == True:
   │   └── HTTP 400 Bad Request con mensaje
   └── Si cliente.activo == False:
       └── Continúa
   ↓
5. cliente.delete() (hard delete)
   ↓
6. HTTP 204 No Content
```

---

## 🛡️ Validaciones y Reglas de Negocio

### Validación de Duplicados

**Restricción Única:** `uniq_doc_cliente_empresa`

**Campos:** `empresa` + `tipo_documento` + `numero_documento`

**Validación:**
- A nivel de base de datos (constraint)
- Capturada en `crear_cliente()` y `actualizar_cliente()`
- Convertida a `ValidationError` con mensaje amigable

**Mensaje de Error:**

```json
{
  "numero_documento": [
    "Ya existe un cliente registrado con este tipo y número de documento en esta empresa."
  ]
}
```

### Validación de Eliminación

**Regla:** No se puede eliminar un cliente activo.

**Validación:**
- En `destroy()` del ViewSet
- En frontend (botón deshabilitado si `activo === true`)

**Mensaje de Error:**

```json
{
  "error": "active_record",
  "message": "No se puede eliminar un ítem activo. Cámbielo a 'Inactivo' en el formulario de edición antes de intentar borrarlo."
}
```

### Validación de Campos Requeridos

**Campos Obligatorios:**
- `tipo_persona`
- `tipo_documento`
- `numero_documento`
- `razon_social`
- `regimen_tributario`

**Validación:**
- A nivel de modelo (sin `blank=True`)
- A nivel de serializer (sin `required=False`)
- A nivel de frontend (atributo HTML `required`)

### SSoT (Single Source of Truth)

**Empresa:** Se inyecta automáticamente desde el tenant.

**Implementación:**
- `get_empresa()` obtiene empresa del tenant
- Todos los servicios filtran por `empresa_id`
- No se expone `empresa` en serializers (read-only implícito)

---

## 🔍 Optimizaciones de Performance

### Queries Optimizadas

**qs_list():**
- Usa `.only()` para cargar solo campos necesarios
- Filtra por `empresa_id` (SSoT)
- Índices en `empresa + activo` y `numero_documento`

**qs_detail():**
- Filtra por `empresa_id` (SSoT)
- No usa `select_related()` (no hay relaciones accedidas)

### Índices de Base de Datos

```python
indexes = [
    models.Index(fields=["empresa", "activo"]),  # Para filtrado por empresa y estado
    models.Index(fields=["numero_documento"]),   # Para búsqueda rápida por documento
]
```

### Paginación

- Default: 10 registros por página
- Máximo: 100 registros por página
- Reduce carga de memoria y tiempo de respuesta

---

## 🔗 Integración con Frontend

### Mapeo Frontend ↔ Backend

| Frontend (JS) | Backend (Python) | Endpoint |
|---------------|------------------|----------|
| `w.clientesAPI.list(params)` | `ClienteViewSet.list()` | `GET /api/v1/clientes/` |
| `w.clientesAPI.get(id)` | `ClienteViewSet.retrieve()` | `GET /api/v1/clientes/{id}/` |
| `w.clientesAPI.create(payload)` | `ClienteViewSet.create()` | `POST /api/v1/clientes/` |
| `w.clientesAPI.update(id, payload)` | `ClienteViewSet.partial_update()` | `PATCH /api/v1/clientes/{id}/` |
| `w.clientesAPI.delete(id)` | `ClienteViewSet.destroy()` | `DELETE /api/v1/clientes/{id}/` |

### Formato de Payload

**Crear/Actualizar:**

```json
{
  "tipo_persona": "JURIDICA",
  "tipo_documento": "NIT",
  "numero_documento": "900123456-1",
  "razon_social": "Empresa Ejemplo S.A.S.",
  "nombre_comercial": "Ejemplo",
  "regimen_tributario": "ORDINARIO",
  "email": "contacto@ejemplo.com",
  "telefono": "+57 300 123 4567",
  "direccion": "Calle 123 #45-67",
  "ciudad": "Bogotá",
  "activo": true,
  "observaciones": "Cliente preferencial"
}
```

**Nota:** `empresa` no se envía desde el frontend; se inyecta automáticamente en el backend.

---

## 🧪 Testing

### Archivos de Pruebas

1. **test_clientes_api_and_service.py**: Pruebas de API y servicios
2. **test_clientes_crud_workspace.py**: Pruebas de CRUD desde workspace
3. **test_auth_session_smoke.py**: Pruebas de autenticación y sesión

### Cobertura de Pruebas

- ✅ Crear cliente
- ✅ Actualizar cliente
- ✅ Eliminar cliente (solo si inactivo)
- ✅ Validación de duplicados
- ✅ Búsqueda y paginación
- ✅ Filtrado por empresa (SSoT)

---

## 📊 Django Admin

### ClienteAdmin

**Archivo:** `apps/tenant/clientes/admin.py`

**Configuración:**

```python
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "numero_documento", "tipo_persona", "tipo_documento", "regimen_tributario", "activo")
    search_fields = ("razon_social", "numero_documento", "nombre_comercial", "email", "telefono")
    list_filter = ("tipo_persona", "tipo_documento", "regimen_tributario", "activo", "ciudad", "empresa")
    readonly_fields = ("created_at", "updated_at")
    
    fieldsets = (
        ("Identificación", {...}),
        ("Información Tributaria", {...}),
        ("Contacto", {...}),
        ("Estado y Observaciones", {...}),
        ("Auditoría", {...}),
    )
    
    ordering = ["razon_social"]
```

**Características:**
- Búsqueda en múltiples campos
- Filtros por tipo, régimen, estado, ciudad, empresa
- Campos de solo lectura para timestamps
- Fieldsets organizados por categorías

---

## 🔄 Servicios Adicionales

### cliente_service.py

**Archivo:** `apps/tenant/clientes/services/cliente_service.py`

**Funciones:**

#### `upsert_cliente(data: dict) -> Cliente`

**Propósito:** Crea/actualiza cliente por `(tipo_documento, numero_documento)`.

```python
@transaction.atomic
def upsert_cliente(data: dict) -> Cliente:
    lookup = {
        "tipo_documento": data["tipo_documento"],
        "numero_documento": data["numero_documento"]
    }
    obj, _ = Cliente.objects.update_or_create(defaults=data, **lookup)
    return obj
```

**Uso:** Para importación masiva o sincronización de datos.

#### `registrar_venta_cliente(cliente_id: int, factura_id: int) -> VentaCliente`

**Propósito:** Registra la asociación Cliente–Factura (venta). Idempotente por `unique_together`.

```python
@transaction.atomic
def registrar_venta_cliente(cliente_id: int, factura_id: int) -> VentaCliente:
    obj, _ = VentaCliente.objects.get_or_create(cliente_id=cliente_id, factura_id=factura_id)
    return obj
```

**Nota:** Requiere modelo `VentaCliente` (no presente en el código actual).

---

## ✅ Checklist de Validación

### Modelo

- [ ] Restricción única `uniq_doc_cliente_empresa` funciona correctamente
- [ ] Índices están creados y optimizan consultas
- [ ] Ordenamiento por defecto es `razon_social`
- [ ] Campo `empresa` es ForeignKey con `PROTECT`

### Serializers

- [ ] `ClienteListSerializer` solo expone campos necesarios
- [ ] `ClienteDetailSerializer` expone todos los campos editables
- [ ] Campos display funcionan correctamente
- [ ] `empresa` no se expone (SSoT)

### ViewSet

- [ ] Todos los endpoints CRUD funcionan
- [ ] Paginación funciona correctamente
- [ ] Búsqueda funciona con parámetro `search`
- [ ] `get_empresa()` obtiene empresa correctamente
- [ ] Validación de eliminación funciona (solo inactivos)

### Services

- [ ] `qs_list()` filtra por empresa (SSoT)
- [ ] `qs_list()` usa `.only()` para optimizar
- [ ] `qs_detail()` filtra por empresa (SSoT)
- [ ] `crear_cliente()` captura IntegrityError y convierte a ValidationError
- [ ] `actualizar_cliente()` captura IntegrityError y convierte a ValidationError
- [ ] Transacciones funcionan correctamente

### URLs

- [ ] Router genera todas las rutas correctamente
- [ ] Basename es 'cliente' (singular)
- [ ] Prefijo 'clientes/' está en config/api_urls.py

### Integración

- [ ] Frontend puede crear clientes
- [ ] Frontend puede listar clientes con paginación
- [ ] Frontend puede buscar clientes
- [ ] Frontend puede editar clientes
- [ ] Frontend puede eliminar clientes (solo inactivos)
- [ ] Errores de validación se muestran correctamente

---

## 📚 Referencias

### Archivos Relacionados

- `apps/tenant/clientes/models.py` - Modelo Cliente
- `apps/tenant/clientes/api/serializers.py` - Serializers DRF
- `apps/tenant/clientes/api/viewsets.py` - ViewSet CRUD
- `apps/tenant/clientes/services.py` - Servicios de dominio
- `apps/tenant/clientes/api/urls.py` - Router DRF
- `apps/tenant/clientes/admin.py` - Configuración Django Admin

### Documentación Frontend

- `apps/tenant/core/static/core/js/clientes/AUDITORIA_FLUJO.md` - Documentación frontend
- `apps/tenant/core/templates/tenant/core/partials/clientes/FLUJO_ARCHIVOS_TEMPLATES.md` - Documentación templates

### Documentación Externa

- Django REST Framework: https://www.django-rest-framework.org/
- Django Models: https://docs.djangoproject.com/en/stable/topics/db/models/
- Django Transactions: https://docs.djangoproject.com/en/stable/topics/db/transactions/

---

## 🔄 Historial de Cambios

### v2.60 (2026-01-XX)

- ✅ Documentación completa de flujo y funcionalidad
- ✅ Validación de eliminación mejorada (solo inactivos)
- ✅ Optimizaciones de queries documentadas

### v2.40 (2024-XX-XX)

- ✅ Migración a API-First Architecture
- ✅ Implementación de Tabulator support
- ✅ Separación de Service Layer
- ✅ Optimización de queries con `.only()`
- ✅ Validación de duplicados mejorada

---

**Fin del Documento**
