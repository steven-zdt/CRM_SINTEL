import types


def test_crear_empresa_calls_db(monkeypatch):
    import apps.tenant.empresa.services.business_service as biz

    created = {}

    def _crear(data):
        created['ok'] = True
        class E:
            id = 1
        return E()

    # Patch the underlying crud primitive
    monkeypatch.setattr(biz, 'crear_empresa_db', _crear, raising=False)

    # Call business API
    empresa = biz.crear_empresa({'razon_social': 'X'})

    assert empresa.id == 1
    assert created.get('ok') is True


def test_update_empresa_when_missing_raises(monkeypatch):
    import apps.tenant.empresa.services.business_service as biz

    class _Mgr:
        def first(self):
            return None

    monkeypatch.setattr(biz, 'Empresa', types.SimpleNamespace(objects=_Mgr()))

    try:
        biz.actualizar_empresa({'razon_social': 'X'})
        raised = False
    except Exception:
        raised = True

    assert raised is True
