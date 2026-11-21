"""Populate the shop with 40 demo products (8 per category, with photos) and, optionally, sample orders.

    python manage.py seed_demo                 # add missing demo products
    python manage.py seed_demo --with-orders   # also create sample orders for the dashboard
    python manage.py seed_demo --refresh-orders  # recreate the sample orders dated "today" (run daily)
    python manage.py seed_demo --force         # overwrite price/description/image of demo products

Safe to run many times: existing products are left untouched unless --force is used.
Photos live in menu/fixtures/demo_images (credits in ATTRIBUTIONS.md).
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from menu.models import Category, MenuItem
from orders.models import Order, OrderItem, StoreSettings

IMAGES = Path(__file__).resolve().parents[2] / 'fixtures' / 'demo_images'

# (slug/image, category, name, price, featured, description)
PRODUCTS = [
    ('espresso', 'Coffees', 'Espresso', '3.50', True,
     'A concentrated shot of our signature house blend.'),
    ('latte', 'Coffees', 'Latte', '4.25', False,
     'Espresso with plenty of milk and a touch of foam.'),
    ('cappuccino', 'Coffees', 'Cappuccino', '4.50', True,
     'Espresso balanced with steamed milk and a thick layer of microfoam.'),
    ('americano', 'Coffees', 'Americano', '3.25', False,
     'Double espresso lengthened with hot water. Clean, bold and smooth.'),
    ('flat-white', 'Coffees', 'Flat White', '4.50', False,
     'Velvety microfoam over a double ristretto with a delicate latte-art finish.'),
    ('mocha', 'Coffees', 'Mocha', '4.95', False,
     'Espresso, steamed milk and dark chocolate, topped with whipped cream.'),
    ('macchiato', 'Coffees', 'Macchiato', '3.60', False,
     'A shot of espresso "marked" with a spoonful of silky milk foam.'),
    ('cortado', 'Coffees', 'Cortado', '3.95', False,
     'Equal parts espresso and warm milk: smooth, balanced and not too strong.'),
    ('chocolate-frappe', 'Cold Drinks', 'Chocolate Frappe', '5.50', True,
     'Rich chocolate blended with ice and milk, finished with whipped cream.'),
    ('vanilla-frappe', 'Cold Drinks', 'Vanilla Frappe', '5.25', False,
     'Iced coffee blended with ice and vanilla.'),
    ('lemonade', 'Cold Drinks', 'Lemonade', '3.95', False,
     'Fresh lemonade with a hint of mint.'),
    ('iced-mocha', 'Cold Drinks', 'Iced Mocha', '5.25', False,
     'Chilled espresso, chocolate and milk over ice. Our summer bestseller.'),
    ('orange-juice', 'Cold Drinks', 'Fresh Orange Juice', '4.25', False,
     'Squeezed to order from ripe oranges. Nothing added, nothing taken away.'),
    ('cold-brew', 'Cold Drinks', 'Cold Brew', '4.75', False,
     'Steeped for 18 hours and served over a big ice cube. Low acidity, naturally sweet.'),
    ('strawberry-smoothie', 'Cold Drinks', 'Strawberry Smoothie', '5.50', False,
     'Fresh strawberries blended with yogurt and a touch of honey.'),
    ('iced-tea', 'Cold Drinks', 'Iced Tea', '3.75', False,
     'House-brewed black tea with fresh lemon, lightly sweetened.'),
    ('matcha-latte', 'Tea', 'Matcha Latte', '5.25', False,
     'Ceremonial-grade matcha whisked with steamed milk. Earthy and creamy.'),
    ('chai-latte', 'Tea', 'Chai Latte', '4.75', False,
     'Spiced black tea with cinnamon, cardamom and ginger, finished with steamed milk.'),
    ('black-tea', 'Tea', 'English Breakfast Tea', '3.25', False,
     'A classic robust black tea, served in a pot with milk on the side.'),
    ('jasmine-tea', 'Tea', 'Jasmine Green Tea', '3.75', False,
     'Delicate green tea scented with jasmine blossoms. Light, floral and calming.'),
    ('earl-grey', 'Tea', 'Earl Grey', '3.50', False,
     'Black tea scented with bergamot orange, served in a pot.'),
    ('chamomile', 'Tea', 'Chamomile Tea', '3.50', False,
     'A soothing caffeine-free infusion of whole chamomile flowers with a hint of honey.'),
    ('mint-tea', 'Tea', 'Moroccan Mint Tea', '3.95', False,
     'Fresh mint leaves steeped in tea and lightly sweetened, the traditional way.'),
    ('hibiscus-tea', 'Tea', 'Hibiscus Tea', '4.25', False,
     'Ruby-red, tart and refreshing. Served chilled over ice with a slice of lime.'),
    ('pancakes', 'Breakfast', 'Pancakes', '8.50', True,
     'Three fluffy buttermilk pancakes served with real maple syrup.'),
    ('avocado-toast', 'Breakfast', 'Avocado Toast', '9.50', True,
     'Sourdough, smashed avocado, cherry tomatoes and arugula with chili flakes.'),
    ('eggs-benedict', 'Breakfast', 'Eggs Benedict', '11.00', False,
     'Poached eggs and ham on a toasted muffin with silky hollandaise.'),
    ('granola-bowl', 'Breakfast', 'Granola Bowl', '7.75', False,
     'Greek yogurt, house granola, sliced apple and a drizzle of honey.'),
    ('waffles', 'Breakfast', 'Waffles with Berries', '9.25', False,
     'Golden Belgian waffles with fresh strawberries and a dusting of powdered sugar.'),
    ('french-toast', 'Breakfast', 'French Toast', '8.75', False,
     'Thick brioche slices soaked in vanilla custard, griddled and finished with butter and maple syrup.'),
    ('omelette', 'Breakfast', 'Cheese Omelette', '8.95', False,
     'Three free-range eggs folded around melted cheese, served with a side of greens.'),
    ('bagel', 'Breakfast', 'Bagel with Cream Cheese', '5.25', False,
     'Freshly baked bagel, toasted and spread with whipped cream cheese.'),
    ('brownie', 'Desserts', 'Brownie', '4.50', False,
     'Chocolate walnut brownie, served warm.'),
    ('cheesecake', 'Desserts', 'Cheesecake', '6.00', True,
     'Classic, creamy New York style cheesecake with a graham cracker crust.'),
    ('croissant', 'Desserts', 'Croissant', '3.75', False,
     'Flaky, buttery, and baked fresh daily in-house.'),
    ('tiramisu', 'Desserts', 'Tiramisu', '6.75', False,
     'Espresso-soaked ladyfingers layered with mascarpone cream and cocoa.'),
    ('blueberry-muffin', 'Desserts', 'Blueberry Muffin', '3.95', False,
     'Baked every morning with plump blueberries and a crumbly sugar top.'),
    ('choc-chip-cookie', 'Desserts', 'Chocolate Chip Cookie', '2.95', False,
     'Crisp edges, gooey center and big chunks of dark chocolate.'),
    ('cinnamon-roll', 'Desserts', 'Cinnamon Roll', '4.50', False,
     'Soft swirled dough with cinnamon sugar, baked fresh and served warm.'),
    ('macarons', 'Desserts', 'Macarons', '6.50', False,
     'A box of assorted French macarons: pistachio, vanilla, chocolate and more.'),
]

# (customer, phone, type, status, notes, minutes ago, [(product name, qty), ...])
SAMPLE_ORDERS = [
    ('Demo - Sofia R.', '555-0101', 'pickup', 'pending', 'Oat milk please', 3, [('Flat White', 2), ('Blueberry Muffin', 1)]),
    ('Demo - Marcus T.', '555-0102', 'dine_in', 'pending', '', 8, [('Eggs Benedict', 1), ('Cold Brew', 1)]),
    ('Demo - Aiko N.', '555-0103', 'pickup', 'preparing', 'Extra hot', 14, [('Matcha Latte', 1), ('Avocado Toast', 1)]),
    ('Demo - Daniel P.', '555-0104', 'pickup', 'preparing', '', 21, [('Americano', 1), ('Cinnamon Roll', 2)]),
    ('Demo - Lucia M.', '555-0105', 'dine_in', 'ready', '', 33, [('Tiramisu', 1), ('Macchiato', 1)]),
    ('Demo - Omar H.', '555-0106', 'pickup', 'completed', '', 47, [('Iced Mocha', 2)]),
    ('Demo - Hannah B.', '555-0107', 'pickup', 'cancelled', 'Changed my mind', 62, [('Granola Bowl', 1)]),
]

DEMO_PREFIX = 'Demo - '


class Command(BaseCommand):
    help = 'Create demo categories, products (with photos) and optionally sample orders.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Overwrite price, description and image of existing demo products.')
        parser.add_argument('--with-orders', action='store_true',
                            help='Also create sample orders (skipped if demo orders already exist).')
        parser.add_argument('--refresh-orders', action='store_true',
                            help='Delete the demo orders and recreate them dated today '
                                 '(real orders are never touched). Meant for a daily timer.')

    @transaction.atomic
    def handle(self, *args, **opts):
        created = updated = skipped = 0
        for slug, cat_name, name, price, featured, desc in PRODUCTS:
            category, _ = Category.objects.get_or_create(name=cat_name)
            item = MenuItem.objects.filter(category=category, name=name).first()
            if item and not opts['force']:
                skipped += 1
                continue
            if item:
                item.price, item.description, item.is_featured = Decimal(price), desc, featured
                updated += 1
            else:
                item = MenuItem(category=category, name=name, price=Decimal(price),
                                description=desc, is_featured=featured, is_available=True)
                created += 1
            item.save()
            self._attach_image(item, slug)

        StoreSettings.load()  # make sure the settings row exists
        self.stdout.write(self.style.SUCCESS(
            f'Products: {created} created, {updated} updated, {skipped} already existed.'))

        if opts['refresh_orders']:
            _, per_model = Order.objects.filter(customer_name__startswith=DEMO_PREFIX).delete()
            self.stdout.write(f"Removed {per_model.get('orders.Order', 0)} old demo orders.")
            self._seed_orders()
        elif opts['with_orders']:
            self._seed_orders()

    def _attach_image(self, item, slug):
        path = IMAGES / f'{slug}.jpg'
        if not path.exists():
            self.stderr.write(self.style.WARNING(f'Missing image: {path.name}'))
            return
        if item.image:
            item.image.delete(save=False)
        item.image.save(f'{slug}.jpg', ContentFile(path.read_bytes()), save=True)

    def _seed_orders(self):
        if Order.objects.filter(customer_name__startswith=DEMO_PREFIX).exists():
            self.stdout.write('Demo orders already exist, skipping (use --refresh-orders to recreate).')
            return
        now = timezone.now()
        midnight = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
        n = 0
        for customer, phone, otype, status, notes, minutes_ago, lines in SAMPLE_ORDERS:
            items = []
            for pname, qty in lines:
                item = MenuItem.objects.filter(name=pname).order_by('-image').first()
                if item:
                    items.append((item, qty))
            if not items:
                continue
            order = Order.objects.create(
                customer_name=customer, phone=phone, order_type=otype, status=status, notes=notes,
                total=sum((i.price * q for i, q in items), Decimal('0.00')))
            OrderItem.objects.bulk_create([
                OrderItem(order=order, menu_item=i, name=i.name, price=i.price, quantity=q)
                for i, q in items])
            # "N minutes ago", but never before today's midnight so the dashboard (today only) shows it
            created = max(now - timedelta(minutes=minutes_ago), midnight + timedelta(seconds=n + 1))
            Order.objects.filter(pk=order.pk).update(created_at=created)
            n += 1
        self.stdout.write(self.style.SUCCESS(f'Sample orders created: {n} (dated today, visible in /dashboard/).'))
