from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from outsourcing.decorators import admin_required
from outsourcing.models import Perusahaan, AreaKerja
from outsourcing.forms.perusahaan_forms import PerusahaanForm


@admin_required
def perusahaan_list(request):
    """Daftar semua perusahaan."""
    q          = request.GET.get('q', '').strip()
    perusahaan = Perusahaan.objects.prefetch_related('jenis_jasa').order_by('nama_perusahaan')

    if q:
        perusahaan = perusahaan.filter(nama_perusahaan__icontains=q)

    context = {
        'perusahaan_list': perusahaan,
        'q'              : q,
        'page_title'     : 'Manajemen Perusahaan',
    }
    return render(request, 'admin/perusahaan/list.html', context)


@admin_required
def perusahaan_create(request):
    """Tambah perusahaan baru."""
    if request.method == 'POST':
        # TAMBAHKAN request.FILES di sini
        form = PerusahaanForm(request.POST, request.FILES) 
        if form.is_valid():
            perusahaan = form.save()
            messages.success(request, f'Perusahaan "{perusahaan.nama_perusahaan}" berhasil ditambahkan.')
            return redirect('admin_perusahaan_list')
    else:
        form = PerusahaanForm()

    context = {
        'form'      : form,
        'page_title': 'Tambah Perusahaan',
        'action'    : 'Tambah',
    }
    return render(request, 'admin/perusahaan/form.html', context)

@admin_required
def perusahaan_detail(request, pk):
    """Detail perusahaan beserta area dan subarea-nya."""
    perusahaan = get_object_or_404(
        Perusahaan.objects.prefetch_related('jenis_jasa'),
        pk=pk,
    )
    area_list = AreaKerja.objects.filter(
        perusahaan=perusahaan
    ).prefetch_related('sub_area').order_by('nama_area')

    context = {
        'perusahaan': perusahaan,
        'area_list' : area_list,
        'page_title': f'Detail — {perusahaan.nama_perusahaan}',
    }
    return render(request, 'admin/perusahaan/detail.html', context)


@admin_required
def perusahaan_edit(request, pk):
    """Edit data perusahaan."""
    perusahaan = get_object_or_404(Perusahaan, pk=pk)

    if request.method == 'POST':
        # TAMBAHKAN request.FILES di sini
        form = PerusahaanForm(request.POST, request.FILES, instance=perusahaan)
        if form.is_valid():
            form.save()
            messages.success(request, f'Perusahaan "{perusahaan.nama_perusahaan}" berhasil diperbarui.')
            return redirect('admin_perusahaan_list')
    else:
        form = PerusahaanForm(instance=perusahaan)

    context = {
        'form'      : form,
        'perusahaan': perusahaan,
        'page_title': f'Edit — {perusahaan.nama_perusahaan}',
        'action'    : 'Simpan Perubahan',
    }
    return render(request, 'admin/perusahaan/form.html', context)

@admin_required
def perusahaan_delete(request, pk):
    """Soft delete perusahaan (set is_active=False). Hanya menerima POST."""
    if request.method != 'POST':
        return redirect('admin_perusahaan_list')

    perusahaan = get_object_or_404(Perusahaan, pk=pk)
    nama = perusahaan.nama_perusahaan
    perusahaan.is_active = False
    perusahaan.save(update_fields=['is_active'])
    messages.success(request, f'Perusahaan "{nama}" berhasil dinonaktifkan.')
    return redirect('admin_perusahaan_list')