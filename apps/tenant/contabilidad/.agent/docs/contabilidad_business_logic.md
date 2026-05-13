# CONTABILIDAD — Lógica de Negocio y Reglas SSoT

**Version:** 3.5.0
**App:** `apps/tenant/contabilidad/`

---

## 1. Principios Fundamentales

### Partida Doble Estricta
Toda transacción debe cumplir con la ecuación patrimonial: **Σ Débitos == Σ Créditos**.
- Tolerancia máxima de descuadre: **0.01** (para redondeos de moneda).
- Un asiento con estado `APROBADO` o `CERRADO` **no puede estar descuadrado**.

### Inmutabilidad por Estado
El ciclo de vida del asiento determina su capacidad de edición:
1. **BORRADOR**: Permite cambios en cuentas, montos y fechas. Puede ser eliminado.
2. **APROBADO**: Solo lectura. Genera número de comprobante definitivo. No puede ser eliminado (debe ser reversado).
3. **CERRADO**: Inmutable a nivel de base de datos. Pertenece a un periodo contable finalizado.

---

## 2. Reglas de Validación (Backend)

### Cuentas Auxiliares (Nivel 6)
- **Regla**: Solo las cuentas de nivel 6 (auxiliares) pueden recibir movimientos.
- **Validación**: `ContabilidadBusinessService` rechaza cualquier asiento que intente afectar cuentas de nivel 1-5.

### Periodos Contables
- **Regla**: No se pueden crear, editar o eliminar asientos en fechas que pertenezcan a un `PeriodoContable` con estado `CERRADO`.
- **Validación**: `validadores.validar_periodo_abierto(periodo)` se invoca en cada mutación.

### Idempotencia del Pull Model
- **Regla**: Un documento fuente (Factura, Gasto, etc.) solo puede generar **un asiento** no reversado.
- **Validación**: El `Contabilizador` verifica la terna `(documento_origen_app, documento_origen_modelo, documento_origen_id)` antes de procesar.

---

## 3. Resolucion de Cuentas (SSoT PUC)

La resolución de qué cuenta PUC usar se centraliza en `integracion/resolver.py` mediante `ReglaContable`:

| App Fuente | Tipo Transacción | Concepto | Cuenta Default |
|---|---|---|---|
| Gastos | `COMPRA_GASTO` | `GASTO_GENERAL` | 5105... |
| Gastos | `COMPRA_GASTO` | `RETEFUENTE` | 2365... |
| Facturas | `VENTA_FACTURA` | `INGRESO_PRINCIPAL` | 4135... |
| Facturas | `VENTA_FACTURA` | `CARTERA_CLIENTE` | 1305... |

---

## 4. Estrategia de Reversión

Los asientos no se eliminan físicamente si ya están aprobados. Se aplica **anulación contable**:
1. Se crea un nuevo asiento con prefijo `RVER-`.
2. Se copian los movimientos originales pero con los montos invertidos (Débito ↔ Crédito).
3. Se vincula el asiento original mediante `asiento_reversado`.
4. El documento origen queda liberado para volver a ser contabilizado si es necesario.

---

## 5. Seguridad y Aislamiento (DSV)

Se aplica la **Doble Verificación Semántica (DSV)** en todas las mutaciones:
- El `empresa_id` se inyecta desde el token JWT/Sesión.
- Se valida que las `CuentaContable` y `TipoComprobante` referenciadas pertenezcan a la misma `empresa_id` del asiento.
- Previene ataques de escalada de privilegios horizontal (IDOR).
