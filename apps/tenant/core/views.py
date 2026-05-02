from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView


@method_decorator(ensure_csrf_cookie, name="dispatch")
class WorkspaceView(LoginRequiredMixin, TemplateView):
    template_name = 'tenant/core/workspace.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        # Inyectar el nombre de la empresa desde request.tenant
        context['empresa_nombre'] = getattr(getattr(request, 'tenant', None), 'nombre', 'Empresa')
        context['user'] = request.user
        return context
