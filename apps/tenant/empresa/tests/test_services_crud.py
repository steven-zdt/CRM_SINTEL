import types


class _MockQS:
    def __init__(self, items=None):
        self._items = items or []

    def filter(self, *args, **kwargs):
        return self

    def only(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._items[0] if self._items else None


def test_qs_list_returns_qs(monkeypatch):
    # Arrange
    import apps.tenant.empresa.services.crud_service as crud

    mock_qs = _MockQS()
    class _Mgr:
        def only(self, *args, **kwargs):
            return mock_qs

    monkeypatch.setattr(crud, 'Empresa', types.SimpleNamespace(objects=_Mgr()))

    # Act
    qs = crud.qs_list(search='foo')

    # Assert
    assert qs is mock_qs


def test_get_empresa_emisor_data_when_missing_raises(monkeypatch):
    import apps.tenant.empresa.services.crud_service as crud

    class _Mgr:
        def only(self, *args, **kwargs):
            return _MockQS()

    monkeypatch.setattr(crud, 'Empresa', types.SimpleNamespace(objects=_Mgr()))

    try:
        crud.get_empresa_emisor_data()
        raised = False
    except Exception:
        raised = True

    assert raised is True
