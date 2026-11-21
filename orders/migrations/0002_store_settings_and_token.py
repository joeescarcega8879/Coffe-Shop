import datetime
import uuid

from django.db import migrations, models


def fill_tokens(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    for order in Order.objects.all():
        order.token = uuid.uuid4()
        order.save(update_fields=['token'])


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accepting_orders', models.BooleanField(default=True, verbose_name='Accepting orders')),
                ('enforce_hours', models.BooleanField(default=False, help_text='Off = open whenever "Accepting orders" is on.', verbose_name='Enforce opening hours')),
                ('opening_time', models.TimeField(default=datetime.time(7, 0), verbose_name='Opens at')),
                ('closing_time', models.TimeField(default=datetime.time(20, 0), verbose_name='Closes at')),
                ('closed_message', models.CharField(default="We're closed right now. Orders will reopen soon!", max_length=200, verbose_name='Closed message')),
                ('notify_email', models.EmailField(blank=True, max_length=254, verbose_name='Send new-order alerts to')),
            ],
            options={'verbose_name': 'Store settings', 'verbose_name_plural': 'Store settings'},
        ),
        # token: add nullable -> fill existing rows -> make unique (safe for existing data)
        migrations.AddField(
            model_name='order',
            name='token',
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(fill_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='order',
            name='token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
