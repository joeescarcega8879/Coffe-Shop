from django.contrib import admin, messages
from django.db.models import Count

from .models import Order, OrderItem, StoreSettings


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('name', 'price', 'quantity', 'line_subtotal')
    readonly_fields = fields
    can_delete = False

    @admin.display(description='Subtotal')
    def line_subtotal(self, obj):
        return f'${obj.subtotal:.2f}'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'phone', 'order_type', 'items_count', 'total', 'status', 'created_at')
    list_display_links = ('id', 'customer_name')
    list_filter = ('status', 'order_type', 'created_at')
    list_editable = ('status',)
    search_fields = ('id', 'customer_name', 'phone', 'email')
    date_hierarchy = 'created_at'
    readonly_fields = ('token', 'total', 'created_at')
    inlines = [OrderItemInline]
    actions = ['mark_preparing', 'mark_ready', 'mark_completed', 'mark_cancelled']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_items=Count('items'))

    @admin.display(description='Items', ordering='_items')
    def items_count(self, obj):
        return obj._items

    def _set_status(self, request, queryset, status):
        n = queryset.update(status=status)
        self.message_user(request, f'{n} order(s) marked as {Order.Status(status).label}.', messages.SUCCESS)

    @admin.action(description='Mark as Preparing')
    def mark_preparing(self, request, queryset):
        self._set_status(request, queryset, Order.Status.PREPARING)

    @admin.action(description='Mark as Ready')
    def mark_ready(self, request, queryset):
        self._set_status(request, queryset, Order.Status.READY)

    @admin.action(description='Mark as Completed')
    def mark_completed(self, request, queryset):
        self._set_status(request, queryset, Order.Status.COMPLETED)

    @admin.action(description='Mark as Cancelled')
    def mark_cancelled(self, request, queryset):
        self._set_status(request, queryset, Order.Status.CANCELLED)


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not StoreSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
