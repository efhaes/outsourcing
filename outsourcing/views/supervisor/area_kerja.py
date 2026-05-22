from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from outsourcing.decorators import kepala_supervisor_required
from outsourcing.models import AreaKerja, Perusahaan

from outsourcing.decorators import supervisor_or_kepala_required
from outsourcing.models import AreaKerja, SupervisorPerusahaan

def _get_supervisor(request):
    if request.user.role == 'supervisor':
        return request.user
    return request.supervisor_context


@supervisor_or_kepala_required
def area_list(request):
    supervisor = _get_supervisor(request)
    q = request.GET.get('q', '').strip()

    # Area yang boleh diakses — filter via perusahaan supervisor
    perusahaan_ids = SupervisorPerusahaan.objects.filter(
        supervisor=supervisor,
        is_active=True,
    ).values_list('perusahaan_id', flat=True)

    area_qs = AreaKerja.objects.filter(
        perusahaan_id__in=perusahaan_ids,
        is_active=True,
    ).select_related('perusahaan', 'supervisor').order_by('perusahaan__nama_perusahaan', 'nama_area')

    if q:
        area_qs = area_qs.filter(
            Q(nama_area__icontains=q) | Q(perusahaan__nama_perusahaan__icontains=q)
        )

    context = {
        'area_list' : area_qs,
        'q'         : q,
        'page_title': 'Area Kerja',
    }
    return render(request, 'supervisor/area_kerja/list.html', context)


@supervisor_or_kepala_required
def area_create(request):
    supervisor = _get_supervisor(request)

    perusahaan_ids = SupervisorPerusahaan.objects.filter(
        supervisor=supervisor,
        is_active=True,
    ).values_list('perusahaan_id', flat=True)

    perusahaan_qs = Perusahaan.objects.filter(pk__in=perusahaan_ids, is_active=True)

    from outsourcing.forms.perusahaan_forms import AreaKerjaForm

    if request.method == 'POST':
        form = AreaKerjaForm(request.POST, perusahaan_qs=perusahaan_qs)
        if form.is_valid():
            area = form.save(commit=False)
            area.supervisor = supervisor  # ← otomatis assign supervisor yang login
            area.is_active  = True
            area.save()
            messages.success(request, f'Area "{area.nama_area}" berhasil dibuat.')
            return redirect('supervisor_area_list')
    else:
        form = AreaKerjaForm(perusahaan_qs=perusahaan_qs)

    context = {
        'form'      : form,
        'page_title': 'Tambah Area Kerja',
        'action'    : 'Buat Area',
    }
    return render(request, 'supervisor/area_kerja/form.html', context)


@supervisor_or_kepala_required
def area_edit(request, pk):
    supervisor = _get_supervisor(request)

    perusahaan_ids = SupervisorPerusahaan.objects.filter(
        supervisor=supervisor,
        is_active=True,
    ).values_list('perusahaan_id', flat=True)

    area          = get_object_or_404(AreaKerja, pk=pk, perusahaan_id__in=perusahaan_ids)
    perusahaan_qs = Perusahaan.objects.filter(pk__in=perusahaan_ids, is_active=True)

    from outsourcing.forms.perusahaan_forms import AreaKerjaForm

    if request.method == 'POST':
        form = AreaKerjaForm(request.POST, instance=area, perusahaan_qs=perusahaan_qs)
        if form.is_valid():
            form.save()
            messages.success(request, f'Area "{area.nama_area}" berhasil diperbarui.')
            return redirect('supervisor_area_list')
    else:
        form = AreaKerjaForm(instance=area, perusahaan_qs=perusahaan_qs)

    context = {
        'form'      : form,
        'area'      : area,
        'page_title': f'Edit Area — {area.nama_area}',
        'action'    : 'Simpan Perubahan',
    }
    return render(request, 'supervisor/area_kerja/form.html', context)


@supervisor_or_kepala_required
def area_delete(request, pk):
    supervisor = _get_supervisor(request)

    perusahaan_ids = SupervisorPerusahaan.objects.filter(
        supervisor=supervisor,
        is_active=True,
    ).values_list('perusahaan_id', flat=True)

    area = get_object_or_404(AreaKerja, pk=pk, perusahaan_id__in=perusahaan_ids)

    if request.method == 'POST':
        area.is_active = False
        area.save()
        messages.success(request, f'Area "{area.nama_area}" berhasil dinonaktifkan.')
        return redirect('supervisor_area_list')

    context = {
        'area'      : area,
        'page_title': f'Hapus Area — {area.nama_area}',
    }
    return render(request, 'supervisor/area_kerja/confirm_delete.html', context)