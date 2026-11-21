from django import forms
from .models import Order

INPUT = 'w-full rounded-lg border border-outline-variant bg-surface-container-lowest p-md'


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer_name', 'phone', 'email', 'order_type', 'notes']
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': INPUT, 'placeholder': 'Your name'}),
            'phone': forms.TextInput(attrs={'class': INPUT, 'placeholder': 'Phone'}),
            'email': forms.EmailInput(attrs={'class': INPUT, 'placeholder': 'Email (optional)'}),
            'order_type': forms.Select(attrs={'class': INPUT}),
            'notes': forms.Textarea(attrs={'class': INPUT, 'rows': 3, 'placeholder': 'Notes (optional)'}),
        }