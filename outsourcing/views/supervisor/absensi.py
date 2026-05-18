import qrcode
import io
import base64
from calendar import monthrange
from datetime import datetime, time, date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timezone import localtime
from django.views.decorators.http import require_POST
from django.db.models import Q

from outsourcing.decorators import supervisor_or_kepala_required
from outsourcing.models import (
    QRAbsensi, QRTypeChoices,
    Absensi, OvertimeStatusChoices,
    StaffSupervisor, IzinStaff, StatusIzinChoices,
    User,AbsensiStatusChoices,StatusHarianChoices
)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _qr_to_base64(url: str) -> str:
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


def _get_supervisor(request):
    """
    Supervisor biasa → dirinya sendiri.
    Kepala supervisor → supervisor yang dipilih di session (request.supervisor_context).
    """
    if request.user.role == 'supervisor':
        return request.user
    return request.supervisor_context


def _staff_ids(supervisor):
    """Ambil staff_ids berdasarkan supervisor context."""
    return StaffSupervisor.objects.filter(
        supervisor=supervisor,
        is_active=True,
    ).values_list('staff_id', flat=True)


# ─────────────────────────────────────────────
# QR — List
# ─────────────────────────────────────────────

@supervisor_or_kepala_required
def qr_list(request):
    supervisor = _get_supervisor(request)
    qr_qs = (
        QRAbsensi.objects
        .filter(supervisor=supervisor)
        .order_by('-tanggal', 'tipe')
    )
    return render(request, 'supervisor/absensi/qr_list.html', {
        'qr_list'   : qr_qs,
        'supervisor': supervisor,
    })


# ─────────────────────────────────────────────
# QR — Generate
# ─────────────────────────────────────────────

@supervisor_or_kepala_required
def qr_generate(request):
    supervisor = _get_supervisor(request)
    hari_ini   = timezone.localdate()
    akhir_hari = timezone.make_aware(
        datetime.combine(hari_ini, time(23, 59, 59))
    )

    qr_masuk  = QRAbsensi.objects.filter(
        supervisor=supervisor, tanggal=hari_ini, tipe=QRTypeChoices.MASUK,
    ).first()
    qr_pulang = QRAbsensi.objects.filter(
        supervisor=supervisor, tanggal=hari_ini, tipe=QRTypeChoices.PULANG,
    ).first()

    # ── AJAX POST ─────────────────────────────
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        jam_masuk_str  = request.POST.get('jam_masuk', '').strip()
        jam_pulang_str = request.POST.get('jam_pulang', '').strip()

        if not jam_masuk_str or not jam_pulang_str:
            return JsonResponse({'ok': False, 'error': 'Jam masuk dan jam pulang wajib diisi.'})

        try:
            h, m         = map(int, jam_masuk_str.split(':'))
            jam_masuk_dt = timezone.make_aware(datetime.combine(hari_ini, time(hour=h, minute=m)))
        except (ValueError, AttributeError):
            return JsonResponse({'ok': False, 'error': 'Format jam masuk tidak valid.'})

        try:
            h, m          = map(int, jam_pulang_str.split(':'))
            jam_pulang_dt = timezone.make_aware(datetime.combine(hari_ini, time(hour=h, minute=m)))
        except (ValueError, AttributeError):
            return JsonResponse({'ok': False, 'error': 'Format jam pulang tidak valid.'})

        if jam_pulang_dt <= jam_masuk_dt:
            return JsonResponse({'ok': False, 'error': 'Jam pulang harus setelah jam masuk.'})

        if qr_masuk:
            qr_masuk.jam_berlaku_mulai = jam_masuk_dt
            qr_masuk.berlaku_hingga    = akhir_hari
            qr_masuk.save(update_fields=['jam_berlaku_mulai', 'berlaku_hingga'])
        else:
            qr_masuk = QRAbsensi.objects.create(
                supervisor=supervisor,
                tanggal=hari_ini,
                tipe=QRTypeChoices.MASUK,
                berlaku_hingga=akhir_hari,
                jam_berlaku_mulai=jam_masuk_dt,
            )

        if qr_pulang:
            qr_pulang.jam_berlaku_mulai = jam_pulang_dt
            qr_pulang.berlaku_hingga    = akhir_hari
            qr_pulang.save(update_fields=['jam_berlaku_mulai', 'berlaku_hingga'])
        else:
            qr_pulang = QRAbsensi.objects.create(
                supervisor=supervisor,
                tanggal=hari_ini,
                tipe=QRTypeChoices.PULANG,
                berlaku_hingga=akhir_hari,
                jam_berlaku_mulai=jam_pulang_dt,
            )

        # ── Auto-create Absensi kosong untuk semua staff ──────────────
        staff_ids = list(_staff_ids(supervisor))
        existing  = set(
            Absensi.objects
            .filter(staff_id__in=staff_ids, tanggal=hari_ini)
            .values_list('staff_id', flat=True)
        )
        absensi_bulk = [
            Absensi(
                staff_id      = sid,
                tanggal       = hari_ini,
                status        = AbsensiStatusChoices.BELUM_ABSEN,
                status_harian = StatusHarianChoices.HADIR,
            )
            for sid in staff_ids if sid not in existing
        ]
        if absensi_bulk:
            Absensi.objects.bulk_create(absensi_bulk, ignore_conflicts=True)
        # ──────────────────────────────────────────────────────────────

        url_masuk  = request.build_absolute_uri(f'/absensi/scan/{qr_masuk.token}/')
        url_pulang = request.build_absolute_uri(f'/absensi/scan/{qr_pulang.token}/')

        return JsonResponse({
            'ok'           : True,
            'qr_masuk_b64' : _qr_to_base64(url_masuk),
            'qr_pulang_b64': _qr_to_base64(url_pulang),
            'url_masuk'    : url_masuk,
            'url_pulang'   : url_pulang,
            'staff_disiapkan': len(absensi_bulk),  # info berapa record baru dibuat
        })

    # ── GET ───────────────────────────────────
    qr_masuk_b64 = qr_pulang_b64 = url_masuk = url_pulang = None

    if qr_masuk:
        url_masuk    = request.build_absolute_uri(f'/absensi/scan/{qr_masuk.token}/')
        qr_masuk_b64 = _qr_to_base64(url_masuk)

    if qr_pulang:
        url_pulang    = request.build_absolute_uri(f'/absensi/scan/{qr_pulang.token}/')
        qr_pulang_b64 = _qr_to_base64(url_pulang)

    return render(request, 'supervisor/absensi/qr_generate.html', {
        'hari_ini'     : hari_ini,
        'qr_masuk'     : qr_masuk,
        'qr_pulang'    : qr_pulang,
        'qr_masuk_b64' : qr_masuk_b64,
        'qr_pulang_b64': qr_pulang_b64,
        'url_masuk'    : url_masuk,
        'url_pulang'   : url_pulang,
        'supervisor'   : supervisor,
    })

@supervisor_or_kepala_required
def absensi_rekap(request):
    supervisor     = _get_supervisor(request)
    ids            = _staff_ids(supervisor)
    bulan_filter   = request.GET.get('bulan', '').strip()
    search_nama    = request.GET.get('q', '').strip()
    filter_hari_ini = request.GET.get('hari_ini', '').strip()  # ← tambah ini
    bulan_sekarang = date.today().strftime('%Y-%m')

    if not bulan_filter:
        bulan_filter = bulan_sekarang

    try:
        tahun_int, bulan_int = map(int, bulan_filter.split('-'))
    except ValueError:
        tahun_int, bulan_int = date.today().year, date.today().month

    absensi_qs = (
        Absensi.objects
        .filter(staff_id__in=ids)
        .select_related('staff', 'qr_masuk', 'qr_pulang')
        .order_by('-tanggal', 'waktu_masuk')
    )

    # ── Filter hari ini override bulan ──────────
    if filter_hari_ini:
        absensi_qs = absensi_qs.filter(tanggal=date.today())
        # sesuaikan tahun/bulan supaya stats card tetap konsisten
        tahun_int  = date.today().year
        bulan_int  = date.today().month
    else:
        absensi_qs = absensi_qs.filter(
            tanggal__year=tahun_int,
            tanggal__month=bulan_int,
        )
    # ────────────────────────────────────────────

    last_day    = monthrange(tahun_int, bulan_int)[1]
    bulan_start = date(tahun_int, bulan_int, 1)
    bulan_end   = date(tahun_int, bulan_int, last_day)

    izin_qs = (
        IzinStaff.objects
        .filter(staff_id__in=ids)
        .select_related('staff', 'direview_oleh')
        .filter(
            tanggal_mulai__lte=bulan_end,
            tanggal_selesai__gte=bulan_start,
        )
        .order_by('-tanggal_mulai')
    )

    if search_nama:
        absensi_qs = absensi_qs.filter(
            Q(staff__nama_lengkap__icontains=search_nama) |
            Q(staff__username__icontains=search_nama)
        )
        izin_qs = izin_qs.filter(
            Q(staff__nama_lengkap__icontains=search_nama) |
            Q(staff__username__icontains=search_nama)
        )

    bulan_tersedia = (
        Absensi.objects
        .filter(staff_id__in=ids)
        .dates('tanggal', 'month', order='DESC')
    )

    total       = absensi_qs.count()
    total_masuk = absensi_qs.filter(waktu_masuk__isnull=False).count()
    belum_absen = absensi_qs.filter(status=AbsensiStatusChoices.BELUM_ABSEN).count()

    return render(request, 'supervisor/absensi/rekap.html', {
        'absensi_qs'     : absensi_qs,
        'izin_qs'        : izin_qs,
        'bulan_filter'   : bulan_filter,
        'bulan_sekarang' : bulan_sekarang,
        'bulan_tersedia' : bulan_tersedia,
        'search_nama'    : search_nama,
        'filter_hari_ini': filter_hari_ini,  # ← tambah ini
        'total'          : total,
        'total_masuk'    : total_masuk,
        'total_pulang'   : absensi_qs.filter(waktu_pulang__isnull=False).count(),
        'total_overtime' : absensi_qs.filter(is_overtime=True).count(),
        'belum_absen'    : belum_absen,
        'belum_masuk'    : total - total_masuk,
        'belum_review'   : absensi_qs.filter(
            is_overtime=True,
            overtime_status=OvertimeStatusChoices.BELUM_REVIEW,
        ).count(),
        'total_izin'    : izin_qs.count(),
        'izin_pending'  : izin_qs.filter(status=StatusIzinChoices.PENDING).count(),
        'izin_approved' : izin_qs.filter(status=StatusIzinChoices.APPROVED).count(),
        'izin_rejected' : izin_qs.filter(status=StatusIzinChoices.REJECTED).count(),
        'supervisor'    : supervisor,
    })


# ─────────────────────────────────────────────
# QR — Nonaktifkan
# ─────────────────────────────────────────────

@supervisor_or_kepala_required
@require_POST
def qr_nonaktifkan(request, pk):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'ok': False, 'error': 'Request tidak valid.'}, status=400)

    supervisor = _get_supervisor(request)
    qr_obj     = get_object_or_404(QRAbsensi, pk=pk, supervisor=supervisor)

    if not qr_obj.is_active:
        return JsonResponse({'ok': False, 'error': 'QR sudah tidak aktif.'})

    qr_obj.is_active = False
    qr_obj.save(update_fields=['is_active'])

    return JsonResponse({
        'ok'     : True,
        'message': f'QR {qr_obj.get_tipe_display()} berhasil dinonaktifkan.',
        'qr_pk'  : qr_obj.pk,
    })


# ─────────────────────────────────────────────
# Rekap Absensi
# ─────────────────────────────────────────────




# ─────────────────────────────────────────────
# Detail Absensi
# ─────────────────────────────────────────────

@supervisor_or_kepala_required
def absensi_detail(request, pk):
    supervisor = _get_supervisor(request)
    absensi    = get_object_or_404(
        Absensi,
        pk=pk,
        staff_id__in=_staff_ids(supervisor),
    )
    return render(request, 'supervisor/absensi/detail.html', {
        'absensi'   : absensi,
        'durasi'    : absensi.durasi_str,
        'supervisor': supervisor,
    })


# ─────────────────────────────────────────────
# Overtime — List
# ─────────────────────────────────────────────

@supervisor_or_kepala_required
def overtime_list(request):
    supervisor = _get_supervisor(request)
    ids        = _staff_ids(supervisor)

    overtime_qs = (
        Absensi.objects
        .filter(staff_id__in=ids, is_overtime=True)
        .select_related('staff', 'qr_pulang', 'overtime_reviewed_by')
        .order_by('-tanggal')
    )

    belum_review = overtime_qs.filter(overtime_status=OvertimeStatusChoices.BELUM_REVIEW)
    sudah_review = overtime_qs.exclude(overtime_status=OvertimeStatusChoices.BELUM_REVIEW)

    return render(request, 'supervisor/absensi/overtime_list.html', {
        'belum_review': belum_review,
        'sudah_review': sudah_review,
        'supervisor'  : supervisor,
    })


# ─────────────────────────────────────────────
# Overtime — Klasifikasi (AJAX POST)
# ─────────────────────────────────────────────

@supervisor_or_kepala_required
@require_POST
def overtime_klasifikasi(request, absensi_id):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'ok': False, 'error': 'Request tidak valid.'}, status=400)

    supervisor = _get_supervisor(request)
    absensi    = get_object_or_404(
        Absensi,
        id=absensi_id,
        staff_id__in=_staff_ids(supervisor),
        is_overtime=True,
    )

    keputusan = request.POST.get('keputusan', '').strip()
    if keputusan not in [OvertimeStatusChoices.PAID, OvertimeStatusChoices.UNPAID]:
        return JsonResponse({'ok': False, 'error': 'Pilihan tidak valid. Harus paid atau unpaid.'})

    absensi.overtime_status      = keputusan
    absensi.overtime_reviewed_by = request.user  # tetap user asli yang login
    absensi.overtime_reviewed_at = timezone.now()
    absensi.save(update_fields=[
        'overtime_status',
        'overtime_reviewed_by',
        'overtime_reviewed_at',
    ])

    nama          = absensi.staff.nama_lengkap or absensi.staff.username
    label         = '💰 Dibayar' if keputusan == OvertimeStatusChoices.PAID else '🔵 Tidak Dibayar'
    reviewer_nama = request.user.nama_lengkap or request.user.username

    return JsonResponse({
        'ok'         : True,
        'message'    : f'Overtime {nama} → {label}',
        'keputusan'  : keputusan,
        'label'      : label,
        'absensi_id' : absensi.id,
        'reviewed_at': localtime(absensi.overtime_reviewed_at).strftime('%d/%m/%Y %H:%M'),
        'reviewed_by': reviewer_nama,
    })


# ─────────────────────────────────────────────
# Overtime — Update Status dari Rekap (AJAX POST)
# ─────────────────────────────────────────────

@supervisor_or_kepala_required
@require_POST
def api_update_overtime_status(request, pk):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'ok': False, 'error': 'Request tidak valid.'}, status=400)

    supervisor = _get_supervisor(request)
    absensi    = get_object_or_404(
        Absensi,
        pk=pk,
        staff_id__in=_staff_ids(supervisor),
    )

    if not absensi.is_overtime:
        return JsonResponse({'success': False, 'error': 'Absensi ini tidak memiliki overtime.'}, status=400)

    new_status = (request.POST.get('action') or request.POST.get('status', '')).strip()
    valid      = [c[0] for c in OvertimeStatusChoices.choices]

    if new_status not in valid:
        return JsonResponse({
            'success': False,
            'error'  : f'Status tidak valid. Pilihan: {", ".join(valid)}',
        }, status=400)

    absensi.overtime_status      = new_status
    absensi.overtime_reviewed_by = request.user  # tetap user asli yang login
    absensi.overtime_reviewed_at = timezone.now()
    absensi.save(update_fields=[
        'overtime_status',
        'overtime_reviewed_by',
        'overtime_reviewed_at',
    ])

    label_map = {
        OvertimeStatusChoices.PAID        : '💰 Dibayar',
        OvertimeStatusChoices.UNPAID      : '🔵 Tidak Dibayar',
        OvertimeStatusChoices.BELUM_REVIEW: '⏱ Belum Review',
    }

    return JsonResponse({
        'success'    : True,
        'status'     : new_status,
        'label'      : label_map.get(new_status, new_status),
        'reviewed_at': localtime(absensi.overtime_reviewed_at).strftime('%d/%m/%Y %H:%M'),
        'reviewed_by': request.user.nama_lengkap or request.user.username,
    })


# ─────────────────────────────────────────────
# Izin — Review
# ─────────────────────────────────────────────

@supervisor_or_kepala_required
@require_POST
def izin_review(request, pk):
    supervisor = _get_supervisor(request)
    ids        = _staff_ids(supervisor)
    izin       = get_object_or_404(IzinStaff, pk=pk, staff_id__in=ids)
    action     = request.POST.get('action')
    catatan    = request.POST.get('catatan', '').strip()

    if action not in ('approved', 'rejected', 'pending'):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Action tidak valid.'}, status=400)
        messages.error(request, 'Action tidak valid.')
        return redirect(request.META.get('HTTP_REFERER', 'supervisor_absensi_rekap'))

    izin.status             = action
    izin.catatan_supervisor = catatan
    izin.direview_oleh      = request.user if action != 'pending' else None  # tetap user asli
    izin.direview_pada      = timezone.now() if action != 'pending' else None
    izin.save(update_fields=[
        'status', 'catatan_supervisor',
        'direview_oleh', 'direview_pada',
    ])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success'           : True,
            'new_status'        : izin.status,
            'new_status_display': izin.get_status_display(),
        })

    label = 'disetujui' if action == 'approved' else 'ditolak'
    messages.success(request, f'Izin {izin.staff.nama_lengkap} berhasil {label}.')
    return redirect(request.META.get('HTTP_REFERER', 'supervisor_absensi_rekap'))