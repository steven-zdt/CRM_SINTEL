import json
import uuid

import pytest


class FakeRedis:
    def __init__(self, store):
        self.store = store

    def set(self, key, value, ex=None, px=None, nx=False, xx=False, keepttl=False):
        self.store[key] = value
        return True

    def get(self, key):
        return self.store.get(key)

    def delete(self, *keys):
        count = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                count += 1
        return count


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    store = {}
    fake = FakeRedis(store)
    monkeypatch.setattr("apps.public.tenants.services.onboarding._get_redis_client", lambda: fake)
    return fake


def _extract_ott_from_store(store: dict, schema: str) -> str:
    """
    REM ONBOARDING-01 (documentacion/AUDITORIA_ONBOARDING_TENANTS_2026-08-30.md
    Hallazgo #1): el OTT ya no viaja en la respuesta HTTP del create -- el
    unico canal valido es el email de activacion real que el tenant recibe.
    Para un test, leer el OTT directamente del Redis simulado equivale a
    "leer el correo que le habria llegado al usuario real".
    """
    for key, raw in store.items():
        if not key.startswith("onboard:"):
            continue
        payload = json.loads(raw)
        if payload.get("schema_name") == schema:
            return key.removeprefix("onboard:")
    raise AssertionError(f"No se encontro OTT en Redis para schema={schema}")


@pytest.mark.django_db
def test_onboarding_create_no_longer_leaks_ott_then_session_auth_works(client, mock_redis):
    """
    Integration-style test: create onboarding NO expone ott/redirect_url en
    la respuesta HTTP (regresion del Hallazgo #1 -- CRITICO); consumir el OTT
    (obtenido como lo haria el usuario real, via el "email" -- aqui, Redis
    simulado) establece sesion Django (`sessionid`, no JWT en cookie -- el
    diseno final tras REM ONBOARDING-02 es sesion estandar) que autentica
    llamadas subsecuentes.
    """
    base_create = "/api/public/v1/tenants/onboarding/create/"

    schema = "t" + uuid.uuid4().hex[:8]
    payload = {
        "company_name": schema,
        "admin_email": f"autotest+{schema}@local.test",
        "schema_name": schema,
    }

    # Create onboarding (public)
    r = client.post(base_create, data=json.dumps(payload), content_type="application/json", HTTP_HOST="localhost")
    assert r.status_code == 201, f"Onboarding create failed: {r.status_code} {r.content}"
    body = r.json()

    # REM ONBOARDING-01: la respuesta NUNCA debe incluir el ott ni el
    # redirect_url -- solo quien controla admin_email debe poder obtenerlo
    # (via el email de activacion, no cubierto en este test unitario).
    assert "ott" not in body, "Hallazgo #1 regresado: el OTT no debe viajar en la respuesta HTTP"
    assert "redirect_url" not in body, "Hallazgo #1 regresado: el redirect_url no debe viajar en la respuesta HTTP"

    # Simula "leer el email": obtener el OTT desde donde el usuario real lo
    # recibiria (aqui, el Redis simulado que el servicio ya escribio).
    ott = _extract_ott_from_store(mock_redis.store, schema)

    # Consume OTT en el host del tenant (deberia establecer sesion Django)
    consume_url = "/api/v1/core/auth/consume-ott/"
    r2 = client.post(consume_url, data=json.dumps({"ott": ott}), content_type="application/json", HTTP_HOST=f"{schema}.sintel.net.co")
    assert r2.status_code == 200, f"Consume OTT failed: {r2.status_code} {r2.content}"

    # Respuesta debe establecer cookie de sesion Django estandar (no JWT
    # custom en cookie -- ver REM ONBOARDING-02, el mecanismo HttpOnly/JWT
    # fue formalmente descontinuado, no solo dejado a medias).
    cookies = r2.cookies
    assert "sessionid" in cookies, "sessionid cookie not set"

    # Subsequent API calls should be authenticated when using the tenant host
    # The test client preserves cookies between requests
    r3 = client.get("/api/v1/empresas/mi-empresa/", HTTP_HOST=f"{schema}.sintel.net.co")
    assert r3.status_code == 200, f"Authenticated API call failed: {r3.status_code} {r3.content}"
