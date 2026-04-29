from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from outsourcing.decorators import kepala_supervisor_required
from outsourcing.models import AreaKerja, SubArea, KepalaSupervisorJasa, Perusahaan


@kepala_supervisor_required
def area_list(request):
    """Daftar area kerja dari perusahaan yang menggunakan jasa kepala supervisor."""
    q = request.GET.get('q', '').strip()
    
    # Jenis jasa yang dipegang kepala supervisor ini
    jasa_ids = KepalaSupervisorJasa.objects.filter(
        kepala_supervisor=request.user
    ).values_list('jenis_jasa_id', flat=True)
    
    # Perusahaan yang menggunakan jasa tersebut
    if jasa_ids:
        perusahaan_ids = Perusahaan.objects.filter(
            jenis_jasa__in=jasa_ids,
            is_active=True
        ).values_list('pk', flat=True)
    else:
        # Fallback: jika belum ada jasa, tampilkan semua perusahaan aktif
        perusahaan_ids = Perusahaan.objects.filter(is_active=True).values_list('pk', flat=True)
    
    area_qs = AreaKerja.objects.filter(
        perusahaan_id__in=perusahaan_ids,
        is_active=True
    ).select_related('perusahaan').order_by('perusahaan__nama_perusahaan', 'nama_area')
    
    if q:
        area_qs = area_qs.filter(
            Q(nama_area__icontains=q) | Q(perusahaan__nama_perusahaan__icontains=q)
        )
    
    context = {
        'area_list': area_qs,
        'q': q,
        'page_title': 'Area Kerja',
    }
    return render(request, 'kepala_supervisor/area_kerja/list.html', context)


@kepala_supervisor_required
def area_create(request):
    """Kepala supervisor membuat area kerja baru."""
    # Jenis jasa yang dipegang kepala supervisor ini
    jasa_ids = KepalaSupervisorJasa.objects.filter(
        kepala_supervisor=request.user
    ).values_list('jenis_jasa_id', flat=True)
    
    # Perusahaan yang menggunakan jasa tersebut
    if jasa_ids:
        perusahaan_qs = Perusahaan.objects.filter(
            jenis_jasa__in=jasa_ids,
            is_active=True
        )
    else:
        # Fallback: jika belum ada jasa, tampilkan semua perusahaan aktif
        perusahaan_qs = Perusahaan.objects.filter(is_active=True)
    
    from outsourcing.forms.perusahaan_forms import AreaKerjaForm
    
    if request.method == 'POST':
        form = AreaKerjaForm(request.POST, perusahaan_qs=perusahaan_qs)
        if form.is_valid():
            area = form.save(commit=False)
            area.is_active = True
            area.save()
            messages.success(request, f'Area "{area.nama_area}" berhasil dibuat.')
            return redirect('kepala_area_list')
    else:
        form = AreaKerjaForm(perusahaan_qs=perusahaan_qs)
    
    context = {
        'form': form,
        'page_title': 'Tambah Area Kerja',
        'action': 'Buat Area',
    }
    return render(request, 'kepala_supervisor/area_kerja/form.html', context)


@kepala_supervisor_required
def area_edit(request, pk):
    """Edit area kerja."""
    # Jenis jasa yang dipegang kepala supervisor ini
    jasa_ids = KepalaSupervisorJasa.objects.filter(
        kepala_supervisor=request.user
    ).values_list('jenis_jasa_id', flat=True)
    
    # Perusahaan yang menggunakan jasa tersebut
    if jasa_ids:
        perusahaan_ids = Perusahaan.objects.filter(
            jenis_jasa__in=jasa_ids,
            is_active=True
        ).values_list('pk', flat=True)
    else:
        # Fallback: jika belum ada jasa, tampilkan semua perusahaan aktif
        perusahaan_ids = Perusahaan.objects.filter(is_active=True).values_list('pk', flat=True)
    
    area = get_object_or_404(AreaKerja, pk=pk, perusahaan_id__in=perusahaan_ids)
    
    from outsourcing.forms.perusahaan_forms import AreaKerjaForm
    
    perusahaan_qs = Perusahaan.objects.filter(pk__in=perusahaan_ids,is_active=True)
    
    if request.method == 'POST':
        form = AreaKerjaForm(request.POST, instance=area, perusahaan_qs=perusahaan_qs)
        if form.is_valid():
            form.save()
            messages.success(request, f'Area "{area.nama_area}" berhasil diperbarui.')
            return redirect('kepala_area_list')
    else:
        form = AreaKerjaForm(instance=area, perusahaan_qs=perusahaan_qs)
    
    context = {
        'form': form,
        'area': area,
        'page_title': f'Edit Area — {area.nama_area}',
        'action': 'Simpan Perubahan',
    }
    return render(request, 'kepala_supervisor/area_kerja/form.html', context)


@kepala_supervisor_required
def area_delete(request, pk):
    """Hapus / nonaktifkan area kerja."""
    # Jenis jasa yang dipegang kepala supervisor ini
    jasa_ids = KepalaSupervisorJasa.objects.filter(
        kepala_supervisor=request.user
    ).values_list('jenis_jasa_id', flat=True)
    
    if jasa_ids:
        perusahaan_ids = Perusahaan.objects.filter(
            jenis_jasa__in=jasa_ids,
            is_active=True
        ).values_list('pk', flat=True)
    else:
        
        perusahaan_ids = Perusahaan.objects.filter(is_active=True).values_list('pk', flat=True)
    
    area = get_object_or_404(AreaKerja, pk=pk, perusahaan_id__in=perusahaan_ids)
    
    if request.method == 'POST':
        area.is_active = False
        area.save()
        messages.success(request, f'Area "{area.nama_area}" berhasil dinonaktifkan.')
        return redirect('kepala_area_list')
    
    context = {
        'area': area,
        'page_title': f'Hapus Area — {area.nama_area}',
    }
    return render(request, 'kepala_supervisor/area_kerja/confirm_delete.html', context)
