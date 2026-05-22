from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from outsourcing.decorators import supervisor_required
from outsourcing.models import SubArea,SupervisorPerusahaan,Perusahaan
from outsourcing.forms.perusahaan_forms import SubAreaForm


@supervisor_required
def subarea_list(request):
    q = request.GET.get('q', '').strip()

    subarea_qs = SubArea.objects.filter(
        supervisor=request.user,
        is_active=True,
    ).select_related('area', 'area__perusahaan')

    if q:
        subarea_qs = subarea_qs.filter(
            Q(nama_sub_area__icontains=q) |
            Q(area__nama_area__icontains=q)
        )

    context = {
        'subarea_list': subarea_qs.order_by('nama_sub_area'),
        'q'           : q,
        'page_title'  : 'Sub Area',
    }
    return render(request, 'supervisor/sub_area/subarea_list.html', context)


@supervisor_required
def subarea_create(request):
    perusahaan_ids = SupervisorPerusahaan.objects.filter(
        supervisor=request.user, is_active=True,
    ).values_list('perusahaan_id', flat=True)

    perusahaan_qs = Perusahaan.objects.filter(pk__in=perusahaan_ids, is_active=True)

    if not perusahaan_qs.exists():
        messages.error(request, 'Anda belum ditugaskan ke perusahaan manapun.')
        return redirect('supervisor_subarea_list')

    if request.method == 'POST':
        form = SubAreaForm(request.POST, perusahaan_qs=perusahaan_qs)
        if form.is_valid():
            subarea = form.save(commit=False)
            subarea.supervisor = request.user
            subarea.is_active  = True
            subarea.save()
            messages.success(request, f'Sub Area "{subarea.nama_sub_area}" berhasil dibuat.')
            return redirect('supervisor_subarea_list')
    else:
        form = SubAreaForm(perusahaan_qs=perusahaan_qs)

    return render(request, 'supervisor/sub_area/subarea_form.html', {
        'form'      : form,
        'page_title': 'Tambah Sub Area',
        'action'    : 'Buat Sub Area',
    })


@supervisor_required
def subarea_edit(request, pk):
    subarea = get_object_or_404(SubArea, pk=pk, supervisor=request.user)

    perusahaan_ids = SupervisorPerusahaan.objects.filter(
        supervisor=request.user, is_active=True,
    ).values_list('perusahaan_id', flat=True)

    perusahaan_qs = Perusahaan.objects.filter(pk__in=perusahaan_ids, is_active=True)

    if request.method == 'POST':
        form = SubAreaForm(request.POST, instance=subarea, perusahaan_qs=perusahaan_qs)
        if form.is_valid():
            form.save()
            messages.success(request, f'Sub Area "{subarea.nama_sub_area}" berhasil diperbarui.')
            return redirect('supervisor_subarea_list')
    else:
        form = SubAreaForm(instance=subarea, perusahaan_qs=perusahaan_qs)

    context = {
        'form'      : form,
        'subarea'   : subarea,
        'page_title': f'Edit Sub Area — {subarea.nama_sub_area}',
        'action'    : 'Simpan Perubahan',
    }
    return render(request, 'supervisor/sub_area/subarea_form.html', context)





@supervisor_required
def subarea_delete(request, pk):
    subarea = get_object_or_404(SubArea, pk=pk, supervisor=request.user)

    if request.method == 'POST':
        subarea.is_active = False
        subarea.save()
        messages.success(request, f'Sub Area "{subarea.nama_sub_area}" berhasil dinonaktifkan.')
        return redirect('supervisor_subarea_list')

    context = {
        'subarea'   : subarea,
        'page_title': f'Hapus Sub Area — {subarea.nama_sub_area}',
    }
    return render(request, 'supervisor/sub_area/subarea_confirm_delete.html', context)