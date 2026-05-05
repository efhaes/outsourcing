from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.utils.timezone import localtime

from outsourcing.models import (
    QRAbsensi, QRTypeChoices,
    Absensi, AbsensiStatusChoices,
    StaffSupervisor,
)
from outsourcing.decorators import staff_required


# ─────────────────────────────────────────────
# QR Scan Page
# ─────────────────────────────────────────────

@staff_required
def qr_scan_page(request):
    """Halaman scan QR untuk staff"""
    return render(request, 'staff/absensi/qr_scan.html')


# ─────────────────────────────────────────────
# Scan QR → proses masuk atau pulang
# ─────────────────────────────────────────────

@staff_required
def qr_scan_landing(request, token):
    """
    Handle QR scan with AJAX support.
    Returns JSON for AJAX requests, renders page for direct access.
    """
    if not request.user.is_staff_lapangan:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Hanya staff lapangan yang bisa absen.'})
        return HttpResponseForbidden("Hanya staff lapangan yang bisa absen.")

    qr_obj = get_object_or_404(QRAbsensi, token=token)

    # Validasi QR (aktif, belum expired, time window)
    valid, alasan = qr_obj.is_valid()
    if not valid:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success'   : False,
                'error'     : alasan,
                'tipe'      : qr_obj.tipe,
                'supervisor': qr_obj.supervisor.nama_lengkap or qr_obj.supervisor.username,
            })
        return render(request, 'staff/absensi/qr_invalid.html', {
            'alasan': alasan,
            'tipe'  : qr_obj.tipe,
            'qr_obj': qr_obj,
        })

    hari_ini = timezone.localdate()

    # Validasi staff terdaftar di bawah supervisor ini
    terdaftar = StaffSupervisor.objects.filter(
        staff      = request.user,
        supervisor = qr_obj.supervisor,
        is_active  = True,
    ).exists()

    if not terdaftar:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success'   : False,
                'error'     : 'Kamu tidak terdaftar di bawah supervisor ini.',
                'tipe'      : qr_obj.tipe,
                'supervisor': qr_obj.supervisor.nama_lengkap or qr_obj.supervisor.username,
            })
        return render(request, 'staff/absensi/qr_invalid.html', {
            'alasan': 'Kamu tidak terdaftar di bawah supervisor ini.',
            'tipe'  : qr_obj.tipe,
            'qr_obj': qr_obj,
        })

    # Ambil atau buat record absensi hari ini
    absensi, created = Absensi.objects.get_or_create(
        staff   = request.user,
        tanggal = hari_ini,
        defaults={'qr_masuk': None, 'qr_pulang': None},
    )

    # Update QR field based on type
    if qr_obj.tipe == QRTypeChoices.MASUK:
        absensi.qr_masuk = qr_obj
    else:
        absensi.qr_pulang = qr_obj
    absensi.save(update_fields=['qr_masuk', 'qr_pulang'])

    # ── QR MASUK ──────────────────────────────
    if qr_obj.tipe == QRTypeChoices.MASUK:
        if absensi.sudah_masuk:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success'      : False,
                    'error'        : 'Kamu sudah absen masuk hari ini.',
                    'tipe'         : 'masuk',
                    'already_absen': True,
                    'waktu'        : localtime(absensi.waktu_masuk).strftime('%H:%M'),
                })
            return render(request, 'staff/absensi/sudah_absen.html', {
                'absensi': absensi,
                'tipe'   : 'masuk',
                'pesan'  : 'Kamu sudah absen masuk hari ini.',
            })

        absensi.waktu_masuk = timezone.now()
        absensi.status      = AbsensiStatusChoices.MASUK
        absensi.save(update_fields=['waktu_masuk', 'status'])

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success'     : True,
                'message'     : 'Absen masuk berhasil!',
                'tipe'        : 'masuk',
                'waktu'       : localtime(absensi.waktu_masuk).strftime('%H:%M'),
                'supervisor'  : qr_obj.supervisor.nama_lengkap or qr_obj.supervisor.username,
                'redirect_url': '/staff/absensi/riwayat/',
            })
        return render(request, 'staff/absensi/sukses.html', {
            'judul'  : 'Absen Masuk Berhasil',
            'tipe'   : 'masuk',
            'absensi': absensi,
            'waktu'  : localtime(absensi.waktu_masuk),
        })

    # ── QR PULANG ─────────────────────────────
    elif qr_obj.tipe == QRTypeChoices.PULANG:
        if not absensi.sudah_masuk:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success'   : False,
                    'error'     : 'Kamu belum absen masuk hari ini. Scan QR masuk terlebih dahulu.',
                    'tipe'      : 'pulang',
                    'need_masuk': True,
                })
            return render(request, 'staff/absensi/qr_invalid.html', {
                'alasan': 'Kamu belum absen masuk hari ini. Scan QR masuk terlebih dahulu.',
                'tipe'  : 'pulang',
                'qr_obj': qr_obj,
            })

        if absensi.sudah_pulang:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success'      : False,
                    'error'        : 'Kamu sudah absen pulang hari ini.',
                    'tipe'         : 'pulang',
                    'already_absen': True,
                    'waktu'        : localtime(absensi.waktu_pulang).strftime('%H:%M'),
                })
            return render(request, 'staff/absensi/sudah_absen.html', {
                'absensi': absensi,
                'tipe'   : 'pulang',
                'pesan'  : 'Kamu sudah absen pulang hari ini.',
            })

        absensi.waktu_pulang = timezone.now()
        absensi.status       = AbsensiStatusChoices.PULANG
        absensi.save(update_fields=['waktu_pulang', 'status'])

        durasi     = absensi.durasi_kerja()
        durasi_str = f"{durasi.seconds // 3600}j {(durasi.seconds % 3600) // 60}m" if durasi else ""

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success'     : True,
                'message'     : 'Absen pulang berhasil!',
                'tipe'        : 'pulang',
                'waktu'       : localtime(absensi.waktu_pulang).strftime('%H:%M'),  # FIX: tambah koma + localtime
                'durasi'      : durasi_str,
                'supervisor'  : qr_obj.supervisor.nama_lengkap or qr_obj.supervisor.username,
                'redirect_url': '/staff/absensi/riwayat/',
            })
        return render(request, 'staff/absensi/sukses.html', {
            'judul'  : 'Absen Pulang Berhasil',
            'tipe'   : 'pulang',
            'absensi': absensi,
            'waktu'  : localtime(absensi.waktu_pulang),  # FIX: localtime
            'durasi' : durasi,
        })


# ─────────────────────────────────────────────
# Riwayat absensi milik staff sendiri
# ─────────────────────────────────────────────

@staff_required
def absensi_riwayat(request):
    absensi_qs = (
        Absensi.objects
        .filter(staff=request.user)
        .select_related('qr_masuk', 'qr_masuk__supervisor', 'qr_pulang', 'qr_pulang__supervisor')
        .order_by('-tanggal')
    )

    total        = absensi_qs.count()
    total_masuk  = absensi_qs.filter(waktu_masuk__isnull=False).count()
    total_pulang = absensi_qs.filter(waktu_pulang__isnull=False).count()

    return render(request, 'staff/absensi/riwayat.html', {
        'absensi_qs'  : absensi_qs,
        'total'       : total,
        'total_masuk' : total_masuk,
        'total_pulang': total_pulang,
    })


# ─────────────────────────────────────────────
# API untuk status hari ini
# ─────────────────────────────────────────────

@staff_required
def api_today_status(request):
    """API endpoint untuk status absensi hari ini"""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    hari_ini = timezone.localdate()

    try:
        absensi_hari_ini = Absensi.objects.get(staff=request.user, tanggal=hari_ini)
        status_display   = absensi_hari_ini.get_status_display()
        last_checkin     = localtime(absensi_hari_ini.waktu_masuk).strftime('%H:%M') if absensi_hari_ini.waktu_masuk else None  # FIX
    except Absensi.DoesNotExist:
        status_display = 'Belum Absen'
        last_checkin   = None

    month_start      = hari_ini.replace(day=1)
    this_month_count = Absensi.objects.filter(
        staff        = request.user,
        tanggal__gte = month_start,
        tanggal__lte = hari_ini,
    ).count()

    return JsonResponse({
        'status_display'  : status_display,
        'last_checkin'    : last_checkin,
        'this_month_count': this_month_count,
    })