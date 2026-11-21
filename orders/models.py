from django.db import models
from menu.models import MenuItem

class Order(models.Model):

    class Type(models.TextChoices):
        PICKUP = 'pickup', 'Pickup'
        DINE_IN = 'dine_in', 'Dine In'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PREPARING = 'preparing', 'Preparing'
        READY = 'ready', 'Ready'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    customer_name = models.CharField('Name', max_length=100)
    phone = models.CharField('Phone', max_length=20)
    email = models.EmailField('Email', blank=True)
    order_type = models.CharField('Order Type', max_length=10, choices=Type.choices, default=Type.PICKUP)
    notes = models.TextField('Notes', blank=True)
    status = models.CharField('Status', max_length=10, choices=Status.choices, default=Status.PENDING)
    total = models.DecimalField('Total', max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField('Created At', auto_now_add=True)


    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.pk} - {self.customer_name}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField('Name', max_length=100)
    price = models.DecimalField('Price', max_digits=6, decimal_places=2)
    quantity = models.PositiveIntegerField('Quantity', default=1)

    def __str__(self):
        return f'{self.quantity} x {self.name}'

    @property
    def subtotal(self):
        return self.price * self.quantity
