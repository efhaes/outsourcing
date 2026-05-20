from datetime import date
from django.shortcuts import render
from outsourcing.decorators import admin_required
from outsourcing.utils import get_dashboard_stats
 
@admin_required
def dashboard_view(request):
    today = date.today()
 
    try:
        tahun = int(request.GET.get('tahun', today.year))
    except (ValueError, TypeError):
        tahun = today.year
 
    try:
        bulan_raw = request.GET.get('bulan', '').strip()
        bulan = int(bulan_raw) if bulan_raw else None
        if bulan and not (1 <= bulan <= 12):
            bulan = None
    except (ValueError, TypeError):
        bulan = None
 
    stats = get_dashboard_stats(request.user, bulan=bulan, tahun=tahun)
 
    tahun_choices = list(range(today.year, today.year - 6, -1))
    bulan_choices = [
        (1,'Januari'),(2,'Februari'),(3,'Maret'),(4,'April'),
        (5,'Mei'),(6,'Juni'),(7,'Juli'),(8,'Agustus'),
        (9,'September'),(10,'Oktober'),(11,'November'),(12,'Desember'),
    ]
 
    return render(request, 'admin/dashboard.html', {
        'stats'        : stats,
        'tahun_choices': tahun_choices,
        'bulan_choices': bulan_choices,
        'filter_tahun' : tahun,
        'filter_bulan' : bulan,
        'page_title'   : 'Dashboard',
    })