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


@pytest.mark.django_db
def test_onboarding_ott_cookie_flow(client):
    """Integration-style test: create onboarding, consume OTT and verify HttpOnly cookies authenticate API calls."""
    base_create = "/api/public/v1/tenants/onboarding/create/"

    schema = "t" + uuid.uuid4().hex[:8]
    payload = {
        "company_name": schema,
        "admin_email": f"autotest+{schema}@local.test",
        "admin_password": "P@ssw0rd123!",
        "schema_name": schema,
    }

    # Create onboarding (public)
    r = client.post(base_create, data=json.dumps(payload), content_type="application/json", HTTP_HOST="localhost")
    assert r.status_code == 201, f"Onboarding create failed: {r.status_code} {r.content}"
    body = r.json()
    ott = body.get("ott")
    assert ott, "No OTT returned from onboarding create"

    # Consume OTT in tenant host (should set HttpOnly cookies)
    consume_url = "/api/v1/core/auth/consume-ott/"
    r2 = client.post(consume_url, data=json.dumps({"ott": ott}), content_type="application/json", HTTP_HOST=f"{schema}.sintel.com")
    assert r2.status_code == 200, f"Consume OTT failed: {r2.status_code} {r2.content}"

    # Response should have set cookies for session
    cookies = r2.cookies
    assert "sessionid" in cookies, "sessionid cookie not set"

    # Subsequent API calls should be authenticated when using the tenant host
    # The test client preserves cookies between requests
    r3 = client.get("/api/v1/empresas/mi-empresa/", HTTP_HOST=f"{schema}.sintel.com")
    assert r3.status_code == 200, f"Authenticated API call failed: {r3.status_code} {r3.content}"
