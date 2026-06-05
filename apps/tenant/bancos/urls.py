from django.urls import path
from apps.tenant.bancos.api.viewsets import ExtractoBancarioViewSet

app_name = "bancos"

urlpatterns = [
    path("", ExtractoBancarioViewSet.as_view({"get": "list"}), name="bancos-list"),
]
