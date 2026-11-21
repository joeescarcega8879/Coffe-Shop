"""Tiny fixed-window rate limiter backed by Django's cache (no extra dependencies)."""
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render


def client_ip(request):
    """Client IP. X-Forwarded-For is only trusted when a proxy we control is in front."""
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded:
            # the last entry is the one appended by our own proxy; earlier ones can be spoofed
            return forwarded.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def rate_limit(scope, limit, window, methods=('POST',)):
    """Allow `limit` requests per `window` seconds per client IP; answer 429 beyond that."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if settings.RATELIMIT_ENABLED and request.method in methods:
                key = f'rl:{scope}:{client_ip(request)}'
                cache.add(key, 0, window)  # starts the window on the first hit
                try:
                    count = cache.incr(key)
                except ValueError:  # key expired between add() and incr()
                    cache.set(key, 1, window)
                    count = 1
                if count > limit:
                    return render(request, '429.html', status=429)
            return view(request, *args, **kwargs)
        return wrapper
    return decorator
