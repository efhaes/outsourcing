from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from outsourcing.decorators import supervisor_required
from outsourcing.models import LaporanKegiatan, ItemKegiatan, StaffTask
from outsourcing.forms.laporan_forms import ItemKegiatanForm


@supervisor_required
def item_create(request, laporan_pk):
    laporan = get_object_or_404(LaporanKegiatan, pk=laporan_pk, supervisor=request.user)

    if laporan.status not in ['draft', 'aktif']:
        messages.error(request, 'Tidak bisa menambah item pada laporan yang sudah selesai.')
        return redirect('supervisor_laporan_detail', pk=laporan_pk)

    if request.method == 'POST':
        form = ItemKegiatanForm(request.POST, laporan=laporan)
        if form.is_valid():
            item = form.save(commit=False)
            item.laporan = laporan
            item.save()
            form.save_m2m()  # Save ManyToMany relationships (staff)
            messages.success(request, f'Item "{item.nama_item}" berhasil ditambahkan.')
            return redirect('supervisor_laporan_detail', pk=laporan_pk)
    else:
        form = ItemKegiatanForm(laporan=laporan)

    # Build staff-task mapping for JavaScript
    staff_task_mapping = {}
    for staff in form.fields['staff'].queryset:
        task_ids = list(staff.tasks_saya.filter(is_active=True).values_list('task_id', flat=True))
        staff_task_mapping[str(staff.pk)] = task_ids

    context = {
        'form'      : form,
        'laporan'   : laporan,
        'page_title': f'Tambah Item — {laporan.nama_laporan}',
        'action'    : 'Tambah Item',
        'staff_task_mapping': staff_task_mapping,
    }
    return render(request, 'supervisor/item/form.html', context)


@supervisor_required
def item_edit(request, pk):
    item    = get_object_or_404(ItemKegiatan, pk=pk, laporan__supervisor=request.user)
    laporan = item.laporan

    if laporan.status not in ['draft', 'aktif']:
        messages.error(request, 'Tidak bisa mengedit item pada laporan yang sudah selesai.')
        return redirect('supervisor_laporan_detail', pk=laporan.pk)

    if request.method == 'POST':
        form = ItemKegiatanForm(request.POST, instance=item, laporan=laporan)
        if form.is_valid():
            form.save()
            messages.success(request, f'Item "{item.nama_item}" berhasil diperbarui.')
            return redirect('supervisor_laporan_detail', pk=laporan.pk)
    else:
        form = ItemKegiatanForm(instance=item, laporan=laporan)

    # Build staff-task mapping for JavaScript
    staff_task_mapping = {}
    for staff in form.fields['staff'].queryset:
        task_ids = list(staff.tasks_saya.filter(is_active=True).values_list('task_id', flat=True))
        staff_task_mapping[str(staff.pk)] = task_ids

    context = {
        'form'      : form,
        'item'      : item,
        'laporan'   : laporan,
        'page_title': f'Edit Item — {item.nama_item}',
        'action'    : 'Simpan Perubahan',
        'staff_task_mapping': staff_task_mapping,
    }
    return render(request, 'supervisor/item/form.html', context)


@supervisor_required
def item_delete(request, pk):
    item    = get_object_or_404(ItemKegiatan, pk=pk, laporan__supervisor=request.user)
    laporan = item.laporan

    if request.method == 'POST':
        nama = item.nama_item
        item.delete()
        messages.success(request, f'Item "{nama}" berhasil dihapus.')
        return redirect('supervisor_laporan_detail', pk=laporan.pk)

    context = {
        'item'      : item,
        'laporan'   : laporan,
        'page_title': f'Hapus Item — {item.nama_item}',
    }
    return render(request, 'supervisor/item/confirm_delete.html', context)