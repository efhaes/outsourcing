from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages


# ============================================================
# BASE MIXIN
# ============================================================

class RoleRequiredMixin(LoginRequiredMixin):
    """
    Mixin dasar untuk class-based views.
    Set `allowed_roles` di view yang pakai mixin ini.

    Contoh pemakaian:
        class DashboardView(RoleRequiredMixin, TemplateView):
            allowed_roles = ['admin', 'kepala_supervisor']
            template_name = 'admin/dashboard.html'
    """
    allowed_roles = []
    login_url     = 'login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if self.allowed_roles and request.user.role not in self.allowed_roles:
            messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
            return redirect('dashboard')

        return super().dispatch(request, *args, **kwargs)


# ============================================================
# MIXIN PER ROLE
# ============================================================

class AdminRequiredMixin(LoginRequiredMixin):
    """Hanya Admin yang bisa akses view ini."""
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != 'admin':
            messages.error(request, 'Halaman ini hanya untuk Admin.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


class KepalaSupervisorRequiredMixin(LoginRequiredMixin):
    """Hanya Kepala Supervisor yang bisa akses view ini."""
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != 'kepala_supervisor':
            messages.error(request, 'Halaman ini hanya untuk Kepala Supervisor.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


class SupervisorRequiredMixin(LoginRequiredMixin):
    """Hanya Supervisor Lapangan yang bisa akses view ini."""
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != 'supervisor':
            messages.error(request, 'Halaman ini hanya untuk Supervisor Lapangan.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


class StaffRequiredMixin(LoginRequiredMixin):
    """Hanya Staff Lapangan yang bisa akses view ini."""
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != 'staff':
            messages.error(request, 'Halaman ini hanya untuk Staff Lapangan.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


class CustomerRequiredMixin(LoginRequiredMixin):
    """Hanya Customer yang bisa akses view ini."""
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != 'customer':
            messages.error(request, 'Halaman ini hanya untuk Customer.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


# ============================================================
# MIXIN GABUNGAN
# ============================================================

class AdminOrKepalaMixin(LoginRequiredMixin):
    """Admin dan Kepala Supervisor bisa akses."""
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in ['admin', 'kepala_supervisor']:
            messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


class ManajemenMixin(LoginRequiredMixin):
    """Admin, Kepala Supervisor, dan Supervisor bisa akses."""
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in ['admin', 'kepala_supervisor', 'supervisor']:
            messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)