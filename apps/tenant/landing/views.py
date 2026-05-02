"""
Compatibility views module for `apps.tenant.landing`.

Some tests import `apps.tenant.landing.views.TenantLandingView`. Provide a
minimal TemplateView implementation to satisfy imports and routing tests.
"""
from django.views.generic import TemplateView


class TenantLandingView(TemplateView):
    template_name = 'tenant/landing/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return ctx


__all__ = ['TenantLandingView']
