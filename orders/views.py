from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from menu.models import MenuItem

from .cart import Cart
from .forms import CheckoutForm
from .models import Order, OrderItem

def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'fetch'


def _payload(cart, **extra):
    """JSON snapshot of the cart used by the drawer and the cart page."""
    rows = list(cart)
    return {
        'count': sum(r['quantity'] for r in rows),
        'total': f"{sum((r['subtotal'] for r in rows), Decimal('0.00')):.2f}",
        'items': [
            {
                'pk': r['item'].pk,
                'name': r['item'].name,
                'price': f"{r['item'].price:.2f}",
                'image': r['item'].image.url if r['item'].image else '',
                'quantity': r['quantity'],
                'subtotal': f"{r['subtotal']:.2f}",
                'update_url': reverse('orders:cart_update', args=[r['item'].pk]),
                'remove_url': reverse('orders:cart_remove', args=[r['item'].pk]),
            }
            for r in rows
        ],
        **extra,
    }


def cart_summary(request):
    return JsonResponse(_payload(Cart(request)))


def cart_detail(request):
    cart = Cart(request)
    return render(request, 'orders/cart.html', {'rows': list(cart), 'total': cart.total()})

@require_POST
def cart_add(request, pk):
    item = get_object_or_404(MenuItem, pk=pk, is_available=True)
    try:
        qty = int(request.POST.get('quantity', 1))

    except ValueError:
        qty = 1
    cart = Cart(request)
    cart.add(item, quantity=max(qty, 1))
    if _is_ajax(request):
        return JsonResponse(_payload(cart, added=item.name))
    messages.success(request, f'{item.name} added to your order.')
    return redirect('orders:cart')

@require_POST
def cart_update(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    try:
        qty = int(request.POST.get('quantity', 1))
    except ValueError:
        qty = 1
    cart = Cart(request)
    if qty <= 0:
        cart.remove(pk)
    else:
        cart.add(item, quantity=qty, override=True)
    if _is_ajax(request):
        return JsonResponse(_payload(cart))
    return redirect('orders:cart')


@require_POST
def cart_remove(request, pk):
    cart = Cart(request)
    cart.remove(pk)
    if _is_ajax(request):
        return JsonResponse(_payload(cart))
    return redirect('orders:cart')


def checkout(request):
    cart = Cart(request)
    rows = list(cart)
    if not rows:
        messages.error(request, 'Your cart is empty.')
        return redirect('menu:menu_list')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.total = cart.total()
                order.save()
                OrderItem.objects.bulk_create([
                    OrderItem(
                        order=order,
                        menu_item=row['item'],
                        name=row['item'].name,
                        price=row['item'].price,
                        quantity=row['quantity'],
                    )
                    for row in rows
                ])
            cart.clear()
            request.session['last_order_id'] = order.pk
            return redirect('orders:success')
    else:
        form = CheckoutForm()

    return render(request, 'orders/checkout.html', {'form': form, 'rows': rows, 'total': cart.total()})


def order_success(request):
    order_id = request.session.get('last_order_id')
    if not order_id:
        return redirect('menu:home')
    order = get_object_or_404(Order, pk=order_id)
    return render(request, 'orders/success.html', {'order': order})
