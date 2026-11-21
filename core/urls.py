from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

# Branding for the (rarely used) admin, and one single sign-in page for everything
admin.site.site_header = 'Coffee Shop admin'
admin.site.site_title = 'Coffee Shop admin'
admin.site.index_title = 'Shop settings'

urlpatterns = [
    path('admin/login/', RedirectView.as_view(pattern_name='orders:dashboard_login', query_string=True)),
    path('admin/', admin.site.urls),
    path('', include('menu.urls')),
    path('', include('orders.urls')),
]

# Servir MEDIA (imágenes subidas por Admin) solo en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
