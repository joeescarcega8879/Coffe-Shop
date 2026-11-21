from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('menu_item', 'name', 'price', 'quantity')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'phone', 'order_type', 'total', 'status', 'created_at')
    list_filter = ('status', 'order_type', 'created_at')
    list_editable = ('status',)
    search_fields = ('customer_name', 'phone', 'email')
    readonly_fields = ('total', 'created_at')
    inlines = [OrderItemInline]