"""
URLs para Core API.

⚠️ POLÍTICA:
- Endpoints de composición/orquestación para presentación
- NO reemplazan CRUD de las apps individuales
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.tenant.core.api.views import (
    CoreDashboardView,
    MiEmpresaView,
    MiPerfilView,
    MiPerfilConfiguracionView,
    FacturasResumenView,
    ContabilidadResumenView,
    LandingResumenView,
    CoreLoginView,
    CoreLogoutView,
    PasswordResetRequestView,
    PasswordResetValidateView,
    PasswordResetConfirmView,
    CoreLandingInfoView,
    CoreLandingActivateView,
    CoreRoutesView,
)
from apps.tenant.core.api.viewsets import CoreLinksViewSet, DashboardSectionsViewSet
from apps.tenant.core.api.viewsets_inventario import CoreInventarioViewSet
from apps.tenant.core.api import viewsets_documentos
from apps.tenant.core.api.views import (
    CoreMailIngestionRunAPIView,
    CoreMailIngestionRunsListAPIView,
    CoreMailIngestionConfigsListAPIView,
    CoreMailIngestionConfigTestAPIView,
    CoreMailIngestionRunStopAPIView,
    CoreMailIngestionRunDetailsAPIView,
    CoreMailIngestionRunDeleteAPIView,
)
from apps.tenant.core.api.views_empresa import (
    CoreEmpresaMailboxConfigsListCreateAPIView,
    CoreEmpresaMailboxConfigRetrieveUpdateDestroyAPIView,
)
from apps.tenant.core.api.views_contabilidad import (
    CoreContabilidadCuentasListCreateAPIView,
    CoreContabilidadCuentaRetrieveUpdateDestroyAPIView,
    CoreContabilidadAsientosListCreateAPIView,
    CoreContabilidadAsientoRetrieveUpdateDestroyAPIView,
    CoreContabilidadAsientoAprobarAPIView,
    CoreContabilidadMovimientosListCreateAPIView,
    CoreContabilidadMovimientoRetrieveUpdateDestroyAPIView,
)
from apps.tenant.core.api.health import HealthView

app_name = 'tenant_core_api'

# Router para ViewSets
router = DefaultRouter()

# FASE 8: Endpoint universal de documentos
router.register(
    r'documentos',
    viewsets_documentos.DocumentoUploadViewSet,
    basename='documentos'
)
router.register(r'links', CoreLinksViewSet, basename='core-links')
router.register(r'dashboard/sections', DashboardSectionsViewSet, basename='core-dashboard-sections')
router.register(r"inventario", CoreInventarioViewSet, basename="core-inventario")

urlpatterns = [
    # ⚠️ FASE 5: Healthcheck
    path('health/', HealthView.as_view(), name='tenant-health'),
    
    # ⚠️ OLA 1: Core Routes API - Descubrimiento centralizado de rutas
    path('routes/', CoreRoutesView.as_view(), name='core-routes'),
    
    # Dashboard completo (compuesto de múltiples apps)
    path('dashboard/', CoreDashboardView.as_view(), name='dashboard'),
    
    # Información de empresa
    path('mi-empresa/', MiEmpresaView.as_view(), name='mi-empresa'),  # Legacy (mantener por compatibilidad)
    path('empresa/', MiEmpresaView.as_view(), name='empresa'),  # ⚠️ v2.30: Core API como orquestador único
    path('empresa/mailbox/configs/', CoreEmpresaMailboxConfigsListCreateAPIView.as_view(), name='empresa-mailbox-configs'),
    path('empresa/mailbox/configs/<int:config_id>/', CoreEmpresaMailboxConfigRetrieveUpdateDestroyAPIView.as_view(), name='empresa-mailbox-config-detail'),
    
    # Contabilidad (Core API)
    path('contabilidad/cuentas/', CoreContabilidadCuentasListCreateAPIView.as_view(), name='contabilidad-cuentas'),
    path('contabilidad/cuentas/<int:cuenta_id>/', CoreContabilidadCuentaRetrieveUpdateDestroyAPIView.as_view(), name='contabilidad-cuenta-detail'),
    path('contabilidad/asientos/', CoreContabilidadAsientosListCreateAPIView.as_view(), name='contabilidad-asientos'),
    path('contabilidad/asientos/<int:asiento_id>/', CoreContabilidadAsientoRetrieveUpdateDestroyAPIView.as_view(), name='contabilidad-asiento-detail'),
    path('contabilidad/asientos/<int:asiento_id>/aprobar/', CoreContabilidadAsientoAprobarAPIView.as_view(), name='contabilidad-asiento-aprobar'),
    path('contabilidad/movimientos/', CoreContabilidadMovimientosListCreateAPIView.as_view(), name='contabilidad-movimientos'),
    path('contabilidad/movimientos/<int:movimiento_id>/', CoreContabilidadMovimientoRetrieveUpdateDestroyAPIView.as_view(), name='contabilidad-movimiento-detail'),
    
    # Perfil del usuario
    path('mi-perfil/', MiPerfilView.as_view(), name='mi-perfil'),
    path('mi-perfil/configuracion/', MiPerfilConfiguracionView.as_view(), name='mi-perfil-configuracion'),
    
    # Resúmenes por app
    path('facturas/resumen/', FacturasResumenView.as_view(), name='facturas-resumen'),
    path('contabilidad/resumen/', ContabilidadResumenView.as_view(), name='contabilidad-resumen'),
    path('landing/resumen/', LandingResumenView.as_view(), name='landing-resumen'),
    
    # Landing (Core Facade - UI única)
    path('landing/info/', CoreLandingInfoView.as_view(), name='core-landing-info'),
    path('landing/auth/activate/', CoreLandingActivateView.as_view(), name='core-landing-activate'),
    
    # Auth (Core Facade - Centralizado)
    path('auth/login/', CoreLoginView.as_view(), name='core-login'),
    path('auth/logout/', CoreLogoutView.as_view(), name='core-logout'),
    
    # Password Reset (Core Facade)
    path('auth/password-reset/request/', PasswordResetRequestView.as_view(), name='core-password-reset-request'),
    path('auth/password-reset/validate/', PasswordResetValidateView.as_view(), name='core-password-reset-validate'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='core-password-reset-confirm'),
    
    # Link Registry (ViewSet)
    path('', include(router.urls)),
    
    # Ingesta por correo (Fase 4 - Opcional)
    path('maildigester/run/', CoreMailIngestionRunAPIView.as_view(), name='core_maildigester_run'),
    path('maildigester/runs/', CoreMailIngestionRunsListAPIView.as_view(), name='core_maildigester_runs'),
    path('maildigester/configs/', CoreMailIngestionConfigsListAPIView.as_view(), name='core_maildigester_configs'),
    path('maildigester/configs/test/', CoreMailIngestionConfigTestAPIView.as_view(), name='core_maildigester_config_test'),
    path('maildigester/run/<int:run_id>/stop/', CoreMailIngestionRunStopAPIView.as_view(), name='core_maildigester_run_stop'),
    path('maildigester/run/<int:run_id>/details/', CoreMailIngestionRunDetailsAPIView.as_view(), name='core_maildigester_run_details'),
    path('maildigester/run/<int:run_id>/', CoreMailIngestionRunDeleteAPIView.as_view(), name='core_maildigester_run_delete'),
]
