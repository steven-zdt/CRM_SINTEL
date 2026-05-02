# Cookbook — Modales CRUD (ModalService + CRUD)

## Crear

```javascript
ModalService.open({
  id: 'modal-clientes',
  title: 'Nuevo cliente',
  body: `<form id="form-clientes"><input name="nombre"></form>`,
  onSubmit: async () => {
    const payload = Object.fromEntries(new FormData(document.getElementById('form-clientes')).entries());
    const r = await CRUD.create('clientes', payload);
    if (r?.ok) {
      // Recargar DataTable sin perder estado
      const dt = window.jQuery('#table-clientes').DataTable();
      dt.refreshSafe?.() ?? dt.ajax.reload(null, false); // no pisar estado [dev.to](https://dev.to/markpelf/aspnet8-using-datatablesnet-part3-state-saving-5gai)
    }
    ModalService.close('modal-clientes');
  }
});
```

## Editar

```javascript
const r = await CRUD.read('clientes', id);
if (r?.ok) {
  ModalService.open({
    id: 'modal-clientes',
    title: 'Editar cliente',
    body: `<form id="form-clientes-edit"><input name="nombre" value="${r.data?.nombre || ''}"></form>`,
    onSubmit: async () => {
      const payload = Object.fromEntries(new FormData(document.getElementById('form-clientes-edit')).entries());
      const u = await CRUD.update('clientes', id, payload);
      if (u?.ok) {
        const dt = window.jQuery('#table-clientes').DataTable();
        dt.refreshSafe?.() ?? dt.ajax.reload(null, false);
      }
      ModalService.close('modal-clientes');
    }
  });
}
```

## Eliminar

```javascript
if (confirm('¿Eliminar?')) {
  const r = await CRUD.delete('clientes', id);
  if (r?.ok) {
    const dt = window.jQuery('#table-clientes').DataTable();
    dt.refreshSafe?.() ?? dt.ajax.reload(null, false);
  }
}
```

## Notas

- Mutaciones con CSRF (se inyecta en `safeFetchJson` o `ajax.beforeSend` de DataTables). [stackoverflow.com](https://stackoverflow.com/questions/28417781/jquery-add-csrf-token-to-all-post-requests-data)
- Tablas en tabs: ajusta al mostrarse (`columns.adjust().responsive.recalc()`). [stackoverflow.com](https://stackoverflow.com/questions/70101412/how-to-make-datatable-responsive-in-bootstrap-tabs)
