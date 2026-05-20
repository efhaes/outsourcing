from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q

from outsourcing.decorators import staff_required
from outsourcing.models import IzinStaff, StatusIzinChoices
from outsourcing.forms.absensi import IzinStaffForm
from django.urls import reverse


@staff_required
def izin_submit(request):
    if request.method == 'POST':
        form = IzinStaffForm(request.POST, request.FILES)
        if form.is_valid():
            izin = form.save(commit=False)
            izin.staff  = request.user
            izin.status = StatusIzinChoices.PENDING

            overlap = IzinStaff.objects.filter(
                staff=request.user,
                status__in=[StatusIzinChoices.PENDING, StatusIzinChoices.APPROVED],
            ).filter(
                Q(tanggal_mulai__lte=izin.tanggal_selesai) &
                Q(tanggal_selesai__gte=izin.tanggal_mulai)
            )
            if overlap.exists():
                form.add_error(None, 'Kamu sudah memiliki izin pada rentang tanggal tersebut.')
            else:
                izin.save()
                messages.success(request, 'Pengajuan izin berhasil dikirim. Menunggu persetujuan supervisor.')
                return redirect(reverse('staff_absensi_riwayat') + '?tab=izin')
    else:
        form = IzinStaffForm()

    return render(request, 'staff/izin/submit.html', {'form': form})


@staff_required
def izin_batal(request, pk):
    izin = get_object_or_404(IzinStaff, pk=pk, staff=request.user)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method != 'POST':
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Request tidak valid.'}, status=400)
        messages.error(request, 'Request tidak valid.')
        return redirect(reverse('staff_absensi_riwayat') + '?tab=izin')

    if izin.status != StatusIzinChoices.PENDING:
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Hanya izin pending yang bisa dibatalkan.'})
        messages.error(request, 'Hanya izin dengan status pending yang bisa dibatalkan.')
        return redirect(reverse('staff_absensi_riwayat') + '?tab=izin')

    izin.delete()

    if is_ajax:
        return JsonResponse({'success': True})

    messages.success(request, 'Pengajuan izin berhasil dibatalkan.')
    return redirect(reverse('staff_absensi_riwayat') + '?tab=izin')


@staff_required
def izin_detail(request, pk):
    """Detail satu izin."""
    izin = get_object_or_404(IzinStaff, pk=pk, staff=request.user)
    return render(request, 'staff/izin/detail.html', {'izin': izin})

