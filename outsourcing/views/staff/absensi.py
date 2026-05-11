from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.utils.timezone import localtime

from outsourcing.models import (
    QRAbsensi, QRTypeChoices,
    Absensi, AbsensiStatusChoices, OvertimeStatusChoices,
    StaffSupervisor,
)
from outsourcing.decorators import staff_required


@staff_required
def qr_scan_page(request):
    return render(request, 'staff/absensi/qr_scan.html')


@staff_required
def qr_scan_landing(request, token):
    """
    Selalu return JsonResponse — semua feedback ditampilkan via modal di qr_scan.html.
    Non-AJAX langsung redirect ke scan page (edge case: user buka URL manual).
    """
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Non-AJAX (buka URL langsung di browser) → redirect ke scan page
    if not is_ajax:
        from django.shortcuts import redirect
        return redirect('qr_scan_page')  # sesuaikan dengan nama url kamu

    if not request.user.is_staff_lapangan:
        return JsonResponse({'success': False, 'error': 'Hanya staff lapangan yang bisa absen.'})

    qr_obj = get_object_or_404(QRAbsensi, token=token)

    valid, alasan = qr_obj.is_valid()
    if not valid:
        return JsonResponse({
            'success'   : False,
            'error'     : alasan,
            'tipe'      : qr_obj.tipe,
            'supervisor': qr_obj.supervisor.nama_lengkap or qr_obj.supervisor.username,
        })

    hari_ini  = timezone.localdate()
    terdaftar = StaffSupervisor.objects.filter(
        staff      = request.user,
        supervisor = qr_obj.supervisor,
        is_active  = True,
    ).exists()

    if not terdaftar:
        return JsonResponse({
            'success'   : False,
            'error'     : 'Kamu tidak terdaftar di bawah supervisor ini.',
            'tipe'      : qr_obj.tipe,
            'supervisor': qr_obj.supervisor.nama_lengkap or qr_obj.supervisor.username,
        })

    absensi, _ = Absensi.objects.get_or_create(
        staff   = request.user,
        tanggal = hari_ini,
        defaults={'qr_masuk': None, 'qr_pulang': None},
    )

    if qr_obj.tipe == QRTypeChoices.MASUK:
        absensi.qr_masuk = qr_obj
    else:
        absensi.qr_pulang = qr_obj
    absensi.save(update_fields=['qr_masuk', 'qr_pulang'])

    # ── QR MASUK ──────────────────────────────
    if qr_obj.tipe == QRTypeChoices.MASUK:
        if absensi.sudah_masuk:
            return JsonResponse({
                'success'      : False,
                'error'        : 'Kamu sudah absen masuk hari ini.',
                'tipe'         : 'masuk',
                'already_absen': True,
                'waktu'        : localtime(absensi.waktu_masuk).strftime('%H:%M'),
            })

        absensi.waktu_masuk = timezone.now()
        absensi.status      = AbsensiStatusChoices.MASUK
        absensi.save(update_fields=['waktu_masuk', 'status'])

        return JsonResponse({
            'success'   : True,
            'message'   : 'Absen masuk berhasil!',
            'tipe'      : 'masuk',
            'waktu'     : localtime(absensi.waktu_masuk).strftime('%H:%M'),
            'supervisor': qr_obj.supervisor.nama_lengkap or qr_obj.supervisor.username,
        })

    # ── QR PULANG ─────────────────────────────
    elif qr_obj.tipe == QRTypeChoices.PULANG:

        if not absensi.sudah_masuk:
            return JsonResponse({
                'success'   : False,
                'error'     : 'Kamu belum absen masuk hari ini. Scan QR masuk terlebih dahulu.',
                'tipe'      : 'pulang',
                'need_masuk': True,
            })

        if absensi.sudah_pulang:
            return JsonResponse({
                'success'      : False,
                'error'        : 'Kamu sudah absen pulang hari ini.',
                'tipe'         : 'pulang',
                'already_absen': True,
                'waktu'        : localtime(absensi.waktu_pulang).strftime('%H:%M'),
            })

        now              = timezone.now()
        jam_pulang_resmi = qr_obj.jam_berlaku_mulai

        is_pulang_awal = jam_pulang_resmi and now < jam_pulang_resmi

        ot_menit = 0
        is_ot    = False
        if jam_pulang_resmi and not is_pulang_awal:
            selisih  = int((now - jam_pulang_resmi).total_seconds() / 60)
            ot_menit = selisih if selisih >= Absensi.THRESHOLD_OT_MENIT else 0
            is_ot    = ot_menit > 0

        # ── GET → kirim flag, tunggu input dari modal ──
        if request.method == 'GET':
            if is_pulang_awal:
                return JsonResponse({
                    'success'         : False,
                    'need_izin_pulang': True,
                    'jam_pulang_resmi': localtime(jam_pulang_resmi).strftime('%H:%M'),
                    'jam_sekarang'    : localtime(now).strftime('%H:%M'),
                })
            if is_ot:
                return JsonResponse({
                    'success'         : False,
                    'need_keterangan' : True,
                    'overtime_menit'  : ot_menit,
                    'overtime_str'    : f"{ot_menit // 60}j {ot_menit % 60}m",
                    'jam_pulang_resmi': localtime(jam_pulang_resmi).strftime('%H:%M'),
                })
            # Tepat waktu — fall through ke simpan

        # ── POST / GET tepat waktu → simpan ────
        update_fields = ['waktu_pulang', 'status']

        if is_pulang_awal:
            keterangan_izin = request.POST.get('keterangan_izin', '').strip()
            if not keterangan_izin:
                return JsonResponse({
                    'success': False,
                    'error'  : 'Keterangan izin pulang awal wajib diisi.',
                })
            absensi.izin_pulang_awal       = True
            absensi.keterangan_izin_pulang = keterangan_izin
            update_fields += ['izin_pulang_awal', 'keterangan_izin_pulang']

        if is_ot:
            keterangan_ot = request.POST.get('keterangan_overtime', '').strip()
            if not keterangan_ot:
                return JsonResponse({
                    'success': False,
                    'error'  : 'Keterangan overtime wajib diisi.',
                })
            absensi.is_overtime     = True
            absensi.overtime_status = OvertimeStatusChoices.BELUM_REVIEW
            absensi.status         = AbsensiStatusChoices.OVERTIME
            update_fields += ['is_overtime', 'overtime_status']

        absensi.waktu_pulang = now
        if not is_ot:
            absensi.status = AbsensiStatusChoices.PULANG
        absensi.save(update_fields=update_fields)

        pesan = 'Absen pulang berhasil!'
        if is_pulang_awal:
            pesan += ' Izin pulang awal tercatat.'
        elif is_ot:
            pesan += f' Overtime {ot_menit // 60}j {ot_menit % 60}m menunggu klasifikasi supervisor.'

        return JsonResponse({
            'success'       : True,
            'message'       : pesan,
            'tipe'          : 'pulang',
            'is_overtime'   : is_ot,
            'is_pulang_awal': is_pulang_awal,
            'waktu'         : localtime(absensi.waktu_pulang).strftime('%H:%M'),
            'durasi'        : absensi.durasi_str,
            'supervisor'    : qr_obj.supervisor.nama_lengkap or qr_obj.supervisor.username,
        })


@staff_required
def absensi_riwayat(request):
    absensi_qs = (
        Absensi.objects
        .filter(staff=request.user)
        .select_related('qr_masuk', 'qr_masuk__supervisor', 'qr_pulang', 'qr_pulang__supervisor')
        .order_by('-tanggal')
    )
    return render(request, 'staff/absensi/riwayat.html', {
        'absensi_qs'  : absensi_qs,
        'total'       : absensi_qs.count(),
        'total_masuk' : absensi_qs.filter(waktu_masuk__isnull=False).count(),
        'total_pulang': absensi_qs.filter(waktu_pulang__isnull=False).count(),
    })


@staff_required
def api_today_status(request):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    hari_ini = timezone.localdate()

    try:
        absensi_hari_ini = Absensi.objects.get(staff=request.user, tanggal=hari_ini)
        status_display   = absensi_hari_ini.get_status_display()
        last_checkin     = localtime(absensi_hari_ini.waktu_masuk).strftime('%H:%M') if absensi_hari_ini.waktu_masuk else None
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