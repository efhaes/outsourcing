from django.shortcuts import render
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from outsourcing.decorators import kepala_supervisor_required
from outsourcing.utils import get_dashboard_stats
from outsourcing.models import SupervisorPerusahaan, LaporanKegiatan, ItemKegiatan
from django.utils import timezone
import json


@kepala_supervisor_required
def dashboard_view(request):
    user  = request.user
    today = timezone.now().date()

    # Filter bulan & tahun
    current_year  = today.year
    current_month = today.month
    tahun  = int(request.GET.get('tahun', current_year))
    bulan  = int(request.GET.get('bulan', current_month))

    stats = get_dashboard_stats(user)

    penugasan = SupervisorPerusahaan.objects.filter(
        kepala_supervisor=user, is_active=True,
    ).select_related('supervisor', 'perusahaan', 'jenis_jasa')

    supervisor_ids = penugasan.values_list('supervisor_id', flat=True)

    # Laporan terbaru
    laporan_terbaru = LaporanKegiatan.objects.filter(
        supervisor_id__in=supervisor_ids
    ).select_related('perusahaan', 'supervisor').order_by('-tanggal_laporan')[:8]

    # Item hari ini
    item_hari_ini = ItemKegiatan.objects.filter(
        laporan__supervisor_id__in=supervisor_ids,
        tanggal=today,
    ).select_related('laporan__perusahaan').prefetch_related('staff').order_by('jam_mulai')

    # ── Chart 1: Laporan per bulan (12 bulan terakhir) ──
    from dateutil.relativedelta import relativedelta
    months_data = []
    for i in range(11, -1, -1):
        d = today - relativedelta(months=i)
        qs = LaporanKegiatan.objects.filter(
            supervisor_id__in=supervisor_ids,
            tanggal_laporan__year=d.year,
            tanggal_laporan__month=d.month,
        )
        months_data.append({
            'label': d.strftime('%b %y'),
            'draft'  : qs.filter(status='draft').count(),
            'selesai': qs.filter(status='selesai').count(),
            'dikirim': qs.filter(status='dikirim_customer').count(),
        })

    chart_laporan_labels  = json.dumps([m['label']   for m in months_data])
    chart_laporan_draft   = json.dumps([m['draft']   for m in months_data])
    chart_laporan_selesai = json.dumps([m['selesai'] for m in months_data])
    chart_laporan_dikirim = json.dumps([m['dikirim'] for m in months_data])

    # ── Chart 2: Donut item hari ini ──
    item_stats = {
        'terjadwal' : item_hari_ini.filter(status='terjadwal').count(),
        'on_progress': item_hari_ini.filter(status='on_progress').count(),
        'selesai'   : item_hari_ini.filter(status='selesai').count(),
    }
    chart_donut_data = json.dumps([
        item_stats['terjadwal'],
        item_stats['on_progress'],
        item_stats['selesai'],
    ])

    # ── Chart 3: Produktivitas supervisor bulan & tahun dipilih ──
    spv_labels = []
    spv_counts = []
    for p in penugasan:
        count = LaporanKegiatan.objects.filter(
            supervisor=p.supervisor,
            tanggal_laporan__year=tahun,
            tanggal_laporan__month=bulan,
        ).count()
        spv_labels.append(p.supervisor.nama_lengkap.split()[0])  # first name only
        spv_counts.append(count)

    chart_spv_labels = json.dumps(spv_labels)
    chart_spv_counts = json.dumps(spv_counts)

    # Tahun choices (5 tahun ke belakang)
    tahun_choices = list(range(current_year, current_year - 5, -1))
    bulan_choices = [
        (1,'Januari'),(2,'Februari'),(3,'Maret'),(4,'April'),
        (5,'Mei'),(6,'Juni'),(7,'Juli'),(8,'Agustus'),
        (9,'September'),(10,'Oktober'),(11,'November'),(12,'Desember'),
    ]

    context = {
        'stats'          : stats,
        'penugasan'      : penugasan,
        'laporan_terbaru': laporan_terbaru,
        'item_hari_ini'  : item_hari_ini,
        'item_stats'     : item_stats,
        'page_title'     : 'Dashboard',
        # chart data
        'chart_laporan_labels' : chart_laporan_labels,
        'chart_laporan_draft'  : chart_laporan_draft,
        'chart_laporan_selesai': chart_laporan_selesai,
        'chart_laporan_dikirim': chart_laporan_dikirim,
        'chart_donut_data'     : chart_donut_data,
        'chart_spv_labels'     : chart_spv_labels,
        'chart_spv_counts'     : chart_spv_counts,
        # filter
        'tahun'         : tahun,
        'bulan'         : bulan,
        'tahun_choices' : tahun_choices,
        'bulan_choices' : bulan_choices,
    }
    return render(request, 'kepala_supervisor/dashboard.html', context)