from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import StoreSettings


def _send(subject, body, to):
    if to:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=True)


def send_order_emails(order, request):
    """Confirmation to the customer + alert to the owner. Runs after the DB commit."""
    track_url = request.build_absolute_uri(order.get_absolute_url())
    lines = '\n'.join(f'  {i.quantity} x {i.name}  ${i.subtotal:.2f}' for i in order.items.all())
    body = (
        f'Hi {order.customer_name},\n\nThanks for your order #{order.pk}!\n\n'
        f'{lines}\n\nTotal: ${order.total:.2f}\n\nFollow it live: {track_url}\n'
    )
    owner = StoreSettings.load().notify_email

    def go():
        _send(f'Your order #{order.pk} is confirmed', body, order.email)
        _send(f'New order #{order.pk} - ${order.total:.2f}',
              f'{order.customer_name} ({order.phone}) - {order.get_order_type_display()}\n\n{lines}\n\n{order.notes}',
              owner)

    transaction.on_commit(go)
