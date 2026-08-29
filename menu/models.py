from django.db import models
from django.utils.text import slugify

class Category(models.Model):
    """Menu category (e.g., Coffees, Desserts)."""
    name = models.CharField('Name', max_length=100, unique=True)
    slug = models.SlugField('Slug', max_length=100, unique=True, blank=True)
    description = models.TextField('Description', blank=True)
    image = models.ImageField('Image', upload_to='categories/', blank=True, null=True)
    created_at = models.DateTimeField('Created at', auto_now_add=True)
    updated_at = models.DateTimeField('Updated at', auto_now=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']


    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class MenuItem(models.Model):
    """Menu item (e.g., Espresso, Cheesecake)."""
    name = models.CharField('Name', max_length=100)
    description = models.TextField('Description', blank=True)
    price = models.DecimalField('Price', max_digits=6, decimal_places=2)
    image = models.ImageField('Image', upload_to='menu_items/', blank=True, null=True)

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='menu_items')
    is_available = models.BooleanField('Is available', default=True)
    is_featured = models.BooleanField('Is featured', default=False)
    created_at = models.DateTimeField('Created at', auto_now_add=True)
    updated_at = models.DateTimeField('Updated at', auto_now=True)

    class Meta:
        verbose_name = 'Menu Item'
        verbose_name_plural = 'Menu Items'
        ordering = ['name']


    def __str__(self):
        return self.name

class ContactMessage(models.Model):
    """Message sent from the contact form."""
    name = models.CharField('Name', max_length=100)
    email = models.EmailField('Email')
    phone = models.CharField('Phone', max_length=20, blank=True)
    message = models.TextField('Message')
    date_sent = models.DateTimeField('Date sent', auto_now_add=True)

    class Meta:
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
        ordering = ['-date_sent']

    def __str__(self):
        return f'Message from {self.name} ({self.email})'

    