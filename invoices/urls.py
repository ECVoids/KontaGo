from django.urls import path
from . import views

urlpatterns = [
    path('', views.sales_list, name='sales_list'),
    path('nueva/', views.register_invoice, name='register_invoice'),
    # Si en el módulo de facturación se tiene exportación pdf para facturas, agregarla aquí
    # por ejemplo: path('pdf/<int:factura_id>/', views.invoice_pdf, name='invoice_pdf'),
]
