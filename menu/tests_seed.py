"""Tests for the seed_demo management command."""
import shutil
import tempfile
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from orders.models import Order

from .management.commands.seed_demo import IMAGES, PRODUCTS, SAMPLE_ORDERS
from .models import Category, MenuItem

TMP_MEDIA = tempfile.mkdtemp(prefix='seed-test-media-')


def seed(*args):
    out = StringIO()
    call_command('seed_demo', *args, stdout=out, stderr=out)
    return out.getvalue()


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class SeedDemoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def test_creates_all_products_with_images(self):
        seed()
        self.assertEqual(MenuItem.objects.count(), len(PRODUCTS))
        for item in MenuItem.objects.all():
            self.assertTrue(item.image, item.name)
            self.assertTrue(item.image.storage.exists(item.image.name), item.name)
            self.assertTrue(item.description, item.name)
            self.assertTrue(item.is_available)

    def test_creates_expected_categories(self):
        seed()
        self.assertEqual(
            set(Category.objects.values_list('name', flat=True)),
            {'Coffees', 'Cold Drinks', 'Breakfast', 'Desserts', 'Tea'})

    def test_is_idempotent(self):
        seed()
        out = seed()
        self.assertEqual(MenuItem.objects.count(), len(PRODUCTS))
        self.assertIn(f'0 created, 0 updated, {len(PRODUCTS)} already existed', out)

    def test_does_not_overwrite_existing_product(self):
        cat = Category.objects.create(name='Coffees')
        MenuItem.objects.create(category=cat, name='Americano', price='99.00', description='mine')
        seed()
        item = MenuItem.objects.get(name='Americano')
        self.assertEqual((item.price, item.description), (Decimal('99.00'), 'mine'))
        self.assertFalse(item.image)

    def test_force_overwrites_demo_product(self):
        cat = Category.objects.create(name='Coffees')
        MenuItem.objects.create(category=cat, name='Americano', price='99.00', description='mine')
        seed('--force')
        item = MenuItem.objects.get(name='Americano')
        self.assertEqual(item.price, Decimal('3.25'))
        self.assertTrue(item.image)

    def test_same_name_in_other_category_is_not_confused(self):
        other = Category.objects.create(name='Coffee')  # similar-looking duplicate category
        MenuItem.objects.create(category=other, name='Americano', price='1.00')
        seed()
        self.assertEqual(MenuItem.objects.filter(name='Americano').count(), 2)

    def test_creates_store_settings(self):
        from orders.models import StoreSettings
        seed()
        self.assertTrue(StoreSettings.objects.filter(pk=1).exists())

    def test_without_orders_flag_creates_no_orders(self):
        seed()
        self.assertEqual(Order.objects.count(), 0)

    def test_with_orders_creates_consistent_orders(self):
        seed('--with-orders')
        self.assertEqual(Order.objects.count(), len(SAMPLE_ORDERS))
        for order in Order.objects.all():
            self.assertTrue(order.items.exists())
            self.assertEqual(order.total, sum(i.subtotal for i in order.items.all()))
        statuses = set(Order.objects.values_list('status', flat=True))
        self.assertTrue({'pending', 'preparing', 'ready', 'completed', 'cancelled'} <= statuses)

    def test_with_orders_is_idempotent(self):
        seed('--with-orders')
        out = seed('--with-orders')
        self.assertEqual(Order.objects.count(), len(SAMPLE_ORDERS))
        self.assertIn('already exist', out)

    def test_demo_orders_visible_on_dashboard(self):
        from django.contrib.auth import get_user_model
        seed('--with-orders')
        self.client.force_login(get_user_model().objects.create_user('s', password='x', is_staff=True))
        r = self.client.get('/dashboard/')
        self.assertEqual(r.context['today_count'], len(SAMPLE_ORDERS) - 1)  # cancelled not counted

    def test_menu_pages_render_with_seed_data(self):
        seed()
        self.assertContains(self.client.get('/menu/'), 'Tiramisu')
        self.assertContains(self.client.get('/'), 'Avocado Toast')  # the one featured demo item


class SeedAssetsTests(TestCase):
    """The repo must ship every photo the command references (media/ is gitignored)."""

    def test_every_product_has_an_image_file(self):
        for slug, *_ in PRODUCTS:
            self.assertTrue((IMAGES / f'{slug}.jpg').exists(), slug)

    def test_no_orphan_images(self):
        used = {f'{slug}.jpg' for slug, *_ in PRODUCTS}
        on_disk = {p.name for p in IMAGES.glob('*.jpg')}
        self.assertEqual(on_disk, used)

    def test_every_image_is_credited(self):
        credits = (IMAGES / 'ATTRIBUTIONS.md').read_text()
        for slug, *_ in PRODUCTS:
            self.assertIn(f'{slug}.jpg', credits)

    def test_images_are_valid_and_uniform(self):
        from PIL import Image
        for p in IMAGES.glob('*.jpg'):
            with Image.open(p) as im:
                im.verify()
            with Image.open(p) as im:
                self.assertEqual(im.size, (900, 600), p.name)

    def test_product_names_and_slugs_unique(self):
        names = [(c, n) for _, c, n, *_ in PRODUCTS]
        slugs = [s for s, *_ in PRODUCTS]
        self.assertEqual(len(set(names)), len(names))
        self.assertEqual(len(set(slugs)), len(slugs))

    def test_sample_orders_reference_seeded_products(self):
        names = {n for _, _, n, *_ in PRODUCTS}
        for *_, lines in SAMPLE_ORDERS:
            for pname, qty in lines:
                self.assertIn(pname, names)
                self.assertGreater(qty, 0)


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class RefreshOrdersTests(TestCase):
    def age_orders(self, days=3):
        from datetime import timedelta
        from django.utils import timezone
        Order.objects.update(created_at=timezone.now() - timedelta(days=days))

    def today_ids(self):
        from django.utils import timezone
        midnight = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        return set(Order.objects.filter(created_at__gte=midnight).values_list('pk', flat=True))

    def test_refresh_without_previous_orders_creates_them(self):
        seed('--refresh-orders')
        self.assertEqual(Order.objects.count(), len(SAMPLE_ORDERS))

    def test_refresh_recreates_orders_dated_today(self):
        seed('--with-orders')
        self.age_orders()
        self.assertEqual(self.today_ids(), set())  # dashboard would be empty
        seed('--refresh-orders')
        self.assertEqual(Order.objects.count(), len(SAMPLE_ORDERS))
        self.assertEqual(len(self.today_ids()), len(SAMPLE_ORDERS))

    def test_refresh_resets_statuses_changed_during_the_day(self):
        seed('--with-orders')
        Order.objects.update(status='completed')
        seed('--refresh-orders')
        statuses = set(Order.objects.values_list('status', flat=True))
        self.assertTrue({'pending', 'preparing', 'ready', 'completed', 'cancelled'} <= statuses)

    def test_refresh_never_touches_real_orders(self):
        real = Order.objects.create(customer_name='Real Customer', phone='1', total='5.00')
        seed('--with-orders')
        seed('--refresh-orders')
        seed('--refresh-orders')
        self.assertTrue(Order.objects.filter(pk=real.pk).exists())
        self.assertEqual(Order.objects.count(), len(SAMPLE_ORDERS) + 1)

    def test_refresh_is_repeatable_without_duplicates(self):
        for _ in range(3):
            seed('--refresh-orders')
        self.assertEqual(Order.objects.count(), len(SAMPLE_ORDERS))

    def test_refreshed_orders_have_items_and_consistent_totals(self):
        seed('--refresh-orders')
        for order in Order.objects.all():
            self.assertTrue(order.items.exists())
            self.assertEqual(order.total, sum(i.subtotal for i in order.items.all()))

    def test_timestamps_are_recent_and_never_in_the_future(self):
        from django.utils import timezone
        seed('--refresh-orders')
        now = timezone.now()
        for order in Order.objects.all():
            self.assertLessEqual(order.created_at, now)
            self.assertGreaterEqual(order.created_at, now - timezone.timedelta(days=1))

    def test_refresh_even_right_after_midnight_stays_on_today(self):
        from datetime import datetime
        from unittest import mock
        from zoneinfo import ZoneInfo
        fake_now = datetime(2026, 11, 21, 0, 10, tzinfo=ZoneInfo('UTC'))
        with mock.patch('django.utils.timezone.now', return_value=fake_now):
            seed('--refresh-orders')
        # an order "62 minutes ago" would be yesterday: it must be clamped to today
        self.assertEqual(Order.objects.filter(created_at__lt=fake_now.replace(hour=0, minute=0)).count(), 0)

    def test_new_orders_get_new_tracking_tokens(self):
        seed('--with-orders')
        old = set(Order.objects.values_list('token', flat=True))
        seed('--refresh-orders')
        self.assertEqual(old & set(Order.objects.values_list('token', flat=True)), set())

    def test_plain_with_orders_still_skips_when_present(self):
        seed('--with-orders')
        before = set(Order.objects.values_list('pk', flat=True))
        out = seed('--with-orders')
        self.assertEqual(before, set(Order.objects.values_list('pk', flat=True)))
        self.assertIn('--refresh-orders', out)  # tells the user how to recreate them

    def test_dashboard_shows_orders_after_refresh(self):
        from django.contrib.auth import get_user_model
        seed('--with-orders')
        self.age_orders()
        seed('--refresh-orders')
        self.client.force_login(get_user_model().objects.create_user('s', password='x', is_staff=True))
        r = self.client.get('/dashboard/')
        self.assertEqual(r.context['today_count'], len(SAMPLE_ORDERS) - 1)  # cancelled not counted
