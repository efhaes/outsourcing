from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q
from outsourcing.decorators import supervisor_required
from outsourcing.models import LaporanKegiatan, ItemKegiatan, StaffSupervisor
import json
from outsourcing.decorators import supervisor_or_kepala_required  # ← ganti import

@supervisor_or_kepala_required  # ← ganti decorator
def dashboard_view(request):
    user  = request.supervisor_context  # ← pakai konteks supervisor, bukan request.user
    today = timezone.now().date()

    # ── Stat Cards ──────────────────────────────────────────
    laporan_aktif   = LaporanKegiatan.objects.filter(supervisor=user, status='aktif').count()
    laporan_draft   = LaporanKegiatan.objects.filter(supervisor=user, status='draft').count()
    laporan_selesai = LaporanKegiatan.objects.filter(supervisor=user, status='selesai').count()
    total_staff = StaffSupervisor.objects.filter(
        supervisor=user, is_active=True
    ).count()

    # ── Item Hari Ini ────────────────────────────────────────
    item_hari_ini = (
        ItemKegiatan.objects
        .filter(laporan__supervisor=user, tanggal=today)
        .select_related('laporan', 'sub_area')
        .prefetch_related('staff')
        .order_by('jam_mulai')
    )

    total_item_hari_ini  = item_hari_ini.count()
    item_terjadwal_count = item_hari_ini.filter(status='terjadwal').count()
    item_progress_count  = item_hari_ini.filter(status='on_progress').count()
    item_selesai_count   = item_hari_ini.filter(status='selesai').count()

    # ── Progress bar pct ────────────────────────────────────
    pct_selesai = (
        round(item_selesai_count / total_item_hari_ini * 100)
        if total_item_hari_ini else 0
    )

    # ── Item Belum Selesai (terjadwal + on_progress) ────────
    item_pending = item_hari_ini.exclude(status='selesai')

    # ── Aktivitas 7 hari terakhir (untuk mini chart) ────────
    from datetime import timedelta
    week_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        selesai = ItemKegiatan.objects.filter(
            laporan__supervisor=user,
            tanggal=day,
            status='selesai'
        ).count()
        total_day = ItemKegiatan.objects.filter(
            laporan__supervisor=user,
            tanggal=day
        ).count()
        week_data.append({
            'label': day.strftime('%a'),
            'date' : day.strftime('%d/%m'),
            'selesai': selesai,
            'total'  : total_day,
        })

    # ── Staff aktif + beban kerja hari ini ──────────────────
    # ── Staff aktif + beban kerja hari ini ──────────────────
# Ambil dulu User ID staff yang ada di bawah supervisor ini
        staff_ids = StaffSupervisor.objects.filter(
            supervisor=user,
            is_active=True
        ).values_list('staff_id', flat=True)

        # Annotate dari model User langsung
        from outsourcing.models import User as AppUser

        staff_list = (
            AppUser.objects
            .filter(id__in=staff_ids)
            .annotate(
                item_hari_ini_count=Count(
                    'item_kegiatan_saya',
                    filter=Q(item_kegiatan_saya__tanggal=today)
                ),
                item_selesai_count=Count(
                    'item_kegiatan_saya',
                    filter=Q(
                        item_kegiatan_saya__tanggal=today,
                        item_kegiatan_saya__status='selesai'
                    )
                )
            )
            .order_by('-item_hari_ini_count')[:6]
        )

    # ── Laporan terbaru ──────────────────────────────────────
    laporan_terbaru = (
        LaporanKegiatan.objects
        .filter(supervisor=user)
        .select_related('perusahaan', 'area')
        .order_by('-tanggal_laporan')[:5]
    )

    # ── Item Insidental bulan ini ────────────────────────────
    item_insidental = (
        ItemKegiatan.objects
        .filter(
            laporan__supervisor=user,
            is_insidental=True,
            tanggal__month=today.month,
            tanggal__year=today.year,
        )
        .select_related('laporan', 'sub_area')
        .prefetch_related('staff')
        .order_by('-tanggal')[:5]
    )

    context = {
        # Stats
        'laporan_aktif'   : laporan_aktif,
        'laporan_draft'   : laporan_draft,
        'laporan_selesai' : laporan_selesai,
        'total_staff'     : total_staff,

        # Item hari ini
        'item_hari_ini'        : item_hari_ini,
        'item_pending'         : item_pending,
        'total_item_hari_ini'  : total_item_hari_ini,
        'item_terjadwal_count' : item_terjadwal_count,
        'item_progress_count'  : item_progress_count,
        'item_selesai_count'   : item_selesai_count,
        'pct_selesai'          : pct_selesai,

        # Chart
        'week_data_json' : json.dumps(week_data),

        # Lainnya
        'staff_list'      : staff_list,
        'laporan_terbaru' : laporan_terbaru,
        'item_insidental' : item_insidental,
        'today'           : today,
        'page_title'      : 'Dashboard',
    }
    return render(request, 'supervisor/dashboard.html', context)