from django.contrib import admin
from django.utils.html import format_html

from .models import Category, MenuItem, ContactMessage

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

    @admin.display(description='Description')
    def short_description(self, obj):
        return obj.description[:60] + ('…' if len(obj.description) > 60 else '')


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('thumbnail', 'name', 'category', 'price', 'is_available', 'is_featured')
    list_filter = ('category', 'is_available', 'is_featured')
    search_fields = ('name', 'description')
    list_editable = ('price','is_available', 'is_featured')
    list_select_related = ('category',)

    @admin.display(description='Image')
    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:8px;" />',
                obj.image.url,
            )
        return '—'


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'date_sent')
    search_fields = ('name', 'email', 'message')
    list_filter = ('date_sent',)
    readonly_fields = ('date_sent',)
    