import qrcode
import io
import base64
from datetime import timedelta, datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from outsourcing.decorators import supervisor_required
from outsourcing.models import (
    QRAbsensi, QRTypeChoices,
    Absensi,
)


# ─────────────────────────────────────────────
# Helper: generate QR image → base64
# ─────────────────────────────────────────────

def _qr_to_base64(url: str) -> str:
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


# ─────────────────────────────────────────────
# QR List
# ─────────────────────────────────────────────

@supervisor_required
def qr_list(request):
    """Daftar QR yang sudah dibuat supervisor ini."""
    qr_qs = (
        QRAbsensi.objects
        .filter(supervisor=request.user)
        .order_by('-tanggal', 'tipe')
    )
    return render(request, 'supervisor/absensi/qr_list.html', {
        'qr_list': qr_qs,
    })


# ─────────────────────────────────────────────
# QR Generate — halaman + AJAX confirm
# ─────────────────────────────────────────────

@supervisor_required
def qr_generate(request):
    """
    GET  → tampilkan halaman dengan QR yang sudah ada (jika ada).
    POST → generate QR masuk & pulang, return JSON (dipanggil dari modal Ajax).
    """
    hari_ini = timezone.localdate()

    qr_masuk  = QRAbsensi.objects.filter(supervisor=request.user, tanggal=hari_ini, tipe=QRTypeChoices.MASUK).first()
    qr_pulang = QRAbsensi.objects.filter(supervisor=request.user, tanggal=hari_ini, tipe=QRTypeChoices.PULANG).first()

    # ── AJAX POST ──────────────────────────────
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        jam_masuk_str = request.POST.get('jam_masuk', '').strip()
        jam_pulang_str = request.POST.get('jam_pulang', '').strip()

        if not jam_masuk_str or not jam_pulang_str:
            return JsonResponse({'ok': False, 'error': 'Jam masuk dan jam pulang wajib diisi.'})

        try:
            h, m = map(int, jam_masuk_str.split(':'))
            jam_masuk_dt = timezone.make_aware(
                datetime.combine(hari_ini, datetime.min.time().replace(hour=h, minute=m))
            )
        except (ValueError, AttributeError):
            return JsonResponse({'ok': False, 'error': 'Format jam masuk tidak valid. Gunakan HH:MM.'})

        try:
            h, m = map(int, jam_pulang_str.split(':'))
            jam_pulang_dt = timezone.make_aware(
                datetime.combine(hari_ini, datetime.min.time().replace(hour=h, minute=m))
            )
        except (ValueError, AttributeError):
            return JsonResponse({'ok': False, 'error': 'Format jam pulang tidak valid. Gunakan HH:MM.'})

        # Buat QR Masuk jika belum ada
        if not qr_masuk:
            qr_masuk = QRAbsensi.objects.create(
                supervisor        = request.user,
                tanggal           = hari_ini,
                tipe              = QRTypeChoices.MASUK,
                berlaku_hingga    = timezone.now() + timedelta(hours=12),
                jam_berlaku_mulai = jam_masuk_dt,  
            )

        # Buat QR Pulang jika belum ada
        if not qr_pulang:
            qr_pulang = QRAbsensi.objects.create(
                supervisor        = request.user,
                tanggal           = hari_ini,
                tipe              = QRTypeChoices.PULANG,
                berlaku_hingga    = timezone.now() + timedelta(hours=12),
                jam_berlaku_mulai = jam_pulang_dt,  
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

    # ── GET ────────────────────────────────────
    qr_masuk_b64  = None
    qr_pulang_b64 = None
    url_masuk     = None
    url_pulang    = None

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
# QR Nonaktifkan — AJAX
# ─────────────────────────────────────────────

@supervisor_required
@require_POST
def qr_nonaktifkan(request, pk):
    """
    Dipanggil via AJAX POST dari modal konfirmasi.
    Return JSON {ok, message}.
    """
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

@supervisor_required
def absensi_rekap(request):
    """Rekap semua absensi staff di bawah supervisor ini, bisa filter per tanggal."""
    
    # Get all staff under this supervisor
    from outsourcing.models import StaffSupervisor
    staff_under_supervisor = StaffSupervisor.objects.filter(
        supervisor=request.user,
        is_active=True
    ).values_list('staff_id', flat=True)
    
    tanggal_filter = request.GET.get('tanggal', '').strip()
    absensi_qs = (
        Absensi.objects
        .filter(staff_id__in=staff_under_supervisor)
        .select_related('staff', 'qr_absensi')
        .order_by('-tanggal', 'waktu_masuk')
    )

    if tanggal_filter:
        absensi_qs = absensi_qs.filter(tanggal=tanggal_filter)

    # Statistik ringkas
    total       = absensi_qs.count()
    total_masuk = absensi_qs.filter(waktu_masuk__isnull=False).count()
    total_pulang= absensi_qs.filter(waktu_pulang__isnull=False).count()

    return render(request, 'supervisor/absensi/rekap.html', {
        'absensi_qs'    : absensi_qs,
        'tanggal_filter': tanggal_filter,
        'total'         : total,
        'total_masuk'   : total_masuk,
        'total_pulang'  : total_pulang,
    })


# ─────────────────────────────────────────────
# Detail Absensi
# ─────────────────────────────────────────────

@supervisor_required
def absensi_detail(request, pk):
    """Detail satu record absensi: GPS, durasi, waktu masuk/pulang."""
    # Get staff under this supervisor
    from outsourcing.models import StaffSupervisor
    staff_under_supervisor = StaffSupervisor.objects.filter(
        supervisor=request.user,
        is_active=True
    ).values_list('staff_id', flat=True)
    
    absensi = get_object_or_404(
        Absensi,
        pk=pk,
        staff_id__in=staff_under_supervisor,
    )
    return render(request, 'supervisor/absensi/detail.html', {
        'absensi': absensi,
        'durasi' : absensi.durasi_kerja(),
    })