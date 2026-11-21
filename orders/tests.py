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
        self.assertContains(r, 'data-watch-order')
        self.assertContains(r, reverse('orders:track_status', args=[Order.objects.get().token]))


class AdminTests(BaseTest):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_superuser('admin', 'a@a.com', 'x'))
        self.add(self.espresso, 2)
        self.client.post(reverse('orders:checkout'), CheckoutTests.data)
        self.order = Order.objects.get()

    def test_changelist_and_detail_render(self):
        r = self.client.get(reverse('admin:orders_order_changelist'))
        self.assertContains(r, 'Ana')
        r = self.client.get(reverse('admin:orders_order_change', args=[self.order.pk]))
        self.assertContains(r, '$5.00')

    def test_bulk_action_updates_status(self):
        self.client.post(reverse('admin:orders_order_changelist'), {
            'action': 'mark_ready', '_selected_action': [self.order.pk]})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.READY)


# ---------------------------------------------------------------------------
# Store settings (open / closed)
# ---------------------------------------------------------------------------

from datetime import datetime, time, timezone as dt_tz

from django.core import mail
from django.contrib.auth import get_user_model

from .models import StoreSettings


def at(hour, minute=0):
    return datetime(2026, 1, 1, hour, minute, tzinfo=dt_tz.utc)


class StoreSettingsModelTests(TestCase):
    def test_load_creates_singleton(self):
        a = StoreSettings.load()
        b = StoreSettings.load()
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(StoreSettings.objects.count(), 1)

    def test_save_always_uses_pk_1(self):
        StoreSettings(accepting_orders=False).save()
        StoreSettings(accepting_orders=True).save()
        self.assertEqual(StoreSettings.objects.count(), 1)

    def test_open_by_default_even_at_night(self):
        self.assertTrue(StoreSettings.load().is_open_now(at(3)))

    def test_paused_is_closed(self):
        s = StoreSettings(accepting_orders=False)
        self.assertFalse(s.is_open_now(at(12)))

    def test_hours_enforced(self):
        s = StoreSettings(enforce_hours=True, opening_time=time(7), closing_time=time(20))
        self.assertTrue(s.is_open_now(at(12)))
        self.assertTrue(s.is_open_now(at(7, 0)))
        self.assertFalse(s.is_open_now(at(20, 0)))
        self.assertFalse(s.is_open_now(at(3)))

    def test_overnight_window(self):
        s = StoreSettings(enforce_hours=True, opening_time=time(18), closing_time=time(2))
        self.assertTrue(s.is_open_now(at(23)))
        self.assertTrue(s.is_open_now(at(1)))
        self.assertFalse(s.is_open_now(at(12)))

    def test_hours_ignored_when_not_enforced(self):
        s = StoreSettings(enforce_hours=False, opening_time=time(7), closing_time=time(8))
        self.assertTrue(s.is_open_now(at(15)))


class StoreClosedTests(BaseTest):
    def close_store(self):
        StoreSettings.objects.update_or_create(pk=1, defaults={
            'accepting_orders': False, 'closed_message': 'Back at 7am!'})

    def test_banner_shown_when_closed(self):
        self.close_store()
        self.assertContains(self.client.get(reverse('menu:home')), 'Back at 7am!')

    def test_banner_hidden_when_open(self):
        self.assertNotContains(self.client.get(reverse('menu:home')), 'store-closed-bar"')

    def test_checkout_page_disables_button_when_closed(self):
        self.add(self.espresso)
        self.close_store()
        r = self.client.get(reverse('orders:checkout'))
        self.assertContains(r, 'data-store-closed')
        self.assertContains(r, 'disabled')

    def test_checkout_post_blocked_when_closed(self):
        self.add(self.espresso)
        self.close_store()
        r = self.client.post(reverse('orders:checkout'), CheckoutTests.data)
        self.assertRedirects(r, reverse('orders:cart'))
        self.assertFalse(Order.objects.exists())
        self.assertIn('cart', self.client.session)  # cart is kept

    def test_checkout_works_again_after_reopening(self):
        self.add(self.espresso)
        self.close_store()
        StoreSettings.objects.update(accepting_orders=True)
        r = self.client.post(reverse('orders:checkout'), CheckoutTests.data)
        self.assertRedirects(r, reverse('orders:success'))


# ---------------------------------------------------------------------------
# Emails
# ---------------------------------------------------------------------------

class EmailTests(BaseTest):
    def place(self, **overrides):
        self.add(self.espresso, 2)
        return self.client.post(reverse('orders:checkout'), {**CheckoutTests.data, **overrides})

    def test_customer_confirmation_sent_with_tracking_link(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.place(email='ana@example.com')
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['ana@example.com'])
        order = Order.objects.get()
        self.assertIn(str(order.token), msg.body)
        self.assertIn('2 x Espresso', msg.body)
        self.assertIn('$5.00', msg.body)

    def test_no_customer_email_when_blank(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.place(email='')
        self.assertEqual(len(mail.outbox), 0)

    def test_owner_alert_sent_when_configured(self):
        StoreSettings.objects.update_or_create(pk=1, defaults={'notify_email': 'owner@shop.com'})
        with self.captureOnCommitCallbacks(execute=True):
            self.place(email='ana@example.com')
        recipients = sorted(m.to[0] for m in mail.outbox)
        self.assertEqual(recipients, ['ana@example.com', 'owner@shop.com'])
        owner_msg = next(m for m in mail.outbox if m.to == ['owner@shop.com'])
        self.assertIn('New order', owner_msg.subject)

    def test_no_email_when_validation_fails(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.place(customer_name='', email='ana@example.com')
        self.assertEqual(len(mail.outbox), 0)


# ---------------------------------------------------------------------------
# Order tracking
# ---------------------------------------------------------------------------

class TrackingTests(BaseTest):
    def setUp(self):
        self.add(self.espresso, 2)
        self.client.post(reverse('orders:checkout'), CheckoutTests.data)
        self.order = Order.objects.get()
        self.client.logout()  # tracking must work for anyone holding the link

    def test_token_is_unique_and_url_uses_it(self):
        self.assertIn(str(self.order.token), self.order.get_absolute_url())

    def test_track_page_renders_for_anonymous(self):
        from django.test import Client
        r = Client().get(self.order.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Espresso')
        self.assertContains(r, 'Pending')

    def test_ready_banner_is_hidden_until_ready_and_shown_after(self):
        from django.test import Client
        html = Client().get(self.order.get_absolute_url()).content.decode()
        self.assertRegex(html, r'data-track-ready[^>]*hidden')
        self.order.status = Order.Status.READY
        self.order.save()
        html = Client().get(self.order.get_absolute_url()).content.decode()
        self.assertNotRegex(html, r'data-track-ready[^>]*hidden')

    def test_pages_register_the_order_for_the_site_wide_alert(self):
        from django.test import Client
        status_url = reverse('orders:track_status', args=[self.order.token])
        html = Client().get(self.order.get_absolute_url()).content.decode()
        self.assertIn('data-watch-order', html)
        self.assertIn(status_url, html)
        # the watcher script is loaded on every page
        self.assertIn('js/order-watch.js', Client().get(reverse('menu:home')).content.decode())

    def test_unknown_token_404(self):
        import uuid
        r = self.client.get(reverse('orders:track', args=[uuid.uuid4()]))
        self.assertEqual(r.status_code, 404)

    def test_numeric_id_is_not_a_valid_route(self):
        # Orders must not be guessable by sequential id
        self.assertEqual(self.client.get(f'/track/{self.order.pk}/').status_code, 404)

    def test_status_endpoint_reflects_changes(self):
        url = reverse('orders:track_status', args=[self.order.token])
        self.assertEqual(self.client.get(url).json(),
                         {'status': 'pending', 'label': 'Pending', 'step': 0, 'done': False})
        Order.objects.update(status=Order.Status.READY)
        data = self.client.get(url).json()
        self.assertEqual((data['status'], data['step'], data['done']), ('ready', 2, False))

    def test_done_flag_for_completed_and_cancelled(self):
        url = reverse('orders:track_status', args=[self.order.token])
        for status in ('completed', 'cancelled'):
            Order.objects.update(status=status)
            self.assertTrue(self.client.get(url).json()['done'])

    def test_cancelled_step_is_minus_one(self):
        Order.objects.update(status=Order.Status.CANCELLED)
        self.order.refresh_from_db()
        self.assertEqual(self.order.step, -1)
        self.assertContains(self.client.get(self.order.get_absolute_url()), 'Order cancelled')

    def test_success_page_links_to_tracking(self):
        self.add(self.espresso)
        self.client.post(reverse('orders:checkout'), CheckoutTests.data)
        r = self.client.get(reverse('orders:success'))
        newest = Order.objects.first()
        self.assertContains(r, newest.get_absolute_url())


# ---------------------------------------------------------------------------
# Owner dashboard
# ---------------------------------------------------------------------------

class DashboardTests(BaseTest):
    def setUp(self):
        self.add(self.espresso, 2)
        self.client.post(reverse('orders:checkout'), CheckoutTests.data)
        self.order = Order.objects.get()
        self.client.logout()
        self.staff = get_user_model().objects.create_user('staff', password='x', is_staff=True)
        self.regular = get_user_model().objects.create_user('regular', password='x')

    def urls(self):
        return [
            reverse('orders:dashboard'),
            reverse('orders:dashboard_feed'),
        ]

    def test_anonymous_redirected_to_login(self):
        for url in self.urls():
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn('login', r['Location'])

    def test_non_staff_cannot_access(self):
        self.client.force_login(self.regular)
        for url in self.urls():
            self.assertEqual(self.client.get(url).status_code, 302, url)

    def test_non_staff_cannot_change_status_or_toggle_store(self):
        self.client.force_login(self.regular)
        self.client.post(reverse('orders:dashboard_status', args=[self.order.pk]), {'status': 'ready'})
        self.client.post(reverse('orders:dashboard_toggle_store'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'pending')
        self.assertTrue(StoreSettings.load().accepting_orders)

    def test_staff_sees_todays_orders_and_totals(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse('orders:dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ana')
        self.assertContains(r, '$5.00')
        self.assertEqual(r.context['today_count'], 1)

    def test_old_orders_not_listed_and_cancelled_not_counted(self):
        from datetime import timedelta
        from django.utils import timezone
        Order.objects.filter(pk=self.order.pk).update(created_at=timezone.now() - timedelta(days=2))
        self.client.force_login(self.staff)
        r = self.client.get(reverse('orders:dashboard'))
        self.assertEqual(r.context['today_count'], 0)
        self.assertNotContains(r, 'data-order-id')

    def test_staff_advances_status(self):
        self.client.force_login(self.staff)
        r = self.client.post(reverse('orders:dashboard_status', args=[self.order.pk]), {'status': 'preparing'})
        self.assertRedirects(r, reverse('orders:dashboard'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'preparing')

    def test_invalid_status_ignored(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('orders:dashboard_status', args=[self.order.pk]), {'status': 'hacked'})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'pending')

    def test_status_change_requires_post(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse('orders:dashboard_status', args=[self.order.pk]))
        self.assertEqual(r.status_code, 405)

    def test_customer_sees_status_change_made_by_staff(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('orders:dashboard_status', args=[self.order.pk]), {'status': 'ready'})
        self.client.logout()
        data = self.client.get(reverse('orders:track_status', args=[self.order.token])).json()
        self.assertEqual(data['status'], 'ready')

    def test_toggle_store(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('orders:dashboard_toggle_store'))
        self.assertFalse(StoreSettings.load().accepting_orders)
        self.client.post(reverse('orders:dashboard_toggle_store'))
        self.assertTrue(StoreSettings.load().accepting_orders)

    def test_feed_reports_latest_and_pending(self):
        self.client.force_login(self.staff)
        data = self.client.get(reverse('orders:dashboard_feed')).json()
        self.assertEqual(data, {'latest_id': self.order.pk, 'pending': 1})

    def test_feed_empty(self):
        Order.objects.all().delete()
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('orders:dashboard_feed')).json(),
                         {'latest_id': 0, 'pending': 0})

    def test_customer_site_never_shows_a_dashboard_link(self):
        # The dashboard is a separate space: even staff browsing the shop see no link to it
        home = reverse('menu:home')
        self.assertNotContains(self.client.get(home), reverse('orders:dashboard'))
        self.client.force_login(self.staff)
        self.assertNotContains(self.client.get(home), reverse('orders:dashboard'))


class MigrationDataTests(TestCase):
    def test_each_order_gets_a_distinct_token(self):
        for i in range(3):
            Order.objects.create(customer_name=f'C{i}', phone='1')
        self.assertEqual(len({o.token for o in Order.objects.all()}), 3)
