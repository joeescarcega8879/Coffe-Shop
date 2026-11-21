"""Owner dashboard: product management (staff only)."""
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.auth import dashboard_required

from .forms import ProductForm
from .models import Category, MenuItem

FEATURED_SLOTS = 6  # the home page shows at most this many featured items


def _back(request, default='menu:dash_products'):
    """Redirect to the page the action came from (keeps search/filter), if safe."""
    target = request.POST.get('next', '')
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect(default)


@dashboard_required
def products(request):
    items = MenuItem.objects.select_related('category')
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    if q:
        items = items.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if category.isdigit():
        items = items.filter(category_id=int(category))
    return render(request, 'dashboard/products.html', {
        'items': items.order_by('category__name', 'name'),
        'categories': Category.objects.all(),
        'q': q,
        'category': category,
        'total': MenuItem.objects.count(),
        'hidden_count': MenuItem.objects.filter(is_available=False).count(),
        'featured_count': MenuItem.objects.filter(is_featured=True, is_available=True).count(),
        'featured_slots': FEATURED_SLOTS,
    })


def _product_form(request, instance=None):
    form = ProductForm(request.POST or None, request.FILES or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        messages.success(request, f'"{item.name}" saved.')
        return redirect('menu:dash_products')
    return render(request, 'dashboard/product_form.html', {
        'form': form, 'item': instance, 'has_categories': Category.objects.exists()})


@dashboard_required
def product_add(request):
    return _product_form(request)


@dashboard_required
def product_edit(request, pk):
    return _product_form(request, get_object_or_404(MenuItem, pk=pk))


@dashboard_required
@require_POST
def product_toggle(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    field = {'available': 'is_available', 'featured': 'is_featured'}.get(request.POST.get('field'))
    if field:
        setattr(item, field, not getattr(item, field))
        item.save(update_fields=[field, 'updated_at'])
    return _back(request)


@dashboard_required
@require_POST
def product_delete(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    name, image = item.name, item.image
    item.delete()  # past orders keep their own copy of the name and price
    if image:
        image.storage.delete(image.name)
    messages.success(request, f'"{name}" deleted.')
    return _back(request)
