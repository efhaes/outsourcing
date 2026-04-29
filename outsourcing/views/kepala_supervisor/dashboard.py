from django.shortcuts import render
from outsourcing.decorators import kepala_supervisor_required
from outsourcing.utils import get_dashboard_stats
from outsourcing.models import SupervisorPerusahaan, LaporanKegiatan, ItemKegiatan
from django.utils import timezone


@kepala_supervisor_required
def dashboard_view(request):
    user  = request.user
    today = timezone.now().date()
    stats = get_dashboard_stats(user)

    # Supervisor yang di bawah kepala ini
    penugasan = SupervisorPerusahaan.objects.filter(
        kepala_supervisor=user,
        is_active=True,
    ).select_related('supervisor', 'perusahaan', 'jenis_jasa')

    # Laporan terbaru dari semua supervisor di bawah kepala ini
    supervisor_ids = penugasan.values_list('supervisor_id', flat=True)
    laporan_terbaru = LaporanKegiatan.objects.filter(
        supervisor_id__in=supervisor_ids
    ).select_related('perusahaan', 'supervisor').order_by('-tanggal_laporan')[:10]

    # Item kegiatan hari ini dari semua supervisor di bawahnya
    item_hari_ini = ItemKegiatan.objects.filter(
        laporan__supervisor_id__in=supervisor_ids,
        tanggal=today,
    ).select_related('laporan__perusahaan').prefetch_related('staff').order_by('jam_mulai')

    context = {
        'stats'          : stats,
        'penugasan'      : penugasan,
        'laporan_terbaru': laporan_terbaru,
        'item_hari_ini'  : item_hari_ini,
        'page_title'     : 'Dashboard Kepala Supervisor',
    }
    return render(request, 'kepala_supervisor/dashboard.html', context)