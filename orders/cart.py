from decimal import Decimal
from menu.models import MenuItem

CART_SESSION_ID = 'cart'
MAX_QTY = 20

class Cart:
    """Session-based cart. Stores only {item_pk: quantity}; prices come from the DB."""

    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.setdefault(CART_SESSION_ID, {})

    def add(self, item, quantity=1, override=False):
        key = str(item.pk)
        current = 0 if override else self.cart.get(key, 0)
        self.cart[key] = max(1, min(current + quantity, MAX_QTY))
        self.save()

    def remove(self, item_pk):
        self.cart.pop(str(item_pk), None)
        self.save()

    def clear(self):
        self.session.pop(CART_SESSION_ID, None)
        self.session.modified = True

    def save(self):
        self.session.modified = True

    def __iter__(self):
        items = MenuItem.objects.filter(pk__in=self.cart.keys(), is_available=True)
        for item in items:
            qty = self.cart[str(item.pk)]
            yield {
                'item': item,
                'quantity': qty,
                'subtotal': item.price * qty,
            }

    def __len__(self):
        return sum(self.cart.values())

    def total(self):
        return sum((row['subtotal'] for row in self), Decimal('0.00'))
