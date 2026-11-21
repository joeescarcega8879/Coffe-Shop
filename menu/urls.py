from django.urls import path
from . import dashboard, views

app_name = 'menu'

urlpatterns = [
    path('', views.home, name='home'),
    path('menu/', views.menu_list, name='menu_list'),
    path('menu/<int:pk>/', views.menu_detail, name='menu_detail'),
    path('contact/', views.contact, name='contact'),

    # Owner dashboard: products (staff only)
    path('dashboard/products/', dashboard.products, name='dash_products'),
    path('dashboard/products/add/', dashboard.product_add, name='dash_product_add'),
    path('dashboard/products/<int:pk>/edit/', dashboard.product_edit, name='dash_product_edit'),
    path('dashboard/products/<int:pk>/toggle/', dashboard.product_toggle, name='dash_product_toggle'),
    path('dashboard/products/<int:pk>/delete/', dashboard.product_delete, name='dash_product_delete'),
]