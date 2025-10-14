from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('inventory/', views.inventory_display, name='inventory_display'),
    path('product-entry/', views.product_entry, name='product_entry'),
    path('product-takeout/', views.product_takeout, name='product_takeout'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/new/', views.supplier_entry, name='supplier_entry'),
    path('suppliers/<int:supplier_id>/delete/', views.delete_supplier, name='delete_supplier'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('add-unit/<int:product_id>/', views.add_unit, name='add_unit'),
    path('inventory/pdf/', views.inventory_pdf, name='inventory_pdf'),
]
