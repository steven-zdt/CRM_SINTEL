"""
URLs de la consola de administración pública.

Todas las rutas están bajo el prefijo /console/ y requieren autenticación y permisos de staff.
Las rutas deben coincidir EXACTAMENTE con las URLs usadas en los tests.
"""
from django.urls import path
from apps.public.console import views

app_name = 'console'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Tenants (API-First: DataTables consume /api/admin/v1/console/dt/tenants/)
    path('tenants/', views.TenantsListView.as_view(), name='tenants-list'),
    path('tenants/new/', views.TenantsNewView.as_view(), name='tenants-new'),
    path('tenants/status/', views.tenants_status_page, name='tenants-status'),  # Mantiene lógica HTMX
    
    # Usuarios (API-First: DataTables consume /api/admin/v1/console/dt/users/)
    path('users/', views.UsersListView.as_view(), name='users-list'),
    
    # Impuestos
    path('impuestos/', views.ImpuestosIndexView.as_view(), name='impuestos-index'),
    path('impuestos/catalogo/', views.ImpuestosCatalogoView.as_view(), name='impuestos-catalogo'),
    path('impuestos/ingesta/', views.impuestos_ingesta_list, name='impuestos-ingesta-list'),  # Mantiene lógica
    path('impuestos/ingesta/nuevo/', views.impuestos_ingesta_create, name='impuestos-ingesta-create'),  # Mantiene lógica
    path('impuestos/ingesta/<int:pk>/', views.impuestos_ingesta_detail, name='impuestos-ingesta-detail'),
    path('impuestos/ingesta/<int:pk>/delete/', views.impuestos_ingesta_delete, name='impuestos-ingesta-delete'),
    
    # Búsqueda tributaria
    path('impuestos/search/', views.ImpuestosSearchPageView.as_view(), name='impuestos-search-page'),
    path('impuestos/search/results/', views.impuestos_search_results, name='impuestos-search-results'),  # Mantiene lógica
    path('impuestos/search/health/', views.impuestos_search_health, name='impuestos-search-health'),  # Mantiene lógica
    
    # CRUD Catálogos: TipoImpuesto
    path('impuestos/tipos/', views.TiposListPageView.as_view(), name='console-impuestos-tipos'),
    path('impuestos/tipos/nuevo/', views.TipoFormNewView.as_view(), name='console-impuestos-tipo-form'),
    path('impuestos/tipos/<int:pk>/editar/', views.TipoFormEditView.as_view(), name='console-impuestos-tipo-edit'),
    path('impuestos/tipos/guardar/', views.tipo_save_proxy, name='console-impuestos-tipo-save'),  # Mantiene lógica proxy
    path('impuestos/tipos/<int:pk>/guardar/', views.tipo_save_proxy, name='console-impuestos-tipo-update'),  # Mantiene lógica proxy
    
    # Nuevos catálogos DIAN (v2.30+) - API-First
    path('impuestos/contribuyentes-tipos/', views.ContribuyentesTiposListView.as_view(), name='console-impuestos-contribuyentes-tipos'),
    path('impuestos/regimenes-renta/', views.RegimenesRentaListView.as_view(), name='console-impuestos-regimenes-renta'),
    path('impuestos/responsabilidades-rut/', views.ResponsabilidadesRUTListView.as_view(), name='console-impuestos-responsabilidades-rut'),
    path('impuestos/perfiles-tributarios/', views.PerfilesTributariosListView.as_view(), name='console-impuestos-perfiles-tributarios'),
    
    # JWT helper: obtener token desde sesión
    path('jwt/from-session/', views.jwt_from_session, name='console-jwt-from-session'),
]
