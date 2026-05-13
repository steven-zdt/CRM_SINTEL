# 🧠 Lógica de Negocio: Módulo Gastos (SSoT)

Este documento centraliza las reglas de integridad, cálculos de retenciones y políticas de inmutabilidad.

---

## 1. Dualidad Documental: DS vs Gasto

- **DocumentoSoporte (DS)**: Representa la evidencia legal ante la DIAN. Sus campos monetarios (`subtotal`, `total`) e identificadores (`consecutivo`, `prefijo`) son **inmutables** tras la creación.
- **Gasto**: Representa la clasificación administrativa interna. Permite edición de campos operativos (`descripcion`, `categoria_contable`, `observaciones`) sin afectar la integridad del documento legal.

---

## 2. Cálculo de Retenciones y Totales

El sistema utiliza `Decimal` para precisión financiera.
- **Base**: `Subtotal` crudo ingresado por el usuario.
- **Retefuente**: `Subtotal * (retefuente_porcentaje / 100)`.
- **ReteICA**: `Subtotal * (reteica_porcentaje / 100)`.
- **Total Neto**: `Subtotal - Retefuente - ReteICA`.

> [!NOTE]
> Los porcentajes UI (ej. 4%, 0.966%) se normalizan a escala decimal (0.04, 0.00966) antes de la persistencia.

---

## 3. Política de Consecutivos DIAN

- **Atomicidad**: El sistema utiliza `select_for_update()` para reservar el siguiente número de soporte, evitando colisiones en ambientes de alta concurrencia.
- **Rango de Validez**: Un gasto solo puede crearse si la fecha actual está dentro del rango `[fecha_inicio, fecha_fin]` de la resolución vigente y el consecutivo no supera el `rango_hasta`.
- **Invariante de Secuencia**: Los números de soporte son estrictamente secuenciales e incrementales. No se reciclan números de documentos anulados.

---

## 4. Estados y Flujo Operativo

- **Activo (`activo=True`)**: Documento válido que afecta sumarios financieros.
- **Desactivado (`activo=False`)**: Estado intermedio previo a la anulación. Deja de contar para sumarios pero es reversible.
- **Anulado (`anulado=True`)**: Estado final e irreversible. El documento pierde validez legal pero el consecutivo queda "quemado" para auditoría.

---

## 5. Desacoplamiento Contable

- El módulo de gastos **NO** almacena códigos contables fijos en su modelo de base.
- La integración con contabilidad es un "Hook" posterior que mapea las categorías del gasto a cuentas del Plan Único de Cuentas (PUC) en tiempo de ejecución.
- Si la materialización del asiento contable falla, el gasto permanece creado para no bloquear la operación del usuario, marcándose como "Pendiente de Contabilización".
