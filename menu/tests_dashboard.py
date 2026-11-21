"""Tests for the standalone owner dashboard: layout isolation and product management."""
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from orders.models import Order, OrderItem

from .images import MAX_SIDE, optimize_image
from .models import Category, MenuItem

TMP_MEDIA = tempfile.mkdtemp(prefix='dash-test-media-')


def image_file(size=(400, 300), mode='RGB', fmt='PNG', name='photo.png', color='red'):
    buf = BytesIO()
    Image.new(mode, size, color).save(buf, fmt)
    ctype = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp'}[fmt]
    return SimpleUploadedFile(name, buf.getvalue(), content_type=ctype)


class DashBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name='Coffees')
        cls.tea = Category.objects.create(name='Tea')
        cls.item = MenuItem.objects.create(name='Espresso', price='3.50', category=cls.cat, description='Strong')
        cls.staff = get_user_model().objects.create_user('staff', password='x', is_staff=True)
        cls.regular = get_user_model().objects.create_user('regular', password='x')

    def login(self):
        self.client.force_login(self.staff)

    def payload(self, **over):
        data = {'name': 'Mocha', 'category': self.cat.pk, 'price': '4.95', 'description': 'Choc',
                'is_available': 'on'}
        data.update(over)
        return data


# ---------------------------------------------------------------------------
# Standalone layout
# ---------------------------------------------------------------------------

class StandaloneLayoutTests(DashBase):
    def pages(self):
        return [reverse('orders:dashboard'), reverse('menu:dash_products'), reverse('menu:dash_product_add'),
                reverse('menu:dash_product_edit', args=[self.item.pk])]

    def test_dashboard_has_no_customer_navigation(self):
        self.login()
        for url in self.pages():
            html = self.client.get(url).content.decode()
            for customer_only in ('data-cart-drawer', 'data-open-cart', 'data-cart-badge', 'store-closed-bar',
                                  f'href="{reverse("menu:menu_list")}"', f'href="{reverse("menu:contact")}"',
                                  'href="/"', f'href="{reverse("orders:cart")}"', 'mobile-menu', 'cart.js'):
                self.assertNotIn(customer_only, html, f'{customer_only} leaked into {url}')

    def test_dashboard_is_hidden_from_search_engines(self):
        self.login()
        for url in self.pages():
            self.assertContains(self.client.get(url), 'noindex')

    def test_dashboard_has_its_own_navigation(self):
        self.login()
        html = self.client.get(reverse('orders:dashboard')).content.decode()
        for url in (reverse('orders:dashboard'), reverse('menu:dash_products'),
                    reverse('admin:orders_storesettings_change', args=[1]), reverse('orders:dashboard_logout')):
            self.assertIn(url, html)

    def test_active_tab_is_highlighted(self):
        self.login()
        orders = self.client.get(reverse('orders:dashboard')).content.decode()
        products = self.client.get(reverse('menu:dash_products')).content.decode()
        self.assertRegex(orders, r'href="%s" class="dash-tab is-active"' % reverse('orders:dashboard'))
        self.assertRegex(products, r'href="%s" class="dash-tab is-active"' % reverse('menu:dash_products'))
        self.assertNotRegex(products, r'href="%s" class="dash-tab is-active"' % reverse('orders:dashboard'))

    def test_customer_pages_do_not_use_the_dashboard_layout(self):
        self.login()
        html = self.client.get(reverse('menu:home')).content.decode()
        self.assertNotIn('data-dashboard-app', html)
        self.assertNotIn('noindex', html)

    def test_logout_requires_post_and_ends_the_session(self):
        self.login()
        self.assertEqual(self.client.get(reverse('orders:dashboard_logout')).status_code, 405)
        r = self.client.post(reverse('orders:dashboard_logout'))
        self.assertRedirects(r, reverse('orders:dashboard'), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse('orders:dashboard')).status_code, 302)  # login again

    def test_unauthenticated_users_are_sent_to_login(self):
        r = self.client.get(reverse('menu:dash_products'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/admin/login/', r['Location'])
        self.assertIn('next=/dashboard/products/', r['Location'])


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

class ProductPermissionTests(DashBase):
    def get_urls(self):
        return [reverse('menu:dash_products'), reverse('menu:dash_product_add'),
                reverse('menu:dash_product_edit', args=[self.item.pk])]

    def post_urls(self):
        return [reverse('menu:dash_product_add'), reverse('menu:dash_product_edit', args=[self.item.pk]),
                reverse('menu:dash_product_toggle', args=[self.item.pk]),
                reverse('menu:dash_product_delete', args=[self.item.pk])]

    def test_anonymous_and_non_staff_are_redirected(self):
        for who in (None, self.regular):
            self.client.logout()
            if who:
                self.client.force_login(who)
            for url in self.get_urls():
                self.assertEqual(self.client.get(url).status_code, 302, url)

    def test_non_staff_cannot_change_anything(self):
        self.client.force_login(self.regular)
        for url in self.post_urls():
            self.client.post(url, self.payload(name='Hacked', field='available'))
        self.assertEqual(MenuItem.objects.count(), 1)
        item = MenuItem.objects.get()
        self.assertEqual((item.name, item.is_available), ('Espresso', True))

    def test_anonymous_cannot_delete(self):
        self.client.post(reverse('menu:dash_product_delete', args=[self.item.pk]))
        self.assertTrue(MenuItem.objects.filter(pk=self.item.pk).exists())

    def test_state_changing_views_reject_get(self):
        self.login()
        for name in ('dash_product_toggle', 'dash_product_delete'):
            self.assertEqual(self.client.get(reverse(f'menu:{name}', args=[self.item.pk])).status_code, 405)


# ---------------------------------------------------------------------------
# Product list
# ---------------------------------------------------------------------------

class ProductListTests(DashBase):
    def setUp(self):
        self.login()
        MenuItem.objects.create(name='Hidden Latte', price='4.00', category=self.cat, is_available=False)
        MenuItem.objects.create(name='Green Tea', price='3.00', category=self.tea, is_featured=True)

    def test_lists_hidden_items_too(self):
        r = self.client.get(reverse('menu:dash_products'))
        self.assertContains(r, 'Hidden Latte')
        self.assertContains(r, 'Espresso')
        self.assertEqual(r.context['total'], 3)
        self.assertEqual(r.context['hidden_count'], 1)

    def test_search(self):
        r = self.client.get(reverse('menu:dash_products'), {'q': 'green'})
        self.assertContains(r, 'Green Tea')
        self.assertNotContains(r, 'Espresso')

    def test_category_filter(self):
        r = self.client.get(reverse('menu:dash_products'), {'category': self.tea.pk})
        self.assertContains(r, 'Green Tea')
        self.assertNotContains(r, 'Espresso')

    def test_garbage_category_filter_is_ignored(self):
        r = self.client.get(reverse('menu:dash_products'), {'category': "1; DROP TABLE"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['items']), 3)

    def test_no_results_message(self):
        self.assertContains(self.client.get(reverse('menu:dash_products'), {'q': 'zzz'}), 'No products match')

    def test_featured_counter_ignores_hidden_items(self):
        MenuItem.objects.filter(name='Green Tea').update(is_available=False)
        self.assertEqual(self.client.get(reverse('menu:dash_products')).context['featured_count'], 0)

    def test_featured_overflow_is_flagged(self):
        for i in range(7):
            MenuItem.objects.create(name=f'F{i}', price='1.00', category=self.cat, is_featured=True)
        r = self.client.get(reverse('menu:dash_products'))
        self.assertGreater(r.context['featured_count'], r.context['featured_slots'])
        self.assertContains(r, 'text-error font-bold')


# ---------------------------------------------------------------------------
# Create / edit / toggle / delete
# ---------------------------------------------------------------------------

@override_settings(MEDIA_ROOT=TMP_MEDIA)
class ProductCrudTests(DashBase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.login()

    def add(self, **over):
        files = over.pop('image', None)
        data = self.payload(**over)
        if files is not None:
            data['image'] = files
        return self.client.post(reverse('menu:dash_product_add'), data)

    # --- create
    def test_add_product_without_photo(self):
        r = self.add()
        self.assertRedirects(r, reverse('menu:dash_products'))
        item = MenuItem.objects.get(name='Mocha')
        self.assertEqual((str(item.price), item.category, item.is_available, item.is_featured),
                         ('4.95', self.cat, True, False))
        self.assertFalse(item.image)

    def test_new_product_appears_on_the_customer_menu(self):
        self.add(name='Caramel Latte')
        self.assertContains(self.client.get(reverse('menu:menu_list')), 'Caramel Latte')

    def test_unchecked_available_hides_it_from_customers(self):
        data = self.payload(name='Secret')
        del data['is_available']
        self.client.post(reverse('menu:dash_product_add'), data, follow=True)  # consumes the flash message
        self.assertTrue(MenuItem.objects.filter(name='Secret', is_available=False).exists())
        self.assertNotContains(self.client.get(reverse('menu:menu_list')), 'Secret')

    def test_add_with_photo_is_stored_as_optimized_jpeg(self):
        self.add(image=image_file((3000, 2000)))
        item = MenuItem.objects.get(name='Mocha')
        self.assertTrue(item.image.name.startswith('menu_items/'))
        self.assertTrue(item.image.name.endswith('.jpg'))
        with Image.open(item.image.path) as im:
            self.assertEqual(im.format, 'JPEG')
            self.assertEqual(max(im.size), MAX_SIDE)
            self.assertEqual(im.size, (1200, 800))  # aspect ratio kept

    def test_small_photo_is_not_upscaled(self):
        self.add(image=image_file((300, 200)))
        with Image.open(MenuItem.objects.get(name='Mocha').image.path) as im:
            self.assertEqual(im.size, (300, 200))

    def test_png_with_transparency_is_flattened_on_white(self):
        self.add(image=image_file((50, 50), mode='RGBA', color=(255, 0, 0, 0)))
        with Image.open(MenuItem.objects.get(name='Mocha').image.path) as im:
            self.assertEqual(im.mode, 'RGB')
            self.assertGreater(min(im.getpixel((25, 25))), 240)  # transparent -> white

    def test_webp_is_accepted(self):
        self.add(image=image_file(fmt='WEBP', name='p.webp'))
        self.assertTrue(MenuItem.objects.get(name='Mocha').image)

    def test_exif_orientation_is_applied(self):
        buf = BytesIO()
        img = Image.new('RGB', (400, 200), 'blue')
        exif = Image.Exif()
        exif[0x0112] = 6  # rotate 90
        img.save(buf, 'JPEG', exif=exif)
        up = SimpleUploadedFile('r.jpg', buf.getvalue(), content_type='image/jpeg')
        self.add(image=up)
        with Image.open(MenuItem.objects.get(name='Mocha').image.path) as im:
            self.assertEqual(im.size, (200, 400))

    def test_non_image_upload_is_rejected(self):
        bad = SimpleUploadedFile('virus.png', b'MZ not an image', content_type='image/png')
        r = self.add(image=bad)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(MenuItem.objects.filter(name='Mocha').exists())
        self.assertIn('image', r.context['form'].errors)

    def test_svg_and_html_uploads_are_rejected(self):
        for name, body, ctype in (('x.svg', b'<svg onload="alert(1)"/>', 'image/svg+xml'),
                                  ('x.html', b'<script>alert(1)</script>', 'text/html')):
            r = self.add(image=SimpleUploadedFile(name, body, content_type=ctype))
            self.assertEqual(r.status_code, 200, name)
        self.assertFalse(MenuItem.objects.filter(name='Mocha').exists())

    def test_oversized_upload_is_rejected(self):
        with self.settings():
            import menu.forms as forms_module
            original = forms_module.MAX_UPLOAD_BYTES
            forms_module.MAX_UPLOAD_BYTES = 100
            try:
                r = self.add(image=image_file((200, 200)))
            finally:
                forms_module.MAX_UPLOAD_BYTES = original
        self.assertContains(r, 'too large')
        self.assertFalse(MenuItem.objects.filter(name='Mocha').exists())

    def test_invalid_prices_are_rejected(self):
        for price in ('0', '-1', '0.001', 'abc', '10000', ''):
            self.add(name=f'P{price}', price=price)
        self.assertEqual(MenuItem.objects.count(), 1)  # only the fixture item

    def test_required_fields(self):
        r = self.add(name='', category='')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.context['form'].errors), {'name', 'category'})

    def test_duplicate_name_in_same_category_is_rejected_case_insensitively(self):
        r = self.add(name='  espresso ')
        self.assertContains(r, 'already exists in Coffees')
        self.assertEqual(MenuItem.objects.filter(category=self.cat).count(), 1)

    def test_same_name_in_another_category_is_allowed(self):
        self.add(name='Espresso', category=self.tea.pk)
        self.assertEqual(MenuItem.objects.filter(name='Espresso').count(), 2)

    def test_add_form_warns_when_no_categories_exist(self):
        Category.objects.all().delete()
        self.assertContains(self.client.get(reverse('menu:dash_product_add')), 'at least one category')

    def test_script_in_name_is_escaped(self):
        self.add(name='<script>alert(1)</script>')
        html = self.client.get(reverse('menu:dash_products')).content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)

    # --- edit
    def edit(self, item=None, **over):
        item = item or self.item
        data = {'name': item.name, 'category': item.category_id, 'price': str(item.price),
                'description': item.description, 'is_available': 'on'}
        data.update(over)
        return self.client.post(reverse('menu:dash_product_edit', args=[item.pk]), data)

    def test_edit_updates_fields(self):
        r = self.edit(price='9.99', name='Double Espresso')
        self.assertRedirects(r, reverse('menu:dash_products'))
        self.item.refresh_from_db()
        self.assertEqual((self.item.name, str(self.item.price)), ('Double Espresso', '9.99'))

    def test_edit_form_prefills_current_values(self):
        r = self.client.get(reverse('menu:dash_product_edit', args=[self.item.pk]))
        self.assertContains(r, 'value="Espresso"')
        self.assertContains(r, 'value="3.50"')

    def test_edit_can_keep_own_name(self):
        self.assertEqual(self.edit().status_code, 302)  # not flagged as a duplicate of itself

    def test_edit_without_new_photo_keeps_the_old_one(self):
        self.add(image=image_file())
        item = MenuItem.objects.get(name='Mocha')
        before = item.image.name
        self.edit(item)
        item.refresh_from_db()
        self.assertEqual(item.image.name, before)

    def test_replacing_photo_deletes_the_old_file(self):
        self.add(image=image_file())
        item = MenuItem.objects.get(name='Mocha')
        old_path = item.image.path
        self.edit(item, image=image_file(color='blue', name='new.png'))
        item.refresh_from_db()
        self.assertNotEqual(item.image.path, old_path)
        self.assertTrue(item.image.storage.exists(item.image.name))
        import os
        self.assertFalse(os.path.exists(old_path))

    def test_remove_photo_checkbox(self):
        self.add(image=image_file())
        item = MenuItem.objects.get(name='Mocha')
        path = item.image.path
        self.edit(item, remove_image='on')
        item.refresh_from_db()
        self.assertFalse(item.image)
        import os
        self.assertFalse(os.path.exists(path))

    def test_edit_unknown_product_404(self):
        self.assertEqual(self.client.get(reverse('menu:dash_product_edit', args=[9999])).status_code, 404)

    # --- toggle
    def toggle(self, field, item=None, **extra):
        return self.client.post(reverse('menu:dash_product_toggle', args=[(item or self.item).pk]),
                                {'field': field, **extra})

    def test_toggle_available_hides_and_shows_on_customer_menu(self):
        self.toggle('available')
        self.item.refresh_from_db()
        self.assertFalse(self.item.is_available)
        self.assertNotContains(self.client.get(reverse('menu:menu_list')), 'Espresso')
        self.assertEqual(self.client.get(reverse('menu:menu_detail', args=[self.item.pk])).status_code, 404)
        self.toggle('available')
        self.assertContains(self.client.get(reverse('menu:menu_list')), 'Espresso')

    def test_hidden_product_cannot_be_ordered(self):
        self.toggle('available')
        r = self.client.post(reverse('orders:cart_add', args=[self.item.pk]), {'quantity': 1})
        self.assertEqual(r.status_code, 404)

    def test_toggle_featured_shows_on_home(self):
        self.toggle('featured')
        self.assertContains(self.client.get(reverse('menu:home')), 'Espresso')
        self.toggle('featured')
        self.assertNotContains(self.client.get(reverse('menu:home')), 'Espresso')

    def test_toggle_unknown_field_is_ignored(self):
        before = self.item.price
        self.toggle('price')
        self.toggle('is_staff')
        self.item.refresh_from_db()
        self.assertEqual((str(self.item.price), self.item.is_available), (str(before), True))

    def test_toggle_redirects_back_to_filtered_list(self):
        r = self.toggle('available', next='/dashboard/products/?q=esp')
        self.assertRedirects(r, '/dashboard/products/?q=esp')

    def test_toggle_refuses_open_redirects(self):
        for evil in ('https://evil.example/', '//evil.example/', 'javascript:alert(1)'):
            r = self.toggle('available', next=evil)
            self.assertRedirects(r, reverse('menu:dash_products'), msg_prefix=evil)

    # --- delete
    def test_delete_removes_product_and_its_photo(self):
        self.add(image=image_file())
        item = MenuItem.objects.get(name='Mocha')
        path = item.image.path
        r = self.client.post(reverse('menu:dash_product_delete', args=[item.pk]))
        self.assertRedirects(r, reverse('menu:dash_products'))
        self.assertFalse(MenuItem.objects.filter(pk=item.pk).exists())
        import os
        self.assertFalse(os.path.exists(path))

    def test_delete_keeps_past_orders_intact(self):
        order = Order.objects.create(customer_name='Ana', phone='1', total='7.00')
        OrderItem.objects.create(order=order, menu_item=self.item, name='Espresso', price='3.50', quantity=2)
        self.client.post(reverse('menu:dash_product_delete', args=[self.item.pk]))
        line = OrderItem.objects.get()
        self.assertIsNone(line.menu_item)
        self.assertEqual((line.name, str(line.price), line.quantity), ('Espresso', '3.50', 2))
        self.assertEqual(Order.objects.get().total, 7)

    def test_flash_messages_are_shown(self):
        r = self.client.post(reverse('menu:dash_product_add'), self.payload(name='Flash'), follow=True)
        self.assertContains(r, '&quot;Flash&quot; saved')


# ---------------------------------------------------------------------------
# Image helper
# ---------------------------------------------------------------------------

class OptimizeImageTests(TestCase):
    def test_output_is_a_jpeg_named_after_the_original(self):
        out = optimize_image(image_file(name='My Cool Photo!.png'))
        self.assertEqual(out.name, 'my-cool-photo.jpg')
        self.assertEqual(out.content_type, 'image/jpeg')
        with Image.open(out) as im:
            self.assertEqual(im.format, 'JPEG')

    def test_output_is_smaller_than_a_huge_input(self):
        big = image_file((4000, 3000), fmt='PNG')
        self.assertLess(len(optimize_image(big).read()), big.size)

    def test_garbage_raises(self):
        with self.assertRaises(Exception):
            optimize_image(SimpleUploadedFile('a.png', b'nope'))
