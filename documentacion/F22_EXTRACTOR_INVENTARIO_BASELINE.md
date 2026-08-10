# F22.3 — Estado Real de `ExtractorInventario` (antes de F22)

**Fecha:** 2026-08-09

## 1. Codigo real (antes de F22)

`apps/tenant/contabilidad/integracion/extractores/inventario.py`:

```python
class ExtractorInventario(AbstractExtractor):
    """
    Extractor legacy deshabilitado.
    ...
    """
    def extraer_pendientes(self) -> List[TransaccionEconomica]:
        logger.info(
            "[contabilidad:extractor_inventario] deshabilitado; empresa_id=%s",
            self.empresa_id,
        )
        return []
```

No implementa `get_documentos_enriquecidos()` (metodo abstracto obligatorio de
`AbstractExtractor`) — heredaria el `NotImplementedError` de la clase base si se invocara.

## 2. Por que retorna `[]` — confirmado, no es un placeholder accidental

- No esta registrado en `EXTRACTORES_DISPONIBLES` de
  `apps/tenant/contabilidad/management/commands/backfill_contabilidad.py` (solo `gastos`,
  `facturas`, `nomina`) — nunca se invoca desde el comando de backfill real.
- 0 referencias a `ExtractorInventario` fuera de su propio archivo y `extractores/__init__.py`
  (no exportado ahi tampoco — confirmado por grep).
- El docstring ("el mapeo vive en Inventario") es **inexacto**: no existe ningun mecanismo real en
  `apps/tenant/inventario/` que contabilice nada (confirmado en `F21_BASELINE.md` §5 y
  re-confirmado en `F22_INVENTARIO_BASELINE.md`).
- Conclusion: es deuda tecnica real y deliberadamente marcada como tal ("legacy deshabilitado"),
  no un bug de regresion ni un placeholder que alguien olvido completar a medias.

## 3. Lo que SI existe y es reutilizable (no hay que construir desde cero)

- El contrato `TipoTransaccion` en `dtos.py` **ya incluye** los 5 valores de inventario:
  `COMPRA_INVENTARIO`, `SALIDA_INVENTARIO_VENTA`, `BAJA_INVENTARIO`, `AJUSTE_INVENTARIO`,
  `INVENTARIO_COSTO_VENTA` — sin usar hasta F22.
- `apps/tenant/contabilidad/management/commands/seed_reglas_contables.py` **ya tiene** reglas
  seedeadas (`ReglaContable`, `get_or_create`, idempotente) para los primeros 4 de esos 5 tipos,
  con codigos PUC reales (143505 Inventario, 220505 Proveedores-Inventario, 613501 Costo de
  Ventas, 529901 Gasto por deterioro, 519595 Consumo interno, 425050 Ingreso por ajuste). Ver
  matriz completa en `F22_ACCOUNTING_CONTRACT.md` §2.
- `AbstractExtractor.contabilizar_pendientes()` (en `extractores/base.py`) ya implementa el loop
  de idempotencia con aislamiento de errores por documento (`try/except AsientoYaExisteError` +
  captura generica) — F22 no necesita reimplementar esta orquestacion, solo `extraer_pendientes()`
  y `get_documentos_enriquecidos()`.
- `ExtractorGastos`/`ExtractorNomina` son plantillas reales, funcionando en produccion, del mismo
  contrato — mismo patron a seguir exactamente.

## 4. Decision F22

Implementar `extraer_pendientes()` y `get_documentos_enriquecidos()` reales, reutilizando el
contrato de `TipoTransaccion` y las reglas ya seedeadas. Registrar `ExtractorInventario` en
`extractores/__init__.py` y en `EXTRACTORES_DISPONIBLES` de `backfill_contabilidad.py`. No se
crea un segundo extractor ni un segundo mecanismo de backfill.
