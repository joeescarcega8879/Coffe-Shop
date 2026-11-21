from django import forms
from .models import Order, StoreSettings

INPUT = 'w-full rounded-lg border border-outline-variant bg-surface-container-lowest p-md'


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer_name', 'phone', 'email', 'order_type', 'notes']
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': INPUT, 'placeholder': 'Your name', 'autocomplete': 'name'}),
            'phone': forms.TextInput(attrs={'class': INPUT, 'placeholder': 'Phone', 'autocomplete': 'tel'}),
            'email': forms.EmailInput(attrs={'class': INPUT, 'placeholder': 'Email (optional)', 'autocomplete': 'email'}),
            'order_type': forms.Select(attrs={'class': INPUT}),
            'notes': forms.Textarea(attrs={'class': INPUT, 'rows': 3, 'placeholder': 'Notes (optional)'}),
        }


class StoreSettingsForm(forms.ModelForm):
    """Owner dashboard: open/close the shop, opening hours and alert email."""

    class Meta:
        model = StoreSettings
        fields = ['accepting_orders', 'enforce_hours', 'opening_time', 'closing_time',
                  'closed_message', 'notify_email']
        widgets = {
            'opening_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': INPUT}),
            'closing_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': INPUT}),
            'closed_message': forms.TextInput(attrs={'class': INPUT, 'maxlength': 200}),
            'notify_email': forms.EmailInput(attrs={'class': INPUT, 'placeholder': 'owner@example.com',
                                                    'autocomplete': 'email'}),
        }

    def clean(self):
        data = super().clean()
        if data.get('enforce_hours') and data.get('opening_time') == data.get('closing_time'):
            self.add_error('closing_time', "Opening and closing time can't be the same.")
        return data
