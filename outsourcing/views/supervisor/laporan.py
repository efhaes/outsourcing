from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from outsourcing.decorators import supervisor_required
from outsourcing.models import LaporanKegiatan, StatusLaporan
from outsourcing.forms.laporan_forms import LaporanKegiatanForm


@supervisor_required
def laporan_list(request):
    q      = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    laporan = LaporanKegiatan.objects.filter(
        supervisor=request.user
    ).select_related('perusahaan', 'jenis_jasa', 'area').order_by('-tanggal_laporan')

    if q:
        laporan = laporan.filter(
            Q(nama_laporan__icontains=q) |
            Q(perusahaan__nama_perusahaan__icontains=q)
        )
    if status:
        laporan = laporan.filter(status=status)

    context = {
        'laporan_list'  : laporan,
        'status_choices': StatusLaporan.choices,
        'filter_status' : status,
        'q'             : q,
        'page_title'    : 'Laporan Kegiatan Saya',
    }
    return render(request, 'supervisor/laporan/list.html', context)


@supervisor_required
def laporan_create(request):
    if request.method == 'POST':
        form = LaporanKegiatanForm(request.POST, supervisor=request.user)
        if form.is_valid():
            laporan = form.save(commit=False)
            laporan.supervisor = request.user
            laporan.status = StatusLaporan.DRAFT
            laporan.save()
            messages.success(request, f'Laporan "{laporan.nama_laporan}" berhasil dibuat.')
            return redirect('supervisor_laporan_detail', pk=laporan.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Error {field}: {error}')
    else:
        form = LaporanKegiatanForm(supervisor=request.user)

    context = {
        'form'      : form,
        'page_title': 'Buat Laporan Baru',
        'action'    : 'Buat Laporan',
    }
    return render(request, 'supervisor/laporan/form.html', context)


@supervisor_required
def laporan_detail(request, pk):
    laporan = get_object_or_404(LaporanKegiatan, pk=pk, supervisor=request.user)
    item_list = laporan.item_kegiatan.select_related('sub_area').prefetch_related('staff').order_by('tanggal', 'jam_mulai')

    stats = {
        'total'      : item_list.count(),
        'terjadwal'  : item_list.filter(status='terjadwal').count(),
        'on_progress': item_list.filter(status='on_progress').count(),
        'selesai'    : item_list.filter(status='selesai').count(),
        'insidental' : item_list.filter(is_insidental=True).count(),
    }

    context = {
        'laporan'   : laporan,
        'item_list' : item_list,
        'stats'     : stats,
        'page_title': f'{laporan.nama_laporan}',
    }
    return render(request, 'supervisor/laporan/detail.html', context)


@supervisor_required
def laporan_edit(request, pk):
    laporan = get_object_or_404(LaporanKegiatan, pk=pk, supervisor=request.user)

    # ✅ Hanya draft yang bisa diedit
    if laporan.status != StatusLaporan.DRAFT:
        messages.error(request, 'Laporan yang sudah selesai atau dikirim tidak bisa diedit.')
        return redirect('supervisor_laporan_detail', pk=pk)

    if request.method == 'POST':
        form = LaporanKegiatanForm(request.POST, instance=laporan, supervisor=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Laporan "{laporan.nama_laporan}" berhasil diperbarui.')
            return redirect('supervisor_laporan_detail', pk=pk)
    else:
        form = LaporanKegiatanForm(instance=laporan, supervisor=request.user)

    context = {
        'form'      : form,
        'laporan'   : laporan,
        'page_title': f'Edit Laporan — {laporan.nama_laporan}',
        'action'    : 'Simpan Perubahan',
    }
    return render(request, 'supervisor/laporan/form.html', context)


@supervisor_required
def laporan_delete(request, pk):
    laporan = get_object_or_404(LaporanKegiatan, pk=pk, supervisor=request.user)

    if laporan.status != StatusLaporan.DRAFT:
        messages.error(request, 'Hanya laporan berstatus Draft yang bisa dihapus.')
        return redirect('supervisor_laporan_detail', pk=pk)

    if request.method == 'POST':
        nama = laporan.nama_laporan
        laporan.delete()
        messages.success(request, f'Laporan "{nama}" berhasil dihapus.')
        return redirect('supervisor_laporan_list')

    context = {
        'laporan'   : laporan,
        'page_title': f'Hapus Laporan — {laporan.nama_laporan}',
    }
    return render(request, 'supervisor/laporan/confirm_delete.html', context)


@supervisor_required
def laporan_selesai(request, pk):
    """Ubah status laporan dari draft → selesai via AJAX."""
    laporan = get_object_or_404(LaporanKegiatan, pk=pk, supervisor=request.user)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method tidak diizinkan.'}, status=405)

    # ✅ Diperbaiki: cek draft, bukan aktif
    if laporan.status != StatusLaporan.DRAFT:
        return JsonResponse({
            'success': False,
            'message': 'Laporan harus berstatus Draft untuk diselesaikan.'
        }, status=400)

    laporan.status = StatusLaporan.SELESAI
    laporan.save()

    return JsonResponse({
        'success': True,
        'message': f'Laporan "{laporan.nama_laporan}" berhasil diselesaikan.'
    })


@supervisor_required
def laporan_kirim(request, pk):
    """Ubah status laporan menjadi 'dikirim_customer'."""
    laporan = get_object_or_404(LaporanKegiatan, pk=pk, supervisor=request.user)

    if laporan.status != StatusLaporan.SELESAI:
        messages.error(request, 'Laporan harus berstatus Selesai sebelum dikirim ke customer.')
        return redirect('supervisor_laporan_detail', pk=pk)

    if request.method == 'POST':
        laporan.status = StatusLaporan.DIKIRIM_CUSTOMER
        laporan.save()
        messages.success(request, f'Laporan "{laporan.nama_laporan}" berhasil dikirim ke customer.')
        return redirect('supervisor_laporan_detail', pk=pk)

    context = {
        'laporan'   : laporan,
        'page_title': f'Kirim Laporan — {laporan.nama_laporan}',
    }
    return render(request, 'supervisor/laporan/confirm_kirim.html', context)