from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.cart_detail, name='cart'),
    path('cart/summary/', views.cart_summary, name='cart_summary'),
    path('cart/add/<int:pk>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:pk>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:pk>/', views.cart_remove, name='cart_remove'),
    path('checkout/', views.checkout, name='checkout'),
    path('order/success/', views.order_success, name='success'),
    path('track/<uuid:token>/', views.order_track, name='track'),
    path('track/<uuid:token>/status/', views.order_track_status, name='track_status'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/feed/', views.dashboard_feed, name='dashboard_feed'),
    path('dashboard/store/toggle/', views.dashboard_toggle_store, name='dashboard_toggle_store'),
    path('dashboard/<int:pk>/status/', views.dashboard_set_status, name='dashboard_status'),
]