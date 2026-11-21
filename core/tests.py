"""Tests for production configuration: security settings, rate limiting and deploy files."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from core.ratelimit import client_ip, rate_limit
from menu.models import Category, MenuItem

BASE = Path(settings.BASE_DIR)
PROD_ENV = {
    'SECRET_KEY': 'x' * 20 + 'abcdefghijklmnopqrstuvwxyz0123456789' + 'Q!#$%&',
    'DEBUG': 'False',
    'ALLOWED_HOSTS': 'coffee.example.com, www.coffee.example.com',
    'CSRF_TRUSTED_ORIGINS': 'https://coffee.example.com',
    'DB_PATH': '/tmp/some-db.sqlite3',
    'MEDIA_ROOT': '/tmp/some-media',
    'TIME_ZONE': 'America/Mexico_City',
    'TRUST_PROXY': 'True',
}


def run_python(args, env_extra):
    env = {'PATH': os.environ.get('PATH', ''), **env_extra}
    return subprocess.run([sys.executable, *args], cwd=BASE, env=env,
                          capture_output=True, text=True, timeout=60)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class ProductionSettingsTests(TestCase):
    def test_check_deploy_has_no_issues(self):
        r = run_python(['manage.py', 'check', '--deploy'], PROD_ENV)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn('no issues', r.stderr + r.stdout)

    def test_production_values(self):
        code = (
            "import os, json, django; os.environ['DJANGO_SETTINGS_MODULE']='core.settings'; django.setup();"
            "from django.conf import settings as s;"
            "print(json.dumps(dict(hosts=s.ALLOWED_HOSTS, csrf=s.CSRF_TRUSTED_ORIGINS, db=str(s.DATABASES['default']['NAME']),"
            "media=str(s.MEDIA_ROOT), tz=s.TIME_ZONE, ssl=s.SECURE_SSL_REDIRECT, sess=s.SESSION_COOKIE_SECURE,"
            "csrfc=s.CSRF_COOKIE_SECURE, proxy=s.SECURE_PROXY_SSL_HEADER, hsts=s.SECURE_HSTS_SECONDS,"
            "trust=s.TRUST_PROXY_HEADERS, debug=s.DEBUG)))"
        )
        r = run_python(['-c', code], PROD_ENV)
        self.assertEqual(r.returncode, 0, r.stderr)
        v = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(v['hosts'], ['coffee.example.com', 'www.coffee.example.com'])
        self.assertEqual(v['csrf'], ['https://coffee.example.com'])
        self.assertEqual((v['db'], v['media']), ('/tmp/some-db.sqlite3', '/tmp/some-media'))
        self.assertEqual(v['tz'], 'America/Mexico_City')
        self.assertTrue(v['ssl'] and v['sess'] and v['csrfc'] and v['trust'])
        self.assertEqual(v['proxy'], ['HTTP_X_FORWARDED_PROTO', 'https'])
        self.assertEqual(v['hsts'], 3600)
        self.assertFalse(v['debug'])

    def test_ssl_redirect_can_be_disabled(self):
        code = ("import os, django; os.environ['DJANGO_SETTINGS_MODULE']='core.settings'; django.setup();"
                "from django.conf import settings as s; print(s.SECURE_SSL_REDIRECT)")
        r = run_python(['-c', code], {**PROD_ENV, 'SECURE_SSL_REDIRECT': 'False'})
        self.assertEqual(r.stdout.strip(), 'False')

    def test_dev_defaults_are_not_forced_to_https(self):
        self.assertFalse(settings.SESSION_COOKIE_SECURE)
        self.assertFalse(settings.SECURE_SSL_REDIRECT)
        self.assertFalse(settings.TRUST_PROXY_HEADERS)

    def test_whitenoise_middleware_right_after_security(self):
        mw = settings.MIDDLEWARE
        self.assertEqual(mw[0], 'django.middleware.security.SecurityMiddleware')
        self.assertEqual(mw[1], 'whitenoise.middleware.WhiteNoiseMiddleware')

    def test_static_storage_and_root(self):
        self.assertEqual(settings.STORAGES['staticfiles']['BACKEND'],
                         'whitenoise.storage.CompressedStaticFilesStorage')
        self.assertEqual(Path(settings.STATIC_ROOT), BASE / 'staticfiles')

    def test_staticfiles_is_gitignored(self):
        self.assertIn('staticfiles/', (BASE / '.gitignore').read_text().splitlines())

    def test_production_dependencies_pinned(self):
        reqs = (BASE / 'requirements.txt').read_text()
        self.assertRegex(reqs, r'(?m)^gunicorn==\d')
        self.assertRegex(reqs, r'(?m)^whitenoise==\d')


# ---------------------------------------------------------------------------
# Deploy files
# ---------------------------------------------------------------------------

class DeployFilesTests(TestCase):
    def test_env_example_documents_every_env_var_used_by_settings(self):
        used = set(re.findall(r"os\.environ\.get\(\s*'([A-Z_]+)'", (BASE / 'core' / 'settings.py').read_text()))
        used |= set(re.findall(r"_csv\('([A-Z_]+)'\)", (BASE / 'core' / 'settings.py').read_text()))
        documented = set(re.findall(r'(?m)^#?\s*([A-Z_]+)=', (BASE / '.env.example').read_text()))
        self.assertEqual(used - documented, set(), 'Undocumented env vars in .env.example')

    def test_env_example_has_no_real_secret(self):
        self.assertIn('SECRET_KEY=change-me', (BASE / '.env.example').read_text())

    def test_deploy_script_is_valid_and_executable(self):
        script = BASE / 'deploy' / 'deploy.sh'
        self.assertTrue(os.access(script, os.X_OK))
        r = subprocess.run(['bash', '-n', str(script)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('set -euo pipefail', script.read_text())

    def test_caddy_proxies_to_the_gunicorn_port(self):
        service = (BASE / 'deploy' / 'coffeeshop.service').read_text()
        caddy = (BASE / 'deploy' / 'Caddyfile').read_text()
        bind = re.search(r'--bind (127\.0\.0\.1:\d+)', service).group(1)
        self.assertIn(f'reverse_proxy {bind}', caddy)

    def test_service_and_paths_are_consistent(self):
        service = (BASE / 'deploy' / 'coffeeshop.service').read_text()
        env = (BASE / '.env.example').read_text()
        caddy = (BASE / 'deploy' / 'Caddyfile').read_text()
        self.assertIn('EnvironmentFile=/etc/coffeeshop/env', service)
        self.assertIn('core.wsgi:application', service)
        media = re.search(r'(?m)^MEDIA_ROOT=(\S+)', env).group(1)
        self.assertIn(f'root * {media}', caddy)  # Caddy serves the same folder Django writes to
        self.assertIn(media.rsplit('/', 1)[0], service)  # and the app may write there

    def test_caddy_upload_limit_is_not_below_the_app_photo_limit(self):
        from menu.images import MAX_UPLOAD_BYTES
        caddy = (BASE / 'deploy' / 'Caddyfile').read_text()
        limit_mb = int(re.search(r'max_size (\d+)MB', caddy).group(1))
        self.assertGreater(limit_mb * 1024 * 1024, MAX_UPLOAD_BYTES)  # room for form fields on top of the photo

    def test_demo_refresh_timer_runs_the_existing_command(self):
        service = (BASE / 'deploy' / 'coffeeshop-demo-refresh.service').read_text()
        timer = (BASE / 'deploy' / 'coffeeshop-demo-refresh.timer').read_text()
        self.assertIn('manage.py seed_demo --refresh-orders', service)
        self.assertIn('Type=oneshot', service)
        self.assertIn('EnvironmentFile=/etc/coffeeshop/env', service)
        self.assertIn('ReadWritePaths=/var/lib/coffeeshop', service)  # same sandbox as the app
        self.assertRegex(timer, r'OnCalendar=\*-\*-\* \d\d:\d\d:\d\d \S+')
        self.assertIn('Persistent=true', timer)
        self.assertIn('WantedBy=timers.target', timer)

    def test_deploy_docs_exist(self):
        text = (BASE / 'deploy' / 'README.md').read_text()
        for needle in ('seed_demo', 'createsuperuser', 'deploy.sh', 'ALLOWED_HOSTS', 'coffeeshop-demo-refresh.timer'):
            self.assertIn(needle, text)


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

@override_settings(RATELIMIT_ENABLED=True,
                   CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def post_checkout(self, ip='1.1.1.1', **extra):
        return self.client.post(reverse('orders:checkout'), {}, REMOTE_ADDR=ip, **extra)

    def add_item(self, ip='1.1.1.1'):
        cat = Category.objects.get_or_create(name='C')[0]
        item = MenuItem.objects.get_or_create(name='I', price='1.00', category=cat)[0]
        self.client.post(reverse('orders:cart_add', args=[item.pk]), {}, REMOTE_ADDR=ip)

    def test_checkout_blocked_after_limit(self):
        self.add_item()
        for _ in range(10):
            self.assertNotEqual(self.post_checkout().status_code, 429)
        r = self.post_checkout()
        self.assertEqual(r.status_code, 429)
        self.assertContains(r, 'Slow down', status_code=429)

    def test_get_requests_are_never_limited(self):
        self.add_item()
        for _ in range(15):
            self.assertEqual(self.client.get(reverse('orders:checkout'), REMOTE_ADDR='1.1.1.1').status_code, 200)

    def test_limit_is_per_ip(self):
        self.add_item()
        for _ in range(11):
            self.post_checkout('1.1.1.1')
        self.assertEqual(self.post_checkout('1.1.1.1').status_code, 429)
        self.assertNotEqual(self.post_checkout('2.2.2.2').status_code, 429)

    def test_contact_limit(self):
        url = reverse('menu:contact')
        for _ in range(5):
            self.assertNotEqual(self.client.post(url, {}, REMOTE_ADDR='3.3.3.3').status_code, 429)
        self.assertEqual(self.client.post(url, {}, REMOTE_ADDR='3.3.3.3').status_code, 429)

    def test_scopes_are_independent(self):
        for _ in range(6):
            self.client.post(reverse('menu:contact'), {}, REMOTE_ADDR='4.4.4.4')
        self.add_item('4.4.4.4')
        self.assertNotEqual(self.post_checkout('4.4.4.4').status_code, 429)

    def test_window_expires(self):
        url = reverse('menu:contact')
        with mock.patch('django.core.cache.backends.locmem.time.time', return_value=1000.0):
            for _ in range(6):
                last = self.client.post(url, {}, REMOTE_ADDR='5.5.5.5')
            self.assertEqual(last.status_code, 429)
        with mock.patch('django.core.cache.backends.locmem.time.time', return_value=1000.0 + 3601):
            self.assertNotEqual(self.client.post(url, {}, REMOTE_ADDR='5.5.5.5').status_code, 429)

    @override_settings(RATELIMIT_ENABLED=False)
    def test_can_be_disabled(self):
        url = reverse('menu:contact')
        for _ in range(8):
            self.assertNotEqual(self.client.post(url, {}, REMOTE_ADDR='6.6.6.6').status_code, 429)

    def test_forwarded_for_ignored_unless_proxy_is_trusted(self):
        url = reverse('menu:contact')
        for i in range(6):  # spoofed header values must not give a fresh quota
            r = self.client.post(url, {}, REMOTE_ADDR='7.7.7.7', HTTP_X_FORWARDED_FOR=f'9.9.9.{i}')
        self.assertEqual(r.status_code, 429)

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_forwarded_for_used_when_proxy_is_trusted(self):
        url = reverse('menu:contact')
        for _ in range(6):
            r = self.client.post(url, {}, REMOTE_ADDR='127.0.0.1', HTTP_X_FORWARDED_FOR='8.8.8.8')
        self.assertEqual(r.status_code, 429)
        # a different real client behind the same proxy is unaffected
        r = self.client.post(url, {}, REMOTE_ADDR='127.0.0.1', HTTP_X_FORWARDED_FOR='8.8.4.4')
        self.assertNotEqual(r.status_code, 429)

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_client_ip_uses_last_forwarded_entry(self):
        req = RequestFactory().get('/', HTTP_X_FORWARDED_FOR='6.6.6.6, 10.0.0.1, 203.0.113.9')
        self.assertEqual(client_ip(req), '203.0.113.9')  # spoofed leading entries are ignored

    def test_decorator_keeps_view_name(self):
        @rate_limit('x', 1, 60)
        def my_view(request):
            return None
        self.assertEqual(my_view.__name__, 'my_view')


class SocialMetaTests(TestCase):
    """Favicon and Open Graph tags so shared links render a proper card."""

    def test_home_has_favicon_and_absolute_og_image(self):
        html = self.client.get(reverse('menu:home')).content.decode()
        self.assertIn('rel="icon"', html)
        self.assertIn('property="og:title"', html)
        self.assertRegex(html, r'og:image" content="http://testserver/static/img/og-image\.jpg"')
        self.assertIn('twitter:card', html)

    def test_social_assets_exist(self):
        for name in ('favicon.svg', 'og-image.jpg'):
            self.assertTrue((Path(settings.BASE_DIR) / 'static' / 'img' / name).exists(), name)


class AccessibilityTests(TestCase):
    """Guards for the basics: skip link, labelled menu button, alt text, decorative icons."""

    def setUp(self):
        self.html = self.client.get(reverse('menu:home')).content.decode()

    def test_skip_link_targets_main(self):
        self.assertIn('href="#main"', self.html)
        self.assertIn('<main id="main"', self.html)

    def test_mobile_menu_button_is_wired_for_screen_readers(self):
        self.assertRegex(self.html, r'id="mobile-menu-btn"')
        self.assertIn('aria-expanded="false"', self.html)
        self.assertIn('aria-controls="mobile-menu"', self.html)
        self.assertIn('id="mobile-menu"', self.html)

    def test_icons_are_hidden_from_screen_readers(self):
        for tag in re.findall(r'<span[^>]*material-symbols-outlined[^>]*>', self.html):
            self.assertIn('aria-hidden="true"', tag)

    def test_every_image_has_alt_attribute(self):
        for tag in re.findall(r'<img\b[^>]*>', self.html, re.S):
            self.assertRegex(tag, r'\balt="', tag[:80])

    def test_low_contrast_accent_not_used_as_text_colour(self):
        for name in ('menu_list.html', 'menu_detail.html'):
            text = (Path(settings.BASE_DIR) / 'templates' / 'menu' / name).read_text()
            self.assertNotIn('text-[#C08552]', text)


class DashboardLoginTests(TestCase):
    """The owner signs in on our own page, not on the stock Django admin login."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.owner = User.objects.create_user('owner@example.com', password='s3cret-pass', is_staff=True)
        cls.customer = User.objects.create_user('someone', password='s3cret-pass')

    def url(self):
        return reverse('orders:dashboard_login')

    def test_page_is_branded_and_not_the_admin_login(self):
        html = self.client.get(self.url()).content.decode()
        self.assertIn('Coffee Shop', html)
        self.assertNotIn('Django administration', html)
        self.assertIn('noindex', html)

    def test_staff_can_sign_in_and_land_on_the_dashboard(self):
        r = self.client.post(self.url(), {'username': 'owner@example.com', 'password': 's3cret-pass'})
        self.assertRedirects(r, reverse('orders:dashboard'), fetch_redirect_response=False)

    def test_next_parameter_is_respected(self):
        r = self.client.post(self.url() + '?next=/dashboard/products/',
                             {'username': 'owner@example.com', 'password': 's3cret-pass', 'next': '/dashboard/products/'})
        self.assertRedirects(r, '/dashboard/products/', fetch_redirect_response=False)

    def test_wrong_password_shows_a_friendly_error(self):
        r = self.client.post(self.url(), {'username': 'owner@example.com', 'password': 'nope'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'do not match')

    def test_non_staff_account_is_rejected(self):
        r = self.client.post(self.url(), {'username': 'someone', 'password': 's3cret-pass'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'does not have access')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_admin_login_url_redirects_here_keeping_next(self):
        r = self.client.get('/admin/login/?next=/admin/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r['Location'], self.url() + '?next=/admin/')

    def test_admin_has_shop_branding(self):
        self.client.force_login(self.owner)
        html = self.client.get('/admin/').content.decode()
        self.assertIn('Coffee Shop admin', html)
        self.assertNotIn('Django administration', html)

    @override_settings(RATELIMIT_ENABLED=True)
    def test_repeated_attempts_are_rate_limited(self):
        cache.clear()
        for _ in range(10):
            self.client.post(self.url(), {'username': 'owner@example.com', 'password': 'bad'})
        self.assertEqual(self.client.post(self.url(), {'username': 'owner@example.com', 'password': 'bad'}).status_code, 429)
        cache.clear()
