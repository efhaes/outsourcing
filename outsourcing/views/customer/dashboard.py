from django.shortcuts import render, redirect
from outsourcing.decorators import customer_required
from outsourcing.models import LaporanKegiatan


@customer_required
def dashboard_view(request):
    # Ambil perusahaan milik customer yang login
    perusahaan = getattr(request.user, 'perusahaan_customer', None)
    if not perusahaan:
        return render(request, 'customer/no_perusahaan.html', {
            'page_title': 'Akun Belum Terhubung'
        })

    laporan_terbaru = LaporanKegiatan.objects.filter(
        perusahaan=perusahaan,
        status='dikirim_customer',
    ).select_related('jenis_jasa', 'area', 'supervisor').order_by('-tanggal_laporan')[:5]

    stats = {
        'total_laporan': LaporanKegiatan.objects.filter(
            perusahaan=perusahaan, status='dikirim_customer'
        ).count(),
    }

    context = {
        'perusahaan'    : perusahaan,
        'laporan_terbaru': laporan_terbaru,
        'stats'         : stats,
        'page_title'    : f'Dashboard — {perusahaan.nama_perusahaan}',
    }
    return render(request, 'customer/dashboard.html', context)