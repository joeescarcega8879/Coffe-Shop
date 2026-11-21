from decimal import Decimal

from django import forms

from .images import MAX_UPLOAD_BYTES, optimize_image
from .models import Category, ContactMessage, MenuItem


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'message']


INPUT = 'w-full rounded-lg border border-outline-variant bg-surface-container-lowest p-md'


class ProductForm(forms.ModelForm):
    """Create / edit a menu item from the owner dashboard."""

    price = forms.DecimalField(
        min_value=Decimal('0.01'), max_digits=6, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': INPUT, 'step': '0.01', 'min': '0.01', 'inputmode': 'decimal'}))
    remove_image = forms.BooleanField(required=False, label='Remove current photo')

    class Meta:
        model = MenuItem
        fields = ['name', 'category', 'price', 'description', 'image', 'is_available', 'is_featured']
        labels = {
            'is_available': 'Available (shown on the menu)',
            'is_featured': 'Featured on the home page',
            'image': 'Photo',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT, 'placeholder': 'e.g. Caramel Latte'}),
            'category': forms.Select(attrs={'class': INPUT}),
            'description': forms.Textarea(attrs={'class': INPUT, 'rows': 3, 'placeholder': 'A short, appetizing description'}),
            'image': forms.FileInput(attrs={'accept': 'image/*', 'class': 'block w-full text-sm'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'content_type'):  # a new upload, not the stored file
            if image.size > MAX_UPLOAD_BYTES:
                raise forms.ValidationError(f'This photo is too large (max {MAX_UPLOAD_BYTES // 1024 // 1024} MB).')
            try:
                return optimize_image(image)
            except Exception:
                raise forms.ValidationError('We could not process this photo. Please use a JPG, PNG or WebP image.')
        return image

    def clean(self):
        data = super().clean()
        name, category = data.get('name'), data.get('category')
        if name and category:
            clash = MenuItem.objects.filter(category=category, name__iexact=name.strip())
            if self.instance.pk:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                self.add_error('name', f'"{name.strip()}" already exists in {category.name}.')
        return data

    def save(self, commit=True):
        item = super().save(commit=False)
        old_image = MenuItem.objects.get(pk=item.pk).image.name if item.pk else ''
        if self.cleaned_data.get('remove_image') and not self.files.get('image'):
            item.image = None
        if commit:
            item.save()
            new_image = item.image.name if item.image else ''
            if old_image and old_image != new_image:  # don't leave replaced photos orphaned on disk
                item._meta.get_field('image').storage.delete(old_image)
        return item
