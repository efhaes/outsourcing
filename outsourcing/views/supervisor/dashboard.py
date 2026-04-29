from django.shortcuts import render
from django.utils import timezone
from outsourcing.decorators import supervisor_required
from outsourcing.models import LaporanKegiatan, ItemKegiatan, StaffSupervisor


@supervisor_required
def dashboard_view(request):
    user  = request.user
    today = timezone.now().date()

    laporan_aktif = LaporanKegiatan.objects.filter(
        supervisor=user, status='aktif'
    ).count()
    laporan_draft = LaporanKegiatan.objects.filter(
        supervisor=user, status='draft'
    ).count()

    item_hari_ini = ItemKegiatan.objects.filter(
        laporan__supervisor=user,
        tanggal=today,
    ).select_related('laporan').prefetch_related('staff').order_by('jam_mulai')

    total_staff = StaffSupervisor.objects.filter(
        supervisor=user, is_active=True
    ).count()

    context = {
        'laporan_aktif' : laporan_aktif,
        'laporan_draft' : laporan_draft,
        'item_hari_ini' : item_hari_ini,
        'total_staff'   : total_staff,
        'today'         : today,
        'page_title'    : 'Dashboard Supervisor',
    }
    return render(request, 'supervisor/dashboard.html', context)