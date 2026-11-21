from .cart import Cart
from .models import StoreSettings


def cart(request):
    return {'cart_count': len(Cart(request))}


def store(request):
    s = StoreSettings.load()
    return {'store_open': s.is_open_now(), 'store_closed_message': s.closed_message}
