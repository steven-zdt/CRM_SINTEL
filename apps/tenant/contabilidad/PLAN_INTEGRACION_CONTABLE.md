# PLAN DE INTEGRACIÓN CONTABLE CENTRALIZADA — SINTEL ERP

**Versión:** 1.0
**Fecha:** 2026-05-03
**Estado:** PROPUESTA — Pendiente de validación
**Marco normativo:** NIIF para PYMES + Decreto 2420/2015 + PUC Colombia

---

## 0. Resumen Ejecutivo

El módulo `contabilidad` ya posee la infraestructura núcleo (Catálogo NIIF, Cuentas, Asientos con cuadratura, Períodos con cierre, Movimientos con campos fiscales). Lo que falta es:

1. **Eliminar el `MAPEO_CUENTAS` hardcoded** y reemplazarlo por una **`ConfiguracionContable` por tenant**.
2. **Estandarizar el contrato de entrada** mediante un DTO `TransaccionEconomica` consumido por una clase **`Contabilizador`** única.
3. **Conectar las apps fuente** que aún no materializan asientos: `facturas`, `inventario`, `empleados`. (Solo `gastos` está conectado actualmente.)
4. **Resolver tres problemas estructurales del modelo actual:**
   - Facturas no exponen retenciones aplicadas (sólo IVA por ítem).
   - Empleados no calcula parafiscales patronales (CAJA, ICBF, SENA, ARL).
   - Inventario no diferencia método de valorización (sólo `costo_promedio` snapshot).

**Patrón recomendado:** **Service Layer explícito, NO Django Signals**. Justificación en §3.

**Entregables priorizados:** Fase 1 (config + facturas) → Fase 2 (inventario kardex) → Fase 3 (nómina + parafiscales) → Fase 4 (proyectos como centros de costo).

---

## 1. Mapeo de Eventos Contables por App

Cada fila representa **un evento de negocio** que debe materializar **uno o más asientos contables**.

### 1.1. App `facturas` (Ventas)

| Evento de negocio | Modelo trigger | Asiento generado | Estado actual |
|---|---|---|---|
| Emisión factura venta (FE aceptada DIAN) | `Factura.estado='ACEPTADA'` | DEBE 1305 (CXC) / HABER 4135 (Ingresos) + 240801 (IVA generado) + retenciones aplicadas por el cliente como debe (235xxx anticipo retención) | ❌ NO conectado |
| Emisión nota crédito | `NotaCredito` | Reverso parcial/total: DEBE 4175 (Devoluciones) + IVA / HABER 1305 | ❌ NO conectado |
| Emisión nota débito | `NotaCredito` (tipo=ND) | Aumento: DEBE 1305 / HABER 4135 + IVA | ❌ NO conectado |
| Recaudo de cartera (cobro a cliente) | Modelo no existe | DEBE 1110 (Bancos) / HABER 1305 (CXC) | ⚠️ Modelo `Pago` no existe |

> **GAP crítico:** Las facturas no almacenan retenciones aplicadas por el cliente. Para una factura de servicios profesionales, el cliente normalmente practica retefuente 11% y el emisor debe registrarla como anticipo (235xxx). Hay que agregar campos a `Factura`: `retefuente_aplicada`, `reteica_aplicada`, `reteiva_aplicada`.

### 1.2. App `gastos` (Compras)

| Evento de negocio | Modelo trigger | Asiento generado | Estado actual |
|---|---|---|---|
| Recepción factura compra/servicio | `DocumentoSoporte` + `Gasto` | DEBE 51xx/52xx/61xx (Gasto/Costo) + 240802 (IVA descontable) / HABER 2335 (CXP) + 2365 (Retefuente) + 2368 (ReteICA) + 2367 (ReteIVA) | ✅ CONECTADO (incompleto: sin IVA descontable) |
| Pago a proveedor | Modelo no existe | DEBE 2335 (CXP) / HABER 1110 (Bancos) | ⚠️ Modelo `Pago` no existe |
| Anulación gasto | `DocumentoSoporte.estado='ANULADO'` | Reverso completo del asiento original | ❌ NO conectado |

> **GAP crítico:** `DocumentoSoporte` actual NO tiene campo `iva` ni `iva_porcentaje`. El IVA descontable se pierde. Hay que agregar `subtotal_gravable`, `iva_descontable_porcentaje` (0/5/19), `iva_descontable_valor`.

### 1.3. App `inventario` (Costo de mercancía)

| Evento de negocio | Modelo trigger | Asiento generado | Estado actual |
|---|---|---|---|
| Entrada por compra | `MovimientoInventario.tipo='ENTRADA_COMPRA'` | DEBE 1435 (Inventario) / HABER 2335 (CXP) — **idealmente integrado al asiento de gastos para evitar doble registro** | ❌ NO conectado |
| Salida por venta | `MovimientoInventario.tipo='SALIDA_VENTA'` | DEBE 6135 (Costo de Ventas) / HABER 1435 (Inventario) — **debe disparar JUNTO al asiento de venta** | ❌ NO conectado |
| Salida por baja/avería | `MovimientoInventario.tipo='SALIDA_BAJA'` | DEBE 5299 (Pérdida en inventarios) / HABER 1435 | ❌ NO conectado |
| Ajuste de inventario (sobrante) | `MovimientoInventario.tipo='ENTRADA_AJUSTE'` | DEBE 1435 / HABER 4250 (Recuperaciones) | ❌ NO conectado |
| Compra activo fijo | `ActivoFijo.create()` | DEBE 1524 (Equipo de oficina) / HABER 2335 | ❌ NO conectado |

> **GAP crítico:** Solo se almacena `costo_promedio` en `Producto`. Para Colombia (NIIF para PYMES sección 13), se acepta promedio ponderado o PEPS. UEPS está prohibido. **Recomendación:** Documentar que el método actual es promedio ponderado y dejarlo así; PEPS requiere lotes con fecha de entrada.

### 1.4. App `empleados` (Nómina)

| Evento de negocio | Modelo trigger | Asiento generado | Estado actual |
|---|---|---|---|
| Liquidación nómina mensual | `Devengo.create()` | DEBE 5105 (Sueldos) + 5103 (Auxilio transporte) + 5210 (Aportes patronales) / HABER 2370 (Salud y pensión empleado) + 2335 (Préstamos) + 2510 (Cesantías) + 2380 (Neto pagar nómina) | ❌ NO conectado |
| Provisión prestaciones sociales | `Devengo.create()` (mismo evento) | DEBE 5210 / HABER 2510 (Cesantías 8.33%) + 2515 (Intereses cesantías 1%) + 2520 (Prima 8.33%) + 2525 (Vacaciones 4.17%) | ❌ NO conectado |
| Aportes parafiscales patronales | `Devengo.create()` (mismo evento) | DEBE 5210 / HABER 2370 (Salud 8.5% + Pensión 12% + ARL) + 2380 (CAJA 4% + ICBF 3% + SENA 2% — exonerados si salario < 10 SMMLV con UVT 2% según art. 114-1 ET) | ❌ NO conectado |
| Pago de nómina (transferencia) | Modelo no existe | DEBE 2380 (Neto por pagar) / HABER 1110 (Bancos) | ⚠️ Falta modelo `PagoNomina` |
| Liquidación contrato (retiro) | `Empleado.estado='RETIRADO'` | Cancela cuentas de provisión + paga indemnización si aplica | ❌ NO conectado |

> **GAP crítico:** `Devengo` solo tiene `salud_empleado` y `pension_empleado` (4% empleado). Faltan campos para: aporte patronal salud (8.5%), pensión (12%), ARL (variable por nivel I-V), CAJA (4%), ICBF (3%), SENA (2%), cesantías (8.33%), prima (8.33%), vacaciones (4.17%), intereses cesantías (1%). **Estos NO son deducciones del empleado, son gastos patronales.**

### 1.5. App `proyectos` (Centros de Costo)

Los proyectos NO generan asientos directos. Funcionan como **etiqueta de clasificación** (centro de costo) sobre los asientos generados por gastos, empleados (asignaciones) e inventario (consumo).

| Evento | Impacto contable |
|---|---|
| Asignar empleado a proyecto | `MovimientoContable.centro_costo_id = proyecto.id` en asiento de nómina |
| Consumir material en proyecto | Asiento de inventario marca el centro de costo |
| Gasto imputado a proyecto | Asiento de gasto marca el centro de costo |

> **GAP estructural:** `MovimientoContable` no tiene campo `centro_costo_id`. Hay que agregarlo (sin FK — referencia desacoplada como en `proyectos`).

### 1.6. Apps sin impacto contable directo

- `core`, `empresa`, `clientes`, `proveedores`, `cotizaciones`: catálogos y maestros. No generan asientos. Cotizaciones se vuelve contable solo cuando se convierte en factura.

---

## 2. Estructura Contable — Mapeo PUC Colombia

### 2.1. Cuentas críticas por clase (resumen operativo)

```
ACTIVO (1)
├── 1110  Bancos
├── 1305  Clientes — CXC
├── 1435  Mercancías no fabricadas — Inventario
├── 1524  Equipo de oficina
└── 235xx  Anticipo de impuestos retenidos por terceros (lo que ME retienen)
        ├── 235515  Retefuente practicada por cliente
        ├── 235517  ReteICA practicada por cliente
        └── 235525  ReteIVA practicada por cliente

PASIVO (2)
├── 2335  Costos y gastos por pagar — Proveedores nacionales
├── 2365  Retención en la fuente por pagar (lo que YO retengo)
├── 2367  Retención IVA por pagar
├── 2368  ReteICA por pagar
├── 2370  Retenciones y aportes nómina (salud + pensión + parafiscales)
├── 2380  Acreedores varios — incluye nómina por pagar
├── 240801 IVA generado en ventas
├── 240802 IVA descontable en compras
├── 2510  Cesantías por pagar
├── 2515  Intereses sobre cesantías
├── 2520  Prima de servicios
└── 2525  Vacaciones

INGRESO (4)
├── 4135  Comercio al por mayor — Ingresos por venta
└── 4175  Devoluciones en ventas (DR)

GASTO (5)
├── 5105  Gastos de personal — Sueldos
├── 5103  Auxilio de transporte
├── 5110  Honorarios
├── 5135  Servicios
├── 5210  Aportes patronales y provisiones
├── 5299  Pérdida en inventarios
└── 51xx  Otros gastos operacionales

COSTO (6)
└── 6135  Costo de ventas y prestación de servicios
```

### 2.2. Tarifas tributarias estándar (Colombia 2026)

| Concepto | Tarifa | Aplicación |
|---|---|---|
| IVA general | 19% | Productos/servicios gravados |
| IVA reducido | 5% | Productos básicos especiales |
| IVA exento | 0% | Exportaciones, salud, educación |
| Retefuente compras | 2.5% | Base ≥ 27 UVT |
| Retefuente servicios | 4% / 6% | Declarantes / no declarantes |
| Retefuente honorarios | 10% / 11% | Personas jurídicas / naturales |
| ReteIVA | 15% del IVA | Base ≥ 4 UVT |
| ReteICA | 0.4% – 1.4% | Variable por municipio y actividad |
| Salud empleado | 4% | Sobre IBC |
| Pensión empleado | 4% | Sobre IBC |
| Salud patronal | 8.5% | Sobre IBC. **Exonerado si salario < 10 SMMLV (art. 114-1 ET)** |
| Pensión patronal | 12% | Sobre IBC |
| ARL | 0.522% – 6.96% | Por nivel de riesgo (I a V) |
| CAJA | 4% | Sobre nómina mensual. Exonerado parcialmente (114-1 ET) |
| ICBF | 3% | Exonerado si salario < 10 SMMLV |
| SENA | 2% | Exonerado si salario < 10 SMMLV |
| Cesantías | 8.33% | Provisión mensual |
| Intereses cesantías | 1% | Provisión mensual |
| Prima servicios | 8.33% | Provisión mensual |
| Vacaciones | 4.17% | Provisión mensual (15 días/año) |

> **Estas tarifas son configurables por tenant** (algunas empresas tienen regímenes especiales: Zona Franca, Régimen Simple, exonerados). Ver §4.

---

## 3. Patrón de Integración: Service Layer vs Signals

### 3.1. Decisión arquitectónica

**Recomendación: Service Layer explícito.**

| Criterio | Service Layer | Django Signals |
|---|---|---|
| Trazabilidad | Explícito en código — grep encuentra todos los call sites | Implícito — debugging requiere conocer los handlers registrados |
| Control transaccional | `with transaction.atomic()` envuelve el flujo completo | Difícil — los handlers ejecutan dentro de la transacción del save() pero el rollback no es atómico entre apps |
| Testing | Mock directo del servicio | Requiere `disconnect()` en cada test, restaurar en tearDown |
| Migraciones/fixtures | Sin efectos colaterales | `post_save` se dispara en `loaddata` causando duplicados |
| Errores | Stack trace claro hacia el call site | Stack trace cruza signal dispatcher |
| Idempotencia | Trivial: chequea antes de crear | Compleja: el handler debe ser idempotente sin contexto |
| Performance | Ejecutado solo cuando se necesita | Ejecutado en TODOS los `.save()` aunque no apliquen |

**Donde SÍ usar signals:** Tareas asíncronas no críticas (envío email, notificaciones push, invalidación caché). NUNCA para integridad contable.

### 3.2. Arquitectura propuesta

```
┌─────────────────────────────────────────────────────────────┐
│                    APPS FUENTE                              │
│  facturas       gastos        inventario      empleados     │
│     │             │              │                │         │
│     └─────────────┴──────────────┴────────────────┘         │
│                       │                                     │
│                       ▼                                     │
│              ┌────────────────────┐                         │
│              │ TransaccionEconomica │                       │
│              │       (DTO)         │                        │
│              └────────────────────┘                         │
│                       │                                     │
│                       ▼                                     │
│  ┌────────────────────────────────────────────────────┐    │
│  │           apps.tenant.contabilidad                  │    │
│  │                                                     │    │
│  │  ┌──────────────────────────────────────────┐      │    │
│  │  │  Contabilizador  (entry point único)     │      │    │
│  │  └──────────────────────────────────────────┘      │    │
│  │                       │                             │    │
│  │                       ▼                             │    │
│  │  ┌──────────────────────────────────────────┐      │    │
│  │  │  ResolverCuentas (lee ConfiguracionContable) │   │    │
│  │  └──────────────────────────────────────────┘      │    │
│  │                       │                             │    │
│  │                       ▼                             │    │
│  │  ┌──────────────────────────────────────────┐      │    │
│  │  │  ValidadorCuadratura + ValidadorPeriodo  │      │    │
│  │  └──────────────────────────────────────────┘      │    │
│  │                       │                             │    │
│  │                       ▼                             │    │
│  │  ┌──────────────────────────────────────────┐      │    │
│  │  │  AsientoContable + MovimientoContable    │      │    │
│  │  │  (persistencia en transaction.atomic)    │      │    │
│  │  └──────────────────────────────────────────┘      │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 3.3. Contrato del DTO `TransaccionEconomica`

```python
# apps/tenant/contabilidad/integracion/dtos.py

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class TipoTransaccion(str, Enum):
    VENTA_FACTURA = "VENTA_FACTURA"
    VENTA_NOTA_CREDITO = "VENTA_NOTA_CREDITO"
    COMPRA_GASTO = "COMPRA_GASTO"
    COMPRA_INVENTARIO = "COMPRA_INVENTARIO"
    SALIDA_INVENTARIO_VENTA = "SALIDA_INVENTARIO_VENTA"
    BAJA_INVENTARIO = "BAJA_INVENTARIO"
    NOMINA_LIQUIDACION = "NOMINA_LIQUIDACION"
    NOMINA_PROVISION = "NOMINA_PROVISION"
    PAGO_PROVEEDOR = "PAGO_PROVEEDOR"
    RECAUDO_CLIENTE = "RECAUDO_CLIENTE"


class TipoTercero(str, Enum):
    CLIENTE = "CLIENTE"
    PROVEEDOR = "PROVEEDOR"
    EMPLEADO = "EMPLEADO"
    OTRO = "OTRO"


@dataclass(frozen=True)
class TerceroSnapshot:
    """Datos del tercero al momento de la transacción (no FK)."""
    tipo: TipoTercero
    id_origen: int                  # PK en su app de origen
    nit: str
    razon_social: str


@dataclass(frozen=True)
class ImpuestoLinea:
    """Un impuesto aplicado a una línea de transacción."""
    tipo: str                       # "IVA_GENERADO", "IVA_DESCONTABLE", "RETEFUENTE", "RETEICA", "RETEIVA"
    base: Decimal
    porcentaje: Decimal             # 19.0, 4.0, etc.
    valor: Decimal                  # Calculado por la app fuente


@dataclass(frozen=True)
class LineaTransaccion:
    """Una línea económica del documento (ítem de factura, deducción de nómina, etc.)."""
    concepto: str                   # "VENTA_PRODUCTO", "AUXILIO_TRANSPORTE", "PROVISION_CESANTIAS"
    monto: Decimal                  # Monto principal de la línea (sin impuestos)
    impuestos: list[ImpuestoLinea] = field(default_factory=list)
    centro_costo_id: Optional[int] = None
    cuenta_hint: Optional[str] = None  # Override opcional del código de cuenta


@dataclass(frozen=True)
class DocumentoOrigen:
    """Trazabilidad al documento que originó la transacción."""
    app_label: str                  # "facturas", "gastos", "empleados"
    modelo: str                     # "Factura", "Gasto", "Devengo"
    id: int                         # PK en su app
    numero: str                     # Número visible del documento


@dataclass(frozen=True)
class TransaccionEconomica:
    """Contrato único de entrada al Contabilizador."""
    tipo: TipoTransaccion
    fecha: date
    descripcion: str
    tercero: Optional[TerceroSnapshot]
    lineas: list[LineaTransaccion]
    documento_origen: DocumentoOrigen
    moneda: str = "COP"
    metadatos: dict = field(default_factory=dict)
```

### 3.4. API del `Contabilizador`

```python
# apps/tenant/contabilidad/integracion/contabilizador.py

class Contabilizador:
    """
    Entry point único para generar asientos contables desde apps fuente.

    Uso:
        from apps.tenant.contabilidad.integracion.contabilizador import Contabilizador
        asiento = Contabilizador(empresa_id=tenant.id).contabilizar(transaccion_dto)
    """

    def __init__(self, empresa_id: int):
        self.empresa_id = empresa_id
        self.config = ConfiguracionContableSelector.get_for_empresa(empresa_id)
        self.resolver = ResolverCuentas(self.config)

    @transaction.atomic
    def contabilizar(self, dto: TransaccionEconomica) -> AsientoContable:
        """
        Materializa la transacción como AsientoContable + MovimientoContable[].

        Lanza ContabilidadError si:
        - El período de la fecha está cerrado.
        - No hay regla de mapeo para algún concepto.
        - El asiento no cuadra (debe != haber).
        - Ya existe asiento para el mismo documento_origen (idempotencia).

        Retorna AsientoContable en estado BORRADOR (requiere aprobación posterior).
        """

    def reversar(self, dto: TransaccionEconomica, motivo: str) -> AsientoContable:
        """Genera asiento de reverso preservando trazabilidad al original."""

    def existe_asiento_para(self, documento: DocumentoOrigen) -> bool:
        """Idempotencia: chequea si ya se contabilizó este documento."""
```

### 3.5. Idempotencia e identificadores únicos

`AsientoContable` debe ganar dos campos:

```python
class AsientoContable(SintelTenantBaseModel):
    # ... campos existentes ...
    documento_origen_app = models.CharField(max_length=50, blank=True)
    documento_origen_modelo = models.CharField(max_length=80, blank=True)
    documento_origen_id = models.PositiveIntegerField(null=True, blank=True)
    asiento_reversado = models.ForeignKey('self', null=True, blank=True,
                                          on_delete=models.PROTECT,
                                          related_name='reversos')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'documento_origen_app', 'documento_origen_modelo', 'documento_origen_id'],
                condition=Q(documento_origen_id__isnull=False),
                name='uniq_asiento_por_documento_origen'
            )
        ]
```

---

## 4. Configuración Contable por Tenant

### 4.1. Modelo `ConfiguracionContable`

```python
# apps/tenant/contabilidad/models.py (agregar)

class ReglaContable(SintelTenantBaseModel):
    """
    Define qué cuenta usar para cada (tipo_transaccion, concepto, lado).

    Ejemplo:
      tipo=VENTA_FACTURA, concepto=INGRESO_PRINCIPAL, lado=HABER -> cuenta 4135
      tipo=VENTA_FACTURA, concepto=CXC,                lado=DEBE  -> cuenta 1305
      tipo=VENTA_FACTURA, concepto=IVA_GENERADO,       lado=HABER -> cuenta 240801
    """
    tipo_transaccion = models.CharField(max_length=50, choices=TIPO_TRANSACCION_CHOICES)
    concepto = models.CharField(max_length=80)
    lado = models.CharField(max_length=5, choices=[("DEBE", "Débito"), ("HABER", "Crédito")])
    cuenta = models.ForeignKey(CuentaContable, on_delete=models.PROTECT)
    activa = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'tipo_transaccion', 'concepto', 'lado'],
                name='uniq_regla_contable'
            )
        ]


class TarifaImpuesto(SintelTenantBaseModel):
    """Tarifas vigentes por tenant. Permite cambios fiscales sin desplegar código."""
    tipo = models.CharField(max_length=30, choices=[
        ("IVA_GENERAL", "IVA general"),
        ("IVA_REDUCIDO", "IVA reducido"),
        ("RETEFUENTE_COMPRAS", "Retefuente compras"),
        ("RETEFUENTE_SERVICIOS", "Retefuente servicios"),
        ("RETEFUENTE_HONORARIOS", "Retefuente honorarios"),
        ("RETEIVA", "Retención IVA"),
        ("RETEICA", "Retención ICA"),
        # parafiscales y nómina:
        ("SALUD_PATRONAL", "Salud patronal"),
        ("PENSION_PATRONAL", "Pensión patronal"),
        ("ARL_NIVEL_I", "ARL nivel I"),
        # ... etc
    ])
    porcentaje = models.DecimalField(max_digits=6, decimal_places=4)
    base_minima_uvt = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)
    activa = models.BooleanField(default=True)
```

### 4.2. Seed inicial por tenant

Al crear un tenant, ejecutar `apps.tenant.contabilidad.management.commands.seed_reglas_contables` que:

1. Importa el catálogo NIIF base (ya existe `CatalogoMaestroNIIF`).
2. Crea las cuentas básicas (1110, 1305, 1435, 2335, 2365, 240801, 240802, 4135, 5105, 6135) en `CuentaContable` enlazadas al catálogo.
3. Crea las reglas estándar para cada `TipoTransaccion` mapeadas a esas cuentas.
4. Crea `TarifaImpuesto` con las tarifas vigentes 2026.

> El admin del tenant puede luego ajustar reglas y tarifas vía UI sin tocar código.

---

## 5. Matriz de Transacciones (Esquema Detallado por App)

### 5.1. `facturas` → `VENTA_FACTURA`

**Trigger:** `Factura.estado` cambia a `'ACEPTADA'` (después de respuesta DIAN OK).

**Llamada:**
```python
# apps/tenant/facturas/services/contabilizacion_service.py

def materializar_factura(factura: Factura) -> AsientoContable:
    dto = TransaccionEconomica(
        tipo=TipoTransaccion.VENTA_FACTURA,
        fecha=factura.fecha_emision,
        descripcion=f"Factura venta {factura.numero}",
        tercero=TerceroSnapshot(
            tipo=TipoTercero.CLIENTE,
            id_origen=factura.cliente_id,
            nit=factura.receptor_nit,
            razon_social=factura.receptor_razon_social,
        ),
        lineas=[
            LineaTransaccion(
                concepto="INGRESO_PRINCIPAL",
                monto=factura.subtotal,
                impuestos=[
                    ImpuestoLinea(
                        tipo="IVA_GENERADO",
                        base=item.subtotal,
                        porcentaje=item.porcentaje_iva,
                        valor=item.valor_iva,
                    )
                    for item in factura.items.all()
                ],
            ),
        ],
        documento_origen=DocumentoOrigen(
            app_label="facturas", modelo="Factura",
            id=factura.id, numero=factura.numero
        ),
    )
    return Contabilizador(empresa_id=factura.empresa_id).contabilizar(dto)
```

**Asiento generado (ejemplo factura $1,000,000 + IVA 19% = $1,190,000):**

| Cuenta | Tercero | DEBE | HABER |
|---|---|---|---|
| 130505 Clientes | NIT cliente | 1.190.000 | |
| 413501 Ingresos | | | 1.000.000 |
| 240801 IVA generado 19% | | | 190.000 |

### 5.2. `gastos` → `COMPRA_GASTO`

**Trigger:** Ya conectado (`gastos.services.materializar_gasto_desde_dto`). Refactorizar para usar el nuevo `Contabilizador`.

**Asiento generado (gasto servicios $1,000,000 + IVA 19%, retefuente 4%, reteica 0.69%):**

| Cuenta | Tercero | DEBE | HABER |
|---|---|---|---|
| 51xxxx Gastos | NIT proveedor | 1.000.000 | |
| 240802 IVA descontable 19% | | 190.000 | |
| 233595 Costos y gastos por pagar | NIT proveedor | | 1.143.100 |
| 236540 Retefuente por pagar | | | 40.000 |
| 236805 ReteICA por pagar | | | 6.900 |

### 5.3. `inventario` → `SALIDA_INVENTARIO_VENTA`

**Trigger:** Cuando se confirma una venta y hay producto involucrado, debe disparar JUNTO al asiento de venta (en la misma transacción atómica).

**Asiento generado (venta de producto con costo unitario $600,000):**

| Cuenta | DEBE | HABER |
|---|---|---|
| 613501 Costo de ventas | 600.000 | |
| 143505 Inventario mercancías | | 600.000 |

> **Decisión arquitectónica:** ¿Asientos separados o consolidados? Recomendación: **dos asientos vinculados** (uno por venta, uno por costo) porque permite anular el costo sin tocar la venta. Ambos en la misma `transaction.atomic`.

### 5.4. `empleados` → `NOMINA_LIQUIDACION` + `NOMINA_PROVISION`

**Trigger:** `Devengo.create()` para cada empleado del período.

**Pre-requisito (GAP a resolver):** Agregar a `Devengo` los campos patronales:
```python
# Aporte patronal (gastos del empleador)
salud_patronal = models.DecimalField(...)         # 8.5% IBC (exonerado si <10 SMMLV)
pension_patronal = models.DecimalField(...)        # 12% IBC
arl = models.DecimalField(...)                     # 0.522% - 6.96% según nivel
caja_compensacion = models.DecimalField(...)       # 4% nómina
icbf = models.DecimalField(...)                    # 3% (exonerado <10 SMMLV)
sena = models.DecimalField(...)                    # 2% (exonerado <10 SMMLV)
# Provisiones
cesantias = models.DecimalField(...)               # 8.33%
intereses_cesantias = models.DecimalField(...)    # 1%
prima_servicios = models.DecimalField(...)         # 8.33%
vacaciones = models.DecimalField(...)              # 4.17%
```

**Asiento generado (salario $2,000,000):**

| Cuenta | Tercero | DEBE | HABER |
|---|---|---|---|
| 510506 Sueldos | empleado | 2.000.000 | |
| 510527 Auxilio transporte | empleado | 162.000 | |
| 510568 Aportes ARL (1%) | | 20.000 | |
| 510569 Aportes pensión patronal (12%) | | 240.000 | |
| 510570 Aportes salud patronal (8.5%) | | 0 (exonerado) | |
| 510572 Cesantías (8.33%) | | 180.046 | |
| 510575 Intereses cesantías (1%) | | 1.620 | |
| 510578 Prima servicios (8.33%) | | 180.046 | |
| 510584 Vacaciones (4.17%) | | 83.400 | |
| 237005 Salud empleado (4%) | empleado | | 80.000 |
| 237006 Pensión empleado (4%) | empleado | | 80.000 |
| 238030 Salarios por pagar | empleado | | 2.002.000 |
| 251005 Cesantías por pagar | empleado | | 180.046 |
| 252005 Intereses cesantías por pagar | empleado | | 1.620 |
| 252010 Prima servicios por pagar | empleado | | 180.046 |
| 252510 Vacaciones por pagar | empleado | | 83.400 |
| 237006 Pensión patronal por pagar | | | 240.000 |
| 237007 ARL por pagar | | | 20.000 |

> **Nota fiscal:** Exoneración 114-1 ET aplica si el empleado gana < 10 SMMLV. La regla está en `TarifaImpuesto.base_minima_uvt` y la lógica en `ResolverCuentas`.

### 5.5. `proyectos` → Centro de Costo (no genera asiento propio)

Cada `LineaTransaccion` puede llevar `centro_costo_id`. Al persistir, `MovimientoContable.centro_costo_id` se llena. Reportes contables filtran por centro de costo para análisis de rentabilidad por proyecto.

---

## 6. Plan de Migración (Fases)

### Fase 0 — Preparación (1 sprint)

- [ ] Crear `apps/tenant/contabilidad/integracion/` con `dtos.py`, `contabilizador.py`, `resolver.py`, `validadores.py`, `excepciones.py`.
- [ ] Crear modelos `ReglaContable` y `TarifaImpuesto` con migración.
- [ ] Agregar campos a `AsientoContable`: `documento_origen_*`, `asiento_reversado` + constraint de idempotencia.
- [ ] Agregar campo `centro_costo_id` (sin FK) a `MovimientoContable`.
- [ ] Crear comando `seed_reglas_contables` y ejecutar contra todos los tenants existentes.
- [ ] Tests unitarios del `Contabilizador` con DTOs sintéticos (sin tocar otras apps).

### Fase 1 — Migrar `gastos` al nuevo contrato (1 sprint)

- [ ] Refactorizar `gastos.services.materializar_gasto_desde_dto` para construir `TransaccionEconomica` y llamar al nuevo `Contabilizador`.
- [ ] Eliminar `MAPEO_CUENTAS` hardcoded de `business_service.py`.
- [ ] **Agregar campos faltantes en `DocumentoSoporte`:** `subtotal_gravable`, `iva_descontable_porcentaje`, `iva_descontable_valor`. Migración con default 0 para registros históricos.
- [ ] Backfill: contabilizar gastos sin asiento existentes (vía comando management).
- [ ] Tests integración: crear gasto → asiento generado correctamente.

### Fase 2 — Conectar `facturas` (1-2 sprints)

- [ ] Agregar campos a `Factura`: `retefuente_aplicada`, `reteica_aplicada`, `reteiva_aplicada` (lo que el cliente nos retiene). Default 0.
- [ ] Crear `apps.tenant.facturas.services.contabilizacion_service`.
- [ ] Trigger: en `Factura.aceptar_dian()` (o el método que cambia estado a ACEPTADA), invocar `materializar_factura(factura)`.
- [ ] Trigger nota crédito: contabilizar reverso al emitir.
- [ ] Backfill: facturas históricas en estado ACEPTADA sin asiento.
- [ ] UI: en el offcanvas de detalle de factura, mostrar el asiento generado (link al asiento contable).

### Fase 3 — Conectar `inventario` (1 sprint)

- [ ] Definir disparador: `MovimientoInventario.save()` con tipo SALIDA_VENTA debe contabilizar costo.
  - **Decisión:** ¿Llamar desde `MovimientoInventario.save()` o desde el orquestador de venta? Recomendación: orquestador (cuando la venta se factura, pasar también las salidas de inventario al contabilizador en el mismo flujo).
- [ ] Asiento de costo de ventas vinculado al asiento de venta (mismo `documento_origen` con sufijo).
- [ ] Compras de inventario: el asiento de gasto/compra YA registra DEBE 1435 cuando el gasto es categoría INVENTARIO. Coordinar para evitar doble registro.
- [ ] Bajas e ajustes: contabilización por evento individual.

### Fase 4 — Conectar `empleados` / Nómina (2 sprints — el más complejo)

- [ ] Agregar campos patronales a `Devengo` (ver §5.4).
- [ ] Servicio de cálculo de parafiscales: `apps.tenant.empleados.services.parafiscales_service.calcular_aportes_patronales(devengo)`. Aplica exoneraciones 114-1 ET.
- [ ] `apps.tenant.empleados.services.contabilizacion_service.materializar_devengo(devengo)`.
- [ ] Trigger: al aprobar el devengo (no al crearlo en borrador).
- [ ] Asientos de provisión separados de nómina liquidada (para auditoría).
- [ ] Contabilización agregada por período (un solo asiento por período con todos los empleados) — **alternativa**: un asiento por empleado para máximo detalle. **Recomendación: agregado por período + auxiliar por empleado en `MovimientoContable.tercero_*`.**

### Fase 5 — Centros de costo (proyectos) (1 sprint)

- [ ] Agregar `centro_costo_id` opcional a todas las invocaciones desde apps fuente.
- [ ] Reportes en `contabilidad`: filtrado por centro de costo en libro mayor, balance de prueba.
- [ ] UI: selector de proyecto en formularios de gasto, asignación nómina.

### Fase 6 — Pagos (modelos pendientes) (2 sprints)

Crear `apps.tenant.tesoreria/` (nueva app):
- [ ] Modelos: `Pago`, `Recaudo`, `MovimientoBancario`.
- [ ] Pago a proveedor: cancela CXP (2335), debita banco (1110).
- [ ] Recaudo cliente: cancela CXC (1305), debita banco (1110).
- [ ] Conciliación bancaria contra extractos.

### Fase 7 — Reportes financieros (continuo)

- [ ] Balance de prueba por período (ya existe parcialmente).
- [ ] Estado de resultados.
- [ ] Estado de situación financiera.
- [ ] Libros oficiales (Diario, Mayor).
- [ ] Medios magnéticos DIAN (formato 1001-1011).

---

## 7. Manejo de Errores y Reglas Especiales

### 7.1. Excepciones del Contabilizador

```python
class ContabilidadError(Exception): pass
class PeriodoCerradoError(ContabilidadError): pass
class ReglaContableNoDefinidaError(ContabilidadError): pass
class AsientoNoCuadradoError(ContabilidadError): pass
class AsientoYaExisteError(ContabilidadError): pass
class TarifaNoVigenteError(ContabilidadError): pass
```

### 7.2. ¿Qué hacer si falla la contabilización?

**Política recomendada: NO bloquear la operación de negocio, pero alertar.**

```python
@transaction.atomic
def aceptar_factura_dian(factura):
    factura.estado = 'ACEPTADA'
    factura.save()
    try:
        materializar_factura(factura)
    except ContabilidadError as e:
        # Log + alerta admin, NO revertir aceptación de la factura
        logger.error(f"Factura {factura.numero} aceptada pero NO contabilizada: {e}")
        AlertaContable.objects.create(
            documento_origen='facturas.Factura',
            documento_id=factura.id,
            error=str(e)
        )
```

> **Razón:** Una factura aceptada por DIAN es un hecho fiscal; no podemos "deshacer" la aceptación porque la contabilización falló. El admin contable debe revisar la cola de alertas y resolver manualmente (corregir regla, ajustar tarifa, contabilizar manualmente).

### 7.3. Aprobación de asientos

Los asientos se crean en estado `BORRADOR`. Un usuario con rol contador los revisa y aprueba (estado `APROBADO`). En estado `APROBADO` no se pueden editar; solo reversar (genera asiento opuesto vinculado).

### 7.4. Cierre de período

Cuando un `PeriodoContable` pasa a `CERRADO`:
- No se aceptan asientos nuevos con fecha en ese período.
- Asientos en BORRADOR del período se rechazan automáticamente (se mueven al período actual o se eliminan según política).
- Reversos de asientos del período cerrado se permiten pero con fecha del período actual.

---

## 8. Checklist de Validación NIIF Colombia

- [x] Plan de cuentas alineado a Decreto 2420/2015 (PUC NIIF para PYMES).
- [ ] Asientos cuadrados (debe = haber) — ya implementado.
- [ ] Trazabilidad documento → asiento (idempotencia por `documento_origen`).
- [ ] Cierre de períodos bloquea ediciones.
- [ ] Aprobación dual de asientos (contador + auditor opcional).
- [ ] IVA generado y descontable separados (240801 vs 240802).
- [ ] Retenciones por pagar separadas (2365 retefuente, 2367 reteIVA, 2368 reteICA).
- [ ] Anticipos de retenciones recibidas (235515, 235517, 235525) — facturas emitidas.
- [ ] Provisiones laborales mensuales (2510, 2515, 2520, 2525).
- [ ] Exoneraciones 114-1 ET aplicadas (CAJA/ICBF/SENA/salud patronal).
- [ ] Centros de costo por proyecto (clasificación gerencial).
- [ ] Reversos generan asiento nuevo (NO eliminan el original).
- [ ] Numeración consecutiva sin huecos por tipo de comprobante.

---

## 9. Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Doble contabilización por reintento | Asientos duplicados | Constraint UNIQUE por `documento_origen` |
| Fallo silencioso al contabilizar | Discrepancias contables | Tabla `AlertaContable` + cola de revisión |
| Cambio de tarifas mid-período | Asientos con tarifas viejas | `TarifaImpuesto.vigente_desde/hasta` + lectura por fecha |
| Tenant sin reglas configuradas | Excepción al primer evento | Seed automático en provisión de tenant |
| Migración masiva de históricos sin asientos | Carga DB pesada | Comando management con `--batch-size` |
| Cambios en PUC oficial | Requeriría actualización masiva | Catálogo NIIF como SSoT, cuentas tenant son referencias |
| Concurrencia en aprobación de asientos | Pérdida de actualización | `select_for_update()` en aprobación |

---

## 10. Métricas de Éxito

Al completar las Fases 1-4:
- **100% de facturas en estado ACEPTADA** tienen asiento contable asociado.
- **100% de gastos** generan asiento (ya está en 100%).
- **100% de devengos APROBADOS** generan asientos de nómina y provisiones.
- **0 alertas en `AlertaContable`** por más de 7 días sin resolver.
- **Balance de prueba cuadrado** al final de cada período.
- **Tiempo de cierre mensual** reducido de N días manuales → 1 día automatizado.

---

## 11. Anexos

### 11.1. Convenciones de naming

- Servicios de contabilización en cada app: `apps/tenant/<app>/services/contabilizacion_service.py`.
- Función pública: `materializar_<modelo>(instancia) -> AsientoContable`.
- DTOs siempre en `apps/tenant/contabilidad/integracion/dtos.py`.

### 11.2. Conceptos canonizados (para `LineaTransaccion.concepto` y `ReglaContable.concepto`)

```
Ventas:        INGRESO_PRINCIPAL, DEVOLUCION_VENTA, IVA_GENERADO, RETEFUENTE_RECIBIDA
Compras:       GASTO_OPERACIONAL, GASTO_HONORARIOS, GASTO_SERVICIOS, IVA_DESCONTABLE
Inventario:    COMPRA_INVENTARIO, COSTO_VENTAS, BAJA_INVENTARIO, AJUSTE_INVENTARIO
Nómina:        SUELDO, AUXILIO_TRANSPORTE, SALUD_EMP, PENSION_EMP,
               SALUD_PAT, PENSION_PAT, ARL, CAJA, ICBF, SENA,
               PROV_CESANTIAS, PROV_INT_CESANTIAS, PROV_PRIMA, PROV_VACACIONES,
               NETO_PAGAR_NOMINA
Tesorería:     CXC, CXP, BANCO, CAJA_GENERAL
```

### 11.3. Referencias

- [apps/tenant/contabilidad/models.py](models.py)
- [apps/tenant/contabilidad/services/business_service.py](services/business_service.py)
- [apps/tenant/gastos/services/](../gastos/services/) — único conector actual
- [Decreto 2420/2015 — Marco técnico normativo NIIF Colombia](https://www.mincit.gov.co/)
- [Decreto Único Reglamentario 2483/2018 — PUC]()
- [Estatuto Tributario Art. 114-1 — Exoneraciones aportes parafiscales]()
