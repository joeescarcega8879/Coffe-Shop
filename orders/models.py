import uuid
from datetime import time

from django.db import models
from django.urls import reverse
from django.utils import timezone
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

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
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

    def get_absolute_url(self):
        return reverse('orders:track', args=[self.token])

    # Happy-path steps shown in the tracker (cancelled is handled separately)
    FLOW = ['pending', 'preparing', 'ready', 'completed']

    @property
    def step(self):
        """0-based index in FLOW, or -1 when cancelled."""
        return self.FLOW.index(self.status) if self.status in self.FLOW else -1


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


class StoreSettings(models.Model):
    """Singleton (pk=1): lets the owner open/close the shop without touching code."""
    accepting_orders = models.BooleanField('Accepting orders', default=True)
    enforce_hours = models.BooleanField('Enforce opening hours', default=False,
                                        help_text='Off = open whenever "Accepting orders" is on.')
    opening_time = models.TimeField('Opens at', default=time(7, 0))
    closing_time = models.TimeField('Closes at', default=time(20, 0))
    closed_message = models.CharField(
        'Closed message', max_length=200,
        default="We're closed right now. Orders will reopen soon!")
    notify_email = models.EmailField('Send new-order alerts to', blank=True)

    class Meta:
        verbose_name = 'Store settings'
        verbose_name_plural = 'Store settings'

    def __str__(self):
        return 'Store settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def is_open_now(self, now=None):
        if not self.accepting_orders:
            return False
        if not self.enforce_hours:
            return True
        now = timezone.localtime(now or timezone.now()).time()
        if self.opening_time <= self.closing_time:
            return self.opening_time <= now < self.closing_time
        # overnight window, e.g. 18:00 -> 02:00
        return now >= self.opening_time or now < self.closing_time
