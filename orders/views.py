from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.auth import dashboard_required
from core.ratelimit import rate_limit
from menu.models import MenuItem

from .cart import Cart
from .forms import CheckoutForm
from .emails import send_order_emails
from .models import Order, OrderItem, StoreSettings

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


@rate_limit('checkout', limit=10, window=3600)
def checkout(request):
    cart = Cart(request)
    rows = list(cart)
    if not rows:
        messages.error(request, 'Your cart is empty.')
        return redirect('menu:menu_list')

    store = StoreSettings.load()
    if request.method == 'POST' and not store.is_open_now():
        messages.error(request, store.closed_message)
        return redirect('orders:cart')

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
            send_order_emails(order, request)
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



# ---------- Customer: order tracking ----------

def order_track(request, token):
    order = get_object_or_404(Order.objects.prefetch_related('items'), token=token)
    return render(request, 'orders/track.html', {
        'order': order,
        'steps': [(s, Order.Status(s).label) for s in Order.FLOW],
    })


def order_track_status(request, token):
    """Polled by the tracking page every few seconds."""
    order = get_object_or_404(Order, token=token)
    return JsonResponse({
        'status': order.status,
        'label': order.get_status_display(),
        'step': order.step,
        'done': order.status in ('completed', 'cancelled'),
    })


# ---------- Owner: dashboard (staff only) ----------

@dashboard_required
def dashboard(request):
    today = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    orders = Order.objects.filter(created_at__gte=today).prefetch_related('items')
    columns = [
        (s, Order.Status(s).label, [o for o in orders if o.status == s])
        for s in ('pending', 'preparing', 'ready', 'completed', 'cancelled')
    ]
    return render(request, 'orders/dashboard.html', {
        'columns': columns,
        'store': StoreSettings.load(),
        'today_total': sum((o.total for o in orders if o.status != 'cancelled'), Decimal('0.00')),
        'today_count': sum(1 for o in orders if o.status != 'cancelled'),
        'statuses': Order.Status.choices,
    })


@dashboard_required
@require_POST
def dashboard_set_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    status = request.POST.get('status')
    if status in Order.Status.values:
        order.status = status
        order.save(update_fields=['status'])
    return redirect('orders:dashboard')


@dashboard_required
@require_POST
def dashboard_toggle_store(request):
    store = StoreSettings.load()
    store.accepting_orders = not store.accepting_orders
    store.save(update_fields=['accepting_orders'])
    return redirect('orders:dashboard')


@dashboard_required
def dashboard_feed(request):
    """Polled by the dashboard to detect new orders without a page reload."""
    latest = Order.objects.order_by('-pk').first()
    return JsonResponse({
        'latest_id': latest.pk if latest else 0,
        'pending': Order.objects.filter(status=Order.Status.PENDING).count(),
    })
