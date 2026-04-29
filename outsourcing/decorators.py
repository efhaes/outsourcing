from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


# ============================================================
# BASE DECORATOR
# ============================================================

def role_required(*roles):
    """
    Decorator dasar untuk mengecek role user.
    Bisa dipakai untuk satu atau banyak role sekaligus.

    Contoh pemakaian:
        @role_required('admin')
        @role_required('admin', 'kepala_supervisor')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='login')
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            if request.user.role not in roles:
                messages.error(
                    request,
                    'Anda tidak memiliki akses ke halaman ini.'
                )
                return redirect('dashboard')  # redirect ke dashboard masing-masing

            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


# ============================================================
# DECORATOR PER ROLE
# ============================================================

def admin_required(view_func):
    """Hanya Admin yang bisa akses."""
    @wraps(view_func)
    @login_required(login_url='login')
    def wrapped_view(request, *args, **kwargs):
        if request.user.role != 'admin':
            messages.error(request, 'Halaman ini hanya untuk Admin.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped_view


def kepala_supervisor_required(view_func):
    """Hanya Kepala Supervisor yang bisa akses."""
    @wraps(view_func)
    @login_required(login_url='login')
    def wrapped_view(request, *args, **kwargs):
        if request.user.role != 'kepala_supervisor':
            messages.error(request, 'Halaman ini hanya untuk Kepala Supervisor.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped_view


def supervisor_required(view_func):
    """Hanya Supervisor Lapangan yang bisa akses."""
    @wraps(view_func)
    @login_required(login_url='login')
    def wrapped_view(request, *args, **kwargs):
        if request.user.role != 'supervisor':
            messages.error(request, 'Halaman ini hanya untuk Supervisor Lapangan.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped_view


def staff_required(view_func):
    """Hanya Staff Lapangan yang bisa akses."""
    @wraps(view_func)
    @login_required(login_url='login')
    def wrapped_view(request, *args, **kwargs):
        if request.user.role != 'staff':
            messages.error(request, 'Halaman ini hanya untuk Staff Lapangan.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped_view


def customer_required(view_func):
    """Hanya Customer yang bisa akses."""
    @wraps(view_func)
    @login_required(login_url='login')
    def wrapped_view(request, *args, **kwargs):
        if request.user.role != 'customer':
            messages.error(request, 'Halaman ini hanya untuk Customer.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped_view


# ============================================================
# DECORATOR GABUNGAN (akses lebih dari 1 role)
# ============================================================

def admin_or_kepala_required(view_func):
    """Admin dan Kepala Supervisor bisa akses."""
    @wraps(view_func)
    @login_required(login_url='login')
    def wrapped_view(request, *args, **kwargs):
        if request.user.role not in ['admin', 'kepala_supervisor']:
            messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped_view


def manajemen_required(view_func):
    """Admin, Kepala Supervisor, dan Supervisor bisa akses."""
    @wraps(view_func)
    @login_required(login_url='login')
    def wrapped_view(request, *args, **kwargs):
        if request.user.role not in ['admin', 'kepala_supervisor', 'supervisor']:
            messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped_view