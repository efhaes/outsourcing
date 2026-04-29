from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from outsourcing.decorators import supervisor_required
from outsourcing.models import AreaKerja, SubArea, SupervisorPerusahaan
from outsourcing.forms.perusahaan_forms import SubAreaForm
from django.db.models import Q
from django.shortcuts import render
from django.contrib import messages


@supervisor_required
def subarea_list(request, area_pk=None):
    q = request.GET.get('q', '').strip()

    # Perusahaan supervisor
    perusahaan_ids = SupervisorPerusahaan.objects.filter(
        supervisor=request.user,
        is_active=True
    ).values_list('perusahaan_id', flat=True)

    # Area yang boleh diakses
    area_qs = AreaKerja.objects.filter(
        perusahaan_id__in=perusahaan_ids,
        is_active=True
    )

    # Kalau supervisor belum punya akses
    if not area_qs.exists():
        messages.warning(request, "Anda belum memiliki area. Hubungi admin.")
    
    # Subarea
    subarea_qs = SubArea.objects.filter(
        area__in=area_qs,
        is_active=True
    ).select_related('area', 'area__perusahaan')

    # Filter area
    if area_pk:
        if not area_qs.filter(pk=area_pk).exists():
            messages.error(request, "Area tidak valid atau bukan akses Anda.")
            subarea_qs = SubArea.objects.none()
        else:
            subarea_qs = subarea_qs.filter(area_id=area_pk)

    # Search
    if q:
        subarea_qs = subarea_qs.filter(
            Q(nama_sub_area__icontains=q) |
            Q(area__nama_area__icontains=q)
        )

    context = {
        'subarea_list': subarea_qs.order_by(
            'area__perusahaan__nama_perusahaan',
            'area__nama_area',
            'nama_sub_area'
        ),
        'area_list': area_qs,
        'q': q,
        'area_pk': area_pk,
        'page_title': 'Sub Area',
    }

    return render(request, 'supervisor/area_kerja/subarea_list.html', context)


@supervisor_required
def subarea_create(request, area_pk=None):
    # Perusahaan supervisor
    perusahaan_ids = SupervisorPerusahaan.objects.filter(
        supervisor=request.user,
        is_active=True
    ).values_list('perusahaan_id', flat=True)

    # Area yang boleh diakses
    area_qs = AreaKerja.objects.filter(
        perusahaan_id__in=perusahaan_ids,
        is_active=True
    )

    if not area_qs.exists():
        messages.error(request, "Anda belum punya akses area.")
        return redirect('supervisor_subarea_list')

    if request.method == 'POST':
        form = SubAreaForm(request.POST, area_qs=area_qs)

        if form.is_valid():
            subarea = form.save(commit=False)
            subarea.is_active = True
            subarea.save()

            messages.success(
                request,
                f'Sub Area "{subarea.nama_sub_area}" berhasil dibuat.'
            )

            return redirect(
                'supervisor_subarea_by_area',
                area_pk=subarea.area_id
            )
    else:
        form = SubAreaForm(area_qs=area_qs)

        if area_pk and area_qs.filter(pk=area_pk).exists():
            form.fields['area'].initial = area_pk

    return render(request, 'supervisor/area_kerja/subarea_form.html', {
        'form': form,
        'page_title': 'Tambah Sub Area',
        'action': 'Buat Sub Area',
    })


@supervisor_required
def subarea_edit(request, pk):
    """Edit sub area."""
    perusahaan_ids = SupervisorPerusahaan.objects.filter(
        supervisor=request.user,
        is_active=True
    ).values_list('perusahaan_id', flat=True)
    
    area_ids = list(AreaKerja.objects.filter(
        perusahaan_id__in=perusahaan_ids,
        is_active=True
    ).values_list('pk', flat=True))
    
    subarea = get_object_or_404(SubArea, pk=pk, area_id__in=area_ids)
    
    area_qs = AreaKerja.objects.filter(pk__in=area_ids,is_active=True)
    
    if request.method == 'POST':
        form = SubAreaForm(request.POST, instance=subarea, area_qs=area_qs)
        if form.is_valid():
            # Validasi tambahan: pastikan area yang dipilih termasuk dalam akses supervisor
            if form.cleaned_data.get('area').id not in area_ids:
                messages.error(request, 'Area yang dipilih tidak dalam akses Anda.')
                return render(request, 'supervisor/area_kerja/subarea_form.html', {
                    'form': form,
                    'subarea': subarea,
                    'page_title': f'Edit Sub Area — {subarea.nama_sub_area}',
                    'action': 'Simpan Perubahan',
                })
            form.save()
            messages.success(request, f'Sub Area "{subarea.nama_sub_area}" berhasil diperbarui.')
            # Redirect ke list dengan filter area yang dipilih
            return redirect('supervisor_subarea_list', area_pk=subarea.area_id)
    else:
        form = SubAreaForm(instance=subarea, area_qs=area_qs)
    
    context = {
        'form': form,
        'subarea': subarea,
        'page_title': f'Edit Sub Area — {subarea.nama_sub_area}',
        'action': 'Simpan Perubahan',
    }
    return render(request, 'supervisor/area_kerja/subarea_form.html', context)


@supervisor_required
def subarea_delete(request, pk):
    """Hapus / nonaktifkan sub area."""
    perusahaan_ids = SupervisorPerusahaan.objects.filter(
        supervisor=request.user,
        is_active=True
    ).values_list('perusahaan_id', flat=True)
    
    area_ids = AreaKerja.objects.filter(
        perusahaan_id__in=perusahaan_ids,
        is_active=True
    ).values_list('pk', flat=True)
    
    subarea = get_object_or_404(SubArea, pk=pk, area_id__in=area_ids)
    
    if request.method == 'POST':
        subarea.is_active = False
        subarea.save()
        messages.success(request, f'Sub Area "{subarea.nama_sub_area}" berhasil dinonaktifkan.')
        return redirect('supervisor_subarea_list')
    
    context = {
        'subarea': subarea,
        'page_title': f'Hapus Sub Area — {subarea.nama_sub_area}',
    }
    return render(request, 'supervisor/area_kerja/subarea_confirm_delete.html', context)
