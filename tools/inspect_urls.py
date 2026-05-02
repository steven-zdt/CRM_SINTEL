import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

print('DJANGO_SETTINGS_MODULE=', os.environ.get('DJANGO_SETTINGS_MODULE'))

import config.api_urls as api
print('LEN config.api_urls.urlpatterns =', len(api.urlpatterns))
for i, p in enumerate(api.urlpatterns):
    try:
        pat = getattr(p, 'pattern', None)
    except Exception:
        pat = repr(p)
    print(f'{i}: {type(p)} - pattern={pat}')

print('\n-- Attempt to import apps.tenant.empresa.api.urls --')
try:
    import apps.tenant.empresa.api.urls as emp
    print('Loaded empresa.api.urls, router urls count =', len(getattr(emp, 'router').urls))
    for u in emp.router.urls:
        print('-', u)
except Exception:
    traceback.print_exc()

print('\n-- End')
