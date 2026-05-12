import qrcode
import io
import base64
from datetime import datetime, time, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timezone import localtime
from django.views.decorators.http import require_POST

from outsourcing.decorators import supervisor_required
from outsourcing.models import (
    QRAbsensi, QRTypeChoices,
    Absensi, OvertimeStatusChoices,
    StaffSupervisor,
)
from datetime import date
from django.db.models import Q
# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _qr_to_base64(url: str) -> str:
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


def _staff_ids(supervisor):
    return StaffSupervisor.objects.filter(
        supervisor=supervisor,
        is_active=True,
    ).values_list('staff_id', flat=True)


# ─────────────────────────────────────────────
# QR — List
# ─────────────────────────────────────────────

@supervisor_required
def qr_list(request):
    qr_qs = (
        QRAbsensi.objects
        .filter(supervisor=request.user)
        .order_by('-tanggal', 'tipe')
    )
    return render(request, 'supervisor/absensi/qr_list.html', {
        'qr_list': qr_qs,
    })


# ─────────────────────────────────────────────
# QR — Generate
# ─────────────────────────────────────────────

@supervisor_required
def qr_generate(request):
    hari_ini  = timezone.localdate()
    akhir_hari = timezone.make_aware(
        datetime.combine(hari_ini, time(23, 59, 59))
    )

    qr_masuk  = QRAbsensi.objects.filter(
        supervisor=request.user, tanggal=hari_ini, tipe=QRTypeChoices.MASUK,
    ).first()
    qr_pulang = QRAbsensi.objects.filter(
        supervisor=request.user, tanggal=hari_ini, tipe=QRTypeChoices.PULANG,
    ).first()

    # ── AJAX POST ─────────────────────────────
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        jam_masuk_str  = request.POST.get('jam_masuk', '').strip()
        jam_pulang_str = request.POST.get('jam_pulang', '').strip()

        if not jam_masuk_str or not jam_pulang_str:
            return JsonResponse({'ok': False, 'error': 'Jam masuk dan jam pulang wajib diisi.'})

        try:
            h, m = map(int, jam_masuk_str.split(':'))
            jam_masuk_dt = timezone.make_aware(datetime.combine(hari_ini, time(hour=h, minute=m)))
        except (ValueError, AttributeError):
            return JsonResponse({'ok': False, 'error': 'Format jam masuk tidak valid.'})

        try:
            h, m = map(int, jam_pulang_str.split(':'))
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
                supervisor=request.user,
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
                supervisor=request.user,
                tanggal=hari_ini,
                tipe=QRTypeChoices.PULANG,
                berlaku_hingga=akhir_hari,
                jam_berlaku_mulai=jam_pulang_dt,
            )

        url_masuk  = request.build_absolute_uri(f'/absensi/scan/{qr_masuk.token}/')
        url_pulang = request.build_absolute_uri(f'/absensi/scan/{qr_pulang.token}/')

        return JsonResponse({
            'ok'           : True,
            'qr_masuk_b64' : _qr_to_base64(url_masuk),
            'qr_pulang_b64': _qr_to_base64(url_pulang),
            'url_masuk'    : url_masuk,
            'url_pulang'   : url_pulang,
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
    })


# ─────────────────────────────────────────────
# QR — Nonaktifkan
# ─────────────────────────────────────────────

@supervisor_required
@require_POST
def qr_nonaktifkan(request, pk):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'ok': False, 'error': 'Request tidak valid.'}, status=400)

    qr_obj = get_object_or_404(QRAbsensi, pk=pk, supervisor=request.user)

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
from datetime import date
from django.db.models import Q

@supervisor_required
def absensi_rekap(request):
    ids = _staff_ids(request.user)

    bulan_filter   = request.GET.get('bulan', '').strip()   # format: "2025-05"
    search_nama    = request.GET.get('q', '').strip()
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

    absensi_qs = absensi_qs.filter(
        tanggal__year=tahun_int,
        tanggal__month=bulan_int,
    )

    if search_nama:
        absensi_qs = absensi_qs.filter(
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

    return render(request, 'supervisor/absensi/rekap.html', {
        'absensi_qs'    : absensi_qs,
        'bulan_filter'  : bulan_filter,
        'bulan_sekarang': bulan_sekarang,
        'bulan_tersedia': bulan_tersedia,
        'search_nama'   : search_nama,
        'total'         : total,
        'total_masuk'   : total_masuk,
        'total_pulang'  : absensi_qs.filter(waktu_pulang__isnull=False).count(),
        'total_overtime': absensi_qs.filter(is_overtime=True).count(),
        'belum_masuk'   : total - total_masuk,
        'belum_review'  : absensi_qs.filter(
            is_overtime=True,
            overtime_status=OvertimeStatusChoices.BELUM_REVIEW,
        ).count(),
    })


# ─────────────────────────────────────────────
# Detail Absensi
# ─────────────────────────────────────────────

@supervisor_required
def absensi_detail(request, pk):
    absensi = get_object_or_404(
        Absensi,
        pk=pk,
        staff_id__in=_staff_ids(request.user),
    )
    return render(request, 'supervisor/absensi/detail.html', {
        'absensi': absensi,
        'durasi' : absensi.durasi_str,
    })


# ─────────────────────────────────────────────
# Overtime — List
# ─────────────────────────────────────────────

@supervisor_required
def overtime_list(request):
    ids = _staff_ids(request.user)

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
    })


# ─────────────────────────────────────────────
# Overtime — Klasifikasi (AJAX POST)
# ─────────────────────────────────────────────

@supervisor_required
@require_POST
def overtime_klasifikasi(request, absensi_id):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'ok': False, 'error': 'Request tidak valid.'}, status=400)

    absensi = get_object_or_404(
        Absensi,
        id=absensi_id,
        staff_id__in=_staff_ids(request.user),
        is_overtime=True,
    )

    keputusan = request.POST.get('keputusan', '').strip()

    if keputusan not in [OvertimeStatusChoices.PAID, OvertimeStatusChoices.UNPAID]:
        return JsonResponse({'ok': False, 'error': 'Pilihan tidak valid. Harus paid atau unpaid.'})

    absensi.overtime_status      = keputusan
    absensi.overtime_reviewed_by = request.user
    absensi.overtime_reviewed_at = timezone.now()
    absensi.save(update_fields=[
        'overtime_status',
        'overtime_reviewed_by',
        'overtime_reviewed_at',
    ])

    nama      = absensi.staff.nama_lengkap or absensi.staff.username
    label     = '💰 Dibayar' if keputusan == OvertimeStatusChoices.PAID else '🔵 Tidak Dibayar'
    reviewer  = absensi.overtime_reviewed_by
    reviewer_nama = reviewer.nama_lengkap or reviewer.username

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
# Digunakan oleh dropdown pill di halaman rekap absensi
# ─────────────────────────────────────────────

@supervisor_required
@require_POST
def api_update_overtime_status(request, pk):
    """
    POST /supervisor/absensi/<pk>/overtime-status/
    Body: { status: 'paid' | 'unpaid' | 'belum_review' }

    Berbeda dengan overtime_klasifikasi:
    - Bisa set ke 3 status (termasuk reset ke belum_review)
    - Dipanggil dari dropdown pill di halaman rekap
    - Tidak memerlukan is_overtime=True sebagai filter get_object_or_404
      (sudah dicek manual agar pesan error lebih jelas)
    """
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'ok': False, 'error': 'Request tidak valid.'}, status=400)

    # Ambil absensi — pastikan staff-nya di bawah supervisor ini
    absensi = get_object_or_404(
        Absensi,
        pk=pk,
        staff_id__in=_staff_ids(request.user),
    )

    if not absensi.is_overtime:
        return JsonResponse({'success': False, 'error': 'Absensi ini tidak memiliki overtime.'}, status=400)

    new_status = request.POST.get('status', '').strip()
    valid = [c[0] for c in OvertimeStatusChoices.choices]  # ['belum_review', 'paid', 'unpaid']

    if new_status not in valid:
        return JsonResponse({
            'success': False,
            'error'  : f'Status tidak valid. Pilihan: {", ".join(valid)}',
        }, status=400)

    absensi.overtime_status      = new_status
    absensi.overtime_reviewed_by = request.user
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
        'reviewed_by': absensi.overtime_reviewed_by.nama_lengkap
                       or absensi.overtime_reviewed_by.username,
    })