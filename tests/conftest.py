import pytest


@pytest.fixture
def client_factory(db, client):
    """Compatibility fixture used by a few onboarding tests.

    Returns the Django test `client`. Tests in this suite only require the
    fixture to exist and do not rely on factory behavior, so this simple
    pass-through keeps test intent while restoring compatibility.
    """
    return client
