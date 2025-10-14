from django.urls import path
from . import views

urlpatterns = [
    path('graphics/', views.graphics, name='graphics'),
    path('sellingsugg/', views.selling, name='selling_suggestions'),
    path('restock-recommendations/', views.restock_recommendations, name='restock_recommendations'),
    path('slow-inventory-alerts/', views.slow_inventory_alerts, name='slow_inventory_alerts'),
]
