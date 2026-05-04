import qrcode
import io
import base64
from datetime import timedelta
from django.shortcuts         import render, redirect, get_object_or_404
from django.contrib           import messages
from django.utils             import timezone
from outsourcing.decorators import supervisor_required
from outsourcing.models       import QRAbsensi, Absensi, LaporanKegiatan






# ------------------------------------------------------------------ #
# QR — Generate & List
# ------------------------------------------------------------------ #

@supervisor_required
def qr_list(request):
    """
    Daftar QR yang sudah dibuat oleh supervisor ini.
    """
    qr_list_qs = QRAbsensi.objects.filter(
        supervisor=request.user
    ).select_related('laporan').order_by('-tanggal')

    return render(request, 'supervisor/absensi/qr_list.html', {
        'qr_list': qr_list_qs,
    })


@supervisor_required
def qr_generate(request, laporan_pk):
    laporan = get_object_or_404(
        LaporanKegiatan,
        pk=laporan_pk,
        supervisor=request.user,
    )

    hari_ini    = timezone.localdate()
    qr_existing = QRAbsensi.objects.filter(laporan=laporan, tanggal=hari_ini).first()

    # ── Kalau belum ada QR hari ini ───────────────────────────────────
    if not qr_existing:
        if request.method != 'POST':
            # GET → halaman konfirmasi dulu
            return render(request, 'supervisor/absensi/qr_confirm.html', {
                'laporan': laporan,
            })
        # POST → buat QR baru
        qr_existing = QRAbsensi.objects.create(
            laporan        = laporan,
            supervisor     = request.user,
            tanggal        = hari_ini,
            berlaku_hingga = timezone.now() + timedelta(hours=12),
        )
        messages.success(request, "QR berhasil dibuat.")
    else:
        messages.info(request, "QR untuk hari ini sudah ada.")

    # ── Render QR (baik yang baru dibuat maupun yang lama) ───────────
    qr_url    = request.build_absolute_uri(f'/absensi/scan/{qr_existing.token}/')
    qr_img    = qrcode.make(qr_url)
    buffer    = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, 'supervisor/absensi/qr_detail.html', {
        'laporan'   : laporan,
        'qr_obj'    : qr_existing,
        'qr_base64' : qr_base64,
        'qr_url'    : qr_url,
    })


@supervisor_required
def qr_nonaktifkan(request, pk):
    """
    Nonaktifkan QR sebelum expired (misal ada kesalahan).
    """
    qr_obj = get_object_or_404(QRAbsensi, pk=pk, supervisor=request.user)

    if request.method == 'POST':
        qr_obj.is_active = False
        qr_obj.save()
        messages.success(request, "QR berhasil dinonaktifkan.")
        return redirect('supervisor_qr_list')

    return render(request, 'supervisor/absensi/qr_nonaktifkan_confirm.html', {
        'qr_obj': qr_obj,
    })


# ------------------------------------------------------------------ #
# Rekap Absensi — baca saja
# ------------------------------------------------------------------ #

@supervisor_required
def absensi_rekap(request, laporan_pk):
    laporan = get_object_or_404(
        LaporanKegiatan,
        pk=laporan_pk,
        supervisor=request.user,
    )

    tanggal_filter = request.GET.get('tanggal')  # opsional, dari ?tanggal=2025-01-01
    absensi_qs = Absensi.objects.filter(
        laporan=laporan
    ).select_related('staff').order_by('tanggal', 'waktu_masuk')

    if tanggal_filter:
        absensi_qs = absensi_qs.filter(tanggal=tanggal_filter)

    return render(request, 'supervisor/absensi/rekap.html', {
        'laporan'        : laporan,
        'absensi_qs'     : absensi_qs,
        'tanggal_filter' : tanggal_filter,
    })


@supervisor_required
def absensi_detail(request, pk):
    """
    Detail satu record absensi (foto, GPS, durasi).
    """
    absensi = get_object_or_404(
        Absensi,
        pk=pk,
        laporan__supervisor=request.user,  # pastikan milik supervisor ini
    )

    return render(request, 'supervisor/absensi/detail.html', {
        'absensi': absensi,
    })