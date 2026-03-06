# Guía de columnas y rowId — DataTables

## Columnas

- Mantén `columns.length` ≈ número de `<th>`; si difiere, el adapter aplica fallback pero se recomienda alinearlo para consistencia visual.
- Para tabs/ocultos: asegura `style="width:100%"` y reajuste al mostrar. [stackoverflow.com](https://stackoverflow.com/questions/70101412/how-to-make-datatable-responsive-in-bootstrap-tabs), [gyrocode.com](https://www.gyrocode.com/articles/jquery-datatables-column-width-issues-with-bootstrap-tabs/)

## rowId / DT_RowId

- **Front**: `rowId: 'id'` (o el campo único de tu recurso).
- **Back**: puedes enviar `DT_RowId` (opción oficial) para autoasignación. [rdrr.io](https://rdrr.io/cran/data.table/man/rowid.html), [quantargo.com](https://www.quantargo.com/help/r/latest/packages/data.table/as.data.table.html/rowid)

## Buenas prácticas

- Evita re‑inicializar: usa la instancia (`retrieve:true`) o destruye de forma segura antes de cambiar configuración. [datatables.net](https://datatables.net/reference/option/stateSave)
