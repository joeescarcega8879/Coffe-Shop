from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from menu.models import Category, MenuItem

from .cart import MAX_QTY
from .models import Order, OrderItem

AJAX = {'HTTP_X_REQUESTED_WITH': 'fetch'}


class BaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cat = Category.objects.create(name='Coffees')
        cls.espresso = MenuItem.objects.create(name='Espresso', price=Decimal('2.50'), category=cat)
        cls.cake = MenuItem.objects.create(name='Cake', price=Decimal('4.00'), category=cat)
        cls.hidden = MenuItem.objects.create(
            name='Hidden', price=Decimal('1.00'), category=cat, is_available=False)

    def add(self, item, qty=1, **kw):
        return self.client.post(reverse('orders:cart_add', args=[item.pk]), {'quantity': qty}, **kw)


class CartTests(BaseTest):
    def test_add_redirects_to_cart(self):
        r = self.add(self.espresso, 2)
        self.assertRedirects(r, reverse('orders:cart'))
        self.assertEqual(self.client.session['cart'], {str(self.espresso.pk): 2})

    def test_add_accumulates(self):
        self.add(self.espresso, 1)
        self.add(self.espresso, 2)
        self.assertEqual(self.client.session['cart'][str(self.espresso.pk)], 3)

    def test_add_caps_at_max_qty(self):
        self.add(self.espresso, MAX_QTY + 50)
        self.assertEqual(self.client.session['cart'][str(self.espresso.pk)], MAX_QTY)

    def test_add_invalid_quantity_defaults_to_one(self):
        self.add(self.espresso, 'abc')
        self.assertEqual(self.client.session['cart'][str(self.espresso.pk)], 1)

    def test_add_negative_quantity_becomes_one(self):
        self.add(self.espresso, -5)
        self.assertEqual(self.client.session['cart'][str(self.espresso.pk)], 1)

    def test_add_unavailable_item_404(self):
        self.assertEqual(self.add(self.hidden).status_code, 404)

    def test_add_requires_post(self):
        r = self.client.get(reverse('orders:cart_add', args=[self.espresso.pk]))
        self.assertEqual(r.status_code, 405)

    def test_add_ajax_returns_json(self):
        r = self.add(self.espresso, 2, **AJAX)
        data = r.json()
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['total'], '5.00')
        self.assertEqual(data['added'], 'Espresso')

    def test_update_sets_quantity(self):
        self.add(self.espresso, 5)
        self.client.post(reverse('orders:cart_update', args=[self.espresso.pk]), {'quantity': 2})
        self.assertEqual(self.client.session['cart'][str(self.espresso.pk)], 2)

    def test_update_zero_removes(self):
        self.add(self.espresso, 5)
        self.client.post(reverse('orders:cart_update', args=[self.espresso.pk]), {'quantity': 0})
        self.assertNotIn(str(self.espresso.pk), self.client.session['cart'])

    def test_remove(self):
        self.add(self.espresso)
        r = self.client.post(reverse('orders:cart_remove', args=[self.espresso.pk]), **AJAX)
        self.assertEqual(r.json()['count'], 0)

    def test_summary_totals(self):
        self.add(self.espresso, 2)
        self.add(self.cake, 1)
        data = self.client.get(reverse('orders:cart_summary')).json()
        self.assertEqual(data['count'], 3)
        self.assertEqual(data['total'], '9.00')
        self.assertEqual(len(data['items']), 2)

    def test_unavailable_item_ignored_in_totals(self):
        self.add(self.espresso)
        session = self.client.session
        session['cart'][str(self.hidden.pk)] = 3
        session.save()
        data = self.client.get(reverse('orders:cart_summary')).json()
        self.assertEqual(data['total'], '2.50')
        self.assertEqual(len(data['items']), 1)

    def test_cart_page_renders(self):
        self.add(self.espresso)
        r = self.client.get(reverse('orders:cart'))
        self.assertContains(r, 'Espresso')

    def test_context_processor_cart_count(self):
        self.add(self.espresso, 3)
        r = self.client.get(reverse('orders:cart'))
        self.assertEqual(r.context['cart_count'], 3)


class CheckoutTests(BaseTest):
    data = {'customer_name': 'Ana', 'phone': '555', 'email': '', 'order_type': 'pickup', 'notes': ''}

    def test_empty_cart_redirects_to_menu(self):
        r = self.client.get(reverse('orders:checkout'))
        self.assertRedirects(r, reverse('menu:menu_list'))

    def test_get_renders_form(self):
        self.add(self.espresso)
        self.assertEqual(self.client.get(reverse('orders:checkout')).status_code, 200)

    def test_valid_checkout_creates_order(self):
        self.add(self.espresso, 2)
        self.add(self.cake, 1)
        r = self.client.post(reverse('orders:checkout'), self.data)
        self.assertRedirects(r, reverse('orders:success'))
        order = Order.objects.get()
        self.assertEqual(order.total, Decimal('9.00'))
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.items.count(), 2)
        line = order.items.get(name='Espresso')
        self.assertEqual((line.price, line.quantity), (Decimal('2.50'), 2))
        self.assertEqual(line.subtotal, Decimal('5.00'))

    def test_checkout_clears_cart(self):
        self.add(self.espresso)
        self.client.post(reverse('orders:checkout'), self.data)
        self.assertNotIn('cart', self.client.session)

    def test_invalid_form_keeps_cart_and_creates_nothing(self):
        self.add(self.espresso)
        r = self.client.post(reverse('orders:checkout'), {**self.data, 'customer_name': ''})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Order.objects.exists())
        self.assertIn('cart', self.client.session)

    def test_price_snapshot_survives_price_change(self):
        self.add(self.espresso)
        self.client.post(reverse('orders:checkout'), self.data)
        self.espresso.price = Decimal('9.99')
        self.espresso.save()
        self.assertEqual(OrderItem.objects.get().price, Decimal('2.50'))

    def test_order_item_survives_menu_item_deletion(self):
        self.add(self.espresso)
        self.client.post(reverse('orders:checkout'), self.data)
        self.espresso.delete()
        item = OrderItem.objects.get()
        self.assertIsNone(item.menu_item)
        self.assertEqual(item.name, 'Espresso')


class SuccessTests(BaseTest):
    def test_without_order_redirects_home(self):
        r = self.client.get(reverse('orders:success'))
        self.assertRedirects(r, reverse('menu:home'))

    def test_shows_last_order(self):
        self.add(self.espresso)
        self.client.post(reverse('orders:checkout'), CheckoutTests.data)
        r = self.client.get(reverse('orders:success'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['order'], Order.objects.get())
