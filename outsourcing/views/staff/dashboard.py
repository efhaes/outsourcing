from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q
from outsourcing.decorators import staff_required
from outsourcing.models import ItemKegiatan


@staff_required
def dashboard_view(request):
    today = timezone.now().date()
    now   = timezone.now()

    # ── Pekerjaan hari ini ───────────────────────────────────────── #
    item_hari_ini = (
        ItemKegiatan.objects
        .filter(staff=request.user, tanggal=today)
        .select_related('laporan__perusahaan', 'laporan__area', 'sub_area')
        .order_by('jam_mulai')
    )

    # ── Pending: belum selesai dari hari-hari sebelumnya ────────── #
    item_pending = (
        ItemKegiatan.objects
        .filter(
            staff=request.user,
            status__in=['terjadwal', 'on_progress'],
            tanggal__lt=today,
        )
        .select_related('laporan__perusahaan', 'laporan__area')
        .order_by('tanggal', 'jam_mulai')
    )

    # ── Stats bulan ini (lebih bermakna dari all-time) ───────────── #
    bulan_ini = ItemKegiatan.objects.filter(
        staff=request.user,
        tanggal__year=today.year,
        tanggal__month=today.month,
    )
    stats_bulan = {
        'total'      : bulan_ini.count(),
        'selesai'    : bulan_ini.filter(status='selesai').count(),
        'on_progress': bulan_ini.filter(status='on_progress').count(),
        'terjadwal'  : bulan_ini.filter(status='terjadwal').count(),
    }
    # Persentase selesai bulan ini
    stats_bulan['pct_selesai'] = (
        round(stats_bulan['selesai'] / stats_bulan['total'] * 100)
        if stats_bulan['total'] > 0 else 0
    )

    # ── Pekerjaan berikutnya hari ini (yang belum selesai) ───────── #
    pekerjaan_berikutnya = (
        item_hari_ini
        .exclude(status='selesai')
        .first()
    )

    context = {
        'item_hari_ini'        : item_hari_ini,
        'item_pending'         : item_pending,
        'stats_bulan'          : stats_bulan,
        'pekerjaan_berikutnya' : pekerjaan_berikutnya,
        'today'                : today,
        'now'                  : now,
        'jumlah_pending'       : item_pending.count(),
        'page_title'           : 'Dashboard',
    }
    return render(request, 'staff/dashboard.html', context)