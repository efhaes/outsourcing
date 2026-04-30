from django.db.models import Q, Count
from django.utils import timezone


# ============================================================
# IMPORT MODEL (lazy untuk hindari circular import)
# ============================================================

def get_models():
    from outsourcing.models import (
        User, Perusahaan, AreaKerja, SubArea,
        LaporanKegiatan, ItemKegiatan,
        KepalaSupervisorJasa, SupervisorPerusahaan, StaffSupervisor,
    )
    return {
        'User': User,
        'Perusahaan': Perusahaan,
        'AreaKerja': AreaKerja,
        'SubArea': SubArea,
        'LaporanKegiatan': LaporanKegiatan,
        'ItemKegiatan': ItemKegiatan,
        'KepalaSupervisorJasa': KepalaSupervisorJasa,
        'SupervisorPerusahaan': SupervisorPerusahaan,
        'StaffSupervisor': StaffSupervisor,
    }


# ============================================================
# REDIRECT DASHBOARD BERDASARKAN ROLE
# ============================================================

def get_dashboard_url(user):
    """
    Kembalikan URL dashboard sesuai role user.
    Dipakai setelah login berhasil.
    """
    role_url_map = {
        'admin'             : 'admin_dashboard',
        'kepala_supervisor' : 'kepala_dashboard',
        'supervisor'        : 'supervisor_dashboard',
        'staff'             : 'staff_dashboard',
        'customer'          : 'customer_dashboard',
    }
    return role_url_map.get(user.role, 'login')


# ============================================================
# FILTER DATA BERDASARKAN ROLE
# ============================================================

def get_supervisor_list(user):
    """
    Ambil daftar supervisor yang bisa dilihat oleh user.
    - Admin         : semua supervisor
    - Kepala Spv    : supervisor yang di bawah dia (termasuk yang belum ditugaskan)
    - Supervisor    : diri sendiri
    """
    m = get_models()
    User = m['User']
    SupervisorPerusahaan = m['SupervisorPerusahaan']

    if user.role == 'admin':
        return User.objects.filter(role='supervisor', is_active=True)

    elif user.role == 'kepala_supervisor':
        # Ambil supervisor yang terhubung lewat SupervisorPerusahaan
        supervisor_ids = SupervisorPerusahaan.objects.filter(
            kepala_supervisor=user,
            is_active=True,
        ).values_list('supervisor_id', flat=True)
        
        # Tambahkan supervisor yang belum memiliki penugasan sama sekali (newly created)
        all_supervisor_ids = SupervisorPerusahaan.objects.values_list('supervisor_id', flat=True)
        unassigned_supervisors = User.objects.filter(
            role='supervisor',
            is_active=True
        ).exclude(id__in=all_supervisor_ids).values_list('id', flat=True)
        
        # Gabungkan kedua set
        all_ids = set(supervisor_ids) | set(unassigned_supervisors)
        
        return User.objects.filter(id__in=all_ids, is_active=True)

    elif user.role == 'supervisor':
        return User.objects.filter(id=user.id)

    return User.objects.none()


def get_staff_list(user):
    """
    Ambil daftar staff yang bisa dilihat oleh user.
    - Admin         : semua staff
    - Kepala Spv    : staff yang di bawah supervisor-nya
    - Supervisor    : staff yang langsung di bawah dia
    - Staff         : diri sendiri
    """
    m = get_models()
    User = m['User']
    StaffSupervisor = m['StaffSupervisor']
    SupervisorPerusahaan = m['SupervisorPerusahaan']

    if user.role == 'admin':
        return User.objects.filter(role='staff',is_active=True)

    elif user.role == 'kepala_supervisor':
        supervisor_ids = SupervisorPerusahaan.objects.filter(
            kepala_supervisor=user,
            is_active=True,
        ).values_list('supervisor_id', flat=True)
        staff_ids = StaffSupervisor.objects.filter(
            supervisor_id__in=supervisor_ids,
            is_active=True,
        ).values_list('staff_id', flat=True)
        return User.objects.filter(id__in=staff_ids,is_active=True)

    elif user.role == 'supervisor':
        staff_ids = StaffSupervisor.objects.filter(
            supervisor=user,
            is_active=True,
        ).values_list('staff_id', flat=True)
        return User.objects.filter(id__in=staff_ids,is_active=True)

    elif user.role == 'staff':
        return User.objects.filter(id=user.id)

    return User.objects.none()


def get_perusahaan_list(user):
    """
    Ambil daftar perusahaan yang bisa dilihat oleh user.
    - Admin         : semua perusahaan
    - Kepala Spv    : perusahaan yang supervisor-nya di bawah dia
    - Supervisor    : perusahaan yang dia tangani
    - Customer      : perusahaan milik dia sendiri
    """
    m = get_models()
    Perusahaan = m['Perusahaan']
    SupervisorPerusahaan = m['SupervisorPerusahaan']

    if user.role == 'admin':
        return Perusahaan.objects.filter(is_active=True)

    elif user.role == 'kepala_supervisor':
        perusahaan_ids = SupervisorPerusahaan.objects.filter(
            kepala_supervisor=user,
            is_active=True,
        ).values_list('perusahaan_id', flat=True)
        return Perusahaan.objects.filter(id__in=perusahaan_ids,is_active=True)

    elif user.role == 'supervisor':
        perusahaan_ids = SupervisorPerusahaan.objects.filter(
            supervisor=user,
            is_active=True,
        ).values_list('perusahaan_id', flat=True)
        return Perusahaan.objects.filter(id__in=perusahaan_ids,is_active=True)

    elif user.role == 'customer':
        return Perusahaan.objects.filter(customer=user,is_active=True)

    return Perusahaan.objects.none()


def get_laporan_list(user):
    """
    Ambil daftar laporan kegiatan yang bisa dilihat oleh user.
    - Admin         : semua laporan
    - Kepala Spv    : laporan dari supervisor yang di bawah dia
    - Supervisor    : laporan yang dia buat
    - Staff         : laporan yang berisi item kegiatan milik dia
    - Customer      : laporan dari perusahaan dia, status dikirim_customer
    """
    m = get_models()
    LaporanKegiatan = m['LaporanKegiatan']
    SupervisorPerusahaan = m['SupervisorPerusahaan']

    if user.role == 'admin':
        return LaporanKegiatan.objects.all()

    elif user.role == 'kepala_supervisor':
        supervisor_ids = SupervisorPerusahaan.objects.filter(
            kepala_supervisor=user,
            is_active=True,
        ).values_list('supervisor_id', flat=True)
        return LaporanKegiatan.objects.filter(supervisor_id__in=supervisor_ids)

    elif user.role == 'supervisor':
        return LaporanKegiatan.objects.filter(supervisor=user)

    elif user.role == 'staff':
        laporan_ids = m['ItemKegiatan'].objects.filter(
            staff=user,
        ).values_list('laporan_id', flat=True)
        return LaporanKegiatan.objects.filter(id__in=laporan_ids)

    elif user.role == 'customer':
        return LaporanKegiatan.objects.filter(
            perusahaan__customer=user,
            status='dikirim_customer',
        )

    return LaporanKegiatan.objects.none()


def get_item_kegiatan_list(user):
    """
    Ambil daftar item kegiatan yang bisa dilihat oleh user.
    - Admin         : semua item
    - Kepala Spv    : item dari laporan supervisor di bawah dia
    - Supervisor    : item dari laporan yang dia buat
    - Staff         : item yang ditugaskan ke dia
    - Customer      : item dari laporan perusahaan dia (status dikirim)
    """
    m = get_models()
    ItemKegiatan = m['ItemKegiatan']
    SupervisorPerusahaan = m['SupervisorPerusahaan']

    if user.role == 'admin':
        return ItemKegiatan.objects.all()

    elif user.role == 'kepala_supervisor':
        supervisor_ids = SupervisorPerusahaan.objects.filter(
            kepala_supervisor=user,
            is_actif=True,
        ).values_list('supervisor_id', flat=True)
        return ItemKegiatan.objects.filter(laporan__supervisor_id__in=supervisor_ids)

    elif user.role == 'supervisor':
        return ItemKegiatan.objects.filter(laporan__supervisor=user)

    elif user.role == 'staff':
        return ItemKegiatan.objects.filter(staff=user)

    elif user.role == 'customer':
        return ItemKegiatan.objects.filter(
            laporan__perusahaan__customer=user,
            laporan__status='dikirim_customer',
        )

    return ItemKegiatan.objects.none()


# ============================================================
# STATISTIK DASHBOARD PER ROLE
# ============================================================

import json
from datetime import date
from django.db.models import Count, Q
from outsourcing.models import (
    User, RoleChoices,
    Perusahaan, JenisJasa,
    LaporanKegiatan, ItemKegiatan,
    StatusLaporan, StatusItem,
)


def get_dashboard_stats(user, bulan=None, tahun=None):
    """
    Menghitung semua statistik untuk dashboard admin.

    Args:
        user  : request.user (untuk keperluan audit log / scope ke depan)
        bulan : int (1–12) atau None → semua bulan
        tahun : int atau None → tahun berjalan

    Returns:
        dict berisi semua stats + data chart serializable ke JSON
    """
    today = date.today()
    tahun = tahun or today.year
    bulan = bulan  # None = semua bulan di tahun tersebut

    # ── FILTER LAPORAN BERDASARKAN PERIODE ──────────────────────────────────
    laporan_qs = LaporanKegiatan.objects.filter(tanggal_laporan__year=tahun)
    if bulan:
        laporan_qs = laporan_qs.filter(tanggal_laporan__month=bulan)

    item_qs = ItemKegiatan.objects.filter(tanggal__year=tahun)
    if bulan:
        item_qs = item_qs.filter(tanggal__month=bulan)

    # ── STATS AKUN (tidak terikat periode) ──────────────────────────────────
    total_perusahaan  = Perusahaan.objects.filter(is_active=True).count()
    total_kepala      = User.objects.filter(role=RoleChoices.KEPALA_SUPERVISOR, is_active=True).count()
    total_supervisor  = User.objects.filter(role=RoleChoices.SUPERVISOR, is_active=True).count()
    total_staff       = User.objects.filter(role=RoleChoices.STAFF, is_active=True).count()
    total_customer    = User.objects.filter(role=RoleChoices.CUSTOMER, is_active=True).count()

    # ── STATS LAPORAN (terikat periode) ────────────────────────────────────
    total_laporan         = laporan_qs.count()
    total_laporan_draft   = laporan_qs.filter(status=StatusLaporan.DRAFT).count()
    total_laporan_selesai = laporan_qs.filter(status=StatusLaporan.SELESAI).count()
    total_laporan_dikirim = laporan_qs.filter(status=StatusLaporan.DIKIRIM_CUSTOMER).count()

    # ── STATS ITEM KEGIATAN (terikat periode) ───────────────────────────────
    total_item            = item_qs.count()
    total_item_selesai    = item_qs.filter(status=StatusItem.SELESAI).count()
    total_item_progress   = item_qs.filter(status=StatusItem.ON_PROGRESS).count()
    total_item_terjadwal  = item_qs.filter(status=StatusItem.TERJADWAL).count()
    total_item_insidental = item_qs.filter(is_insidental=True).count()

    # ── CHART: Laporan per bulan (bar chart) ─────────────────────────────────
    # Selalu tampilkan 12 bulan dalam tahun yang dipilih
    BULAN_LABELS = ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des']

    laporan_per_bulan_qs = (
        LaporanKegiatan.objects
        .filter(tanggal_laporan__year=tahun)
        .values('tanggal_laporan__month')
        .annotate(
            total=Count('id'),
            dikirim=Count('id', filter=Q(status=StatusLaporan.DIKIRIM_CUSTOMER)),
            selesai=Count('id', filter=Q(status=StatusLaporan.SELESAI)),
        )
        .order_by('tanggal_laporan__month')
    )

    # Inisialisasi array 12 bulan dengan 0
    chart_total   = [0] * 12
    chart_dikirim = [0] * 12
    chart_selesai = [0] * 12

    for row in laporan_per_bulan_qs:
        idx = row['tanggal_laporan__month'] - 1
        chart_total[idx]   = row['total']
        chart_dikirim[idx] = row['dikirim']
        chart_selesai[idx] = row['selesai']

    # ── CHART: Laporan per Jenis Jasa (donut) ───────────────────────────────
    laporan_per_jasa = (
        laporan_qs
        .values('jenis_jasa__nama_jasa')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    chart_jasa_labels = [r['jenis_jasa__nama_jasa'] for r in laporan_per_jasa]
    chart_jasa_data   = [r['total'] for r in laporan_per_jasa]

    # ── CHART: Item per Status (bar horizontal) ──────────────────────────────
    chart_item_labels = ['Terjadwal', 'On Progress', 'Selesai']
    chart_item_data   = [total_item_terjadwal, total_item_progress, total_item_selesai]

    # ── TOP 5 PERUSAHAAN PALING AKTIF ───────────────────────────────────────
    top_perusahaan = (
        laporan_qs
        .values('perusahaan__nama_perusahaan')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    # ── LAPORAN TERBARU ──────────────────────────────────────────────────────
    laporan_terbaru = (
        laporan_qs
        .select_related('perusahaan', 'jenis_jasa', 'supervisor')
        .order_by('-dibuat_pada')[:8]
    )

    return {
        # Periode aktif
        'tahun'               : tahun,
        'bulan'               : bulan,
        'bulan_label'         : BULAN_LABELS[bulan - 1] if bulan else 'Semua Bulan',
        'bulan_labels_json'   : json.dumps(BULAN_LABELS),

        # Akun
        'total_perusahaan'    : total_perusahaan,
        'total_kepala'        : total_kepala,
        'total_supervisor'    : total_supervisor,
        'total_staff'         : total_staff,
        'total_customer'      : total_customer,

        # Laporan
        'total_laporan'       : total_laporan,
        'total_laporan_draft' : total_laporan_draft,
        'total_laporan_selesai': total_laporan_selesai,
        'total_laporan_dikirim': total_laporan_dikirim,

        # Item kegiatan
        'total_item'          : total_item,
        'total_item_selesai'  : total_item_selesai,
        'total_item_progress' : total_item_progress,
        'total_item_terjadwal': total_item_terjadwal,
        'total_item_insidental': total_item_insidental,

        # Chart data (JSON untuk JavaScript)
        'chart_total_json'    : json.dumps(chart_total),
        'chart_dikirim_json'  : json.dumps(chart_dikirim),
        'chart_selesai_json'  : json.dumps(chart_selesai),
        'chart_jasa_labels_json': json.dumps(chart_jasa_labels),
        'chart_jasa_data_json': json.dumps(chart_jasa_data),
        'chart_item_labels_json': json.dumps(chart_item_labels),
        'chart_item_data_json': json.dumps(chart_item_data),

        # Tabel
        'top_perusahaan'      : top_perusahaan,
        'laporan_terbaru'     : laporan_terbaru,
    }
# ============================================================
# HELPER VALIDASI AKSES OBJECT
# ============================================================

def user_can_access_laporan(user, laporan):
    """
    Cek apakah user boleh mengakses laporan tertentu.
    Kembalikan True/False.
    """
    if user.role == 'admin':
        return True

    elif user.role == 'kepala_supervisor':
        m = get_models()
        return m['SupervisorPerusahaan'].objects.filter(
            kepala_supervisor=user,
            supervisor=laporan.supervisor,
            is_active=True,
        ).exists()

    elif user.role == 'supervisor':
        return laporan.supervisor == user

    elif user.role == 'staff':
        m = get_models()
        return m['ItemKegiatan'].objects.filter(
            laporan=laporan, staff=user
        ).exists()

    elif user.role == 'customer':
        return (
            laporan.perusahaan.customer == user
            and laporan.status == 'dikirim_customer'
        )

    return False


def user_can_access_item(user, item):
    """
    Cek apakah user boleh mengakses item kegiatan tertentu.
    Kembalikan True/False.
    """
    if user.role == 'admin':
        return True

    elif user.role == 'kepala_supervisor':
        m = get_models()
        return m['SupervisorPerusahaan'].objects.filter(
            kepala_supervisor=user,
            supervisor=item.laporan.supervisor,
            is_active=True,
        ).exists()

    elif user.role == 'supervisor':
        return item.laporan.supervisor == user

    elif user.role == 'staff':
        return item.staff == user

    elif user.role == 'customer':
        return (
            item.laporan.perusahaan.customer == user
            and item.laporan.status == 'dikirim_customer'
        )

    return False