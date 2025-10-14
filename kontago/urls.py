from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('inventory.urls')),    # incluye la home y demás rutas de inventario
    path('invoices/', include('invoices.urls')),  # incluye las rutas de facturación
    path('analytics/', include('analytics.urls')),  # incluye las rutas de análisis
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
