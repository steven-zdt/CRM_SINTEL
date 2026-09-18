from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth.hashers import check_password
from django_tenants.utils import schema_context

User = get_user_model()

with schema_context("home"):
    user = User.objects.get(username="admin-1")
    session = SessionStore()
    session[ "_auth_user_id"] = str(user.pk)
    session["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
    session["_auth_user_hash"] = user.get_session_auth_hash()
    session.save()
    print("SESSION_KEY=" + session.session_key)
    print("USER_ID=" + str(user.pk))
