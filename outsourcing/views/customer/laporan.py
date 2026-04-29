from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from outsourcing.decorators import customer_required
from outsourcing.models import LaporanKegiatan, ItemKegiatan


@customer_required
def laporan_list(request):
    perusahaan = getattr(request.user, 'perusahaan_customer', None)
    if not perusahaan:
        return render(request, 'customer/no_perusahaan.html', {
            'page_title': 'Akun Belum Terhubung'
        })

    q          = request.GET.get('q', '').strip()
    tgl_dari   = request.GET.get('tgl_dari', '').strip()
    tgl_sampai = request.GET.get('tgl_sampai', '').strip()

    # Customer hanya lihat laporan yang sudah dikirim ke mereka
    laporan = LaporanKegiatan.objects.filter(
        perusahaan=perusahaan,
        status='dikirim_customer',
    ).select_related('jenis_jasa', 'area', 'supervisor').order_by('-tanggal_laporan')

    if q:
        laporan = laporan.filter(
            Q(nama_laporan__icontains=q) |
            Q(jenis_jasa__nama_jasa__icontains=q) |
            Q(supervisor__nama_lengkap__icontains=q)
        )
    if tgl_dari:
        laporan = laporan.filter(tanggal_laporan__gte=tgl_dari)
    if tgl_sampai:
        laporan = laporan.filter(tanggal_laporan__lte=tgl_sampai)

    context = {
        'laporan_list' : laporan,
        'perusahaan'   : perusahaan,
        'q'            : q,
        'tgl_dari'     : tgl_dari,
        'tgl_sampai'   : tgl_sampai,
        'page_title'   : 'Laporan Kegiatan',
    }
    return render(request, 'customer/laporan/list.html', context)


@customer_required
def laporan_detail(request, pk):
    perusahaan = getattr(request.user, 'perusahaan_customer', None)
    if not perusahaan:
        return render(request, 'customer/no_perusahaan.html', {
            'page_title': 'Akun Belum Terhubung'
        })

    # Pastikan laporan ini milik perusahaan customer & sudah dikirim
    laporan = get_object_or_404(
        LaporanKegiatan,
        pk=pk,
        perusahaan=perusahaan,
        status='dikirim_customer',
    )

    item_list = ItemKegiatan.objects.filter(
        laporan=laporan
    ).select_related('sub_area').prefetch_related('staff').order_by('tanggal', 'jam_mulai')

    stats = {
        'total'      : item_list.count(),
        'terjadwal'  : item_list.filter(status='terjadwal').count(),
        'on_progress': item_list.filter(status='on_progress').count(),
        'selesai'    : item_list.filter(status='selesai').count(),
    }

    context = {
        'laporan'   : laporan,
        'item_list' : item_list,
        'stats'     : stats,
        'perusahaan': perusahaan,
        'page_title': f'Laporan — {laporan.nama_laporan}',
    }
    return render(request, 'customer/laporan/detail.html', context)