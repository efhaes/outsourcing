from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from outsourcing.decorators import kepala_supervisor_required
from outsourcing.models import (
    SupervisorPerusahaan, User, Perusahaan,
    JenisJasa, KepalaSupervisorJasa
)
from outsourcing.forms.perusahaan_forms import SupervisorPerusahaanForm


@kepala_supervisor_required
def penugasan_list(request):
    """
    Daftar penugasan supervisor ke perusahaan
    yang dikelola oleh kepala supervisor yang login.
    """
    penugasan = SupervisorPerusahaan.objects.filter(
        kepala_supervisor=request.user,
    ).select_related('supervisor', 'perusahaan', 'jenis_jasa').order_by(
        '-is_active', 'perusahaan__nama_perusahaan'
    )

    context = {
        'penugasan_list': penugasan,
        'page_title'    : 'Penugasan Supervisor',
    }
    return render(request, 'kepala_supervisor/penugasan/list.html', context)


@kepala_supervisor_required
def penugasan_create(request):
    """
    Kepala Supervisor assign Supervisor ke Perusahaan & Jenis Jasa.
    Jenis jasa yang tersedia hanya yang dipegang kepala ini.
    Perusahaan yang tersedia hanya yang pakai jasa tersebut.
    """
    # Jenis jasa yang dipegang kepala ini
    jasa_ids = KepalaSupervisorJasa.objects.filter(
        kepala_supervisor=request.user
    ).values_list('jenis_jasa_id', flat=True)

    # Supervisor yang sudah dibuat (belum tentu sudah di-assign)
    supervisor_qs  = User.objects.filter(role='supervisor',is_active=True)
    jenis_jasa_qs  = JenisJasa.objects.filter(pk__in=jasa_ids,is_active=True)
    perusahaan_qs  = Perusahaan.objects.filter(
        jenis_jasa__in=jasa_ids, is_active=True
    ).distinct()

    if request.method == 'POST':
        form = SupervisorPerusahaanForm(
            request.POST,
            supervisor_qs=supervisor_qs,
            jenis_jasa_qs=jenis_jasa_qs,
            perusahaan_qs=perusahaan_qs,
        )
        if form.is_valid():
            penugasan = form.save(commit=False)
            penugasan.kepala_supervisor = request.user
            penugasan.save()
            messages.success(
                request,
                f'Supervisor "{penugasan.supervisor.nama_lengkap}" berhasil '
                f'ditugaskan ke "{penugasan.perusahaan.nama_perusahaan}".'
            )
            return redirect('kepala_penugasan_list')
    else:
        form = SupervisorPerusahaanForm(
            supervisor_qs=supervisor_qs,
            jenis_jasa_qs=jenis_jasa_qs,
            perusahaan_qs=perusahaan_qs,
        )

    context = {
        'form'      : form,
        'page_title': 'Tambah Penugasan Supervisor',
        'action'    : 'Tugaskan',
    }
    return render(request, 'kepala_supervisor/penugasan/form.html', context)


@kepala_supervisor_required
def penugasan_edit(request, pk):
    """Edit penugasan supervisor ke perusahaan."""
    penugasan = get_object_or_404(
        SupervisorPerusahaan,
        pk=pk,
        kepala_supervisor=request.user,
    )
    
    # Jenis jasa yang dipegang kepala ini
    jasa_ids = KepalaSupervisorJasa.objects.filter(
        kepala_supervisor=request.user
    ).values_list('jenis_jasa_id', flat=True)

    supervisor_qs  = User.objects.filter(role='supervisor',is_active=True)
    jenis_jasa_qs  = JenisJasa.objects.filter(pk__in=jasa_ids,is_active=True)
    perusahaan_qs  = Perusahaan.objects.filter(
        jenis_jasa__in=jasa_ids, is_active=True
    ).distinct()

    if request.method == 'POST':
        form = SupervisorPerusahaanForm(
            request.POST,
            instance=penugasan,
            supervisor_qs=supervisor_qs,
            jenis_jasa_qs=jenis_jasa_qs,
            perusahaan_qs=perusahaan_qs,
        )
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Penugasan berhasil diperbarui.'
            )
            return redirect('kepala_penugasan_list')
    else:
        form = SupervisorPerusahaanForm(
            instance=penugasan,
            supervisor_qs=supervisor_qs,
            jenis_jasa_qs=jenis_jasa_qs,
            perusahaan_qs=perusahaan_qs,
        )

    context = {
        'form'      : form,
        'penugasan' : penugasan,
        'page_title': 'Edit Penugasan',
        'action'    : 'Simpan Perubahan',
    }
    return render(request, 'kepala_supervisor/penugasan/form.html', context)


@kepala_supervisor_required
def penugasan_delete(request, pk):
    """Toggle aktif/nonaktif penugasan supervisor."""
    penugasan = get_object_or_404(
        SupervisorPerusahaan,
        pk=pk,
        kepala_supervisor=request.user,  
    )

    if request.method == 'POST':
        penugasan.is_active = not penugasan.is_active
        penugasan.save()
        status = 'diaktifkan' if penugasan.is_active else 'dinonaktifkan'
        messages.success(
            request,
            f'Penugasan "{penugasan.supervisor.nama_lengkap}" '
            f'dari "{penugasan.perusahaan.nama_perusahaan}" berhasil {status}.'
        )
        return redirect('kepala_penugasan_list')

    context = {
        'penugasan' : penugasan,
        'page_title': 'Toggle Penugasan',
    }
    return render(request, 'kepala_supervisor/penugasan/confirm_delete.html', context)