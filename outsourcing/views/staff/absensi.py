from django.shortcuts         import render, redirect, get_object_or_404
from django.contrib           import messages
from django.utils             import timezone
from outsourcing.models       import QRAbsensi, Absensi, StaffSupervisor
from outsourcing.forms.absensi import AbsenMasukForm, AbsenPulangForm
from outsourcing.decorators import staff_required




# ------------------------------------------------------------------ #
# Scan QR → landing page
# ------------------------------------------------------------------ #

@staff_required
def qr_scan_landing(request, token):
    """
    URL ini yang di-encode di dalam QR code.
    Bisa diakses siapa saja yang login — validasi role di dalam.
    
    Flow:
    1. Validasi token & expired
    2. Validasi staff terdaftar di bawah supervisor laporan ini
    3. Cek sudah absen masuk atau belum
    4. Redirect ke form yang sesuai
    """
    if not request.user.is_staff_lapangan:
        return HttpResponseForbidden("Hanya staff yang bisa absen via QR.")

    qr_obj = get_object_or_404(QRAbsensi, token=token)

    # Validasi QR masih berlaku
    if not qr_obj.is_valid():
        return render(request, 'staff/absensi/qr_invalid.html', {
            'alasan': 'QR sudah tidak aktif atau sudah expired.'
        })

    laporan    = qr_obj.laporan
    supervisor = laporan.supervisor
    hari_ini   = timezone.localdate()

    # Validasi: staff harus di bawah supervisor laporan ini
    terdaftar = StaffSupervisor.objects.filter(
        staff      = request.user,
        supervisor = supervisor,
        is_active  = True,
    ).exists()

    if not terdaftar:
        return render(request, 'staff/absensi/qr_invalid.html', {
            'alasan': 'Kamu tidak terdaftar di laporan ini.'
        })

    # Cek record absensi hari ini
    absensi = Absensi.objects.filter(
        staff   = request.user,
        laporan = laporan,
        tanggal = hari_ini,
    ).first()

    if absensi is None:
        # Belum absen masuk sama sekali → redirect ke form masuk
        return redirect('staff_absen_masuk', token=token)

    if absensi.sudah_masuk and not absensi.sudah_pulang:
        # Sudah masuk, belum pulang → redirect ke form pulang
        return redirect('staff_absen_pulang', token=token)

    # Sudah lengkap masuk & pulang
    return render(request, 'staff/absensi/sudah_absen.html', {
        'absensi': absensi,
    })


# ------------------------------------------------------------------ #
# Absen Masuk
# ------------------------------------------------------------------ #


@staff_required
def absen_masuk(request, token):
    qr_obj = get_object_or_404(QRAbsensi, token=token)

    if not qr_obj.is_valid():
        return render(request, 'staff/absensi/qr_invalid.html', {
            'alasan': 'QR sudah tidak aktif atau expired.'
        })

    laporan  = qr_obj.laporan
    hari_ini = timezone.localdate()

    # Guard: jangan dobel absen masuk
    sudah_ada = Absensi.objects.filter(
        staff=request.user, laporan=laporan, tanggal=hari_ini
    ).exists()
    if sudah_ada:
        messages.warning(request, "Kamu sudah absen masuk hari ini.")
        return redirect('staff_absensi_riwayat')

    if request.method == 'POST':
        form = AbsenMasukForm(request.POST, request.FILES)
        if form.is_valid():
            absensi = form.save(commit=False)
            absensi.qr_absensi  = qr_obj
            absensi.staff       = request.user
            absensi.laporan     = laporan
            absensi.tanggal     = hari_ini
            absensi.waktu_masuk = timezone.now()
            absensi.status      = Absensi.StatusAbsen.HADIR
            absensi.save()
            messages.success(request, "Absen masuk berhasil! Selamat bekerja 💪")
            return redirect('staff_absensi_riwayat')
    else:
        form = AbsenMasukForm()

    return render(request, 'staff/absensi/absen_masuk.html', {
        'form'   : form,
        'qr_obj' : qr_obj,
        'laporan': laporan,
    })


# ------------------------------------------------------------------ #
# Absen Pulang
# ------------------------------------------------------------------ #


@staff_required
def absen_pulang(request, token):
    qr_obj = get_object_or_404(QRAbsensi, token=token)

    if not qr_obj.is_valid():
        return render(request, 'staff/absensi/qr_invalid.html', {
            'alasan': 'QR sudah tidak aktif atau expired.'
        })

    laporan  = qr_obj.laporan
    hari_ini = timezone.localdate()

    absensi = get_object_or_404(
        Absensi,
        staff   = request.user,
        laporan = laporan,
        tanggal = hari_ini,
    )

    # Guard: jangan dobel absen pulang
    if absensi.sudah_pulang:
        messages.warning(request, "Kamu sudah absen pulang hari ini.")
        return redirect('staff_absensi_riwayat')

    if request.method == 'POST':
        form = AbsenPulangForm(request.POST, request.FILES, instance=absensi)
        if form.is_valid():
            ab = form.save(commit=False)
            ab.waktu_pulang = timezone.now()
            ab.save()
            messages.success(request, f"Absen pulang berhasil! Durasi kerja: {absensi.durasi_kerja()}")
            return redirect('staff_absensi_riwayat')
    else:
        form = AbsenPulangForm(instance=absensi)

    return render(request, 'staff/absensi/absen_pulang.html', {
        'form'   : form,
        'absensi': absensi,
        'laporan': laporan,
    })


# ------------------------------------------------------------------ #
# Riwayat absensi milik staff sendiri
# ------------------------------------------------------------------ #


@staff_required
def absensi_riwayat(request):
    absensi_qs = Absensi.objects.filter(
        staff=request.user
    ).select_related('laporan', 'laporan__perusahaan').order_by('-tanggal')

    return render(request, 'staff/absensi/riwayat.html', {
        'absensi_qs': absensi_qs,
    })