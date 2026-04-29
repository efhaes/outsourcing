from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from outsourcing.utils import get_dashboard_url


# ============================================================
# LOGIN
# ============================================================

def login_view(request):
    """
    Halaman login untuk semua role.
    Setelah login berhasil, redirect ke dashboard sesuai role.
    Jika sudah login, langsung redirect ke dashboard.
    """
    # Kalau sudah login, langsung redirect
    if request.user.is_authenticated:
        return redirect(get_dashboard_url(request.user))

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        # Validasi field kosong
        if not username or not password:
            messages.error(request, 'Username dan password wajib diisi.')
            return render(request, 'auth/login.html', {'username': username})

        # Autentikasi user
        user = authenticate(request, username=username, password=password)

        if user is not None:
    
            if not user.is_active:
                messages.error(
                    request,
                    'Akun Anda telah dinonaktifkan. Hubungi administrator.'
                )
                return render(request, 'auth/login.html', {'username': username})

            login(request, user)
            messages.success(request, f'Selamat datang, {user.nama_lengkap or user.username}!')

            # Redirect ke halaman yang dituju sebelum login (jika ada)
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)

            return redirect(get_dashboard_url(user))

        else:
            messages.error(request, 'Username atau password salah.')
            return render(request, 'auth/login.html', {'username': username})

    return render(request, 'auth/login.html')


# ============================================================
# LOGOUT
# ============================================================

@login_required(login_url='login')
def logout_view(request):
    """
    Logout user dan redirect ke halaman login.
    Hanya menerima POST untuk keamanan (hindari logout via GET).
    """
    if request.method == 'POST':
        nama = request.user.nama_lengkap or request.user.username
        logout(request)
        messages.success(request, f'Sampai jumpa, {nama}!')
        return redirect('login')

    # Kalau ada yang akses via GET, tetap logout tapi kasih warning
    logout(request)
    return redirect('login')


# ============================================================
# DASHBOARD REDIRECT
# ============================================================

@login_required(login_url='login')
def dashboard_redirect(request):
    """
    View untuk URL '/dashboard/' yang redirect ke dashboard sesuai role.
    Berguna sebagai fallback setelah login atau dari messages.
    """
    return redirect(get_dashboard_url(request.user))