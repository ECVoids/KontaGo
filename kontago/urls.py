"""
URL configuration for kontago project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from kontaG import views as kontaG_views
from django.conf.urls.static import static
from django.conf import settings




urlpatterns = [
    path('admin/', admin.site.urls),
    path('', kontaG_views.home, name='home'),  # Home page route
    path('product-entry/', kontaG_views.product_entry, name='product_entry'),
    path('product-takeout/', kontaG_views.product_takeout, name='product_takeout'),
    path('inventory/', kontaG_views.inventory_display, name='inventory_display'),
    path('delete-product/<int:product_id>/', kontaG_views.delete_product, name='delete_product'),
    path('add-unit/<int:product_id>/', kontaG_views.add_unit, name='add_unit'),
    path('suppliers/', kontaG_views.supplier_list, name='supplier_list'),
    path('suppliers/new/', kontaG_views.supplier_entry, name='supplier_entry'),
    path('suppliers/<int:supplier_id>/delete/', kontaG_views.delete_supplier, name='delete_supplier'),
    path("facturas/", kontaG_views.sales_list, name="sales_list"),
    path("facturas/nueva/", kontaG_views.register_invoice, name="register_invoice"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
