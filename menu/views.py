from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .forms import ContactForm
from .models import Category, MenuItem, ContactMessage

def home(request):    
    """Home page: restaurant info + featured items."""
    featured_items = MenuItem.objects.filter(is_available=True, is_featured=True).select_related('category')[:6]
    categories = Category.objects.all()

    return render(request, 'menu/home.html', {
        'featured_items': featured_items,
        'categories': categories,})

def menu_list(request):
    """Full menu with optional category filter via ?categoria=slug."""
    category_slug = request.GET.get('categoria')
    items = MenuItem.objects.filter(is_available=True).select_related('category')

    if category_slug:
        items = items.filter(category__slug=category_slug)

    categories = Category.objects.all()

    return render(request, 'menu/menu_list.html', {
        'items': items,
        'categories': categories,
        'active_category': category_slug,
    })

def menu_detail(request, pk):
    """Single menu item detail page."""
    item = get_object_or_404(MenuItem, pk=pk, is_available=True)
    return render(request, 'menu/menu_detail.html', {'item': item})

def contact(request):
    """Contact page: restaurant info + validated form (POST -> ContactMessage)."""
    form = ContactForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you for your message! We will get back to you soon.')
            return redirect('menu:contact')
        messages.error(request, 'Please fix the highlighted fields.')

    return render(request, 'menu/contact.html', {'form': form})
