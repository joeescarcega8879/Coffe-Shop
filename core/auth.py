"""Branded sign-in for the owner dashboard (replaces the stock "Django administration" login)."""
from django import forms
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

LOGIN_URL = 'orders:dashboard_login'

_INPUT = ('w-full rounded-lg border border-outline-variant bg-surface-container-lowest p-sm '
          'text-on-surface')


def dashboard_required(view):
    """Staff only; anyone else is sent to our own login page (not the admin one)."""
    return staff_member_required(view, login_url=LOGIN_URL)


class StaffAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'That email/username and password do not match. Please try again.',
        'no_access': 'This account does not have access to the dashboard.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email or username'
        self.fields['username'].widget.attrs.update({
            'class': _INPUT, 'autocomplete': 'username', 'autofocus': True,
            'autocapitalize': 'none', 'spellcheck': 'false',
        })
        self.fields['password'].widget.attrs.update({'class': _INPUT, 'autocomplete': 'current-password'})

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError(self.error_messages['no_access'], code='no_access')


class DashboardLoginView(LoginView):
    template_name = 'dashboard/login.html'
    authentication_form = StaffAuthenticationForm
    next_page = reverse_lazy('orders:dashboard')
    redirect_authenticated_user = False
