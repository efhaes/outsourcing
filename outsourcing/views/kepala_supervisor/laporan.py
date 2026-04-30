from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from outsourcing.decorators import kepala_supervisor_required
from outsourcing.models import (
    LaporanKegiatan, ItemKegiatan,
    SupervisorPerusahaan, Perusahaan
)
from outsourcing.utils import user_can_access_laporan


@kepala_supervisor_required
def laporan_list(request):
    """
    Kepala Supervisor memantau laporan dari semua supervisor di bawahnya.
    """
    user = request.user
    q           = request.GET.get('q', '').strip()
    perusahaan  = request.GET.get('perusahaan', '').strip()
    status      = request.GET.get('status', '').strip()
    tgl_dari    = request.GET.get('tgl_dari', '').strip()
    tgl_sampai  = request.GET.get('tgl_sampai', '').strip()

    # Hanya supervisor di bawah kepala ini
    supervisor_ids = SupervisorPerusahaan.objects.filter(
        kepala_supervisor=user,
        is_active=True,
    ).values_list('supervisor_id', flat=True)

    laporan = LaporanKegiatan.objects.filter(
        supervisor_id__in=supervisor_ids
    ).select_related(
        'perusahaan', 'jenis_jasa', 'area', 'supervisor'
    ).order_by('-tanggal_laporan')

    if q:
        laporan = laporan.filter(
            Q(nama_laporan__icontains=q) |
            Q(perusahaan__nama_perusahaan__icontains=q) |
            Q(supervisor__nama_lengkap__icontains=q)
        )
    if perusahaan:
        laporan = laporan.filter(perusahaan__pk=perusahaan)
    if status:
        laporan = laporan.filter(status=status)
    if tgl_dari:
        laporan = laporan.filter(tanggal_laporan__gte=tgl_dari)
    if tgl_sampai:
        laporan = laporan.filter(tanggal_laporan__lte=tgl_sampai)

    # Perusahaan yang terkait dengan kepala ini untuk filter dropdown
    perusahaan_ids = SupervisorPerusahaan.objects.filter(
        kepala_supervisor=user, is_active=True
    ).values_list('perusahaan_id', flat=True)

    context = {
        'laporan_list'   : laporan,
        'perusahaan_list': Perusahaan.objects.filter(pk__in=perusahaan_ids),
        'status_choices' : LaporanKegiatan._meta.get_field('status').choices,
        'filter'         : {
            'q'         : q,
            'perusahaan': int(perusahaan) if perusahaan.isdigit() else '',  # ← fix
            'status'    : status,
            'tgl_dari'  : tgl_dari,
            'tgl_sampai': tgl_sampai,
        },
        'page_title': 'Pantau Laporan Kegiatan',
    }
    return render(request, 'kepala_supervisor/laporan/list.html', context)


@kepala_supervisor_required
def laporan_detail(request, pk):
    """Detail laporan + semua item kegiatan."""
    laporan = get_object_or_404(
        LaporanKegiatan.objects.select_related(
            'perusahaan', 'jenis_jasa', 'area', 'supervisor'
        ),
        pk=pk
    )

    # Validasi akses
    if not user_can_access_laporan(request.user, laporan):
        from django.contrib import messages
        messages.error(request, 'Anda tidak memiliki akses ke laporan ini.')
        return __import__('django.shortcuts', fromlist=['redirect']).redirect('kepala:laporan_list')

    item_list = ItemKegiatan.objects.filter(
        laporan=laporan
    ).select_related('sub_area').prefetch_related('staff').order_by('tanggal', 'jam_mulai')

    stats = {
        'total'      : item_list.count(),
        'terjadwal'  : item_list.filter(status='terjadwal').count(),
        'on_progress': item_list.filter(status='on_progress').count(),
        'selesai'    : item_list.filter(status='selesai').count(),
        'insidental' : item_list.filter(is_insidental=True).count(),
    }

    context = {
        'laporan'   : laporan,
        'item_list' : item_list,
        'stats'     : stats,
        'page_title': f'Detail Laporan — {laporan.nama_laporan}',
    }
    return render(request, 'kepala_supervisor/laporan/detail.html', context)