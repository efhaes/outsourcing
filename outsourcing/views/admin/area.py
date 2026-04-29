from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from outsourcing.decorators import admin_required
from outsourcing.models import Perusahaan, AreaKerja, SubArea
from outsourcing.forms.perusahaan_forms import AreaKerjaForm, SubAreaForm


# ============================================================
# AREA KERJA
# ============================================================

@admin_required
def area_list(request, perusahaan_pk):
    """Daftar area kerja milik satu perusahaan."""
    perusahaan = get_object_or_404(Perusahaan, pk=perusahaan_pk)
    area_list  = AreaKerja.objects.filter(
        perusahaan=perusahaan
    ).prefetch_related('sub_area').order_by('nama_area')

    context = {
        'perusahaan': perusahaan,
        'area_list' : area_list,
        'page_title': f'Area Kerja — {perusahaan.nama_perusahaan}',
    }
    return render(request, 'admin/area/list.html', context)


@admin_required
def area_create(request, perusahaan_pk):
    """Tambah area kerja baru untuk perusahaan tertentu."""
    perusahaan = get_object_or_404(Perusahaan, pk=perusahaan_pk)

    if request.method == 'POST':
        form = AreaKerjaForm(request.POST)
        if form.is_valid():
            area            = form.save(commit=False)
            area.perusahaan = perusahaan
            area.save()
            messages.success(request, f'Area "{area.nama_area}" berhasil ditambahkan.')
            return redirect('admin_area_list', perusahaan_pk=perusahaan.pk)
    else:
        form = AreaKerjaForm()

    context = {
        'form'      : form,
        'perusahaan': perusahaan,
        'page_title': f'Tambah Area — {perusahaan.nama_perusahaan}',
        'action'    : 'Tambah',
    }
    return render(request, 'admin/area/form.html', context)


@admin_required
def area_edit(request, pk):
    """Edit area kerja."""
    area = get_object_or_404(AreaKerja, pk=pk)

    if request.method == 'POST':
        form = AreaKerjaForm(request.POST, instance=area)
        if form.is_valid():
            form.save()
            messages.success(request, f'Area "{area.nama_area}" berhasil diperbarui.')
            return redirect('admin_area_list', perusahaan_pk=area.perusahaan.pk)
    else:
        form = AreaKerjaForm(instance=area)

    context = {
        'form'      : form,
        'area'      : area,
        'page_title': f'Edit Area — {area.nama_area}',
        'action'    : 'Simpan Perubahan',
    }
    return render(request, 'admin/area/form.html', context)


@admin_required
def area_delete(request, pk):
    """Soft delete area kerja. Hanya menerima POST."""
    if request.method != 'POST':
        area = get_object_or_404(AreaKerja, pk=pk)
        return redirect('admin_area_list', perusahaan_pk=area.perusahaan.pk)

    area          = get_object_or_404(AreaKerja, pk=pk)
    perusahaan_pk = area.perusahaan.pk
    nama          = area.nama_area
    area.is_active = False
    area.save(update_fields=['is_active'])
    messages.success(request, f'Area "{nama}" berhasil dinonaktifkan.')
    return redirect('admin_area_list', perusahaan_pk=perusahaan_pk)


# ============================================================
# SUB AREA
# ============================================================

@admin_required
def subarea_create(request, area_pk):
    """Tambah sub area baru untuk area tertentu."""
    area = get_object_or_404(AreaKerja, pk=area_pk)

    if request.method == 'POST':
        form = SubAreaForm(request.POST)
        if form.is_valid():
            subarea      = form.save(commit=False)
            subarea.area = area
            subarea.save()
            messages.success(request, f'Sub area "{subarea.nama_sub_area}" berhasil ditambahkan.')
            return redirect('admin_area_list', perusahaan_pk=area.perusahaan.pk)
    else:
        form = SubAreaForm()

    context = {
        'form'      : form,
        'area'      : area,
        'page_title': f'Tambah Sub Area — {area.nama_area}',
        'action'    : 'Tambah',
    }
    return render(request, 'admin/area/form_subarea.html', context)


@admin_required
def subarea_edit(request, pk):
    """Edit sub area."""
    subarea = get_object_or_404(SubArea, pk=pk)

    if request.method == 'POST':
        form = SubAreaForm(request.POST, instance=subarea)
        if form.is_valid():
            form.save()
            messages.success(request, f'Sub area "{subarea.nama_sub_area}" berhasil diperbarui.')
            return redirect('admin_area_list', perusahaan_pk=subarea.area.perusahaan.pk)
    else:
        form = SubAreaForm(instance=subarea)

    context = {
        'form'      : form,
        'subarea'   : subarea,
        'page_title': f'Edit Sub Area — {subarea.nama_sub_area}',
        'action'    : 'Simpan Perubahan',
    }
    return render(request, 'admin/area/form_subarea.html', context)


@admin_required
def subarea_delete(request, pk):
    """Soft delete sub area. Hanya menerima POST."""
    if request.method != 'POST':
        subarea = get_object_or_404(SubArea, pk=pk)
        return redirect('admin_area_list', perusahaan_pk=subarea.area.perusahaan.pk)

    subarea          = get_object_or_404(SubArea, pk=pk)
    perusahaan_pk    = subarea.area.perusahaan.pk
    nama             = subarea.nama_sub_area
    subarea.is_active = False
    subarea.save(update_fields=['is_active'])
    messages.success(request, f'Sub area "{nama}" berhasil dinonaktifkan.')
    return redirect('admin_area_list', perusahaan_pk=perusahaan_pk)