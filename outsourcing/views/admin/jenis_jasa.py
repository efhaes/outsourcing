from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from outsourcing.decorators import admin_required
from outsourcing.models import JenisJasa
from outsourcing.forms.perusahaan_forms import JenisJasaForm


@admin_required
def jenis_jasa_list(request):
    """Daftar semua jenis jasa."""
    jenis_jasa_list = JenisJasa.objects.all()
    context = {
        'jenis_jasa_list': jenis_jasa_list,
        'page_title'     : 'Manajemen Jenis Jasa',
    }
    return render(request, 'admin/jenis_jasa/list.html', context)


@admin_required
def jenis_jasa_create(request):
    """Tambah jenis jasa baru."""
    if request.method == 'POST':
        form = JenisJasaForm(request.POST)
        if form.is_valid():
            jasa = form.save()
            messages.success(request, f'Jenis jasa "{jasa.nama_jasa}" berhasil ditambahkan.')
            return redirect('admin_jenis_jasa_list')
    else:
        form = JenisJasaForm()

    context = {
        'form'      : form,
        'page_title': 'Tambah Jenis Jasa',
        'action'    : 'Tambah',
    }
    return render(request, 'admin/jenis_jasa/form.html', context)


@admin_required
def jenis_jasa_edit(request, pk):
    """Edit jenis jasa."""
    jasa = get_object_or_404(JenisJasa, pk=pk)
    if request.method == 'POST':
        form = JenisJasaForm(request.POST, instance=jasa)
        if form.is_valid():
            form.save()
            messages.success(request, f'Jenis jasa "{jasa.nama_jasa}" berhasil diperbarui.')
            return redirect('admin_jenis_jasa_list')
    else:
        form = JenisJasaForm(instance=jasa)

    context = {
        'form'      : form,
        'jasa'      : jasa,
        'page_title': f'Edit — {jasa.nama_jasa}',
        'action'    : 'Simpan Perubahan',
    }
    return render(request, 'admin/jenis_jasa/form.html', context)


@admin_required
def jenis_jasa_delete(request, pk):
    """Nonaktifkan jenis jasa."""
    jasa = get_object_or_404(JenisJasa, pk=pk)
    if request.method == 'POST':
        nama = jasa.nama_jasa
        jasa.is_active = False
        jasa.save()
        messages.success(request, f'Jenis jasa "{nama}" berhasil dinonaktifkan.')
        return redirect('admin_jenis_jasa_list')

    context = {
        'jasa'      : jasa,
        'page_title': f'Hapus — {jasa.nama_jasa}',
    }
    return render(request, 'admin/jenis_jasa/confirm_delete.html', context)